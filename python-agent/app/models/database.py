"""
SQLAlchemy database models for Ultimate Coding Agent
Provides ORM layer for PostgreSQL persistence with audit trails
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class BuildStatus(str, enum.Enum):
    """Build execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    """User account model with role-based access"""
    __tablename__ = "users"
    __table_args__ = (
        Index('idx_username', 'username', unique=True),
        Index('idx_email', 'email', unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # API quota
    api_calls_today = Column(Integer, default=0)
    api_quota_daily = Column(Integer, default=1000)
    storage_used_mb = Column(Float, default=0.0)
    storage_quota_mb = Column(Float, default=500.0)
    
    # Relationships
    builds = relationship("Build", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("CodeAnalysis", back_populates="user", cascade="all, delete-orphan")
    memory_entries = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")


class APIKey(Base):
    """API key for programmatic access"""
    __tablename__ = "api_keys"
    __table_args__ = (
        Index('idx_user_key', 'user_id', 'key_hash'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")


class Build(Base):
    """Build execution record with task tracking"""
    __tablename__ = "builds"
    __table_args__ = (
        Index('idx_user_builds', 'user_id', 'created_at'),
        Index('idx_build_status', 'status', 'created_at'),
    )

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Build Details
    project_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=False)
    status = Column(Enum(BuildStatus), default=BuildStatus.PENDING, nullable=False, index=True)
    
    # Execution Details
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Output
    generated_code = Column(Text, nullable=True)
    test_results = Column(JSON, nullable=True)
    build_logs = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(JSON, default=list, nullable=False)
    
    # Celery Task
    celery_task_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", back_populates="builds")
    analysis = relationship("CodeAnalysis", uselist=False, back_populates="build", cascade="all, delete-orphan")
    memory_vector = relationship("VectorMemory", back_populates="build", cascade="all, delete-orphan")


class CodeAnalysis(Base):
    """Code quality and security analysis results"""
    __tablename__ = "code_analysis"
    __table_args__ = (
        Index('idx_user_analysis', 'user_id', 'created_at'),
    )

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    build_id = Column(String(36), ForeignKey("builds.id"), nullable=True, index=True)
    
    # Analysis Results
    code_to_analyze = Column(Text, nullable=False)
    quality_score = Column(Float, default=0.0, nullable=False)
    security_score = Column(Float, default=0.0, nullable=False)
    maintainability_index = Column(Float, default=0.0, nullable=False)
    
    # Findings
    security_issues = Column(JSON, default=list, nullable=False)
    code_smells = Column(JSON, default=list, nullable=False)
    type_errors = Column(JSON, default=list, nullable=False)
    coverage_percent = Column(Float, default=0.0, nullable=False)
    
    # Recommendations
    recommendations = Column(JSON, default=list, nullable=False)
    suggested_refactorings = Column(JSON, default=list, nullable=False)
    
    # Metrics
    lines_of_code = Column(Integer, default=0)
    cyclomatic_complexity = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    analysis_duration_ms = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    build = relationship("Build", back_populates="analysis")


class VectorMemory(Base):
    """Vector embeddings for semantic search and retrieval"""
    __tablename__ = "vector_memory"
    __table_args__ = (
        Index('idx_build_memory', 'build_id'),
        Index('idx_content_type', 'content_type'),
    )

    id = Column(String(36), primary_key=True, index=True)
    build_id = Column(String(36), ForeignKey("builds.id"), nullable=True, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False)  # "code", "documentation", "test", "analysis"
    
    # Metadata for context
    source_file = Column(String(255), nullable=True)
    language = Column(String(50), nullable=True)  # "python", "javascript", etc.
    
    # Vector embedding (stored as list in JSON)
    embedding = Column(JSON, nullable=False)  # 768-dim vector from embedding model
    
    # Similarity tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    build = relationship("Build", back_populates="memory_vector")


class Memory(Base):
    """Long-term memory and conversation history"""
    __tablename__ = "memory"
    __table_args__ = (
        Index('idx_user_memory', 'user_id', 'created_at'),
        Index('idx_memory_type', 'memory_type'),
    )

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Memory Type
    memory_type = Column(String(50), nullable=False)  # "conversation", "preference", "learning", "context"
    
    # Content
    key = Column(String(255), nullable=False)
    value = Column(JSON, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # TTL for temporary memories
    
    # Importance score for prioritization
    importance = Column(Float, default=0.5, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="memory_entries")


class TelegramUser(Base):
    """Telegram user linking for bot integration"""
    __tablename__ = "telegram_users"
    __table_args__ = (
        Index('idx_telegram_id', 'telegram_id', unique=True),
        Index('idx_user_id', 'user_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255), nullable=True)
    chat_id = Column(Integer, nullable=False)
    
    # Telegram state
    is_active = Column(Boolean, default=True)
    conversation_state = Column(String(50), default="idle")  # idle, awaiting_input, processing
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_interaction = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Audit trail for security and compliance"""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('idx_user_audit', 'user_id', 'created_at'),
        Index('idx_action_time', 'action', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Action Details
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    
    # Details
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
