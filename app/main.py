"""
AI Lead Response System
Main FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import webhooks
from app.api.routes import auth, clients, conversations, health, leads, knowledge, dashboard, escalations
from app.core.rate_limit import RateLimitMiddleware
from app.core.config import settings
from app.db.session import close_db, init_db

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.is_production else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize Sentry for error tracking
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        enable_tracing=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI Lead Response System", env=settings.app_env)
    # await init_db()
    # logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down AI Lead Response System")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="AI Lead Response System",
    description="AI-powered lead qualification and response system",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )

    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred"},
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )


# =============================================================================
# Middleware
# =============================================================================


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = structlog.contextvars.get_contextvars()

    # Generate request ID
    import uuid
    request_id = str(uuid.uuid4())[:8]

    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    response = await call_next(request)

    logger.info(
        "Request completed",
        request_id=request_id,
        status_code=response.status_code,
    )

    response.headers["X-Request-ID"] = request_id
    return response


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(webhooks.router)
app.include_router(leads.router)
app.include_router(conversations.router)
app.include_router(clients.router)
app.include_router(knowledge.router)
app.include_router(dashboard.router)
app.include_router(escalations.router)


# =============================================================================
# Root Endpoint
# =============================================================================


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.app_env,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        workers=1 if settings.is_development else settings.api_workers,
    )
