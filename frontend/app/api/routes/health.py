"""
Health Check Endpoints
Comprehensive health monitoring for all services
"""

import asyncio
from datetime import datetime
from typing import Any, Dict

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.circuit_breaker import get_all_circuit_status
from app.db.session import get_db_session

router = APIRouter(prefix="/health", tags=["Health"])


async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        start = datetime.utcnow()
        await db.execute(text("SELECT 1"))
        latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        start = datetime.utcnow()
        client = redis.from_url(settings.redis_url)
        await client.ping()
        latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        
        # Get memory info
        info = await client.info("memory")
        await client.close()
        
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("")
async def health_check():
    """Basic health check - always returns 200 if app is running."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.app_env,
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db_session)):
    """
    Readiness check for load balancers/Kubernetes.
    Checks all critical dependencies.
    """
    # Run checks concurrently
    db_check, redis_check = await asyncio.gather(
        check_database(db),
        check_redis(),
        return_exceptions=True,
    )
    
    # Handle exceptions
    if isinstance(db_check, Exception):
        db_check = {"status": "unhealthy", "error": str(db_check)}
    if isinstance(redis_check, Exception):
        redis_check = {"status": "unhealthy", "error": str(redis_check)}
    
    checks = {
        "database": db_check,
        "redis": redis_check,
    }
    
    all_healthy = all(
        c.get("status") == "healthy" 
        for c in checks.values()
    )
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check - indicates if app should be restarted.
    Only fails if app is fundamentally broken.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db_session)):
    """
    Detailed health check with all service statuses.
    For monitoring dashboards.
    """
    # Run all checks
    db_check, redis_check = await asyncio.gather(
        check_database(db),
        check_redis(),
        return_exceptions=True,
    )
    
    # Handle exceptions
    if isinstance(db_check, Exception):
        db_check = {"status": "unhealthy", "error": str(db_check)}
    if isinstance(redis_check, Exception):
        redis_check = {"status": "unhealthy", "error": str(redis_check)}
    
    # Get circuit breaker status
    circuits = get_all_circuit_status()
    
    # Calculate overall status
    services_healthy = all(
        c.get("status") == "healthy"
        for c in [db_check, redis_check]
    )
    
    circuits_healthy = all(
        c.get("state") in ["closed", "half_open"]
        for c in circuits.values()
    ) if circuits else True
    
    overall_status = "healthy" if (services_healthy and circuits_healthy) else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.app_env,
        "uptime_seconds": None,  # TODO: Track app start time
        "services": {
            "database": db_check,
            "redis": redis_check,
        },
        "circuit_breakers": circuits,
    }


@router.get("/metrics")
async def metrics_endpoint(db: AsyncSession = Depends(get_db_session)):
    """
    Prometheus-style metrics endpoint.
    """
    # Get counts from database
    try:
        result = await db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM clients WHERE deleted_at IS NULL) as clients,
                (SELECT COUNT(*) FROM leads WHERE deleted_at IS NULL) as leads,
                (SELECT COUNT(*) FROM conversations WHERE is_active = true) as active_conversations,
                (SELECT COUNT(*) FROM escalations WHERE status = 'pending') as pending_escalations,
                (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users
        """))
        row = result.fetchone()
        
        metrics = {
            "clients_total": row[0],
            "leads_total": row[1],
            "conversations_active": row[2],
            "escalations_pending": row[3],
            "users_active": row[4],
        }
    except Exception:
        metrics = {}
    
    # Get circuit breaker metrics
    circuits = get_all_circuit_status()
    for name, status in circuits.items():
        metrics[f"circuit_{name}_failures"] = status.get("failures", 0)
        metrics[f"circuit_{name}_state"] = 1 if status.get("state") == "closed" else 0
    
    return metrics
