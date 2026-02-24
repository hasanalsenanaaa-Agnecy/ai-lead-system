"""
Rate Limiting Middleware
Protects API from abuse with configurable limits per endpoint
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Tuple

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.dependencies import get_client_ip


# =============================================================================
# In-Memory Rate Limiter (for single instance)
# For production with multiple instances, use Redis
# =============================================================================


class RateLimiter:
    """
    Token bucket rate limiter.
    Thread-safe for single process.
    """
    
    def __init__(self):
        # Store: {key: (tokens, last_update)}
        self._buckets: Dict[str, Tuple[float, float]] = defaultdict(lambda: (0.0, 0.0))
        self._locks: Dict[str, bool] = defaultdict(bool)
    
    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, dict]:
        """
        Check if request is allowed.
        Returns (allowed, headers_dict).
        """
        now = time.time()
        tokens, last_update = self._buckets[key]
        
        # Calculate token refill
        time_passed = now - last_update
        refill_rate = max_requests / window_seconds
        tokens = min(max_requests, tokens + time_passed * refill_rate)
        
        # Check if request allowed
        if tokens >= 1:
            tokens -= 1
            allowed = True
        else:
            allowed = False
        
        # Update bucket
        self._buckets[key] = (tokens, now)
        
        # Calculate retry-after if blocked
        if not allowed:
            retry_after = int((1 - tokens) / refill_rate) + 1
        else:
            retry_after = 0
        
        # Headers
        headers = {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(max(0, int(tokens))),
            "X-RateLimit-Reset": str(int(now + window_seconds)),
        }
        
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        return allowed, headers
    
    def cleanup_old_buckets(self, max_age_seconds: int = 3600):
        """Remove old buckets to prevent memory leak."""
        now = time.time()
        cutoff = now - max_age_seconds
        
        keys_to_remove = [
            key for key, (_, last_update) in self._buckets.items()
            if last_update < cutoff
        ]
        
        for key in keys_to_remove:
            del self._buckets[key]


# Global rate limiter instance
_rate_limiter = RateLimiter()


# =============================================================================
# Rate Limit Configurations
# =============================================================================


# Default limits per endpoint pattern
RATE_LIMITS = {
    # Auth endpoints (strict)
    "/api/v1/auth/login": (5, 60),          # 5 per minute
    "/api/v1/auth/register": (3, 60),       # 3 per minute
    "/api/v1/auth/password/reset": (3, 60), # 3 per minute
    "/api/v1/auth/password/forgot": (3, 60),# 3 per minute
    "/api/v1/auth/2fa": (5, 60),            # 5 per minute
    
    # Webhooks (higher limits)
    "/webhooks/": (100, 60),                # 100 per minute
    
    # API endpoints (moderate)
    "/api/v1/leads": (60, 60),              # 60 per minute
    "/api/v1/conversations": (60, 60),
    "/api/v1/knowledge": (30, 60),          # 30 per minute
    
    # Default
    "default": (100, 60),                   # 100 per minute
}


def get_rate_limit_for_path(path: str) -> Tuple[int, int]:
    """Get rate limit (requests, seconds) for a path."""
    # Check exact match
    if path in RATE_LIMITS:
        return RATE_LIMITS[path]
    
    # Check prefix match
    for pattern, limit in RATE_LIMITS.items():
        if pattern != "default" and path.startswith(pattern):
            return limit
    
    return RATE_LIMITS["default"]


# =============================================================================
# Middleware
# =============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    Applies per-IP rate limits with endpoint-specific configurations.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = get_client_ip(request)
        path = request.url.path
        
        # Get rate limit for this path
        max_requests, window_seconds = get_rate_limit_for_path(path)
        
        # Create rate limit key
        rate_key = f"{client_ip}:{path}"
        
        # Check rate limit
        allowed, headers = _rate_limiter.is_allowed(rate_key, max_requests, window_seconds)
        
        if not allowed:
            response = Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
            )
            for key, value in headers.items():
                response.headers[key] = value
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# =============================================================================
# Rate Limit Decorator (for fine-grained control)
# =============================================================================


def rate_limit(
    max_requests: int = 10,
    window_seconds: int = 60,
    key_func: Callable[[Request], str] | None = None,
):
    """
    Decorator for rate limiting specific endpoints.
    
    Usage:
        @router.get("/expensive-operation")
        @rate_limit(max_requests=5, window_seconds=300)
        async def expensive_operation():
            ...
    """
    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            # Get key
            if key_func:
                key = key_func(request)
            else:
                key = f"{get_client_ip(request)}:{request.url.path}"
            
            # Check limit
            allowed, headers = _rate_limiter.is_allowed(key, max_requests, window_seconds)
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers=headers,
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# Client-Specific Rate Limiting
# =============================================================================


async def check_client_rate_limit(
    client_id: str,
    endpoint: str,
    max_requests: int = 1000,
    window_seconds: int = 3600,
) -> Tuple[bool, dict]:
    """
    Check rate limit for a specific client.
    Used for API key authenticated requests.
    """
    key = f"client:{client_id}:{endpoint}"
    return _rate_limiter.is_allowed(key, max_requests, window_seconds)


# =============================================================================
# Cleanup Task
# =============================================================================


async def cleanup_rate_limit_buckets():
    """Periodic cleanup of old rate limit buckets."""
    _rate_limiter.cleanup_old_buckets(max_age_seconds=3600)
