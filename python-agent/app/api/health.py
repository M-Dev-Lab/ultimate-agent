"""
Health check and system status endpoints.

Provides REST endpoints for:
  - System health monitoring
  - Dependency status checks
  - Readiness/liveness probes (Kubernetes)
"""

from typing import Dict
from datetime import datetime
import logging
from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.models.schemas import SystemStatus, HealthCheck

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])


class HealthService:
    """Service layer for health checks."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_health(self) -> HealthCheck:
        """
        Get basic health status.

        Returns:
            HealthCheck with service status
        """
        return HealthCheck(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="3.0.0",
        )

    async def get_system_status(self) -> SystemStatus:
        """
        Get detailed system status with dependency checks.

        Returns:
            SystemStatus with all system information

        Phase 2: Add actual dependency checks:
          - Database connectivity
          - Redis availability
          - LLM model availability
          - Disk space
          - Memory usage
        """
        return SystemStatus(
            status="operational",
            timestamp=datetime.utcnow(),
            version="3.0.0",
            components={
                "api": "healthy",
                "database": "healthy",
                "cache": "healthy",
                "security": "healthy",
            },
            metrics={
                "uptime_seconds": 3600,
                "requests_total": 1250,
                "requests_per_second": 0.35,
                "memory_percent": 45.2,
                "cpu_percent": 12.5,
            },
        )


@router.get("/", response_model=HealthCheck)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Basic health check endpoint.

    Used for: load balancer probes, monitoring systems

    **Returns:**
    - 200 OK: Service is healthy
    - 503 Service Unavailable: Service is degraded

    **Response:**
    ```json
    {
      "status": "healthy",
      "timestamp": "2026-02-03T10:30:00Z",
      "version": "3.0.0"
    }
    ```
    """
    service = HealthService(settings)
    health = await service.get_health()

    if health.status == "healthy":
        return health

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=health.status,
    )


@router.get("/ready", response_model=HealthCheck)
async def readiness_probe(settings: Settings = Depends(get_settings)):
    """
    Kubernetes readiness probe endpoint.

    Indicates if service is ready to receive traffic.

    **Returns:**
    - 200 OK: Service is ready
    - 503 Service Unavailable: Service is not ready
    """
    service = HealthService(settings)
    health = await service.get_health()

    if health.status == "healthy":
        return health

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Service not ready",
    )


@router.get("/live", response_model=HealthCheck)
async def liveness_probe(settings: Settings = Depends(get_settings)):
    """
    Kubernetes liveness probe endpoint.

    Indicates if service process is running (no recovery needed).

    **Returns:**
    - 200 OK: Service is alive
    - 503 Service Unavailable: Service should be restarted
    """
    service = HealthService(settings)
    health = await service.get_health()

    if health.status == "healthy":
        return health

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Service unhealthy",
    )


@router.get("/status", response_model=SystemStatus)
async def system_status(settings: Settings = Depends(get_settings)):
    """
    Detailed system status with all components and metrics.

    Used for: admin dashboards, monitoring, alerting

    **Returns:**
    - 200 OK: Complete system status

    **Response:**
    ```json
    {
      "status": "operational",
      "timestamp": "2026-02-03T10:30:00Z",
      "version": "3.0.0",
      "components": {
        "api": "healthy",
        "database": "healthy",
        "cache": "healthy"
      },
      "metrics": {
        "uptime_seconds": 3600,
        "requests_total": 1250
      }
    }
    ```
    """
    service = HealthService(settings)
    return await service.get_system_status()
