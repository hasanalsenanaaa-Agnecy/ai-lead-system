"""
Error Handling & Monitoring
Sentry integration, structured error logging
"""

import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry():
    """Initialize Sentry error tracking."""
    if not settings.sentry_dsn:
        logger.warning("Sentry DSN not configured, error tracking disabled")
        return
    
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.app_env,
        traces_sample_rate=settings.sentry_traces_sample_rate or 0.1,
        profiles_sample_rate=0.1,
        enable_tracing=True,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
        ],
        # Don't send PII
        send_default_pii=False,
        # Filter out health checks
        before_send=filter_events,
        before_send_transaction=filter_transactions,
    )
    
    logger.info(f"Sentry initialized for environment: {settings.sentry_environment}")


def filter_events(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter out events we don't want to send to Sentry."""
    # Don't send 4xx errors
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        if isinstance(exc_value, HTTPException):
            if 400 <= exc_value.status_code < 500:
                return None
    
    # Scrub sensitive data
    if "request" in event:
        request = event["request"]
        # Remove auth headers
        if "headers" in request:
            request["headers"] = {
                k: v for k, v in request["headers"].items()
                if k.lower() not in ["authorization", "x-api-key", "cookie"]
            }
    
    return event


def filter_transactions(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter out transactions we don't want to track."""
    transaction = event.get("transaction", "")
    
    # Skip health checks
    if "/health" in transaction:
        return None
    
    # Skip static files
    if any(ext in transaction for ext in [".js", ".css", ".ico", ".png"]):
        return None
    
    return event


def capture_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    client_id: Optional[str] = None,
):
    """Capture an exception with context."""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_extra(key, value)
        
        if user_id:
            scope.set_user({"id": user_id})
        
        if client_id:
            scope.set_tag("client_id", client_id)
        
        sentry_sdk.capture_exception(error)


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
):
    """Capture a message with context."""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_extra(key, value)
        
        sentry_sdk.capture_message(message, level=level)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for consistent error handling and logging.
    """
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())[:8]
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            return response
            
        except Exception as exc:
            # Log the error
            logger.error(
                f"Unhandled error",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
            
            # Capture in Sentry
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("request_id", request_id)
                scope.set_extra("path", request.url.path)
                scope.set_extra("method", request.method)
                sentry_sdk.capture_exception(exc)
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                },
            )


def setup_exception_handlers(app: FastAPI):
    """Set up custom exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail if isinstance(exc.detail, str) else "error",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "request_id": request_id,
            },
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        request_id = getattr(request.state, "request_id", "unknown")
        
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_error",
                "message": str(exc),
                "request_id": request_id,
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log
        logger.error(
            f"Unhandled exception: {exc}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "traceback": traceback.format_exc(),
            },
        )
        
        # Capture in Sentry
        capture_exception(exc, context={"request_id": request_id})
        
        # Return generic error in production
        if settings.is_production:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                },
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": str(exc),
                    "request_id": request_id,
                    "traceback": traceback.format_exc(),
                },
            )


class GracefulDegradation:
    """
    Helper for graceful degradation when services fail.
    """
    
    @staticmethod
    async def with_fallback(
        primary_func,
        fallback_value,
        error_message: str = "Service unavailable",
        log_error: bool = True,
    ):
        """
        Try primary function, return fallback on failure.
        
        Usage:
            result = await GracefulDegradation.with_fallback(
                lambda: external_api.fetch_data(),
                fallback_value=[],
                error_message="External API failed",
            )
        """
        try:
            return await primary_func()
        except Exception as e:
            if log_error:
                logger.warning(f"{error_message}: {e}")
            return fallback_value
    
    @staticmethod
    def cached_fallback(cache_key: str, ttl_seconds: int = 300):
        """
        Decorator that caches successful results and returns cache on failure.
        """
        _cache: Dict[str, Any] = {}
        
        def decorator(func):
            async def wrapper(*args, **kwargs):
                try:
                    result = await func(*args, **kwargs)
                    _cache[cache_key] = {
                        "value": result,
                        "timestamp": datetime.utcnow(),
                    }
                    return result
                except Exception as e:
                    cached = _cache.get(cache_key)
                    if cached:
                        age = (datetime.utcnow() - cached["timestamp"]).total_seconds()
                        if age < ttl_seconds:
                            logger.warning(f"Using cached value for {cache_key}, age: {age}s")
                            return cached["value"]
                    raise e
            return wrapper
        return decorator
