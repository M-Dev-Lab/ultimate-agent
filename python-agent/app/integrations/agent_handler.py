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
import structlog

logger = structlog.get_logger(__name__)


class WorkflowState(Enum):
    IDLE = "idle"
    PROJECT_NAME = "project_name"
    PROJECT_LANGUAGE = "project_language"
    PROJECT_FRAMEWORK = "project_framework"
    PROJECT_GOAL = "project_goal"
    SOCIAL_PLATFORM = "social_platform"
    SOCIAL_CONTENT = "social_content"
    SCHEDULE_TASK = "schedule_task"
    SCHEDULE_TIME = "schedule_time"
    SCHEDULE_SKILL = "schedule_skill"
    CODE_ANALYSIS = "code_analysis"
    CONFIRMATION = "confirmation"


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
        """Get or create conversation context for user"""
        if user_id not in self.contexts:
            self.contexts[user_id] = {
                "user_id": user_id,
                "workflow_state": WorkflowState.IDLE,
                "workflow_data": {},
                "conversation_history": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        return self.contexts[user_id]
    
    def clear_context(self, user_id: int):
        """Clear conversation context for user"""
        if user_id in self.contexts:
            del self.contexts[user_id]
    
    async def process_message(
        self,
        user_id: int,
        message: str,
        context_type: str = "message"
    ) -> Dict[str, Any]:
        """
        Process a message from Telegram user
        
        Args:
            user_id: Telegram user ID
            message: User message
            context_type: Type of message (message, button_callback, etc.)
            
        Returns:
            Response dictionary with text and optional actions
        """
        context = self.get_context(user_id)
        
        logger.info(
            "Processing message",
            user_id=user_id,
            workflow_state=context["workflow_state"].value,
            message_length=len(message)
        )
        
        context["conversation_history"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if len(context["conversation_history"]) > 20:
            context["conversation_history"] = context["conversation_history"][-20:]
        
        if context["workflow_state"] != WorkflowState.IDLE:
            result = await self._handle_workflow(user_id, message)
            context["updated_at"] = datetime.utcnow()
            return result
        
        return await self._handle_general_message(user_id, message)
    
    async def _handle_workflow(self, user_id: int, message: str) -> Dict[str, Any]:
        """Handle multi-step workflows"""
        context = self.get_context(user_id)
        state = context["workflow_state"]
        data = context["workflow_data"]
        
        if state == WorkflowState.PROJECT_NAME:
            data["project_name"] = message.strip()
            context["workflow_state"] = WorkflowState.PROJECT_LANGUAGE
            return {
                "text": f"📦 <b>Project: {data['project_name']}</b>\n\nSelect programming language:",
                "buttons": [
                    [{"text": "🐍 Python", "callback": "lang_python"}],
                    [{"text": "🟢 JavaScript", "callback": "lang_js"}],
                    [{"text": "🔵 TypeScript", "callback": "lang_ts"}],
                    [{"text": "🔴 Go", "callback": "lang_go"}],
                    [{"text": "⬅️ Back", "callback": "cancel"}],
                ],
                "workflow_state": WorkflowState.PROJECT_LANGUAGE.value
            }
        
        elif state == WorkflowState.PROJECT_LANGUAGE:
            lang_map = {
                "lang_python": "python",
                "lang_js": "javascript",
                "lang_ts": "typescript",
                "lang_go": "go",
            }
            if message in lang_map:
                data["language"] = lang_map[message]
                if data["language"] == "python":
                    context["workflow_state"] = WorkflowState.PROJECT_FRAMEWORK
                    return {
                        "text": "Select Python framework:",
                        "buttons": [
                            [{"text": "⚡ FastAPI", "callback": "fw_fastapi"}],
                            [{"text": "🌶️ Flask", "callback": "fw_flask"}],
                            [{"text": "🔺 Django", "callback": "fw_django"}],
                            [{"text": "⬅️ Back", "callback": "cancel"}],
                        ],
                        "workflow_state": WorkflowState.PROJECT_FRAMEWORK.value
                    }
                else:
                    data["framework"] = data["language"]
                    context["workflow_state"] = WorkflowState.PROJECT_GOAL
                    return {
                        "text": f"📝 Describe your project goal and requirements:",
                        "workflow_state": WorkflowState.PROJECT_GOAL.value
                    }
            else:
                return {"text": "Please select a language from the buttons."}
        
        elif state == WorkflowState.PROJECT_FRAMEWORK:
            fw_map = {
                "fw_fastapi": "FastAPI",
                "fw_flask": "Flask",
                "fw_django": "Django",
            }
            if message in fw_map:
                data["framework"] = fw_map[message]
            context["workflow_state"] = WorkflowState.PROJECT_GOAL
            return {
                "text": f"📝 Describe your project goal and requirements:"
            }
        
        elif state == WorkflowState.PROJECT_GOAL:
            data["goal"] = message
            return await self._execute_project_creation(user_id, data)
        
        elif state == WorkflowState.SOCIAL_PLATFORM:
            platform_map = {
                "🐦 Tweet": "twitter",
                "📘 LinkedIn": "linkedin",
                "📕 Facebook": "facebook",
                "📷 Instagram": "instagram",
            }
            if message in platform_map:
                data["platform"] = platform_map[message]
                context["workflow_state"] = WorkflowState.SOCIAL_CONTENT
                return {
                    "text": f"✍️ What would you like to post to {message}?"
                }
            else:
                return {"text": "Please select a platform from the buttons."}
        
        elif state == WorkflowState.SOCIAL_CONTENT:
            data["content"] = message
            return await self._execute_social_post(user_id, data)
        
        elif state == WorkflowState.SCHEDULE_TASK:
            data["task_name"] = message
            context["workflow_state"] = WorkflowState.SCHEDULE_TIME
            return {
                "text": "📅 When should this task run?\nFormat: cron expression or natural language (e.g., 'every day at 9am', '2026-02-15 10:00')"
            }
        
        elif state == WorkflowState.SCHEDULE_TIME:
            data["schedule"] = message
            context["workflow_state"] = WorkflowState.SCHEDULE_SKILL
            return {
                "text": "⚡ What skill should run?\n(Skill name or description)",
                "buttons": [
                    [{"text": "🔨 Create Project", "callback": "skill_project"}],
                    [{"text": "📱 Social Post", "callback": "skill_social"}],
                    [{"text": "📝 Custom Code", "callback": "skill_code"}],
                ]
            }
        
        elif state == WorkflowState.SCHEDULE_SKILL:
            data["skill"] = message
            return await self._execute_schedule_creation(user_id, data)
        
        elif state == WorkflowState.CONFIRMATION:
            if message.lower() in ["yes", "y", "confirm"]:
                action = data.get("pending_action")
                if action == "restart":
                    return {"text": "🔄 Restarting agent...", "action": "restart"}
                elif action == "shutdown":
                    return {"text": "⚡ Shutting down...", "action": "shutdown"}
            else:
                self.clear_context(user_id)
                return {"text": "❌ Cancelled."}
        
        return {"text": "Workflow completed or cancelled."}
    
    async def _handle_general_message(self, user_id: int, message: str) -> Dict[str, Any]:
        """Handle general messages without active workflow"""
        context = self.get_context(user_id)
        
        msg_lower = message.lower().strip()
        
        # NEW 7-BUTTON MAIN MENU DETECTION
        if msg_lower == "🏗️ project" or "project" in msg_lower and ("new" in msg_lower or "create" in msg_lower):
            context["workflow_state"] = WorkflowState.PROJECT_NAME
            return {
                "text": "🏗️ <b>Create New Project</b>\n\nWhat's your project name?",
                "workflow_state": WorkflowState.PROJECT_NAME.value
            }
        
        if msg_lower == "📱 social" or "social" in msg_lower or "post" in msg_lower:
            context["workflow_state"] = WorkflowState.SOCIAL_PLATFORM
            return {
                "text": "📱 <b>Social Media</b>\n\nSelect platform:",
                "buttons": [
                    [{"text": "🐦 Tweet", "callback": "platform_twitter"}],
                    [{"text": "📘 LinkedIn", "callback": "platform_linkedin"}],
                    [{"text": "📕 Facebook", "callback": "platform_facebook"}],
                    [{"text": "📷 Instagram", "callback": "platform_instagram"}],
                    [{"text": "⬅️ Back", "callback": "cancel"}],
                ],
                "workflow_state": WorkflowState.SOCIAL_PLATFORM.value
            }
        
        if msg_lower == "📅 schedule" or "schedule" in msg_lower or "task" in msg_lower:
            context["workflow_state"] = WorkflowState.SCHEDULE_TASK
            return {
                "text": "📅 <b>Schedule Task</b>\n\nWhat's the task name?",
                "workflow_state": WorkflowState.SCHEDULE_TASK.value
            }
        
        if "restart" in msg_lower:
            context["workflow_state"] = WorkflowState.CONFIRMATION
            context["workflow_data"] = {"pending_action": "restart"}
            return {
                "text": "⚠️ <b>Confirm Restart</b>\n\nAre you sure you want to restart the agent?",
                "workflow_state": WorkflowState.CONFIRMATION.value
            }
        
        if "shutdown" in msg_lower:
            context["workflow_state"] = WorkflowState.CONFIRMATION
            context["workflow_data"] = {"pending_action": "shutdown"}
            return {
                "text": "⚠️ <b>⚠️ CONFIRM SHUTDOWN ⚠️</b>\n\nThis will STOP the agent completely!\n\nType 'SHUTDOWN' to confirm.",
                "workflow_state": WorkflowState.CONFIRMATION.value
            }
        
        if msg_lower == "❓ help" or "help" in msg_lower or msg_lower == "/help":
            return await self._send_help(user_id)
        
        if "status" in msg_lower or msg_lower == "/status":
            return await self._send_status(user_id)
        
        if "back" in msg_lower or "⬅️" in message:
            self.clear_context(user_id)
            return await self._send_main_menu(user_id)
        
        # Default: Send to AI
        return await self._send_to_ai(user_id, message, context)
    
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
            
            context["workflow_state"] = WorkflowState.IDLE
            
            return {
                "text": f"📱 <b>Post for {platform.capitalize()}</b>\n\n"
                        f"Original: {content}\n\n"
                        f"Optimized:\n{result}\n\n"
                        f"[Post button would go here - requires API integration]",
                "buttons": [
                    [{"text": "✅ Post Now", "callback": f"post_{platform}"}],
                    [{"text": "✏️ Edit", "callback": "edit_post"}],
                    [{"text": "❌ Cancel", "callback": "cancel"}],
                ],
                "platform": platform,
                "content": result
            }
            
        except Exception as e:
            logger.error(f"Social post failed: {e}")
            return {"text": f"❌ Error: {e}"}
    
    async def _execute_schedule_creation(self, user_id: int, data: Dict) -> Dict[str, Any]:
        """Execute schedule creation"""
        context = self.get_context(user_id)
        
        task_name = data.get("task_name", "Unnamed Task")
        schedule = data.get("schedule", "")
        skill = data.get("skill", "")
        
        context["workflow_state"] = WorkflowState.IDLE
        
        return {
            "text": f"📅 <b>Task Scheduled</b>\n\n"
                    f"Task: {task_name}\n"
                    f"Schedule: {schedule}\n"
                    f"Skill: {skill}\n\n"
                    f"✅ Task saved to scheduler!\n\n"
                    f"[Scheduler persistence requires database integration]",
            "schedule_data": data
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
                [{"text": "🏗️ Project", "callback": "menu_project"}],
                [{"text": "📱 Social", "callback": "menu_social"}],
                [{"text": "📅 Schedule", "callback": "menu_schedule"}],
                [{"text": "🔄 Restart Agent", "callback": "cmd_restart"}],
                [{"text": "⚡ Shutdown", "callback": "cmd_shutdown"}],
                [{"text": "❓ Help", "callback": "cmd_help"}],
            ]
        }


_handler: Optional[AgentHandler] = None


def get_agent_handler() -> AgentHandler:
    """Get or create agent handler instance"""
    global _handler
    if _handler is None:
        _handler = AgentHandler()
    return _handler
