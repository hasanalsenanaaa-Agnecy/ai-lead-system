"""
Authentication API Routes
Login, registration, password reset, 2FA, etc.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import (
    # Registration
    UserRegisterRequest,
    UserRegisterResponse,
    # Login
    LoginRequest,
    LoginResponse,
    TwoFactorLoginRequest,
    BackupCodeLoginRequest,
    TwoFactorRequiredResponse,
    # Tokens
    TokenRefreshRequest,
    TokenRefreshResponse,
    # Password
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    # Email verification
    VerifyEmailRequest,
    VerifyEmailResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    # 2FA
    Enable2FAResponse,
    Disable2FARequest,
    Disable2FAResponse,
    RegenerateBackupCodesRequest,
    RegenerateBackupCodesResponse,
    # Sessions
    SessionInfo,
    SessionListResponse,
    LogoutResponse,
    LogoutAllResponse,
    # User
    UserResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)
from app.core.auth import hash_token, verify_token
from app.core.dependencies import (
    get_client_ip,
    get_user_agent,
    get_current_user,
    get_current_verified_user,
    CurrentUser,
    CurrentVerifiedUser,
)
from app.db.models_auth import User, UserSession
from app.db.session import get_db_session as get_db
from app.services.auth_service import AuthService, AuthError


router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Registration
# =============================================================================


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    data: UserRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Register a new user account.
    
    - Validates email uniqueness
    - Enforces password strength requirements
    - Sends verification email
    """
    auth_service = AuthService(db)
    
    try:
        user, verification_token = await auth_service.register_user(
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
        )
        
        # TODO: Send verification email with token
        # await email_service.send_verification_email(user.email, verification_token)
        
        return UserRegisterResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# Login
# =============================================================================


@router.post("/login", response_model=LoginResponse | TwoFactorRequiredResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Authenticate user and receive access tokens.
    
    - Returns tokens if successful
    - Returns 2FA challenge if enabled
    - Tracks failed attempts and locks account after 5 failures
    """
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    try:
        user, tokens, two_factor_code = await auth_service.login(
            email=data.email,
            password=data.password,
            ip_address=ip_address,
            user_agent=user_agent,
            remember_me=data.remember_me,
        )
        
        # 2FA required
        if two_factor_code is not None:
            # TODO: Send 2FA code via email/SMS
            # await email_service.send_2fa_code(user.email, two_factor_code)
            
            return TwoFactorRequiredResponse(user_id=user.id)
        
        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            user=UserResponse(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                full_name=user.full_name,
                phone=user.phone,
                avatar_url=user.avatar_url,
                role=user.role,
                is_verified=user.is_verified,
                two_factor_enabled=user.two_factor_enabled,
                client_id=user.client_id,
                timezone=user.timezone,
                language=user.language,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
            ),
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/login/2fa", response_model=LoginResponse)
async def verify_two_factor_login(
    request: Request,
    data: TwoFactorLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify 2FA code and complete login."""
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    try:
        user, tokens = await auth_service.verify_two_factor(
            user_id=data.user_id,
            code=data.code,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            user=UserResponse.model_validate(user),
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/login/backup-code", response_model=LoginResponse)
async def verify_backup_code_login(
    request: Request,
    data: BackupCodeLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Login using a backup code when 2FA device unavailable."""
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    try:
        user, tokens = await auth_service.verify_backup_code(
            user_id=data.user_id,
            backup_code=data.backup_code,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            user=UserResponse.model_validate(user),
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# Token Refresh
# =============================================================================


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_tokens(
    request: Request,
    data: TokenRefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Refresh access token using refresh token.
    
    - Validates refresh token
    - Issues new token pair
    - Updates session last activity
    """
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    
    # Hash the refresh token to look it up
    refresh_token_hash = hash_token(data.refresh_token)
    
    try:
        tokens = await auth_service.refresh_tokens(
            refresh_token_hash=refresh_token_hash,
            ip_address=ip_address,
        )
        
        return TokenRefreshResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# Logout
# =============================================================================


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Logout and invalidate current session."""
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    
    # Get session ID from token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload and payload.session_id:
            await auth_service.logout(
                user_id=current_user.id,
                session_id=UUID(payload.session_id),
                ip_address=ip_address,
            )
    
    return LogoutResponse()


@router.post("/logout/all", response_model=LogoutAllResponse)
async def logout_all_sessions(
    request: Request,
    current_user: CurrentVerifiedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Logout from all sessions except current."""
    auth_service = AuthService(db)
    
    # Get current session ID
    current_session_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload and payload.session_id:
            current_session_id = UUID(payload.session_id)
    
    count = await auth_service.logout_all_sessions(
        user_id=current_user.id,
        except_session_id=current_session_id,
    )
    
    return LogoutAllResponse(
        message=f"Logged out from {count} other session(s).",
        sessions_invalidated=count,
    )


# =============================================================================
# Password Management
# =============================================================================


@router.post("/password/forgot", response_model=ForgotPasswordResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Request password reset email.
    
    Always returns success to prevent email enumeration.
    """
    auth_service = AuthService(db)
    
    token = await auth_service.request_password_reset(email=data.email)
    
    if token:
        # TODO: Send password reset email
        # await email_service.send_password_reset_email(data.email, token)
        pass
    
    return ForgotPasswordResponse()


@router.post("/password/reset", response_model=ResetPasswordResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reset password using reset token."""
    auth_service = AuthService(db)
    
    try:
        await auth_service.reset_password(
            token=data.token,
            new_password=data.new_password,
        )
        return ResetPasswordResponse()
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/password/change", response_model=ChangePasswordResponse)
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: CurrentVerifiedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Change password for logged-in user."""
    auth_service = AuthService(db)
    
    # Get current session ID
    current_session_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload and payload.session_id:
            current_session_id = UUID(payload.session_id)
    
    try:
        await auth_service.change_password(
            user_id=current_user.id,
            current_password=data.current_password,
            new_password=data.new_password,
            logout_other_sessions=data.logout_other_sessions,
            current_session_id=current_session_id,
        )
        return ChangePasswordResponse()
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# Email Verification
# =============================================================================


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    data: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify email address using verification token."""
    auth_service = AuthService(db)
    
    try:
        await auth_service.verify_email(token=data.token)
        return VerifyEmailResponse()
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification_email(
    data: ResendVerificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Resend verification email."""
    auth_service = AuthService(db)
    
    try:
        token = await auth_service.resend_verification(email=data.email)
        
        # TODO: Send verification email
        # await email_service.send_verification_email(data.email, token)
        
    except AuthError:
        pass  # Don't reveal if user exists
    
    return ResendVerificationResponse()


# =============================================================================
# Two-Factor Authentication
# =============================================================================


@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_two_factor(
    current_user: CurrentVerifiedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Enable two-factor authentication."""
    auth_service = AuthService(db)
    
    try:
        secret, backup_codes = await auth_service.enable_two_factor(
            user_id=current_user.id,
        )
        return Enable2FAResponse(
            secret=secret,
            backup_codes=backup_codes,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/2fa/disable", response_model=Disable2FAResponse)
async def disable_two_factor(
    data: Disable2FARequest,
    current_user: CurrentVerifiedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Disable two-factor authentication (requires password)."""
    auth_service = AuthService(db)
    
    try:
        await auth_service.disable_two_factor(
            user_id=current_user.id,
            password=data.password,
        )
        return Disable2FAResponse()
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/2fa/backup-codes", response_model=RegenerateBackupCodesResponse)
async def regenerate_backup_codes(
    data: RegenerateBackupCodesRequest,
    current_user: CurrentVerifiedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate new backup codes (invalidates old ones)."""
    auth_service = AuthService(db)
    
    try:
        backup_codes = await auth_service.regenerate_backup_codes(
            user_id=current_user.id,
            password=data.password,
        )
        return RegenerateBackupCodesResponse(backup_codes=backup_codes)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =============================================================================
# Session Management
# =============================================================================


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    current_user: CurrentVerifiedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all active sessions for current user."""
    from datetime import datetime
    
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_valid == True,
            UserSession.expires_at > datetime.utcnow(),
        ).order_by(UserSession.last_activity_at.desc())
    )
    sessions = result.scalars().all()
    
    # Get current session ID
    current_session_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload and payload.session_id:
            current_session_id = UUID(payload.session_id)
    
    session_list = [
        SessionInfo(
            id=s.id,
            device_info=s.device_info,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            created_at=s.created_at,
            last_activity_at=s.last_activity_at,
            expires_at=s.expires_at,
            is_current=(s.id == current_session_id),
        )
        for s in sessions
    ]
    
    return SessionListResponse(sessions=session_list, total=len(session_list))


@router.delete("/sessions/{session_id}", response_model=LogoutResponse)
async def revoke_session(
    session_id: UUID,
    current_user: CurrentVerifiedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revoke a specific session."""
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_valid = False
    session.invalidated_at = datetime.utcnow()
    session.invalidation_reason = "revoked"
    
    await db.commit()
    
    return LogoutResponse(message="Session revoked successfully.")


# =============================================================================
# Current User
# =============================================================================


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        phone=current_user.phone,
        avatar_url=current_user.avatar_url,
        role=current_user.role,
        is_verified=current_user.is_verified,
        two_factor_enabled=current_user.two_factor_enabled,
        client_id=current_user.client_id,
        timezone=current_user.timezone,
        language=current_user.language,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )


@router.patch("/me", response_model=UserUpdateResponse)
async def update_current_user(
    data: UserUpdateRequest,
    current_user: CurrentVerifiedUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update current user profile."""
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserUpdateResponse(
        user=UserResponse.model_validate(current_user),
    )


# Import datetime at top if not already
from datetime import datetime
