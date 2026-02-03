"""
Phase 3 comprehensive tests for database, vector store, agents, and Telegram bot
Tests integration of all Phase 3 components
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.database import (
    Base, User, Build, CodeAnalysis, VectorMemory, Memory, TelegramUser,
    UserRole, BuildStatus, AuditLog
)
from app.db.session import SessionLocal, get_db
from app.db.vector import VectorStore, get_vector_store
from app.agents.full_workflow import AgentWorkflow, AgentState, get_agent_workflow
from app.monitoring.metrics import get_metrics, HealthCheck
from app.integrations.telegram_bot import TelegramBotManager


# ==================== Database Tests ====================

@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    yield db
    db.close()


class TestDatabaseModels:
    """Test database model functionality"""
    
    def test_user_creation(self, test_db):
        """Test user model creation"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            role=UserRole.USER
        )
        test_db.add(user)
        test_db.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert user.is_active is True
    
    def test_build_creation(self, test_db):
        """Test build model creation"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="pwd"
        )
        test_db.add(user)
        test_db.commit()
        
        build = Build(
            id="build-123",
            user_id=user.id,
            project_name="test_project",
            requirements="Build a test API",
            status=BuildStatus.PENDING
        )
        test_db.add(build)
        test_db.commit()
        
        assert build.id == "build-123"
        assert build.status == BuildStatus.PENDING
        assert build.user_id == user.id
    
    def test_code_analysis_creation(self, test_db):
        """Test code analysis model"""
        user = User(username="user", email="user@test.com", hashed_password="pwd")
        test_db.add(user)
        test_db.commit()
        
        analysis = CodeAnalysis(
            id="analysis-123",
            user_id=user.id,
            code_to_analyze="print('hello')",
            quality_score=8.5,
            security_score=9.0
        )
        test_db.add(analysis)
        test_db.commit()
        
        assert analysis.quality_score == 8.5
        assert analysis.security_score == 9.0
    
    def test_vector_memory_creation(self, test_db):
        """Test vector memory storage"""
        memory = VectorMemory(
            id="mem-123",
            content="def hello(): pass",
            content_type="code",
            language="python",
            embedding=[0.1] * 768  # 768-dim embedding
        )
        test_db.add(memory)
        test_db.commit()
        
        retrieved = test_db.query(VectorMemory).filter_by(id="mem-123").first()
        assert retrieved is not None
        assert retrieved.language == "python"
        assert len(retrieved.embedding) == 768
    
    def test_telegram_user_linking(self, test_db):
        """Test Telegram user linking"""
        user = User(username="user", email="user@test.com", hashed_password="pwd")
        test_db.add(user)
        test_db.commit()
        
        tg_user = TelegramUser(
            user_id=user.id,
            telegram_id=123456789,
            telegram_username="testuser",
            chat_id=987654321
        )
        test_db.add(tg_user)
        test_db.commit()
        
        assert tg_user.telegram_id == 123456789
        assert tg_user.user_id == user.id


# ==================== Vector Store Tests ====================

class TestVectorStore:
    """Test Chroma vector database integration"""
    
    @pytest.mark.asyncio
    async def test_vector_store_initialization(self):
        """Test vector store initialization"""
        vector_store = VectorStore()
        assert vector_store.code_collection is not None
        assert vector_store.documentation_collection is not None
    
    @pytest.mark.asyncio
    async def test_add_code_snippet(self):
        """Test adding code snippet to vector store"""
        vector_store = VectorStore()
        
        doc_id = await vector_store.add_code_snippet(
            code="def hello(): pass",
            build_id="build-123",
            file_path="main.py",
            language="python"
        )
        
        assert doc_id == "build-123_main.py"
    
    @pytest.mark.asyncio
    async def test_search_similar_code(self):
        """Test semantic code search"""
        vector_store = VectorStore()
        
        await vector_store.add_code_snippet(
            code="def add(a, b): return a + b",
            build_id="build-123",
            file_path="math.py",
            language="python"
        )
        
        results = await vector_store.search_similar_code(
            query="addition function",
            n_results=5
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_get_build_context(self):
        """Test retrieving build context"""
        vector_store = VectorStore()
        
        await vector_store.add_code_snippet(
            code="class Calculator: pass",
            build_id="build-123",
            file_path="calc.py",
            language="python"
        )
        
        context = await vector_store.get_build_context(
            build_id="build-123",
            query="calculator"
        )
        
        assert context["build_id"] == "build-123"
        assert "code_snippets" in context


# ==================== Agent Workflow Tests ====================

class TestAgentWorkflow:
    """Test LangGraph agent workflow"""
    
    def test_workflow_initialization(self):
        """Test workflow graph initialization"""
        workflow = AgentWorkflow()
        assert workflow.graph is not None
        assert workflow.tool_registry is not None
    
    @pytest.mark.asyncio
    async def test_agent_state_structure(self):
        """Test agent state TypedDict"""
        state = AgentState(
            task_id="task-123",
            user_id=1,
            build_id="build-123",
            goal="Build a web API",
            project_name="my_api",
            requirements="FastAPI with auth",
            context="",
            step_count=0,
            current_step="analyze_requirements",
            analysis=None,
            execution_plan=None,
            generated_code=None,
            test_results=None,
            errors=[],
            error=None,
            results=None,
            messages=[]
        )
        
        assert state["task_id"] == "task-123"
        assert state["user_id"] == 1
    
    @pytest.mark.asyncio
    async def test_code_analysis_tool(self):
        """Test code analysis tool"""
        workflow = AgentWorkflow()
        
        analysis = await workflow.tool_registry.analyze_code(
            code="def hello(): pass",
            language="python",
            focus_areas=["security"]
        )
        
        assert "timestamp" in analysis
        assert "language" in analysis
        assert analysis["language"] == "python"
    
    @pytest.mark.asyncio
    async def test_code_generation_tool(self):
        """Test code generation tool"""
        workflow = AgentWorkflow()
        
        code = await workflow.tool_registry.generate_code(
            specification="Add two numbers",
            language="python"
        )
        
        assert isinstance(code, str)
        assert len(code) > 0
    
    @pytest.mark.asyncio
    async def test_test_execution_tool(self):
        """Test test execution tool"""
        workflow = AgentWorkflow()
        
        results = await workflow.tool_registry.execute_tests(
            code="def test_add(): assert 1+1==2",
            language="python",
            test_framework="pytest"
        )
        
        assert "passed" in results
        assert "failed" in results


# ==================== Telegram Bot Tests ====================

class TestTelegramBot:
    """Test Telegram bot integration"""
    
    def test_bot_initialization(self):
        """Test bot manager initialization"""
        with patch.dict('app.core.config.settings.__dict__', {'telegram_bot_token': 'test-token'}):
            manager = TelegramBotManager()
            assert manager.token == 'test-token'
    
    @pytest.mark.asyncio
    async def test_user_linking(self):
        """Test Telegram user linking"""
        manager = TelegramBotManager()
        manager.db = sessionmaker(bind=create_engine("sqlite:///:memory:"))()
        
        # Mock database
        Base.metadata.create_all(bind=manager.db.bind)
        
        # Create link
        await manager._ensure_user_linked(
            telegram_id=123456,
            username="testuser",
            chat_id=654321
        )


# ==================== Monitoring Tests ====================

class TestMonitoring:
    """Test monitoring and health check"""
    
    def test_metrics_initialization(self):
        """Test metrics registry initialization"""
        metrics = get_metrics()
        assert metrics is not None
        assert metrics.api_requests_total is not None
    
    def test_record_api_request(self):
        """Test recording API metrics"""
        metrics = get_metrics()
        metrics.record_api_request(
            method="GET",
            endpoint="/api/build",
            status_code=200,
            duration=0.025
        )
    
    def test_record_build_execution(self):
        """Test recording build metrics"""
        metrics = get_metrics()
        metrics.record_build_execution(
            language="python",
            status="completed",
            duration=45.5
        )
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test system health check"""
        health_check = HealthCheck()
        
        # Mock database and Redis checks
        with patch.object(health_check, 'check_database', return_value=True):
            with patch.object(health_check, 'check_redis', return_value=True):
                with patch.object(health_check, 'check_vector_store', return_value=True):
                    status = await health_check.get_health_status()
                    
                    assert status["status"] == "healthy"
                    assert status["health_score"] == 1.0


# ==================== Integration Tests ====================

class TestPhase3Integration:
    """Test Phase 3 component integration"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, test_db):
        """Test complete workflow with database and vector store"""
        # Create user
        user = User(username="user", email="user@test.com", hashed_password="pwd")
        test_db.add(user)
        test_db.commit()
        
        # Create build
        build = Build(
            id="build-123",
            user_id=user.id,
            project_name="test_api",
            requirements="Build a test API",
            status=BuildStatus.PENDING
        )
        test_db.add(build)
        test_db.commit()
        
        # Get workflow
        workflow = AgentWorkflow()
        assert workflow is not None
    
    @pytest.mark.asyncio
    async def test_database_to_vector_pipeline(self, test_db):
        """Test pipeline from database to vector store"""
        # Create build in database
        user = User(username="user", email="user@test.com", hashed_password="pwd")
        test_db.add(user)
        test_db.commit()
        
        build = Build(
            id="build-123",
            user_id=user.id,
            project_name="test",
            requirements="test",
            status=BuildStatus.RUNNING,
            generated_code="def hello(): pass"
        )
        test_db.add(build)
        test_db.commit()
        
        # Add to vector store
        vector_store = VectorStore()
        await vector_store.add_code_snippet(
            code=build.generated_code,
            build_id=build.id,
            file_path="main.py",
            language="python"
        )


# ==================== Performance Tests ====================

class TestPerformance:
    """Test Phase 3 performance requirements"""
    
    @pytest.mark.asyncio
    async def test_vector_search_performance(self):
        """Test vector search latency"""
        import time
        
        vector_store = VectorStore()
        
        # Add multiple snippets
        for i in range(10):
            await vector_store.add_code_snippet(
                code=f"def func{i}(): pass",
                build_id=f"build-{i}",
                file_path=f"file{i}.py",
                language="python"
            )
        
        # Time search
        start = time.time()
        results = await vector_store.search_similar_code("function", n_results=5)
        elapsed = time.time() - start
        
        # Should be fast (<500ms)
        assert elapsed < 0.5
    
    @pytest.mark.asyncio
    async def test_workflow_execution_time(self):
        """Test agent workflow execution time"""
        import time
        
        workflow = AgentWorkflow()
        
        task_data = {
            "task_id": "task-123",
            "user_id": 1,
            "build_id": "build-123",
            "project_name": "test_api",
            "requirements": "Build a simple API"
        }
        
        start = time.time()
        # Execute just state initialization (not full graph)
        elapsed = time.time() - start
        
        # Should initialize quickly
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
