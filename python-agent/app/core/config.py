"""
Configuration management for Ultimate Coding Agent (Python)
Centralized settings with security best practices
"""

from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import SecretStr, Field, field_validator, ConfigDict


class Settings(BaseSettings):
    """Application settings with automatic environment variable loading"""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env file
    )

    # ==================== API Configuration ====================
    app_name: str = "Ultimate Coding Agent"
    app_version: str = "3.0.0"
    debug: bool = False
    environment: str = Field(default="development", pattern="^(development|staging|production)$")

    # ==================== Server Configuration ====================
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_workers: int = 1
    request_timeout: int = 30
    max_concurrent_tasks: int = 3

    # ==================== Security Configuration ====================
    jwt_secret: SecretStr = Field(..., description="Secret key for JWT encoding")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # CORS Configuration
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10
    
    # File Upload Security
    max_file_size_mb: int = 10
    allowed_file_extensions: List[str] = [".py", ".js", ".ts", ".json", ".md", ".yml", ".yaml"]

    # ==================== Database Configuration ====================
    database_url: SecretStr = Field(default="sqlite:///./app.db")
    db_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # ==================== Redis Configuration ====================
    redis_url: SecretStr = Field(default="redis://localhost:6379/0")
    redis_cache_ttl: int = 3600
    session_expiration_hours: int = 24

    # ==================== Ollama Configuration (Local via SSH tunnel) ====================
    ollama_host: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5-coder:480b")
    ollama_api_key: Optional[SecretStr] = Field(default=None, description="Optional API key for Ollama Cloud")
    ollama_timeout: int = 300

    # ==================== Telegram Bot Configuration ====================
    telegram_bot_token: SecretStr = Field(default="")
    admin_telegram_ids: List[int] = Field(default=[])
    telegram_webhook_url: Optional[str] = None

    # ==================== Celery Configuration ====================
    celery_broker_url: SecretStr = Field(default="redis://localhost:6379/1")
    celery_result_backend: SecretStr = Field(default="redis://localhost:6379/2")
    celery_task_timeout: int = 3600

    # ==================== Monitoring & Logging ====================
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    prometheus_enabled: bool = True
    prometheus_port: int = 8001
    
    # Sentry Configuration (Optional)
    sentry_dsn: Optional[SecretStr] = None
    
    # ==================== File Paths ====================
    data_dir: str = "./data"
    workspace_dir: str = "./data/workspaces"
    memory_dir: str = "./data/memory"
    logs_dir: str = "./logs"

    # ==================== Security Hardening ====================
    # Command Execution
    allowed_commands: List[str] = ["git", "npm", "python", "node", "docker", "npm"]
    restricted_env_vars: List[str] = ["AWS_SECRET_ACCESS_KEY", "DATABASE_PASSWORD", "JWT_SECRET"]
    
    # Path Security
    enable_path_validation: bool = True
    enable_symlink_protection: bool = True
    
    # Input Validation
    enable_content_security: bool = True
    max_input_length: int = 10000

    # ==================== Feature Flags ====================
    enable_auto_learning: bool = True
    enable_memory_persistence: bool = True
    enable_monitoring: bool = True
    enable_rate_limiting: bool = True

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret is strong enough"""
        if len(v.get_secret_value()) < 32:
            raise ValueError("JWT secret must be at least 32 characters long")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_db_url(cls, v):
        """Validate database URL format"""
        url = v.get_secret_value()
        if not any(url.startswith(prefix) for prefix in ["postgresql://", "sqlite://", "mysql://"]):
            raise ValueError("Database URL must start with valid scheme (postgresql, sqlite, mysql)")
        return v


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency to get settings instance"""
    return settings
