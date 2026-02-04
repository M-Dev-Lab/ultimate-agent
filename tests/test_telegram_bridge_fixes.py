"""
Test suite for Telegram Bridge and Ollama integration fixes
Tests Phase 1 core connection fixes
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from datetime import datetime

# Add app to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "python-agent"))

from app.integrations.telegram_bridge import TelegramAgentBridge, get_telegram_bridge
from app.integrations.ollama import OllamaClient
from app.integrations.agent_handler import AgentHandler, WorkflowState


class TestOllamaResponseParsing:
    """Test Ollama response parsing with multiple formats"""
    
    def test_extract_response_chat_format(self):
        """Test extraction from chat endpoint format"""
        ollama = OllamaClient()
        
        response = {
            "message": {
                "role": "assistant",
                "content": "This is the AI response"
            },
            "done": True
        }
        
        result = ollama._extract_response(response)
        assert result == "This is the AI response"
    
    def test_extract_response_generate_format(self):
        """Test extraction from generate endpoint format"""
        ollama = OllamaClient()
        
        response = {
            "response": "This is a generated response",
            "done": True
        }
        
        result = ollama._extract_response(response)
        assert result == "This is a generated response"
    
    def test_extract_response_string_input(self):
        """Test handling of string input"""
        ollama = OllamaClient()
        
        result = ollama._extract_response("Direct string response")
        assert result == "Direct string response"
    
    def test_extract_response_openai_format(self):
        """Test extraction from OpenAI-compatible format"""
        ollama = OllamaClient()
        
        response = {
            "choices": [
                {
                    "message": {
                        "content": "OpenAI format response"
                    }
                }
            ]
        }
        
        result = ollama._extract_response(response)
        assert result == "OpenAI format response"
    
    def test_extract_response_empty_fallback(self):
        """Test that empty string is returned on failure"""
        ollama = OllamaClient()
        
        response = {"unknown_field": "value"}
        
        result = ollama._extract_response(response)
        assert result == ""
    
    def test_extract_response_strips_whitespace(self):
        """Test that whitespace is stripped"""
        ollama = OllamaClient()
        
        response = {
            "message": {
                "content": "  Response with whitespace  \n"
            }
        }
        
        result = ollama._extract_response(response)
        assert result == "Response with whitespace"


class TestTelegramBridge:
    """Test Telegram bridge message processing"""
    
    @pytest.mark.asyncio
    async def test_process_message_with_valid_response(self):
        """Test processing message with valid agent response"""
        # Mock the agent handler
        with patch('app.integrations.telegram_bridge.get_agent_handler') as mock_handler:
            mock_handler_instance = AsyncMock()
            mock_handler.return_value = mock_handler_instance
            
            # Simulate agent response
            mock_handler_instance.process_message.return_value = {
                "text": "Hello from AI",
                "buttons": [
                    [{"text": "Button 1"}],
                    [{"text": "Button 2"}]
                ]
            }
            
            bridge = TelegramAgentBridge()
            result = await bridge.process_telegram_message(user_id=12345, message="Hi")
            
            assert "text" in result
            assert "Hello from AI" in result["text"]
            assert result["keyboard"] is not None
    
    @pytest.mark.asyncio
    async def test_process_message_with_exception(self):
        """Test handling of exceptions in message processing"""
        with patch('app.integrations.telegram_bridge.get_agent_handler') as mock_handler:
            mock_handler_instance = AsyncMock()
            mock_handler.return_value = mock_handler_instance
            
            # Simulate error
            mock_handler_instance.process_message.side_effect = Exception("Test error")
            
            bridge = TelegramAgentBridge()
            result = await bridge.process_telegram_message(user_id=12345, message="Hi")
            
            assert "Error" in result["text"]
            assert result["keyboard"] is None
    
    def test_has_html_tags(self):
        """Test HTML tag detection"""
        bridge = TelegramAgentBridge()
        
        assert bridge._has_html_tags("<b>Bold text</b>") is True
        assert bridge._has_html_tags("Plain text") is False
        assert bridge._has_html_tags("<code>Code</code>") is True
        assert bridge._has_html_tags("Line with <i>italic</i> text") is True
    
    def test_format_plain_text(self):
        """Test plain text formatting"""
        bridge = TelegramAgentBridge()
        
        # Short first line should be bolded
        text = "Short header\nSome content"
        result = bridge._format_plain_text(text)
        assert "<b>Short header</b>" in result
        
        # Long first line should not be bolded
        text = "This is a very long line that exceeds the character limit and should not be bolded\nContent"
        result = bridge._format_plain_text(text)
        assert "<b>" not in result.split("\n")[0]
    
    def test_build_keyboard(self):
        """Test keyboard building"""
        bridge = TelegramAgentBridge()
        
        buttons = [
            [{"text": "Button 1"}, {"text": "Button 2"}],
            [{"text": "Button 3"}]
        ]
        
        keyboard = bridge._build_keyboard(buttons)
        assert keyboard is not None
        assert len(keyboard.keyboard) == 2
        assert len(keyboard.keyboard[0]) == 2
        assert len(keyboard.keyboard[1]) == 1
    
    def test_build_keyboard_empty(self):
        """Test keyboard building with empty buttons"""
        bridge = TelegramAgentBridge()
        
        keyboard = bridge._build_keyboard([])
        assert keyboard is None
        
        keyboard = bridge._build_keyboard(None)
        assert keyboard is None


class TestAgentHandlerIntegration:
    """Test agent handler with mock Ollama"""
    
    @pytest.mark.asyncio
    async def test_process_general_message(self):
        """Test processing general message through AI"""
        with patch('app.integrations.agent_handler.get_ollama_client') as mock_ollama_factory:
            mock_ollama = AsyncMock()
            mock_ollama_factory.return_value = mock_ollama
            
            # Simulate Ollama response
            mock_ollama.chat.return_value = "This is an AI response"
            
            handler = AgentHandler()
            handler.ollama = mock_ollama
            
            result = await handler._send_to_ai(
                user_id=12345,
                message="What is Python?",
                context=handler.get_context(12345)
            )
            
            assert "text" in result
            assert "AI response" in result["text"]
            mock_ollama.chat.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_workflow_project_creation(self):
        """Test workflow transitions for project creation"""
        with patch('app.integrations.agent_handler.get_ollama_client') as mock_ollama_factory:
            mock_ollama = AsyncMock()
            mock_ollama_factory.return_value = mock_ollama
            
            handler = AgentHandler()
            handler.ollama = mock_ollama
            
            # Start project workflow
            context = handler.get_context(12345)
            result = await handler._handle_general_message(12345, "🏗️ project")
            
            assert result["workflow_state"] == WorkflowState.PROJECT_NAME.value
            assert "project" in result["text"].lower()


class TestEndToEndFlow:
    """End-to-end flow testing"""
    
    @pytest.mark.asyncio
    async def test_message_telegram_to_ai_to_telegram(self):
        """Test full flow: Telegram message → Bridge → Handler → Ollama → Response"""
        
        with patch('app.integrations.agent_handler.get_ollama_client') as mock_ollama_factory, \
             patch('app.integrations.agent_handler.get_skill_registry') as mock_registry:
            
            # Setup mocks
            mock_ollama = AsyncMock()
            mock_ollama_factory.return_value = mock_ollama
            mock_registry.return_value = MagicMock()
            
            # Simulate Ollama response
            mock_ollama.chat.return_value = "Here's your answer to that question"
            
            # Process through handler
            handler = AgentHandler()
            handler.ollama = mock_ollama
            
            handler_result = await handler.process_message(
                user_id=12345,
                message="Hello, can you help me?",
                context_type="message"
            )
            
            # Verify handler returned valid response
            assert isinstance(handler_result, dict)
            assert "text" in handler_result
            
            # Process through bridge
            bridge = TelegramAgentBridge()
            bridge.agent_handler = handler
            
            bridge_result = await bridge.process_telegram_message(12345, "Hello, can you help me?")
            
            # Verify bridge transformed response properly
            assert bridge_result["text"] is not None
            assert len(bridge_result["text"]) > 0
            assert bridge_result["parse_mode"] is not None


class TestErrorRecovery:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_ollama_timeout_recovery(self):
        """Test recovery from Ollama timeout"""
        with patch('app.integrations.ollama.httpx.AsyncClient') as mock_client:
            import httpx
            
            # Simulate timeout
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            ollama = OllamaClient()
            ollama.is_cloud = False  # Force local only
            
            with pytest.raises(Exception):
                await ollama.chat([{"role": "user", "content": "test"}])
    
    @pytest.mark.asyncio
    async def test_bridge_malformed_response_handling(self):
        """Test bridge handling of malformed responses"""
        with patch('app.integrations.telegram_bridge.get_agent_handler') as mock_handler:
            mock_handler_instance = AsyncMock()
            mock_handler.return_value = mock_handler_instance
            
            # Return None instead of dict
            mock_handler_instance.process_message.return_value = None
            
            bridge = TelegramAgentBridge()
            result = await bridge.process_telegram_message(12345, "test")
            
            assert "Invalid response" in result["text"]


# Run tests if called directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
