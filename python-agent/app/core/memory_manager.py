"""
Advanced Memory Manager - Migrated from TypeScript telegram-memory-manager.ts
Manages conversation history, context windows, and SOUL.md integration
"""

import structlog
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from collections import deque

logger = structlog.get_logger(__name__)


@dataclass
class Message:
    """Single message in conversation"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_ollama_format(self) -> Dict[str, str]:
        """Convert to Ollama message format"""
        return {
            "role": self.role,
            "content": self.content
        }


@dataclass
class ConversationContext:
    """Conversation context for a user"""
    user_id: int
    messages: deque = field(default_factory=lambda: deque(maxlen=50))
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to context"""
        msg = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.last_activity = datetime.now()
    
    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get recent messages"""
        return list(self.messages)[-count:]
    
    def clear(self):
        """Clear conversation history"""
        self.messages.clear()
        self.last_activity = datetime.now()


class MemoryManager:
    """
    Advanced memory management system
    Handles conversation context, SOUL.md integration, and context window optimization
    """
    
    def __init__(
        self,
        max_context_messages: int = 20,
        context_timeout_minutes: int = 30,
        soul_file: Optional[Path] = None
    ):
        self.max_context_messages = max_context_messages
        self.context_timeout = timedelta(minutes=context_timeout_minutes)
        # Fix: The plan used Path(__file__).parent.parent.parent / "SOUL.md" which would be project root.
        self.soul_file = soul_file or Path(__file__).parent.parent.parent / "SOUL.md"
        
        # User contexts
        self.contexts: Dict[int, ConversationContext] = {}
        
        # Load SOUL configuration
        self.soul_identity = self._load_soul()
        
        logger.info(
            "memory_manager_initialized",
            max_context=max_context_messages,
            timeout_minutes=context_timeout_minutes,
            soul_loaded=bool(self.soul_identity)
        )
    
    def _load_soul(self) -> Optional[str]:
        """Load SOUL.md identity file"""
        try:
            if self.soul_file.exists():
                content = self.soul_file.read_text()
                logger.info("soul_loaded", file=str(self.soul_file), length=len(content))
                return content
            else:
                logger.warning("soul_file_not_found", path=str(self.soul_file))
                return None
        except Exception as e:
            logger.error("soul_load_failed", error=str(e))
            return None
    
    def get_context(self, user_id: int) -> ConversationContext:
        """Get or create conversation context for user"""
        if user_id not in self.contexts:
            self.contexts[user_id] = ConversationContext(user_id=user_id)
            logger.info("context_created", user_id=user_id)
        
        context = self.contexts[user_id]
        
        # Check if context expired
        if datetime.now() - context.last_activity > self.context_timeout:
            logger.info("context_expired", user_id=user_id, clearing=True)
            context.clear()
        
        return context
    
    def add_user_message(self, user_id: int, content: str, metadata: Optional[Dict] = None):
        """Add user message to context"""
        context = self.get_context(user_id)
        context.add_message("user", content, metadata)
        logger.debug("user_message_added", user_id=user_id, length=len(content))
    
    def add_assistant_message(self, user_id: int, content: str, metadata: Optional[Dict] = None):
        """Add assistant message to context"""
        context = self.get_context(user_id)
        context.add_message("assistant", content, metadata)
        logger.debug("assistant_message_added", user_id=user_id, length=len(content))
    
    def build_conversation_for_ollama(
        self,
        user_id: int,
        include_system_prompt: bool = True
    ) -> List[Dict[str, str]]:
        """
        Build conversation messages for Ollama API
        Optimizes context window by including:
        1. System prompt (SOUL.md if available)
        2. Recent conversation history
        3. Current user message
        """
        messages = []
        
        # Add system prompt
        if include_system_prompt and self.soul_identity:
            messages.append({
                "role": "system",
                "content": self.soul_identity
            })
        
        # Add conversation history
        context = self.get_context(user_id)
        recent_messages = context.get_recent_messages(self.max_context_messages)
        
        for msg in recent_messages:
            messages.append(msg.to_ollama_format())
        
        logger.debug(
            "conversation_built",
            user_id=user_id,
            total_messages=len(messages),
            history_messages=len(recent_messages),
            has_system=include_system_prompt
        )
        
        return messages
    
    def get_context_summary(self, user_id: int) -> Dict[str, Any]:
        """Get summary of user's context"""
        if user_id not in self.contexts:
            return {"exists": False}
        
        context = self.contexts[user_id]
        return {
            "exists": True,
            "message_count": len(context.messages),
            "last_activity": context.last_activity.isoformat(),
            "metadata": context.metadata
        }
    
    def clear_context(self, user_id: int):
        """Clear user's conversation context"""
        if user_id in self.contexts:
            self.contexts[user_id].clear()
            logger.info("context_cleared", user_id=user_id)
    
    def cleanup_expired_contexts(self):
        """Remove expired contexts to free memory"""
        now = datetime.now()
        expired_users = []
        
        for user_id, context in self.contexts.items():
            if now - context.last_activity > self.context_timeout * 2:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.contexts[user_id]
            logger.info("expired_context_removed", user_id=user_id)
        
        if expired_users:
            logger.info("cleanup_complete", removed_count=len(expired_users))


# Global memory manager instance
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
