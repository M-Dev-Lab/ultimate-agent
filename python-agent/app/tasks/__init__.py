"""
Celery configuration and task queue setup.

Celery handles asynchronous task execution including:
  - Long-running build tasks
  - Scheduled maintenance jobs
  - Retry logic with exponential backoff
  - Task monitoring and metrics

Phase 2: Celery integration for production task processing.
Currently using FastAPI BackgroundTasks for MVP.
"""

from celery import Celery
from celery.schedules import crontab
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    settings.app_name,
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task routing
    task_routes={
        "app.tasks.build.execute_build": {"queue": "builds"},
        "app.tasks.analysis.analyze_code": {"queue": "analysis"},
        "app.tasks.maintenance.*": {"queue": "maintenance"},
    },
    
    # Task execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    
    # Retry policy
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Result settings
    result_expires=3600,  # 1 hour
    result_compression="gzip",
    
    # Monitoring
    worker_disable_rate_limits=False,
)


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-expired-tasks": {
        "task": "app.tasks.maintenance.cleanup_expired_builds",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    "health-check": {
        "task": "app.tasks.maintenance.health_check",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}


# Task definitions (Phase 2: implement actual tasks)
@celery_app.task(bind=True, max_retries=3)
def execute_build_task(self, task_id: str, project_name: str, goal: str):
    """
    Execute build task asynchronously.
    
    Args:
        task_id: Unique build identifier
        project_name: Project name
        goal: Build goal/description
    
    Returns:
        Task result with status and output
    
    Raises:
        Exception: If build execution fails (triggers retry)
    """
    try:
        logger.info(
            "Build task started",
            extra={"task_id": task_id, "project": project_name},
        )
        
        # Phase 2: Implement actual build execution
        # 1. Clone/prepare project
        # 2. Run LangGraph agent
        # 3. Execute generated code
        # 4. Collect results
        
        return {
            "task_id": task_id,
            "status": "completed",
            "results": {
                "generated_files": ["module.py"],
                "tests_passed": 12,
            },
        }
        
    except Exception as exc:
        logger.error(
            "Build task failed",
            extra={
                "task_id": task_id,
                "attempt": self.request.retries,
                "error": str(exc),
            },
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=2)
def analyze_code_task(self, analysis_id: str, project_name: str):
    """
    Analyze code quality, security, and types.
    
    Args:
        analysis_id: Unique analysis identifier
        project_name: Project name
    
    Returns:
        Analysis results
    """
    try:
        logger.info(
            "Code analysis started",
            extra={"analysis_id": analysis_id, "project": project_name},
        )
        
        # Phase 2: Implement actual analysis
        # 1. Run pylint/flake8
        # 2. Run bandit (security)
        # 3. Run mypy (types)
        # 4. Generate report
        
        return {
            "analysis_id": analysis_id,
            "quality_score": 8.5,
            "security_issues": [],
            "type_errors": 0,
        }
        
    except Exception as exc:
        logger.error(
            "Code analysis failed",
            extra={
                "analysis_id": analysis_id,
                "error": str(exc),
            },
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_expired_builds():
    """
    Periodic task: Clean up expired build records.
    
    Runs every 6 hours.
    Removes builds older than 30 days.
    """
    try:
        logger.info("Cleanup task: removing expired builds")
        # Phase 2: Implement database cleanup
        return {"cleaned": 0}
    except Exception as e:
        logger.error("Cleanup task failed", extra={"error": str(e)})


@celery_app.task
def health_check():
    """
    Periodic task: Monitor system health.
    
    Runs every 5 minutes.
    Checks database, cache, and service status.
    """
    try:
        logger.info("Health check running")
        # Phase 2: Implement health checks
        return {"status": "healthy"}
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})


# Task monitoring and metrics
class TaskMetrics:
    """Track task execution metrics."""
    
    @staticmethod
    def on_task_success(sender=None, result=None, **kwargs):
        """Called when task completes successfully."""
        logger.info(
            "task_completed",
            extra={"task_id": sender.request.id, "result": result},
        )
    
    @staticmethod
    def on_task_failure(sender=None, exception=None, **kwargs):
        """Called when task fails."""
        logger.error(
            "task_failed",
            extra={
                "task_id": sender.request.id,
                "exception": str(exception),
            },
        )
    
    @staticmethod
    def on_task_retry(sender=None, einfo=None, **kwargs):
        """Called when task is retried."""
        logger.warning(
            "task_retry",
            extra={
                "task_id": sender.request.id,
                "retries": sender.request.retries,
            },
        )


# Register signal handlers
celery_app.on_after_task_publish.connect(
    lambda sender, body, exchange, routing_key, **kwargs: logger.info(
        "Task published", extra={"routing_key": routing_key}
    )
)
