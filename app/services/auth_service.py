"""
Authentication Service
Business logic for authentication, registration, password reset, etc.
"""

import json
from datetime import datetime, timedelta
from typing import Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    hash_password,
    verify_password,
    check_password_strength,
    create_token_pair,
    hash_token,
    create_password_reset_token,
    create_email_verification_token,
    create_two_factor_code,
    generate_backup_codes,
    TokenPair,
    LOCKOUT_DURATION_MINUTES,
    MAX_FAILED_ATTEMPTS,
)
from app.db.models_auth import User, UserRole, UserSession, AuditLog


class AuthError(Exception):
    """Authentication error with status code."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthService:
    """Service for all authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # User Registration
    # =========================================================================
    
    async def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        client_id: UUID | None = None,
        role: UserRole = UserRole.AGENT,
        phone: str | None = None,
    ) -> Tuple[User, str]:
        """
        Register a new user.
        Returns (user, verification_token).
        """
        # Normalize email
        email = email.lower().strip()
        
        # Check email not taken
        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise AuthError("Email already registered", 409)
        
        # Validate password strength
        is_valid, errors = check_password_strength(password)
        if not is_valid:
            raise AuthError("; ".join(errors), 400)
        
        # Create verification token
        token, token_hash, expires = create_email_verification_token()
        
        # Create user
        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            client_id=client_id,
            role=role,
            phone=phone,
            is_active=True,
            is_verified=False,
            verification_token=token_hash,
            verification_token_expires=expires,
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # Audit log
        await self._log_action(
            user_id=user.id,
            client_id=client_id,
            action="user.registered",
            resource_type="user",
            resource_id=str(user.id),
        )
        
        return user, token
    
    async def verify_email(self, token: str) -> User:
        """Verify user email with token."""
        token_hash = hash_token(token)
        
        result = await self.db.execute(
            select(User).where(
                User.verification_token == token_hash,
                User.verification_token_expires > datetime.utcnow(),
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("Invalid or expired verification token", 400)
        
        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        user.verification_token = None
        user.verification_token_expires = None
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.email_verified",
            resource_type="user",
            resource_id=str(user.id),
        )
        
        return user
    
    async def resend_verification(self, email: str) -> str:
        """Resend verification email. Returns new token."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("User not found", 404)
        
        if user.is_verified:
            raise AuthError("Email already verified", 400)
        
        # Create new token
        token, token_hash, expires = create_email_verification_token()
        user.verification_token = token_hash
        user.verification_token_expires = expires
        
        await self.db.commit()
        
        return token
    
    # =========================================================================
    # Login / Logout
    # =========================================================================
    
    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        remember_me: bool = False,
    ) -> Tuple[User, TokenPair, str | None]:
        """
        Authenticate user and create session.
        Returns (user, tokens, two_factor_code) - 2FA code is None if not enabled.
        """
        email = email.lower().strip()
        
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("Invalid email or password", 401)
        
        # Check if locked
        if user.is_locked():
            minutes_left = (user.locked_until - datetime.utcnow()).seconds // 60 + 1
            raise AuthError(f"Account locked. Try again in {minutes_left} minutes.", 403)
        
        # Verify password
        if not verify_password(password, user.password_hash):
            await self._handle_failed_login(user)
            raise AuthError("Invalid email or password", 401)
        
        # Check if active
        if not user.is_active:
            raise AuthError("Account is disabled", 403)
        
        # Reset failed attempts on successful password
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Check 2FA
        two_factor_code = None
        if user.two_factor_enabled:
            code, code_hash, expires = create_two_factor_code()
            # Store temporarily (you'd send this via email/SMS)
            user.verification_token = code_hash  # Reusing field temporarily
            user.verification_token_expires = expires
            two_factor_code = code
            await self.db.commit()
            
            # Return without creating full session yet
            return user, None, two_factor_code
        
        # Create session and tokens
        tokens = await self._create_session(user, ip_address, user_agent, remember_me)
        
        # Update login info
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        user.login_count += 1
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.login",
            resource_type="session",
            ip_address=ip_address,
        )
        
        return user, tokens, None
    
    async def verify_two_factor(
        self,
        user_id: UUID,
        code: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        remember_me: bool = False,
    ) -> Tuple[User, TokenPair]:
        """Verify 2FA code and complete login."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("User not found", 404)
        
        # Verify code
        code_hash = hash_token(code)
        if (
            user.verification_token != code_hash or
            user.verification_token_expires < datetime.utcnow()
        ):
            raise AuthError("Invalid or expired 2FA code", 401)
        
        # Clear the temporary code
        user.verification_token = None
        user.verification_token_expires = None
        
        # Create session
        tokens = await self._create_session(user, ip_address, user_agent, remember_me)
        
        # Update login info
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        user.login_count += 1
        
        await self.db.commit()
        
        return user, tokens
    
    async def verify_backup_code(
        self,
        user_id: UUID,
        backup_code: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        remember_me: bool = False,
    ) -> Tuple[User, TokenPair]:
        """Verify 2FA backup code and complete login."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("User not found", 404)
        
        if not user.two_factor_backup_codes:
            raise AuthError("No backup codes configured", 400)
        
        # Check backup codes
        code_hash = hash_token(backup_code.lower().replace(" ", ""))
        backup_codes = json.loads(user.two_factor_backup_codes)
        
        if code_hash not in backup_codes:
            raise AuthError("Invalid backup code", 401)
        
        # Remove used code
        backup_codes.remove(code_hash)
        user.two_factor_backup_codes = json.dumps(backup_codes)
        
        # Clear any pending 2FA
        user.verification_token = None
        user.verification_token_expires = None
        
        # Create session
        tokens = await self._create_session(user, ip_address, user_agent, remember_me)
        
        # Update login info
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        user.login_count += 1
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.login_backup_code",
            resource_type="session",
            ip_address=ip_address,
            severity="warning",
        )
        
        return user, tokens
    
    async def logout(
        self,
        user_id: UUID,
        session_id: UUID,
        ip_address: str | None = None,
    ) -> None:
        """Invalidate current session."""
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        
        if session:
            session.is_valid = False
            session.invalidated_at = datetime.utcnow()
            session.invalidation_reason = "logout"
            await self.db.commit()
            
            await self._log_action(
                user_id=user_id,
                action="user.logout",
                resource_type="session",
                resource_id=str(session_id),
                ip_address=ip_address,
            )
    
    async def logout_all_sessions(
        self,
        user_id: UUID,
        except_session_id: UUID | None = None,
    ) -> int:
        """Invalidate all user sessions. Returns count."""
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_valid == True,
            )
        )
        sessions = result.scalars().all()
        
        count = 0
        for session in sessions:
            if except_session_id and session.id == except_session_id:
                continue
            session.is_valid = False
            session.invalidated_at = datetime.utcnow()
            session.invalidation_reason = "logout_all"
            count += 1
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user_id,
            action="user.logout_all",
            resource_type="session",
            description=f"Invalidated {count} sessions",
        )
        
        return count
    
    async def refresh_tokens(
        self,
        refresh_token_hash: str,
        ip_address: str | None = None,
    ) -> TokenPair:
        """Refresh access token using refresh token."""
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.refresh_token_hash == refresh_token_hash,
                UserSession.is_valid == True,
                UserSession.expires_at > datetime.utcnow(),
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise AuthError("Invalid or expired refresh token", 401)
        
        # Get user
        user_result = await self.db.execute(
            select(User).where(
                User.id == session.user_id,
                User.is_active == True,
            )
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise AuthError("User not found or inactive", 401)
        
        # Create new token pair
        tokens = create_token_pair(
            user_id=str(user.id),
            client_id=str(user.client_id) if user.client_id else None,
            role=user.role if isinstance(user.role, str) else user.role.value,
            session_id=str(session.id),
            remember_me=session.remember_me,
        )
        
        # Update session
        session.refresh_token_hash = hash_token(tokens.refresh_token)
        session.access_token_hash = hash_token(tokens.access_token)
        session.last_activity_at = datetime.utcnow()
        session.ip_address = ip_address
        
        await self.db.commit()
        
        return tokens
    
    # =========================================================================
    # Password Management
    # =========================================================================
    
    async def request_password_reset(self, email: str) -> str | None:
        """
        Request password reset.
        Returns token if user exists, None otherwise (for security).
        """
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Don't reveal if user exists
            return None
        
        # Create reset token
        token, token_hash, expires = create_password_reset_token()
        user.password_reset_token = token_hash
        user.password_reset_expires = expires
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.password_reset_requested",
            resource_type="user",
            resource_id=str(user.id),
        )
        
        return token
    
    async def reset_password(self, token: str, new_password: str) -> User:
        """Reset password using token."""
        token_hash = hash_token(token)
        
        result = await self.db.execute(
            select(User).where(
                User.password_reset_token == token_hash,
                User.password_reset_expires > datetime.utcnow(),
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("Invalid or expired reset token", 400)
        
        # Validate new password
        is_valid, errors = check_password_strength(new_password)
        if not is_valid:
            raise AuthError("; ".join(errors), 400)
        
        # Update password
        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.password_changed_at = datetime.utcnow()
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Invalidate all sessions
        await self.logout_all_sessions(user.id)
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.password_reset",
            resource_type="user",
            resource_id=str(user.id),
            severity="warning",
        )
        
        return user
    
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        logout_other_sessions: bool = True,
        current_session_id: UUID | None = None,
    ) -> User:
        """Change password for logged-in user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("User not found", 404)
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise AuthError("Current password is incorrect", 401)
        
        # Validate new password
        is_valid, errors = check_password_strength(new_password)
        if not is_valid:
            raise AuthError("; ".join(errors), 400)
        
        # Update password
        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        
        # Optionally invalidate other sessions
        if logout_other_sessions:
            await self.logout_all_sessions(user.id, except_session_id=current_session_id)
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.password_changed",
            resource_type="user",
            resource_id=str(user.id),
        )
        
        return user
    
    # =========================================================================
    # Two-Factor Authentication
    # =========================================================================
    
    async def enable_two_factor(self, user_id: UUID) -> Tuple[str, list[str]]:
        """
        Enable 2FA for user.
        Returns (secret, backup_codes).
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("User not found", 404)
        
        if user.two_factor_enabled:
            raise AuthError("2FA already enabled", 400)
        
        # Generate secret (for TOTP apps - simplified here)
        import secrets
        secret = secrets.token_hex(20)
        
        # Generate backup codes
        backup_pairs = generate_backup_codes(10)
        backup_codes_plain = [code for code, _ in backup_pairs]
        backup_codes_hashed = [hashed for _, hashed in backup_pairs]
        
        user.two_factor_secret = secret
        user.two_factor_backup_codes = json.dumps(backup_codes_hashed)
        user.two_factor_enabled = True
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.2fa_enabled",
            resource_type="user",
            resource_id=str(user.id),
        )
        
        return secret, backup_codes_plain
    
    async def disable_two_factor(self, user_id: UUID, password: str) -> User:
        """Disable 2FA (requires password confirmation)."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("User not found", 404)
        
        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid password", 401)
        
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.two_factor_backup_codes = None
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.2fa_disabled",
            resource_type="user",
            resource_id=str(user.id),
            severity="warning",
        )
        
        return user
    
    async def regenerate_backup_codes(self, user_id: UUID, password: str) -> list[str]:
        """Generate new backup codes (requires password)."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError("User not found", 404)
        
        if not user.two_factor_enabled:
            raise AuthError("2FA not enabled", 400)
        
        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid password", 401)
        
        # Generate new backup codes
        backup_pairs = generate_backup_codes(10)
        backup_codes_plain = [code for code, _ in backup_pairs]
        backup_codes_hashed = [hashed for _, hashed in backup_pairs]
        
        user.two_factor_backup_codes = json.dumps(backup_codes_hashed)
        
        await self.db.commit()
        
        await self._log_action(
            user_id=user.id,
            client_id=user.client_id,
            action="user.backup_codes_regenerated",
            resource_type="user",
            resource_id=str(user.id),
        )
        
        return backup_codes_plain
    
    # =========================================================================
    # Private Helpers
    # =========================================================================
    
    async def _create_session(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        remember_me: bool,
    ) -> TokenPair:
        """Create a new session and return tokens."""
        session_id = uuid4()
        
        tokens = create_token_pair(
            user_id=str(user.id),
            client_id=str(user.client_id) if user.client_id else None,
            role=user.role if isinstance(user.role, str) else user.role.value,
            session_id=str(session_id),
            remember_me=remember_me,
        )
        
        # Calculate expiration
        days = 30 if remember_me else 7
        expires_at = datetime.utcnow() + timedelta(days=days)
        
        session = UserSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_token(tokens.refresh_token),
            access_token_hash=hash_token(tokens.access_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            remember_me=remember_me,
        )
        
        self.db.add(session)
        
        return tokens
    
    async def _handle_failed_login(self, user: User) -> None:
        """Handle failed login attempt."""
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            
            await self._log_action(
                user_id=user.id,
                client_id=user.client_id,
                action="user.account_locked",
                resource_type="user",
                resource_id=str(user.id),
                severity="warning",
            )
        
        await self.db.commit()
    
    async def _log_action(
        self,
        action: str,
        resource_type: str,
        user_id: UUID | None = None,
        client_id: UUID | None = None,
        resource_id: str | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        description: str | None = None,
        severity: str = "info",
    ) -> None:
        """Create an audit log entry."""
        log = AuditLog(
            user_id=user_id,
            client_id=client_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            severity=severity,
        )
        self.db.add(log)
