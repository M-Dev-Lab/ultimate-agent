"""
Pydantic models for API request/response validation
Provides automatic input sanitization and type checking
"""

from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field, field_validator, StringConstraints
from datetime import datetime


# ==================== Authentication Models ====================

class LoginRequest(BaseModel):
    username: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "admin",
                "password": "secure_password_123"
            }
        }
    }


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    username: Annotated[str, StringConstraints(min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')]
    email: str
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    role: str = "user"

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ['admin', 'user', 'viewer']:
            raise ValueError('Invalid role')
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== Build/Code Generation Models ====================

class BuildRequest(BaseModel):
    """Request model for project build"""
    goal: Annotated[str, StringConstraints(min_length=5, max_length=2000)]
    stack: Optional[Annotated[str, StringConstraints(max_length=100)]] = None
    name: Optional[Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9_-]+$', max_length=50)]] = None
    auto_fix: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "goal": "Create a REST API for user management with PostgreSQL",
                "stack": "python/fastapi",
                "name": "user-api-service",
                "auto_fix": True
            }
        }
    }


class BuildResponse(BaseModel):
    """Response model for build execution"""
    task_id: str
    status: str
    message: str
    created_at: datetime
    workspace_path: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "build_12345",
                "status": "queued",
                "message": "Build task created and queued for processing",
                "created_at": "2024-02-03T10:00:00Z",
                "workspace_path": "/data/workspaces/user123/build_12345"
            }
        }
    }


class BuildStatus(BaseModel):
    """Status of a build task"""
    task_id: str
    status: str  # queued, processing, completed, failed
    progress: int  # 0-100
    output: str
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ==================== Code Analysis Models ====================

class CodeAnalysisRequest(BaseModel):
    """Request for code analysis"""
    code: Annotated[str, StringConstraints(min_length=10, max_length=50000)]
    language: Annotated[str, StringConstraints(pattern=r'^(python|javascript|typescript|java|go|rust)$')]
    analysis_type: Annotated[str, StringConstraints(pattern=r'^(security|performance|style|complexity)$')]


class CodeIssue(BaseModel):
    """A single code issue found in analysis"""
    type: str  # error, warning, info
    line: int
    column: int
    message: str
    suggestion: Optional[str] = None


class CodeAnalysisResponse(BaseModel):
    """Response from code analysis"""
    language: str
    issues: List[CodeIssue]
    score: float  # 0-100
    summary: str


# ==================== Memory & Learning Models ====================

class MemoryEntry(BaseModel):
    """Memory entry for persistent learning"""
    content: Annotated[str, StringConstraints(min_length=1, max_length=5000)]
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None
    importance: int = Field(default=5, ge=1, le=10)


class MemorySearchRequest(BaseModel):
    """Request to search memory"""
    query: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    limit: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class MemorySearchResponse(BaseModel):
    """Search results from memory"""
    query: str
    results: List[Dict[str, Any]]
    total: int


# ==================== Telegram Integration Models ====================

class TelegramMessageRequest(BaseModel):
    """Request from Telegram webhook"""
    chat_id: int
    message: str
    user_id: int
    command: Optional[str] = None


class TelegramResponse(BaseModel):
    """Response to send to Telegram"""
    chat_id: int
    message: str
    parse_mode: str = "Markdown"
    reply_markup: Optional[Dict[str, Any]] = None


# ==================== System Status Models ====================

class SystemStatus(BaseModel):
    """System health and status"""
    timestamp: datetime
    status: str  # healthy, degraded, unhealthy
    ollama_status: str
    database_status: str
    redis_status: str
    memory_usage: float  # percentage
    disk_usage: float   # percentage
    active_tasks: int
    error_rate: float


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    environment: str


# ==================== Error Models ====================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: str
    status_code: int
    timestamp: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "validation_error",
                "detail": "Project name must contain only alphanumeric characters",
                "status_code": 400,
                "timestamp": "2024-02-03T10:00:00Z"
            }
        }
    }


# ==================== Skills/Tools Models ====================

class SkillMetadata(BaseModel):
    """Metadata for an available skill"""
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    tags: List[str]


class SkillExecutionRequest(BaseModel):
    """Request to execute a skill"""
    skill_id: str
    parameters: Dict[str, Any]
    timeout: int = Field(default=30, ge=5, le=300)


class SkillExecutionResponse(BaseModel):
    """Result of skill execution"""
    skill_id: str
    status: str
    result: Any
    execution_time: float
    error: Optional[str] = None


# ==================== Build Status Models ====================

class BuildStatus(BaseModel):
    """Status of a build task"""
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int = Field(default=0, ge=0, le=100)
    output: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BuildStatusResponse(BaseModel):
    """Response for build status query"""
    task_id: str
    status: str
    progress: int
    output: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime


class BuildHistoryResponse(BaseModel):
    """Build history entry"""
    task_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
