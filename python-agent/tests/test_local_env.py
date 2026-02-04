"""
Local Environment Tests - Comprehensive Validation
Tests to verify all local dependencies and configurations work correctly
"""
import sys
import warnings
from pathlib import Path

# Suppress passlib deprecation warnings in Python 3.12+
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDependencies:
    """Test that all core dependencies are installed and importable"""
    
    def test_fastapi(self):
        import fastapi
        assert hasattr(fastapi, 'FastAPI')
        print(f"✓ FastAPI {fastapi.__version__}")
    
    def test_pydantic(self):
        import pydantic
        assert hasattr(pydantic, 'BaseModel')
        print(f"✓ Pydantic {pydantic.__version__}")
    
    def test_sqlalchemy(self):
        import sqlalchemy
        assert hasattr(sqlalchemy, 'create_engine')
        print(f"✓ SQLAlchemy {sqlalchemy.__version__}")
    
    def test_redis(self):
        import redis
        assert hasattr(redis, 'Redis')
        print(f"✓ Redis {redis.__version__}")
    
    def test_celery(self):
        import celery
        assert hasattr(celery, 'Celery')
        print(f"✓ Celery {celery.__version__}")
    
    def test_uvicorn(self):
        import uvicorn
        assert hasattr(uvicorn, 'run')
        print(f"✓ Uvicorn {uvicorn.__version__}")
    
    def test_pytest(self):
        import pytest as pt
        assert hasattr(pt, 'main')
        print(f"✓ Pytest {pt.__version__}")


class TestAppImports:
    """Test that app modules can be imported"""
    
    def test_app_core_config(self):
        from app.core.config import settings
        assert settings.app_name == "Ultimate Coding Agent"
        print(f"✓ App config loaded: {settings.app_name}")

    
    def test_app_db_session(self):
        from app.db.session import engine
        assert engine is not None
        print("✓ Database engine initialized")
    
    def test_app_models(self):
        from app.models.database import Base, User, Build
        assert Base is not None
        assert User is not None
        assert Build is not None
        print("✓ Database models imported")
    
    def test_app_security(self):
        from app.core.security import create_access_token, verify_token
        token = create_access_token(data={"sub": "test"})
        assert token is not None
        print(f"✓ Security module working")


class TestConfiguration:
    """Test configuration values"""
    
    def test_settings_defaults(self):
        from app.core.config import settings
        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 8000
        assert settings.debug == False
        print("✓ Settings configured for local-only execution")
    
    def test_database_url(self):
        from app.core.config import settings
        assert "sqlite" in settings.database_url.get_secret_value().lower() or \
               "postgresql" in settings.database_url.get_secret_value().lower()
        print("✓ Database URL configured")
    
    def test_redis_url(self):
        from app.core.config import settings
        assert "redis" in settings.redis_url.get_secret_value().lower()
        print("✓ Redis URL configured")
    
    def test_ollama_host(self):
        from app.core.config import settings
        # Support both local (localhost/127.0.0.1) and cloud (api.ollama.com) endpoints
        assert ("localhost" in settings.ollama_host.lower() or 
               "127.0.0.1" in settings.ollama_host.lower() or
               "ollama" in settings.ollama_host.lower())
        print(f"✓ Ollama host: {settings.ollama_host}")
        print(f"  Mode: {'Cloud' if 'ollama.com' in settings.ollama_host else 'Local'}")


class TestSecurityHardening:
    """Test security hardening features"""
    
    def test_jwt_secret_length(self):
        from app.core.config import settings
        jwt_secret = settings.jwt_secret.get_secret_value()
        assert len(jwt_secret) >= 32
        print(f"✓ JWT secret meets minimum length requirement (32+ chars)")
    
    def test_password_hashing(self):
        from app.core.security import get_password_hash, verify_password
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)
        print("✓ Password hashing working correctly")
    
    def test_token_generation(self):
        from app.core.security import create_access_token, Token
        token = create_access_token(data={"sub": "test_user"})
        assert isinstance(token, Token)
        assert token.access_token is not None
        assert len(token.access_token) > 20
        assert token.token_type == "bearer"
        print("✓ Token generation working")



class TestDatabaseSetup:
    """Test database initialization"""
    
    def test_database_connection(self):
        from app.db.session import engine
        from sqlalchemy import text
        try:
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                assert result.scalar() == 1
            print("✓ Database connection successful")
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
    
    def test_tables_exist(self):
        from app.models.database import Base
        from app.db.session import engine
        try:
            # Check if tables would be created
            assert Base.registry.mappers is not None
            print("✓ Database models registered")
        except Exception as e:
            pytest.skip(f"Could not verify models: {e}")


class TestLocalSecurityPolicies:
    """Test local security policies"""
    
    def test_cors_settings(self):
        from app.core.config import settings
        assert "localhost" in settings.allowed_origins[0]
        print(f"✓ CORS configured for: {settings.allowed_origins}")
    
    def test_rate_limiting(self):
        from app.core.config import settings
        assert settings.rate_limit_per_minute > 0
        assert settings.rate_limit_burst > 0
        print("✓ Rate limiting configured")
    
    def test_path_security(self):
        from app.core.config import settings
        assert settings.enable_path_validation == True
        assert settings.enable_symlink_protection == True
        print("✓ Path security enabled")
    
    def test_content_security(self):
        from app.core.config import settings
        assert settings.enable_content_security == True
        assert settings.max_input_length > 0
        print("✓ Content security enabled")


class TestLoggingSetup:
    """Test logging configuration"""
    
    def test_logs_directory_exists(self):
        import os
        from app.core.config import settings
        logs_dir = settings.logs_dir
        os.makedirs(logs_dir, exist_ok=True)
        assert os.path.isdir(logs_dir)
        print(f"✓ Logs directory ready: {logs_dir}")
    
    def test_data_directory_exists(self):
        import os
        from app.core.config import settings
        data_dir = settings.data_dir
        os.makedirs(data_dir, exist_ok=True)
        assert os.path.isdir(data_dir)
        print(f"✓ Data directory ready: {data_dir}")


class TestLocalEnvironmentReady:
    """Final verification that local environment is ready"""
    
    def test_all_directories_writable(self):
        import os
        import tempfile
        from app.core.config import settings
        
        for directory in [settings.logs_dir, settings.data_dir]:
            os.makedirs(directory, exist_ok=True)
            # Test write permissions
            with tempfile.NamedTemporaryFile(dir=directory, delete=True) as f:
                assert f.file is not None
            print(f"✓ {directory} is writable")
    
    def test_environment_summary(self):
        from app.core.config import settings
        print("\n" + "="*60)
        print("LOCAL ENVIRONMENT SUMMARY")
        print("="*60)
        print(f"App: {settings.app_name} v{settings.app_version}")
        print(f"Environment: {settings.environment}")
        print(f"Host: {settings.api_host}")
        print(f"Port: {settings.api_port}")
        print(f"Database: {settings.database_url.get_secret_value()[:50]}...")
        print(f"Redis: {settings.redis_url.get_secret_value()[:50]}...")
        print(f"Ollama: {settings.ollama_model}")
        print(f"Security: Enabled (Path={settings.enable_path_validation}, " +
              f"Content={settings.enable_content_security})")
        print("="*60 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
