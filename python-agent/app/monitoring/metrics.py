"""
Monitoring and observability infrastructure
Prometheus metrics, structured logging, and performance tracking
"""

import time
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_client.core import REGISTRY
import structlog

logger = structlog.get_logger(__name__)


class MetricsRegistry:
    """Central metrics collection and exposure"""
    
    def __init__(self):
        """Initialize Prometheus metrics"""
        
        # API Metrics
        self.api_requests_total = Counter(
            'api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.api_request_duration_seconds = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
        )
        
        # Build Metrics
        self.builds_created_total = Counter(
            'builds_created_total',
            'Total builds created',
            ['user_id', 'project_type']
        )
        
        self.build_duration_seconds = Histogram(
            'build_duration_seconds',
            'Build execution duration',
            ['language', 'status'],
            buckets=(1, 5, 10, 30, 60, 120, 300, 600)
        )
        
        self.builds_active = Gauge(
            'builds_active',
            'Active builds currently executing',
            ['language']
        )
        
        # Task Queue Metrics
        self.celery_tasks_total = Counter(
            'celery_tasks_total',
            'Total Celery tasks',
            ['task_name', 'status']
        )
        
        self.celery_task_duration_seconds = Histogram(
            'celery_task_duration_seconds',
            'Celery task duration',
            ['task_name'],
            buckets=(1, 5, 10, 30, 60, 300)
        )
        
        # Database Metrics
        self.db_queries_total = Counter(
            'db_queries_total',
            'Total database queries',
            ['operation', 'table']
        )
        
        self.db_query_duration_seconds = Histogram(
            'db_query_duration_seconds',
            'Database query duration',
            ['operation'],
            buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0)
        )
        
        # Vector Store Metrics
        self.vector_store_operations_total = Counter(
            'vector_store_operations_total',
            'Vector store operations',
            ['operation', 'collection']
        )
        
        self.vector_search_duration_seconds = Histogram(
            'vector_search_duration_seconds',
            'Vector search duration',
            ['collection'],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0)
        )
        
        # Agent Metrics
        self.agent_workflows_total = Counter(
            'agent_workflows_total',
            'Agent workflows executed',
            ['workflow_type', 'status']
        )
        
        self.agent_workflow_duration_seconds = Histogram(
            'agent_workflow_duration_seconds',
            'Agent workflow duration',
            ['workflow_type'],
            buckets=(10, 30, 60, 120, 300, 600, 1800)
        )
        
        # System Metrics
        self.system_health = Gauge(
            'system_health',
            'System health score (0-1)',
        )
        
        self.active_connections = Gauge(
            'active_connections',
            'Active database connections',
        )
        
        logger.info("Metrics registry initialized")
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record API request metrics"""
        self.api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        self.api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_build_execution(self, language: str, status: str, duration: float):
        """Record build execution metrics"""
        self.build_duration_seconds.labels(
            language=language,
            status=status
        ).observe(duration)
    
    def record_celery_task(self, task_name: str, status: str, duration: float):
        """Record Celery task metrics"""
        self.celery_tasks_total.labels(
            task_name=task_name,
            status=status
        ).inc()
        
        self.celery_task_duration_seconds.labels(
            task_name=task_name
        ).observe(duration)
    
    def record_db_query(self, operation: str, table: str, duration: float):
        """Record database query metrics"""
        self.db_queries_total.labels(
            operation=operation,
            table=table
        ).inc()
        
        self.db_query_duration_seconds.labels(
            operation=operation
        ).observe(duration)
    
    def record_vector_search(self, collection: str, duration: float):
        """Record vector search metrics"""
        self.vector_store_operations_total.labels(
            operation="search",
            collection=collection
        ).inc()
        
        self.vector_search_duration_seconds.labels(
            collection=collection
        ).observe(duration)


# Global metrics registry
_metrics_registry: Optional[MetricsRegistry] = None


def get_metrics() -> MetricsRegistry:
    """Get or initialize metrics registry"""
    global _metrics_registry
    if _metrics_registry is None:
        _metrics_registry = MetricsRegistry()
    return _metrics_registry


@contextmanager
def timer(metric_name: str, **labels):
    """Context manager for timing operations"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"Timing: {metric_name}", duration_ms=duration * 1000, **labels)


class PerformanceTracker:
    """Track performance metrics for operations"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = time.time()
        self.checkpoints = {}
    
    def checkpoint(self, name: str):
        """Record a checkpoint"""
        elapsed = time.time() - self.start_time
        self.checkpoints[name] = elapsed
        logger.debug(f"Checkpoint: {name}", elapsed_ms=elapsed * 1000)
    
    def end(self) -> Dict[str, float]:
        """End tracking and return summary"""
        total_duration = time.time() - self.start_time
        
        summary = {
            "operation": self.operation_name,
            "total_duration_seconds": total_duration,
            "checkpoints": self.checkpoints
        }
        
        logger.info(
            f"Operation complete: {self.operation_name}",
            duration_seconds=total_duration,
            checkpoint_count=len(self.checkpoints)
        )
        
        return summary


class HealthCheck:
    """System health monitoring"""
    
    def __init__(self):
        self.metrics = get_metrics()
    
    async def check_database(self) -> bool:
        """Check database connectivity"""
        try:
            from app.db.session import SessionLocal
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            logger.debug("Database health: OK")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def check_redis(self) -> bool:
        """Check Redis connectivity"""
        try:
            import redis
            from app.core.config import settings
            
            redis_client = redis.from_url(
                settings.redis_url.get_secret_value()
            )
            redis_client.ping()
            logger.debug("Redis health: OK")
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def check_vector_store(self) -> bool:
        """Check vector store connectivity"""
        try:
            from app.db.vector import get_vector_store
            await get_vector_store()
            logger.debug("Vector store health: OK")
            return True
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        db_healthy = await self.check_database()
        redis_healthy = await self.check_redis()
        vector_healthy = await self.check_vector_store()
        
        all_healthy = db_healthy and redis_healthy and vector_healthy
        health_score = sum([db_healthy, redis_healthy, vector_healthy]) / 3
        
        self.metrics.system_health.set(health_score)
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": time.time(),
            "health_score": health_score,
            "components": {
                "database": "ok" if db_healthy else "failed",
                "redis": "ok" if redis_healthy else "failed",
                "vector_store": "ok" if vector_healthy else "failed"
            }
        }


# Global health check instance
_health_check: Optional[HealthCheck] = None


def get_health_check() -> HealthCheck:
    """Get or initialize health check"""
    global _health_check
    if _health_check is None:
        _health_check = HealthCheck()
    return _health_check
