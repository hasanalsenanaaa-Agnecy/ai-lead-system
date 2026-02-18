"""
Core Authentication Module
JWT tokens, password hashing, security utilities
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


# =============================================================================
# Configuration
# =============================================================================

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER = 30
PASSWORD_RESET_EXPIRE_HOURS = 24
EMAIL_VERIFICATION_EXPIRE_HOURS = 48
TWO_FACTOR_CODE_EXPIRE_MINUTES = 10

# Account lockout
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


# =============================================================================
# Token Models
# =============================================================================


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user_id
    type: str  # access, refresh
    client_id: str | None = None
    role: str | None = None
    session_id: str | None = None
    exp: datetime
    iat: datetime


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# =============================================================================
# Password Hashing
# =============================================================================


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def check_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Check password meets security requirements.
    Returns (is_valid, list of error messages).
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if len(password) > 128:
        errors.append("Password must not exceed 128 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors


# =============================================================================
# JWT Tokens
# =============================================================================


def create_access_token(
    user_id: str,
    client_id: str | None = None,
    role: str | None = None,
    session_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,
        "type": "access",
        "client_id": client_id,
        "role": role,
        "session_id": session_id,
        "exp": expire,
        "iat": now,
    }
    
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)


def create_refresh_token(
    user_id: str,
    session_id: str,
    remember_me: bool = False,
) -> str:
    """Create a JWT refresh token."""
    now = datetime.utcnow()
    days = REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER if remember_me else REFRESH_TOKEN_EXPIRE_DAYS
    expire = now + timedelta(days=days)
    
    payload = {
        "sub": user_id,
        "type": "refresh",
        "session_id": session_id,
        "exp": expire,
        "iat": now,
    }
    
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)


def create_token_pair(
    user_id: str,
    client_id: str | None,
    role: str,
    session_id: str,
    remember_me: bool = False,
) -> TokenPair:
    """Create both access and refresh tokens."""
    access_token = create_access_token(
        user_id=user_id,
        client_id=client_id,
        role=role,
        session_id=session_id,
    )
    refresh_token = create_refresh_token(
        user_id=user_id,
        session_id=session_id,
        remember_me=remember_me,
    )
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def decode_token(token: str) -> TokenPayload | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> TokenPayload | None:
    """Verify token is valid and of correct type."""
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.type != token_type:
        return None
    if payload.exp < datetime.utcnow():
        return None
    return payload


# =============================================================================
# Special Purpose Tokens
# =============================================================================


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token for storage (non-reversible)."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_password_reset_token() -> tuple[str, str, datetime]:
    """
    Create a password reset token.
    Returns (plain_token, hashed_token, expires_at).
    """
    token = generate_secure_token(32)
    hashed = hash_token(token)
    expires = datetime.utcnow() + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
    return token, hashed, expires


def create_email_verification_token() -> tuple[str, str, datetime]:
    """
    Create an email verification token.
    Returns (plain_token, hashed_token, expires_at).
    """
    token = generate_secure_token(32)
    hashed = hash_token(token)
    expires = datetime.utcnow() + timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS)
    return token, hashed, expires


def create_two_factor_code() -> tuple[str, str, datetime]:
    """
    Create a 6-digit 2FA code.
    Returns (code, hashed_code, expires_at).
    """
    code = ''.join(secrets.choice('0123456789') for _ in range(6))
    hashed = hash_token(code)
    expires = datetime.utcnow() + timedelta(minutes=TWO_FACTOR_CODE_EXPIRE_MINUTES)
    return code, hashed, expires


def generate_backup_codes(count: int = 10) -> list[tuple[str, str]]:
    """
    Generate 2FA backup codes.
    Returns list of (plain_code, hashed_code).
    """
    codes = []
    for _ in range(count):
        code = f"{secrets.token_hex(4)}-{secrets.token_hex(4)}"
        hashed = hash_token(code)
        codes.append((code, hashed))
    return codes


# =============================================================================
# Webhook Verification
# =============================================================================


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256"
) -> bool:
    """Verify webhook signature (HMAC)."""
    expected = hmac.new(
        secret.encode(),
        payload,
        getattr(hashlib, algorithm)
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_twilio_signature(
    url: str,
    params: dict,
    signature: str,
    auth_token: str,
) -> bool:
    """Verify Twilio webhook signature."""
    from urllib.parse import urlencode
    
    # Build the validation string
    s = url
    if params:
        s += urlencode(sorted(params.items()))
    
    # Calculate expected signature
    expected = hmac.new(
        auth_token.encode(),
        s.encode(),
        hashlib.sha1
    ).digest()
    
    import base64
    expected_b64 = base64.b64encode(expected).decode()
    
    return hmac.compare_digest(expected_b64, signature)


def verify_stripe_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify Stripe webhook signature."""
    import time
    
    try:
        # Parse the signature header
        parts = dict(item.split("=") for item in signature.split(","))
        timestamp = parts.get("t")
        v1_signature = parts.get("v1")
        
        if not timestamp or not v1_signature:
            return False
        
        # Check timestamp (prevent replay attacks)
        if abs(time.time() - int(timestamp)) > 300:  # 5 minutes
            return False
        
        # Calculate expected signature
        signed_payload = f"{timestamp}.{payload.decode()}"
        expected = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, v1_signature)
    except Exception:
        return False


# =============================================================================
# Input Sanitization
# =============================================================================


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize a string input."""
    if not isinstance(value, str):
        return ""
    
    # Truncate
    value = value[:max_length]
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Strip whitespace
    value = value.strip()
    
    return value


def sanitize_email(email: str) -> str:
    """Sanitize and normalize email."""
    email = sanitize_string(email, 255)
    email = email.lower()
    return email


def sanitize_phone(phone: str) -> str:
    """Sanitize phone number, keeping only digits and +."""
    phone = sanitize_string(phone, 20)
    return ''.join(c for c in phone if c.isdigit() or c == '+')


def sanitize_html(value: str) -> str:
    """Remove HTML tags from string."""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', value)
