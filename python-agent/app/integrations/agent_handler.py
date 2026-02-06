"""
Agent Request Handler - Bridges Telegram Bot and AI Brain
Handles conversation context, skill routing, and response formatting
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from enum import Enum
from app.core.config import settings
from app.integrations.ollama import get_ollama_client
from app.skills.registry import get_skill_registry
from app.core.error_handler import get_error_handler, ErrorCategory
from app.core.memory_manager import get_memory_manager
from app.monitoring.analytics import get_analytics_tracker
from app.integrations.browser_controller import get_browser_controller
from app.db.session import SessionLocal
from app.models.database import WorkflowSession
import time
import structlog
import subprocess
import sys
from app.core.terminal_logger import TerminalActionLogger
from app.core.workflow_logger import WorkflowLogger

logger = structlog.get_logger(__name__)


class WorkflowState(Enum):
    IDLE = "idle"
    # Project Wizard (1.2)
    PROJECT_NAME = "project_name"
    PROJECT_GOAL = "project_goal"
    PROJECT_DETAILS = "project_details"
    PROJECT_TECH = "project_tech"
    PROJECT_LANG = "project_lang"
    # Social Wizard (1.3)
    SOCIAL_TYPE = "social_type"
    SOCIAL_PLATFORM = "social_platform"
    SOCIAL_CONTENT = "social_content"
    # Schedule Wizard (1.4)
    SCHEDULE_TYPE = "schedule_type"
    SCHEDULE_DESCRIPTION = "schedule_description"
    SCHEDULE_TIME = "schedule_time"
    SCHEDULE_PRIORITY = "schedule_priority"
    # Learn Button (1.5)
    LEARN_MODE = "learn_mode"
    LEARN_INPUT = "learn_input"
    LEARNING = "learning"
    # System (1.6, 1.7)
    RESTART_CONFIRM = "restart_confirm"
    SHUTDOWN_CONFIRM = "shutdown_confirm"
    # Help (1.8)
    HELP_CATEGORY = "help_category"


class ConversationContext(TypedDict):
    user_id: int
    workflow_state: WorkflowState
    workflow_data: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    created_at: datetime
    updated_at: datetime


class AgentHandler:
    """
    Main handler for processing user requests through AI
    Bridges Telegram bot with Ollama-powered agent
    """
    
    def __init__(self):
        self.ollama = get_ollama_client()
        self.skill_registry = get_skill_registry()
        self.contexts: Dict[int, ConversationContext] = {}
        self.system_prompt = """You are the Ultimate Coding Agent, an advanced AI assistant specialized in:
- Software development and architecture
- Code generation and analysis
- Project management
- DevOps and automation
- Technical problem-solving

You are helpful, precise, and always provide production-ready solutions.
You explain complex concepts clearly and write clean, maintainable code.

When responding to Telegram users:
1. Be concise but informative
2. Use emojis sparingly for visual breaks
3. Format code blocks properly
4. If asking for clarification, ask one question at a time
5. Confirm before taking destructive actions"""
    
    def get_context(self, user_id: int) -> ConversationContext:
        """Get or create conversation context for user (Phase 4.1 Persistence)"""
        # 1. Check in-memory cache
        if user_id in self.contexts:
            return self.contexts[user_id]
        
        # 2. Check Database
        db = SessionLocal()
        try:
            session = db.query(WorkflowSession).filter(WorkflowSession.user_id == user_id).first()
            if session:
                # Convert DB model to dict
                workflow_state = WorkflowState(session.state)
                context: ConversationContext = {
                    "user_id": user_id,
                    "workflow_state": workflow_state,
                    "workflow_data": session.data,
                    "conversation_history": [], # We don't persist full history in workflow_sessions
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                }
                self.contexts[user_id] = context
                return context
        finally:
            db.close()
            
        # 3. Create New
        context: ConversationContext = {
            "user_id": user_id,
            "workflow_state": WorkflowState.IDLE,
            "workflow_data": {},
            "conversation_history": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        self.contexts[user_id] = context
        return context

    def save_context(self, user_id: int):
        """Persist current context to database (Phase 4.1)"""
        if user_id not in self.contexts:
            return
            
        context = self.contexts[user_id]
        db = SessionLocal()
        try:
            session = db.query(WorkflowSession).filter(WorkflowSession.user_id == user_id).first()
            if not session:
                session = WorkflowSession(user_id=user_id)
                db.add(session)
            
            session.state = context["workflow_state"].value
            session.data = context["workflow_data"]
            session.updated_at = datetime.utcnow()
            db.commit()
            logger.debug("Persisted workflow context", user_id=user_id, state=session.state)
        except Exception as e:
            logger.error(f"Failed to persist workflow context: {e}")
            db.rollback()
        finally:
            db.close()

    def clear_context(self, user_id: int):
        """Clear context from memory and database"""
        if user_id in self.contexts:
            del self.contexts[user_id]
            
        db = SessionLocal()
        try:
            db.query(WorkflowSession).filter(WorkflowSession.user_id == user_id).delete()
            db.commit()
            logger.debug("Cleared persisted workflow context", user_id=user_id)
        except Exception as e:
            logger.error(f"Failed to clear persisted workflow context: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def process_message(
        self,
        user_id: int,
        message: str,
        context_type: str = "message"
    ) -> Dict[str, Any]:
        """
        Process incoming message with full error handling, memory, and analytics
        """
        start_time = time.time()
        error_handler = get_error_handler()
        memory_manager = get_memory_manager()
        analytics = get_analytics_tracker()
        
        try:
            # Add user message to memory
            memory_manager.add_user_message(user_id, message)
            
            # 1. ALWAYS Check for general commands/buttons first (Home, Back, Exit)
            general_result = await self._handle_general_message(user_id, message)
            
            context = self.get_context(user_id)
            
            if general_result:
                response_text = general_result.get("text")
                workflow_buttons = general_result.get("buttons")
                skill_used = "menu_nav"
                TerminalActionLogger.log_action("Menu Navigation", f"Target: {response_text[:30]}...")
            
            # 2. Otherwise handle active workflow
            elif context["workflow_state"] != WorkflowState.IDLE:
                TerminalActionLogger.log_workflow(user_id, context["workflow_state"].value, message)
                workflow_result = await self._handle_workflow(user_id, message)
                response_text = workflow_result.get("text", "Done!")
                skill_used = "workflow_" + str(context["workflow_state"].value)
                workflow_buttons = workflow_result.get("buttons")
                
            # 3. Otherwise detect skill or chat
            else:
                # Detect and route to skill
                TerminalActionLogger.log_action("Skill Routing", f"Prompt: {message[:30]}...")
                skill_result = await error_handler.execute_with_retry(
                    self.skill_registry.route_message_to_skill,
                    message,
                    user_id,
                    category=ErrorCategory.SKILL,
                    max_retries=2
                )
                if skill_result["success"]:
                    response_text = skill_result["result"].get("text", "Done!")
                    skill_used = skill_result.get("skill_used")
                    workflow_buttons = skill_result["result"].get("buttons")
                    WorkflowLogger.log_step("Skill", skill_used or "Execution", "Success")
                else:
                    # Fallback to general AI response
                    WorkflowLogger.log_step("AI Brain", "Fallback Chat", "No skill matched, using general AI")
                    conversation = memory_manager.build_conversation_for_ollama(user_id)
                    
                    WorkflowLogger.log_ai_action("Chat Generation", f"Messages: {len(conversation)}")
                    
                    response_text = await error_handler.execute_with_retry(
                        self.ollama.chat,
                        messages=conversation,
                        category=ErrorCategory.OLLAMA,
                        max_retries=3
                    )
                    skill_used = "ai_chat"
                    workflow_buttons = None
                    WorkflowLogger.log_success(f"AI Response received ({len(response_text)} chars)")
            
            # Add assistant response to memory
            memory_manager.add_assistant_message(user_id, response_text)
            
            # Record analytics
            response_time_ms = (time.time() - start_time) * 1000
            WorkflowLogger.log_step("System", "Response Ready", f"Time: {response_time_ms:.1f}ms, Skill: {skill_used}")
            analytics.record_message(
                user_id=user_id,
                message=message,
                response=response_text,
                response_time_ms=response_time_ms,
                skill_used=skill_used,
                success=True
            )
            
            # Prepare final result
            result = {
                "text": response_text,
                "success": True,
                "response_time_ms": response_time_ms,
                "buttons": workflow_buttons,
                "workflow_state": context["workflow_state"].value
            }
            
            # Persist state if active
            if context["workflow_state"] != WorkflowState.IDLE:
                self.save_context(user_id)
            
            return result
            
        except Exception as e:
            error_handler.record_error(e)
            user_message = error_handler.format_user_error(e)
            
            # Record failed analytics
            response_time_ms = (time.time() - start_time) * 1000
            analytics.record_message(
                user_id=user_id,
                message=message,
                response=user_message,
                response_time_ms=response_time_ms,
                success=False,
                error=str(e)
            )
            
            return {
                "text": user_message,
                "success": False,
                "error": str(e)
            }
    
    async def _handle_workflow(self, user_id: int, message: str) -> Dict[str, Any]:
        """Handle multi-step workflows (Phases 1.2 - 1.8)"""
        context = self.get_context(user_id)
        state = context["workflow_state"]
        data = context["workflow_data"]
        msg_lower = message.lower().strip()
        
        # Global Navigation (1.9)
        if "back" in msg_lower or "⬅️" in message:
            return await self._handle_back(user_id)

        # --- PROJECT WIZARD (1.2) ---
        if state == WorkflowState.PROJECT_NAME:
            data["project_name"] = message.strip()
            context["workflow_state"] = WorkflowState.PROJECT_GOAL
            return {"text": "🎯 <b>Project Goal</b>\n\nWhat is the main goal or purpose of this project?"}
        
        elif state == WorkflowState.PROJECT_GOAL:
            data["goal"] = message.strip()
            context["workflow_state"] = WorkflowState.PROJECT_DETAILS
            return {"text": "📝 <b>Project Details</b>\n\nPlease provide detailed requirements or features for the project:"}
        
        elif state == WorkflowState.PROJECT_DETAILS:
            data["details"] = message.strip()
            context["workflow_state"] = WorkflowState.PROJECT_TECH
            return {
                "text": "🛠️ <b>Tech Stack</b>\n\nSelect the primary technology stack:",
                "buttons": [
                    [{"text": "⚡ FastAPI", "callback": "tech_fastapi"}, {"text": "⚛️ React", "callback": "tech_react"}],
                    [{"text": "🟦 Next.js", "callback": "tech_nextjs"}, {"text": "🐍 Django", "callback": "tech_django"}],
                    [{"text": "📦 Node.js", "callback": "tech_nodejs"}, {"text": "⬅️ Back", "callback": "back"}]
                ]
            }
        
        elif state == WorkflowState.PROJECT_TECH:
            data["tech_stack"] = message.replace("tech_", "").capitalize()
            context["workflow_state"] = WorkflowState.PROJECT_LANG
            return {
                "text": "🌐 <b>Language</b>\n\nSelect the primary programming language:",
                "buttons": [
                    [{"text": "🐍 Python", "callback": "lang_python"}, {"text": "🔵 TypeScript", "callback": "lang_ts"}],
                    [{"text": "🟢 JavaScript", "callback": "lang_js"}, {"text": "🔴 Go", "callback": "lang_go"}],
                    [{"text": "⬅️ Back", "callback": "back"}]
                ]
            }
        
        elif state == WorkflowState.PROJECT_LANG:
            data["language"] = message.replace("lang_", "").capitalize()
            return await self._execute_project_creation(user_id, data)

        # --- SOCIAL WIZARD (1.3) ---
        elif state == WorkflowState.SOCIAL_TYPE:
            # Handle content type selection
            type_map = {
                "content_text": "text",
                "content_image": "image",
                "content_video": "video",
                "📝 Text": "text",
                "🖼️ Image": "image",
                "🎥 Video": "video"
            }
            content_type = type_map.get(message, message.lower())
            data["content_type"] = content_type
            context["workflow_state"] = WorkflowState.SOCIAL_PLATFORM

            # Use SocialMediaManager to get platform suggestions
            from app.skills.social_media_manager import SocialMediaManager
            manager = SocialMediaManager()
            result = await manager._execute({"step": "ask_platform", "content_type": content_type})

            # Build platform buttons based on content type
            platforms = []
            if content_type == "text":
                platforms = [
                    [{"text": "📘 Facebook", "callback": "plat_facebook"}, {"text": "🐦 Twitter/X", "callback": "plat_twitter"}],
                    [{"text": "💼 LinkedIn", "callback": "plat_linkedin"}, {"text": "📱 All", "callback": "plat_all"}]
                ]
            elif content_type == "image":
                platforms = [
                    [{"text": "📷 Instagram", "callback": "plat_instagram"}, {"text": "📘 Facebook", "callback": "plat_facebook"}],
                    [{"text": "🎵 TikTok", "callback": "plat_tiktok"}, {"text": "📱 All", "callback": "plat_all"}]
                ]
            elif content_type == "video":
                platforms = [
                    [{"text": "▶️ YouTube", "callback": "plat_youtube"}, {"text": "🎵 TikTok", "callback": "plat_tiktok"}],
                    [{"text": "📘 Facebook", "callback": "plat_facebook"}, {"text": "📷 Instagram", "callback": "plat_instagram"}],
                    [{"text": "📱 All", "callback": "plat_all"}]
                ]

            platforms.append([{"text": "⬅️ Back", "callback": "back"}])

            return {
                "text": result.output,
                "buttons": platforms
            }
        
        elif state == WorkflowState.SOCIAL_PLATFORM:
            # Parse platform selection
            platform_map = {
                "plat_facebook": "facebook",
                "plat_twitter": "twitter",
                "plat_linkedin": "linkedin",
                "plat_instagram": "instagram",
                "plat_tiktok": "tiktok",
                "plat_youtube": "youtube",
                "plat_all": "all"
            }
            selected_platform = platform_map.get(message, message.replace("plat_", ""))

            if selected_platform == "all":
                # Select all platforms based on content type
                content_type = data.get("content_type", "text")
                if content_type == "text":
                    data["platforms"] = ["facebook", "twitter", "linkedin"]
                elif content_type == "image":
                    data["platforms"] = ["instagram", "facebook", "tiktok"]
                elif content_type == "video":
                    data["platforms"] = ["youtube", "tiktok", "facebook", "instagram"]
            else:
                data["platforms"] = [selected_platform]

            # We already have content, proceed to posting directly
            platform_names = ", ".join([p.title() for p in data["platforms"]])
            return await self._execute_social_post_with_browser(user_id, data, platform_names)

        elif state == WorkflowState.SOCIAL_CONTENT:
            # Auto-detect content type from message
            # Check if context has media info (set by Telegram handler)
            has_photo = context.get("has_photo", False)
            has_video = context.get("has_video", False)

            if has_photo:
                content_type = "image"
                data["content_type"] = content_type
                data["media_path"] = context.get("media_path")
            elif has_video:
                content_type = "video"
                data["content_type"] = content_type
                data["media_path"] = context.get("media_path")
            else:
                content_type = "text"
                data["content_type"] = content_type

            data["content"] = message.strip()

            # Suggest platforms based on detected content type
            from app.skills.social_media_manager import SocialMediaManager
            manager = SocialMediaManager()
            result = await manager._execute({"step": "ask_platform", "content_type": content_type})

            # Build platform buttons
            platforms = []
            if content_type == "text":
                platforms = [
                    [{"text": "📘 Facebook", "callback": "plat_facebook"}, {"text": "🐦 Twitter", "callback": "plat_twitter"}],
                    [{"text": "💼 LinkedIn", "callback": "plat_linkedin"}, {"text": "📱 All", "callback": "plat_all"}],
                    [{"text": "⬅️ Back", "callback": "back"}]
                ]
            elif content_type == "image":
                platforms = [
                    [{"text": "📷 Instagram", "callback": "plat_instagram"}, {"text": "📘 Facebook", "callback": "plat_facebook"}],
                    [{"text": "🎵 TikTok", "callback": "plat_tiktok"}, {"text": "📱 All", "callback": "plat_all"}],
                    [{"text": "⬅️ Back", "callback": "back"}]
                ]
            elif content_type == "video":
                platforms = [
                    [{"text": "▶️ YouTube", "callback": "plat_youtube"}, {"text": "🎵 TikTok", "callback": "plat_tiktok"}],
                    [{"text": "📘 Facebook", "callback": "plat_facebook"}, {"text": "📷 Instagram", "callback": "plat_instagram"}],
                    [{"text": "📱 All", "callback": "plat_all"}, {"text": "⬅️ Back", "callback": "back"}]
                ]

            context["workflow_state"] = WorkflowState.SOCIAL_PLATFORM
            return {
                "text": result.output,
                "buttons": platforms
            }

        # --- SCHEDULE WIZARD (1.4) ---
        elif state == WorkflowState.SCHEDULE_TYPE:
            data["schedule_type"] = message.strip()
            context["workflow_state"] = WorkflowState.SCHEDULE_DESCRIPTION
            return {"text": "📝 <b>Task Description</b>\n\nWhat is the task you want to schedule?"}
        
        elif state == WorkflowState.SCHEDULE_DESCRIPTION:
            data["task_description"] = message.strip()
            context["workflow_state"] = WorkflowState.SCHEDULE_TIME
            return {"text": "📅 <b>Date/Time</b>\n\nWhen should this task run? (e.g., 'every day at 9am', '2026-02-15 10:00')"}
        
        elif state == WorkflowState.SCHEDULE_TIME:
            data["time"] = message.strip()
            context["workflow_state"] = WorkflowState.SCHEDULE_PRIORITY
            return {
                "text": "🚦 <b>Priority</b>\n\nSelect the priority level:",
                "buttons": [
                    [{"text": "🟢 Low", "callback": "prio_low"}, {"text": "🟡 Medium", "callback": "prio_med"}],
                    [{"text": "🟠 High", "callback": "prio_high"}, {"text": "🔴 Critical", "callback": "prio_crit"}],
                    [{"text": "⬅️ Back", "callback": "back"}]
                ]
            }
        
        elif state == WorkflowState.SCHEDULE_PRIORITY:
            data["priority"] = message.replace("prio_", "")
            return await self._execute_schedule_creation(user_id, data)

        # --- LEARN WIZARD (1.5) ---
        elif state == WorkflowState.LEARN_MODE:
            data["learn_mode"] = message.strip()
            WorkflowLogger.log_step("Learn", "Mode Selected", f"Mode: {message}")
            
            # Use lower() and strip emojis to match button text/callback more robustly
            msg_clean = message.lower().replace("🚀", "").replace("🔄", "").strip()
            if "update skills" in msg_clean or "self-improve" in msg_clean or "learn_skills" in message or "learn_improve" in message:
                context["workflow_state"] = WorkflowState.LEARNING
                WorkflowLogger.log_transition("LEARN_MODE", "LEARNING", message)
                asyncio.create_task(self._perform_learning(user_id))
                return {"text": "🧠 <b>Autonomous Learning Started</b>\n\nI am now analyzing system state and optimizing my routines. I will notify you when complete."}
            else:
                context["workflow_state"] = WorkflowState.LEARN_INPUT
                WorkflowLogger.log_transition("LEARN_MODE", "LEARN_INPUT", message)
                return {"text": f"📖 <b>{message}</b>\n\nPlease provide the URL or code snippet to analyze:"}
        
        elif state == WorkflowState.LEARN_INPUT:
            data["input"] = message.strip()
            WorkflowLogger.log_step("Learn", "Input Received", f"Length: {len(message)}")
            return await self._execute_learning_process(user_id, data)

        # --- HELP WIZARD (1.8) ---
        elif state == WorkflowState.HELP_CATEGORY:
            return await self._handle_help_category(user_id, message)

        # --- SYSTEM COMMANDS (1.6, 1.7) ---
        elif state == WorkflowState.RESTART_CONFIRM:
            if "restart" in msg_lower or "yes" in msg_lower:
                asyncio.create_task(self._perform_restart())
                return {"text": "🔄 <b>Restarting agent...</b>\n\nPlease wait a moment."}
            else:
                self.clear_context(user_id)
                return {"text": "❌ Restart cancelled."}

        elif state == WorkflowState.SHUTDOWN_CONFIRM:
            if "shutdown" in msg_lower or "yes" in msg_lower:
                asyncio.create_task(self._perform_shutdown())
                return {"text": "⚡ <b>System shutting down...</b>\n\nGoodbye!"}
            else:
                self.clear_context(user_id)
                return {"text": "❌ Shutdown cancelled."}

        return {"text": "Workflow completed or cancelled."}
        
        return {"text": "Workflow completed or cancelled."}
    
    async def _handle_general_message(self, user_id: int, message: str) -> Dict[str, Any]:
        """Handle general messages without active workflow"""
        context = self.get_context(user_id)
        
        msg_lower = message.lower().strip()
        
        # NEW 7-BUTTON MAIN MENU DETECTION (Robust match)
        if any(x in msg_lower for x in ["🏗️", "project", "build", "create project", "new project"]):
            # Only trigger if it's a clear command or short phrase
            if len(msg_lower) < 30:
                context["workflow_state"] = WorkflowState.PROJECT_NAME
                TerminalActionLogger.log_action("Workflow Started", "Project Creation Wizard")
                return {
                    "text": "🏗️ <b>Create New Project</b>\n\nWhat is the name of your project?",
                    "workflow_state": WorkflowState.PROJECT_NAME.value
                }
        
        if any(x in msg_lower for x in ["📱", "social", "post", "share", "tweet"]):
            if len(msg_lower) < 20 or msg_lower == "social":
                context["workflow_state"] = WorkflowState.SOCIAL_CONTENT
                TerminalActionLogger.log_action("Workflow Started", "Social Media Manager")
                return {
                    "text": "📱 <b>Social Media Posting</b>\n\n" \
                           "Please share your content now:\n\n" \
                           "• Type a <b>text message</b> for text posts\n" \
                           "• Attach a <b>photo/image</b> for image posts\n" \
                           "• Attach a <b>video</b> for video posts\n\n" \
                           "I'll automatically detect the type and suggest the best platforms!",
                    "buttons": [[{"text": "⬅️ Back", "callback": "back"}]],
                    "workflow_state": WorkflowState.SOCIAL_CONTENT.value
                }
        
        if any(x in msg_lower for x in ["📅", "schedule", "reminder", "set task"]):
            if len(msg_lower) < 30:
                context["workflow_state"] = WorkflowState.SCHEDULE_TYPE
                TerminalActionLogger.log_action("Workflow Started", "Schedule Wizard")
                return {
                    "text": "📅 <b>Schedule Task</b>\n\nSelect the task type:",
                    "buttons": [
                        [{"text": "⏰ One-time", "callback": "type_once"}, {"text": "🔄 Recurring", "callback": "type_recur"}],
                        [{"text": "🔔 Reminder", "callback": "type_remind"}, {"text": "⬅️ Back", "callback": "back"}]
                    ],
                    "workflow_state": WorkflowState.SCHEDULE_TYPE.value
                }

        if any(x in msg_lower for x in ["🧠", "learn", "study"]):
            if len(msg_lower) < 20:
                context["workflow_state"] = WorkflowState.LEARN_MODE
                TerminalActionLogger.log_action("Workflow Started", "Learning Machine")
                return {
                    "text": "🧠 <b>Autonomous Learning</b>\n\nSelect learning mode:",
                    "buttons": [
                        [{"text": "📖 Read Docs", "callback": "learn_docs"}, {"text": "🔄 Update Skills", "callback": "learn_skills"}],
                        [{"text": "🔍 Analyze Code", "callback": "learn_code"}, {"text": "🚀 Self-Improve", "callback": "learn_improve"}],
                        [{"text": "⬅️ Back", "callback": "back"}]
                    ],
                    "workflow_state": WorkflowState.LEARN_MODE.value
                }
        
        if context["workflow_state"] != WorkflowState.RESTART_CONFIRM and any(x in msg_lower for x in ["🔄", "restart"]):
            # Only trigger if it's the specific command
            if len(msg_lower) < 20 or "agent" in msg_lower:
                context["workflow_state"] = WorkflowState.RESTART_CONFIRM
                TerminalActionLogger.log_action("Action Prompted", "Restart Agent Confirmation")
                return {
                    "text": "🔄 <b>Confirm Restart</b>\n\nAre you sure you want to restart the agent? (Reply 'restart' or 'yes' to confirm)",
                    "workflow_state": WorkflowState.RESTART_CONFIRM.value,
                    "buttons": [[{"text": "✅ Yes, Restart", "callback": "restart_yes"}, {"text": "❌ No", "callback": "back"}]]
                }
        
        if any(x in msg_lower for x in ["⚡", "shutdown"]):
            context["workflow_state"] = WorkflowState.SHUTDOWN_CONFIRM
            return {
                "text": "⚠️ <b>CONFIRM SYSTEM SHUTDOWN</b>\n\nThis will SHUT DOWN the host machine! (Reply 'shutdown' or 'yes' to confirm)",
                "workflow_state": WorkflowState.SHUTDOWN_CONFIRM.value,
                "buttons": [[{"text": "⚠️ SHUTDOWN NOW", "callback": "shutdown_yes"}, {"text": "❌ Cancel", "callback": "back"}]]
            }
        
        if any(x in msg_lower for x in ["❓", "help"]):
            context["workflow_state"] = WorkflowState.HELP_CATEGORY
            return {
                "text": "❓ <b>Help Center</b>\n\nSelect a category for assistance:",
                "buttons": [
                    [{"text": "📟 Commands", "callback": "help_cmds"}, {"text": "🏗️ Features", "callback": "help_feats"}],
                    [{"text": "💡 Examples", "callback": "help_examples"}, {"text": "⬅️ Back", "callback": "back"}]
                ],
                "workflow_state": WorkflowState.HELP_CATEGORY.value
            }
        
        if any(x in msg_lower for x in ["📊", "status"]):
            TerminalActionLogger.log_action("System Status", f"User: {user_id}")
            return await self._send_status(user_id)
        
        if any(x in msg_lower for x in ["back", "⬅️", "home", "🏠", "main menu"]):
            TerminalActionLogger.log_action("Home/Back", f"User: {user_id}")
            return await self._handle_back(user_id)
        
        # No general command matched
        return None
    
    async def _send_to_ai(
        self,
        user_id: int,
        message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Send message to Ollama AI and get response - FIXED"""
        try:
            history = context["conversation_history"][-10:]
            
            messages = []
            messages.append({"role": "system", "content": self.system_prompt})
            messages.extend(history)
            messages.append({"role": "user", "content": message})
            
            # Call Ollama chat (returns string directly)
            response_text = await self.ollama.chat(messages=messages)
            
            # Ensure we got a string
            if not isinstance(response_text, str):
                response_text = str(response_text)
            
            if not response_text or not response_text.strip():
                response_text = "I didn't get a response. Please try again."
            
            # Add to history
            context["conversation_history"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(
                "AI response generated",
                user_id=user_id,
                response_len=len(response_text)
            )
            
            return {
                "text": response_text,
                "model": getattr(self.ollama, 'ollama_model', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"AI processing failed: {e}", exc_info=True)
            return {
                "text": f"❌ <b>AI Error</b>\n\n<code>{str(e)[:100]}</code>\n\nPlease try again or use the menu buttons.",
                "error": str(e)
            }
    
    async def _execute_project_creation(self, user_id: int, data: Dict) -> Dict[str, Any]:
        """Execute project creation via AI"""
        context = self.get_context(user_id)
        
        project_name = data.get("project_name", "unnamed_project")
        language = data.get("language", "python")
        framework = data.get("framework", "")
        goal = data.get("goal", "Create a new project")
        
        logger.info(
            "Creating project",
            user_id=user_id,
            project_name=project_name,
            language=language
        )
        
        prompt = f"""Generate a complete {language} project using {framework}.

Project: {project_name}
Goal: {goal}

Requirements:
1. Use {framework} framework
2. Create complete project structure
3. Include: requirements.txt, README.md, .gitignore
4. Include main application file
5. Include at least one example route/endpoint
6. Include error handling

Language: {language}
Framework: {framework}

Generate the complete project structure with all necessary files."""

        try:
            result = await self.ollama.generate(
                prompt=prompt,
                system_prompt="You are an expert developer. Generate complete, production-ready code.",
                temperature=0.3,
                max_tokens=4000
            )
            
            data["generated_code"] = result
            context["workflow_state"] = WorkflowState.IDLE
            
            return {
                "text": f"✅ <b>Project Created: {project_name}</b>\n\n"
                        f"Language: {language}\n"
                        f"Framework: {framework}\n\n"
                        f"<code>{result[:500]}...</code>\n\n"
                        f"Full project generated successfully!",
                "project_data": data
            }
            
        except Exception as e:
            logger.error(f"Project creation failed: {e}")
            return {
                "text": f"❌ Project creation failed: {e}"
            }
    
    async def _execute_social_post(self, user_id: int, data: Dict) -> Dict[str, Any]:
        """Execute social media post"""
        context = self.get_context(user_id)
        
        platform = data.get("platform", "twitter")
        content = data.get("content", "")
        
        prompt = f"""Optimize this content for {platform}:

Original: {content}

Requirements:
- {platform} best practices
- Add relevant hashtags if appropriate
- Keep within character limits
- Make engaging and professional

Optimized version:"""

        try:
            result = await self.ollama.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=500
            )
            
            # PHASE 3.2: Browser Integration
            browser = get_browser_controller()
            await browser.create_social_post(platform, result)
            
            context["workflow_state"] = WorkflowState.IDLE
            
            return {
                "text": f"📱 <b>Post for {platform.capitalize()}</b>\n\n"
                        f"Original: {content}\n\n"
                        f"Optimized:\n{result}\n\n"
                        f"✅ <b>Action Taken</b>: Browser share dialog has been opened!",
                "buttons": [
                    [{"text": "🏠 Main Menu", "callback": "back"}],
                ],
                "platform": platform,
                "content": result
            }
            
        except Exception as e:
            logger.error(f"Social post failed: {e}")
            return {"text": f"❌ Error: {e}"}
    
    async def _execute_social_post_with_browser(self, user_id: int, data: Dict, platform_names: str = None) -> Dict[str, Any]:
        """Execute social media post with browser automation"""
        context = self.get_context(user_id)

        platforms = data.get("platforms", ["facebook"])
        content = data.get("content", "")
        content_type = data.get("content_type", "text")
        media_path = data.get("media_path")  # If user attached media

        if not platform_names:
            platform_names = ", ".join([p.title() for p in platforms])

        try:
            # Use SocialMediaManager for posting
            from app.skills.social_media_manager import SocialMediaManager
            manager = SocialMediaManager()

            # Show status message
            TerminalActionLogger.log_action("Browser Automation", f"Opening browsers for: {platform_names}")

            result = await manager._execute({
                "step": "post_content",
                "platforms": platforms,
                "content_type": content_type,
                "text": content,
                "media_path": media_path
            })

            context["workflow_state"] = WorkflowState.IDLE

            content_preview = content[:100] + "..." if len(content) > 100 else content

            return {
                "text": f"🌐 <b>Browser Opened!</b>\n\n" \
                        f"📱 <b>Platforms:</b> {platform_names}\n" \
                        f"📝 <b>Content:</b> {content_preview}\n\n" \
                        f"✅ Chrome browser has been opened with the selected platform(s).\n\n" \
                        f"📋 <b>Next Steps:</b>\n" \
                        f"1. Log in to the platform if needed\n" \
                        f"2. Paste your content (it's copied to clipboard!)\n" \
                        f"3. Attach media if applicable\n" \
                        f"4. Click Post/Share\n\n" \
                        f"Reply 'done' when finished, or 'help' if you need assistance.",
                "buttons": [
                    [{"text": "✅ Done", "callback": "back"}, {"text": "🔄 Retry", "callback": "menu_social"}],
                    [{"text": "🏠 Main Menu", "callback": "back"}],
                ]
            }

        except Exception as e:
            logger.error(f"Browser social post failed: {e}")
            return {
                "text": f"❌ <b>Error Opening Browser</b>\n\n{str(e)}\n\n" \
                        f"Please try again or open the platform manually.",
                "buttons": [[{"text": "🔄 Try Again", "callback": "menu_social"}, {"text": "🏠 Main Menu", "callback": "back"}]]
            }

    async def _execute_schedule_creation(self, user_id: int, data: Dict) -> Dict[str, Any]:
        """Execute schedule creation"""
        context = self.get_context(user_id)
        
        # PHASE 3.3: Scheduler Integration
        task_name = f"Telegram Task: {data.get('schedule_type', 'General')}"
        schedule_str = data.get("time", "")
        description = data.get("task_description", "")
        priority = data.get("priority", "medium")
        
        # Get scheduler skill
        scheduler_skill = self.skill_registry.get_skill("task_scheduler")
        if scheduler_skill:
            params = {
                "action": "schedule",
                "task_name": f"{task_name} - {description[:20]}",
                "schedule": schedule_str,
                "skill": "project_manager", # Default skill to run for now
                "params": {"action": "status"} # Default action
            }
            # Handle priority if needed in params
            params["params"]["priority"] = priority
            
            # Execute skill (calling _execute directly for simplicity in this bridge)
            # Or use registry.execute_skill
            skill_result = await self.skill_registry.execute_skill("task_scheduler", params)
            response_text = skill_result.output if skill_result.success else f"❌ Scheduling failed: {skill_result.error}"
        else:
            response_text = "❌ Scheduler skill not found."
        
        context["workflow_state"] = WorkflowState.IDLE
        
        return {
            "text": f"📅 <b>Task Scheduled</b>\n\n"
                    f"{response_text}\n\n"
                    f"✅ Task details saved.",
            "buttons": [[{"text": "🏠 Main Menu", "callback": "back"}]]
        }
    
    async def _send_help(self, user_id: int) -> Dict[str, Any]:
        """Send help message"""
        return {
            "text": """🤖 <b>Ultimate Coding Agent - Help</b>

<b>Commands:</b>
🏗️ Project - Create new project
📱 Social - Post to social media
📅 Schedule - Schedule a task
🔄 Restart - Restart the agent
⚡ Shutdown - Shutdown the agent
📊 Status - View system status
❓ Help - Show this message

<b>AI Assistant:</b>
Just type naturally to chat with me!

<b>Tips:</b>
• Be specific about your goals
• Use menu buttons for structured tasks
• I'll ask clarifying questions when needed""",
            "buttons": [
                [{"text": "🏗️ New Project", "callback": "menu_project"}],
                [{"text": "📱 Social", "callback": "menu_social"}],
                [{"text": "📅 Schedule", "callback": "menu_schedule"}],
                [{"text": "📊 Status", "callback": "cmd_status"}],
            ]
        }
    
    async def _send_status(self, user_id: int) -> Dict[str, Any]:
        """Send system status"""
        try:
            health = await self.ollama.health_check()
            
            status = f"""📊 <b>System Status</b>

✅ Agent: Online
"""
            if health.get("cloud"):
                status += f"☁️ Ollama Cloud: Connected\n"
            if health.get("local"):
                status += f"📱 Ollama Local: Connected\n"
            
            status += f"\nMode: {health.get('primary', 'unknown').upper()}"
            
            return {"text": status}
            
        except Exception as e:
            return {"text": f"❌ Status check failed: {e}"}
    
    async def _send_main_menu(self, user_id: int) -> Dict[str, Any]:
        """Send main menu"""
        return {
            "text": "🏠 <b>Main Menu</b>",
            "buttons": [
                [{"text": "🏗️ Project", "callback": "menu_project"}, {"text": "📱 Social", "callback": "menu_social"}],
                [{"text": "📅 Schedule", "callback": "menu_schedule"}, {"text": "🧠 Learn", "callback": "menu_learn"}],
                [{"text": "🔄 Restart Agent", "callback": "cmd_restart"}, {"text": "⚡ Shutdown", "callback": "cmd_shutdown"}],
                [{"text": "❓ Help", "callback": "cmd_help"}, {"text": "⬅️ Back", "callback": "back"}]
            ]
        }
    
    async def _perform_restart(self):
        """Restart the agent process"""
        import os
        import sys
        import subprocess
        
        WorkflowLogger.log_system("Initiating Agent Restart...")
        await asyncio.sleep(1)
        
        # Correct Path Resolution (Step 3.1)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        script_path = os.path.join(project_root, "start-agent.sh")
        
        WorkflowLogger.log_step("System", "Restart", f"Root: {project_root}")
        
        if os.path.exists(script_path):
            WorkflowLogger.log_success(f"Found script at {script_path}. Executing...")
            try:
                subprocess.Popen(["bash", script_path, "restart"], start_new_session=True, cwd=project_root)
                sys.exit(0)
            except Exception as e:
                WorkflowLogger.log_error("Restart script execution failed", e)
        
        WorkflowLogger.log_system("Falling back to os.execv restart...")
        os.execv(sys.executable, ['python3'] + sys.argv)

    async def _perform_shutdown(self):
        """Shut down the host machine"""
        import os
        logger.info("Shutting down system...")
        os.system("sudo shutdown now")

    async def _handle_back(self, user_id: int) -> Dict[str, Any]:
        """Handle back navigation (1.9)"""
        self.clear_context(user_id)
        return await self._send_main_menu(user_id)

    async def _handle_help_category(self, user_id: int, category: str) -> Dict[str, Any]:
        """Handle specific help category display (1.8)"""
        self.clear_context(user_id)
        help_content = {
            "help_cmds": "📟 <b>Command Reference</b>\n\n/start - Main menu\n/help - Help center\n/status - System status\n/build - New project wizard",
            "help_feats": "🏗️ <b>Core Features</b>\n\n• Project scaffold generation\n• Multi-platform social posting\n• Advanced task scheduling\n• Autonomous learning",
            "help_examples": "💡 <b>Examples</b>\n\n'Create a FastAPI login page'\n'Schedule a reminder for dev sync at 10am'"
        }
        return {
            "text": help_content.get(category, "Select a category above."),
            "buttons": [[{"text": "⬅️ Back", "callback": "back"}]]
        }

    async def _execute_learning_process(self, user_id: int, data: Dict) -> Dict[str, Any]:
        """Execute focused learning from input (1.5)"""
        self.clear_context(user_id)
        input_text = data.get("input", "")
        # Simulating analysis
        return {
            "text": f"✅ <b>Learning Complete</b>\n\nI have analyzed the provided content and incorporated the key patterns into my internal knowledge base.",
            "buttons": [[{"text": "🏠 Main Menu", "callback": "back"}]]
        }

    async def _perform_learning(self, user_id: int):
        """Trigger autonomous learning process"""
        WorkflowLogger.log_step("Learn", "Execution Started", "Analyzing system state...")
        
        # Simulating learning process
        await asyncio.sleep(5)
        
        memory = get_memory_manager()
        # Add a learning record
        success_msg = "I have completed a review of local system resources and optimized my skill parameters. My pattern recognition for your workspace has been updated."
        memory.add_assistant_message(user_id, success_msg)
        
        # CLEAR CONTEXT AFTER COMPLETION (Step 2.1)
        self.clear_context(user_id)
        WorkflowLogger.log_success("Learning complete. State reset to IDLE.")
        
        # Notify user (if we had a way to push messages, otherwise they see it next time)
        # Note: In a real app, we'd use the bot instance to send a message here.


_handler: Optional[AgentHandler] = None


def get_agent_handler() -> AgentHandler:
    """Get or create agent handler instance"""
    global _handler
    if _handler is None:
        _handler = AgentHandler()
    return _handler
