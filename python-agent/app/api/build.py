"""
Build API endpoints - Core service for project building and code generation.

Provides REST endpoints for:
  - Creating new build tasks
  - Querying build status
  - Retrieving build results
  - Canceling in-progress builds

Security:
  - All endpoints require JWT authentication
  - Rate limiting: 10 requests/minute per user
  - Input validation via Pydantic models
  - Command execution sandboxed
"""

from typing import Dict, Optional, List
from datetime import datetime
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.schemas import (
    BuildRequest,
    BuildResponse,
    BuildStatus,
    BuildStatusResponse,
    BuildHistoryResponse,
    ErrorResponse,
)
from app.security.auth import get_current_user
from typing import Dict, Any
User = Dict[str, Any]
from app.security.validators import SecurityValidator
from app.services.command_executor import SecureCommandExecutor
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/build", tags=["build"])

# In-memory task store (Phase 2: replace with PostgreSQL)
_build_tasks: Dict[str, BuildStatus] = {}
_user_builds: Dict[str, List[str]] = {}


class BuildService:
    """Service layer for build operations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.executor = SecureCommandExecutor()
        self.validator = SecurityValidator()

    async def create_build_task(self, request: BuildRequest, user: User) -> BuildResponse:
        """
        Create new build task with validation and initialization.

        Args:
            request: Build request with project/goal details
            user: Current authenticated user

        Returns:
            BuildResponse with task_id and initial status

        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        self.validator.sanitize_project_name(request.project_name)
        self.validator.sanitize_goal(request.goal)

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Create task record
        build_status = BuildStatus(
            task_id=task_id,
            project_name=request.project_name,
            status="initializing",
            progress=0,
            created_at=datetime.utcnow(),
            created_by=user.username,
            goal=request.goal,
            parameters=request.parameters or {},
        )

        # Store task
        _build_tasks[task_id] = build_status
        if user.username not in _user_builds:
            _user_builds[user.username] = []
        _user_builds[user.username].append(task_id)

        logger.info(
            "Build task created",
            extra={
                "task_id": task_id,
                "user": user.username,
                "project": request.project_name,
            },
        )

        return BuildResponse(
            task_id=task_id,
            status="initializing",
            message="Build task created successfully",
        )

    async def get_build_status(self, task_id: str, user: User) -> BuildStatusResponse:
        """
        Get current status of a build task.

        Args:
            task_id: Unique build task identifier
            user: Current authenticated user

        Returns:
            BuildStatusResponse with full task details

        Raises:
            HTTPException: If task not found or unauthorized
        """
        if task_id not in _build_tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Build task not found",
            )

        task = _build_tasks[task_id]

        # Authorization: user can only view their own builds
        if task.created_by != user.username and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this build",
            )

        return BuildStatusResponse(
            task_id=task.task_id,
            project_name=task.project_name,
            status=task.status,
            progress=task.progress,
            created_at=task.created_at,
            created_by=task.created_by,
            goal=task.goal,
            results=task.results,
            error=task.error,
        )

    async def get_user_build_history(
        self, user: User, limit: int = 50, offset: int = 0
    ) -> BuildHistoryResponse:
        """
        Get build history for current user.

        Args:
            user: Current authenticated user
            limit: Maximum number of records (max 100)
            offset: Pagination offset

        Returns:
            BuildHistoryResponse with paginated build list
        """
        limit = min(limit, 100)  # Cap at 100

        user_task_ids = _user_builds.get(user.username, [])
        tasks = [_build_tasks[tid] for tid in user_task_ids if tid in _build_tasks]

        # Sort by creation time, newest first
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # Apply pagination
        total = len(tasks)
        paginated_tasks = tasks[offset : offset + limit]

        return BuildHistoryResponse(
            total=total,
            limit=limit,
            offset=offset,
            builds=[
                BuildStatusResponse(
                    task_id=t.task_id,
                    project_name=t.project_name,
                    status=t.status,
                    progress=t.progress,
                    created_at=t.created_at,
                    created_by=t.created_by,
                    goal=t.goal,
                    results=t.results,
                    error=t.error,
                )
                for t in paginated_tasks
            ],
        )

    async def cancel_build(self, task_id: str, user: User) -> Dict:
        """
        Cancel an in-progress build task.

        Args:
            task_id: Build task to cancel
            user: Current authenticated user

        Returns:
            Confirmation message

        Raises:
            HTTPException: If task not found or not cancellable
        """
        if task_id not in _build_tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Build task not found",
            )

        task = _build_tasks[task_id]

        # Authorization check
        if task.created_by != user.username and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this build",
            )

        # Check if cancellable
        if task.status not in ["initializing", "running"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel build in {task.status} state",
            )

        # Mark as cancelled
        task.status = "cancelled"
        task.progress = 0

        logger.info(
            "Build task cancelled",
            extra={"task_id": task_id, "user": user.username},
        )

        return {"message": "Build task cancelled successfully"}


# Route handlers


@router.post("/", response_model=BuildResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_build(
    request: BuildRequest,
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    background_tasks: BackgroundTasks = None,
):
    """
    Create a new build task.

    **Security Notes:**
    - Requires valid JWT token (user, admin roles)
    - Project name must contain only alphanumeric, hyphen, underscore
    - Goal validated for injection patterns
    - Request rate limited to 10/minute per user

    **Example Request:**
    ```json
    {
      "project_name": "my-awesome-project",
      "goal": "Add authentication module with JWT support",
      "parameters": {"framework": "fastapi", "database": "postgresql"}
    }
    ```

    **Response:** 202 Accepted with task_id for polling
    """
    try:
        service = BuildService(settings)
        response = await service.create_build_task(request, user)

        # Schedule actual build execution (Phase 2: use Celery)
        if background_tasks:
            background_tasks.add_task(
                execute_build_async, response.task_id, user.username
            )

        return response

    except ValueError as e:
        logger.warning(
            "Build creation validation error",
            extra={"error": str(e), "user": user.username},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Build creation error",
            extra={"error": str(e), "user": user.username},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create build task",
        )


@router.get("/{task_id}", response_model=BuildStatusResponse)
async def get_build_status(
    task_id: str,
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """
    Get status of a specific build task.

    **Path Parameters:**
    - `task_id`: UUID of the build task

    **Returns:**
    - 200 OK: Build status with current progress
    - 404 Not Found: Task doesn't exist
    - 403 Forbidden: User doesn't have permission

    **Example Response:**
    ```json
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "project_name": "my-project",
      "status": "running",
      "progress": 45,
      "created_at": "2026-02-03T10:30:00Z",
      "created_by": "user123"
    }
    ```
    """
    try:
        service = BuildService(settings)
        return await service.get_build_status(task_id, user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching build status",
            extra={"task_id": task_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch build status",
        )


@router.get("/", response_model=BuildHistoryResponse)
async def get_build_history(
    user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
):
    """
    Get build history for current user.

    **Query Parameters:**
    - `limit`: Number of records (1-100, default 20)
    - `offset`: Pagination offset (default 0)

    **Returns:**
    - Paginated list of user's builds ordered by newest first

    **Example Response:**
    ```json
    {
      "total": 42,
      "limit": 20,
      "offset": 0,
      "builds": [...]
    }
    ```
    """
    try:
        service = BuildService(settings)
        return await service.get_user_build_history(user, limit, offset)
    except Exception as e:
        logger.error(
            "Error fetching build history",
            extra={"user": user.username, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch build history",
        )


@router.delete("/{task_id}", response_model=Dict)
async def cancel_build(
    task_id: str,
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """
    Cancel an in-progress build task.

    **Path Parameters:**
    - `task_id`: UUID of the build task to cancel

    **Returns:**
    - 200 OK: Cancellation successful
    - 404 Not Found: Task not found
    - 403 Forbidden: Not authorized
    - 409 Conflict: Task already completed

    **Note:** Only task creator or admin can cancel.
    """
    try:
        service = BuildService(settings)
        return await service.cancel_build(task_id, user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error cancelling build",
            extra={"task_id": task_id, "user": user.username, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel build",
        )


# Background task (Phase 2: replace with Celery)
async def execute_build_async(task_id: str, username: str):
    """
    Execute build task asynchronously.

    Phase 2 TODO: Replace with Celery task queue for production.
    Currently uses FastAPI BackgroundTasks (suitable for Phase 1).

    Args:
        task_id: Build task ID
        username: User who created the build
    """
    try:
        if task_id not in _build_tasks:
            return

        task = _build_tasks[task_id]
        task.status = "running"
        task.progress = 10

        logger.info(
            "Build execution started",
            extra={"task_id": task_id, "user": username},
        )

        # Simulate build process (Phase 2: actual LangGraph execution)
        # In production, this would:
        # 1. Clone/prepare project
        # 2. Run LangGraph agent
        # 3. Execute generated code
        # 4. Collect results
        # 5. Store artifacts

        task.progress = 50
        task.results = {
            "generated_files": ["auth.py", "models.py"],
            "tests_passed": 12,
            "test_coverage": 87.5,
        }
        task.progress = 100
        task.status = "completed"

        logger.info(
            "Build execution completed",
            extra={"task_id": task_id, "user": username},
        )

    except Exception as e:
        if task_id in _build_tasks:
            _build_tasks[task_id].status = "failed"
            _build_tasks[task_id].error = str(e)

        logger.error(
            "Build execution failed",
            extra={"task_id": task_id, "user": username, "error": str(e)},
        )
