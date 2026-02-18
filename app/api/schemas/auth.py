"""
Authentication Schemas
Pydantic models for auth requests and responses
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.models_auth import UserRole


# =============================================================================
# Registration
# =============================================================================


class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()
    
    @field_validator('email')
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()


class UserRegisterResponse(BaseModel):
    """User registration response."""
    id: UUID
    email: str
    first_name: str
    last_name: str
    message: str = "Registration successful. Please check your email to verify your account."


# =============================================================================
# Login
# =============================================================================


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"
    requires_2fa: bool = False


class TwoFactorLoginRequest(BaseModel):
    """2FA verification request."""
    user_id: UUID
    code: str = Field(..., min_length=6, max_length=6)


class BackupCodeLoginRequest(BaseModel):
    """Backup code login request."""
    user_id: UUID
    backup_code: str


class TwoFactorRequiredResponse(BaseModel):
    """Response when 2FA is required."""
    requires_2fa: bool = True
    user_id: UUID
    message: str = "Two-factor authentication required"


# =============================================================================
# Token Refresh
# =============================================================================


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# =============================================================================
# Password Management
# =============================================================================


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Forgot password response."""
    message: str = "If an account exists with this email, a password reset link has been sent."


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    """Reset password response."""
    message: str = "Password reset successful. Please log in with your new password."


class ChangePasswordRequest(BaseModel):
    """Change password request (for logged-in users)."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    logout_other_sessions: bool = True


class ChangePasswordResponse(BaseModel):
    """Change password response."""
    message: str = "Password changed successfully."


# =============================================================================
# Email Verification
# =============================================================================


class VerifyEmailRequest(BaseModel):
    """Email verification request."""
    token: str


class VerifyEmailResponse(BaseModel):
    """Email verification response."""
    message: str = "Email verified successfully."
    verified: bool = True


class ResendVerificationRequest(BaseModel):
    """Resend verification email request."""
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    """Resend verification response."""
    message: str = "If an unverified account exists with this email, a verification link has been sent."


# =============================================================================
# Two-Factor Authentication
# =============================================================================


class Enable2FAResponse(BaseModel):
    """Enable 2FA response."""
    secret: str
    backup_codes: List[str]
    message: str = "Two-factor authentication enabled. Save your backup codes securely."


class Disable2FARequest(BaseModel):
    """Disable 2FA request."""
    password: str


class Disable2FAResponse(BaseModel):
    """Disable 2FA response."""
    message: str = "Two-factor authentication disabled."


class RegenerateBackupCodesRequest(BaseModel):
    """Regenerate backup codes request."""
    password: str


class RegenerateBackupCodesResponse(BaseModel):
    """Regenerate backup codes response."""
    backup_codes: List[str]
    message: str = "New backup codes generated. Previous codes are now invalid."


# =============================================================================
# Session Management
# =============================================================================


class SessionInfo(BaseModel):
    """Session information."""
    id: UUID
    device_info: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    is_current: bool = False

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """List of active sessions."""
    sessions: List[SessionInfo]
    total: int


class LogoutResponse(BaseModel):
    """Logout response."""
    message: str = "Logged out successfully."


class LogoutAllResponse(BaseModel):
    """Logout all sessions response."""
    message: str
    sessions_invalidated: int


# =============================================================================
# User Response
# =============================================================================


class UserResponse(BaseModel):
    """User information response."""
    id: UUID
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str]
    avatar_url: Optional[str]
    role: UserRole
    is_verified: bool
    two_factor_enabled: bool
    client_id: Optional[UUID]
    timezone: str
    language: str
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Update user profile request."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)


class UserUpdateResponse(BaseModel):
    """Update user profile response."""
    user: UserResponse
    message: str = "Profile updated successfully."


# =============================================================================
# Admin User Management
# =============================================================================


class CreateUserRequest(BaseModel):
    """Admin create user request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.AGENT
    client_id: Optional[UUID] = None
    phone: Optional[str] = None
    send_welcome_email: bool = True


class UpdateUserRoleRequest(BaseModel):
    """Update user role request."""
    role: UserRole


class DeactivateUserRequest(BaseModel):
    """Deactivate user request."""
    reason: Optional[str] = None


# =============================================================================
# Audit Log
# =============================================================================


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    description: Optional[str]
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """List of audit logs."""
    logs: List[AuditLogEntry]
    total: int
    page: int
    page_size: int


# Forward reference resolution
LoginResponse.model_rebuild()
