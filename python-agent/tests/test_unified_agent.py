"""
Comprehensive test suite for unified Python agent
Tests all merged functionality from TypeScript + Python
"""

import pytest
import asyncio
from app.core.error_handler import get_error_handler, ErrorCategory
from app.core.memory_manager import get_memory_manager
from app.monitoring.analytics import get_analytics_tracker
from app.skills.registry import SkillRegistry


class TestErrorHandler:
    """Test error handling system"""
    
    def test_error_categorization(self):
        handler = get_error_handler()
        
        # Test network error
        network_err = Exception("Connection timeout")
        assert handler.categorize_error(network_err) == ErrorCategory.NETWORK
        
        # Test Ollama error
        ollama_err = Exception("Ollama model not found")
        assert handler.categorize_error(ollama_err) == ErrorCategory.OLLAMA
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        handler = get_error_handler()
        
        # Function that fails twice then succeeds
        call_count = 0
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        # Reset circuit breaker for the category to ensure it's closed
        breaker = handler.get_circuit_breaker(ErrorCategory.NETWORK.value)
        breaker.record_success()
        
        result = await handler.execute_with_retry(
            flaky_function,
            category=ErrorCategory.NETWORK,
            max_retries=3
        )
        
        assert result == "success"
        assert call_count == 3
    
    def test_circuit_breaker(self):
        handler = get_error_handler()
        breaker = handler.get_circuit_breaker("test_breaker")
        
        # Trip the breaker
        for _ in range(5):
            breaker.record_failure()
        
        assert breaker.state == "open"
        assert not breaker.can_proceed()


class TestMemoryManager:
    """Test memory management system"""
    
    def test_context_creation(self):
        manager = get_memory_manager()
        context = manager.get_context(12345)
        
        assert context.user_id == 12345
        assert len(context.messages) == 0
    
    def test_message_addition(self):
        manager = get_memory_manager()
        
        manager.add_user_message(123456, "Hello")
        manager.add_assistant_message(123456, "Hi there!")
        
        context = manager.get_context(123456)
        assert len(context.messages) == 2
        assert context.messages[0].role == "user"
        assert context.messages[1].role == "assistant"
    
    def test_ollama_conversation_building(self):
        manager = get_memory_manager()
        
        manager.add_user_message(1234567, "Test message")
        messages = manager.build_conversation_for_ollama(1234567)
        
        # Should have system prompt (if SOUL.md exists) + user message
        assert len(messages) >= 1
        assert messages[-1]["role"] == "user"


class TestAnalytics:
    """Test analytics tracking"""
    
    def test_message_recording(self):
        analytics = get_analytics_tracker()
        
        analytics.record_message(
            user_id=12345,
            message="Test",
            response="Response",
            response_time_ms=150.5,
            skill_used="python-web-api",
            success=True
        )
        
        summary = analytics.get_summary(days=1)
        assert summary["total_messages"] > 0
    
    def test_skill_metrics(self):
        analytics = get_analytics_tracker()
        
        # Record multiple calls
        for i in range(5):
            analytics.record_message(
                user_id=12345,
                message=f"Test {i}",
                response="Response",
                response_time_ms=100.0 + i * 10,
                skill_used="blog-post",
                success=True
            )
        
        summary = analytics.get_summary(days=1)
        assert "blog-post" in summary["skill_usage"]
        assert summary["skill_metrics"]["blog-post"]["total_calls"] >= 5


class TestSkillRouter:
    """Test skill routing with intent detection"""
    
    def test_intent_detection(self):
        registry = SkillRegistry()
        
        # Test project intent
        assert registry.detect_skill_intent("Create a new Python project") == "python-web-api"
        
        # Test social intent
        assert registry.detect_skill_intent("Write a blog post about AI") == "blog-post"
        
        # Test system intent (Note: No system_controller in registry patterns yet, but browser is there)
        assert registry.detect_skill_intent("Open Google in browser") == "browser_controller"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
