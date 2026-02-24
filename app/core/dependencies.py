"""
Authentication Dependencies
FastAPI dependencies for protected routes
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_token, TokenPayload
from app.db.models_auth import User, UserRole, UserSession
from app.db.session import get_db_session as get_db

# Security scheme
security = HTTPBearer(auto_error=False)


# =============================================================================
# Current User Dependencies
# =============================================================================


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get current authenticated user from JWT token.
    Raises 401 if not authenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    result = await db.execute(
        select(User).where(
            User.id == UUID(payload.sub),
            User.is_active == True,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is locked
    if user.is_locked():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked",
        )
    
    # Verify session is still valid
    if payload.session_id:
        session_result = await db.execute(
            select(UserSession).where(
                UserSession.id == UUID(payload.session_id),
                UserSession.user_id == user.id,
                UserSession.is_valid == True,
                UserSession.expires_at > datetime.utcnow(),
            )
        )
        session = session_result.scalar_one_or_none()
        
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalidated",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """
    Get current user if authenticated, None otherwise.
    Does not raise exception.
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Ensure user has verified email."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return current_user


# =============================================================================
# Role-Based Dependencies
# =============================================================================


class RoleChecker:
    """Dependency for checking user roles."""
    
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_verified_user)],
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user


# Pre-configured role checkers
require_super_admin = RoleChecker([UserRole.SUPER_ADMIN])
require_admin = RoleChecker([UserRole.SUPER_ADMIN, UserRole.ADMIN])
require_agent = RoleChecker([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.AGENT])
require_viewer = RoleChecker([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER])


# =============================================================================
# Client Access Dependencies
# =============================================================================


async def get_current_client_id(
    current_user: Annotated[User, Depends(get_current_verified_user)],
) -> UUID | None:
    """Get the client_id for the current user."""
    return current_user.client_id


async def require_client_access(
    current_user: Annotated[User, Depends(get_current_verified_user)],
    client_id: UUID,
) -> User:
    """
    Ensure user has access to the specified client.
    Super admins have access to all clients.
    Other users must belong to the client.
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        return current_user
    
    if current_user.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this client",
        )
    
    return current_user


class ClientAccessChecker:
    """Dependency for checking client access from path parameter."""
    
    async def __call__(
        self,
        client_id: UUID,
        current_user: Annotated[User, Depends(get_current_verified_user)],
    ) -> User:
        return await require_client_access(current_user, client_id)


require_client_access_dep = ClientAccessChecker()


# =============================================================================
# Request Context
# =============================================================================


def get_client_ip(request: Request) -> str:
    """Get client IP address, considering proxies."""
    # Check for forwarded headers (behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the list is the original client
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent string."""
    return request.headers.get("User-Agent", "unknown")[:500]


# =============================================================================
# Type Aliases for Cleaner Routes
# =============================================================================

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentVerifiedUser = Annotated[User, Depends(get_current_verified_user)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]
AdminUser = Annotated[User, Depends(require_admin)]
AgentUser = Annotated[User, Depends(require_agent)]
ViewerUser = Annotated[User, Depends(require_viewer)]
