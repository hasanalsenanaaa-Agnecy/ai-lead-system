"""
Health Check Endpoints
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.app_env,
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db_session)):
    """
    Readiness check including database connectivity.
    Used by Kubernetes/load balancers.
    """
    checks = {
        "database": False,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Check database
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)

    all_healthy = all([checks["database"]])

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check.
    Used by Kubernetes to determine if pod should be restarted.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
