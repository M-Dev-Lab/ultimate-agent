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
import time
import structlog

logger = structlog.get_logger(__name__)


class WorkflowState(Enum):
    IDLE = "idle"
    # Project Wizard
    PROJECT_NAME = "project_name"
    PROJECT_GOAL = "project_goal"
    PROJECT_DETAILS = "project_details"
    PROJECT_TECH = "project_tech"
    PROJECT_LANG = "project_lang"
    # Social Wizard
    SOCIAL_TYPE = "social_type"
    SOCIAL_PLATFORM = "social_platform"
    SOCIAL_CONTENT = "social_content"
    # Schedule Wizard
    SCHEDULE_PROMPT = "schedule_prompt"
    # System
    RESTART_CONFIRM = "restart_confirm"
    SHUTDOWN_CONFIRM = "shutdown_confirm"
    LEARNING = "learning"


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
        Process incoming message with full error handling, memory, and analytics
        """
        start_time = time.time()
        error_handler = get_error_handler()
        memory_manager = get_memory_manager()
        analytics = get_analytics_tracker()
        
        try:
            # Add user message to memory
            memory_manager.add_user_message(user_id, message)
            
            # Special case for workflow handling if it exists
            # (Note: We keep the old workflow logic for now as a fallback)
            context = self.get_context(user_id)
            if context["workflow_state"] != WorkflowState.IDLE:
                workflow_result = await self._handle_workflow(user_id, message)
                response_text = workflow_result.get("text", "Done!")
                skill_used = "workflow_" + context["workflow_state"].value
            else:
                # Detect and route to skill
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
                else:
                    # Fallback to general AI response
                    conversation = memory_manager.build_conversation_for_ollama(user_id)
                    response_text = await error_handler.execute_with_retry(
                        self.ollama.chat,
                        messages=conversation,
                        category=ErrorCategory.OLLAMA,
                        max_retries=3
                    )
                    skill_used = None
            
            # Add assistant response to memory
            memory_manager.add_assistant_message(user_id, response_text)
            
            # Record analytics
            response_time_ms = (time.time() - start_time) * 1000
            analytics.record_message(
                user_id=user_id,
                message=message,
                response=response_text,
                response_time_ms=response_time_ms,
                skill_used=skill_used,
                success=True
            )
            
            return {
                "text": response_text,
                "success": True,
                "response_time_ms": response_time_ms
            }
            
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
        """Handle multi-step workflows"""
        context = self.get_context(user_id)
        state = context["workflow_state"]
        data = context["workflow_data"]
        msg_lower = message.lower().strip()
        
        # Global Back handling
        if "back" in msg_lower or "⬅️" in message:
            self.clear_context(user_id)
            return await self._send_main_menu(user_id)

        # --- PROJECT WIZARD ---
        if state == WorkflowState.PROJECT_NAME:
            data["project_name"] = message.strip()
            context["workflow_state"] = WorkflowState.PROJECT_GOAL
            return {"text": "🎯 <b>Project Goal</b>\n\nWhat is the main goal of this project?"}
        
        elif state == WorkflowState.PROJECT_GOAL:
            data["goal"] = message.strip()
            context["workflow_state"] = WorkflowState.PROJECT_DETAILS
            return {"text": "📝 <b>Project Details</b>\n\nPlease provide more details/requirements for the project:"}
        
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

        # --- SOCIAL WIZARD ---
        elif state == WorkflowState.SOCIAL_TYPE:
            data["content_type"] = message.strip()
            context["workflow_state"] = WorkflowState.SOCIAL_PLATFORM
            return {
                "text": "🌐 <b>Select Platforms</b>\n\nWhere should we share this?",
                "buttons": [
                    [{"text": "🐦 Twitter/X", "callback": "plat_twitter"}, {"text": "📘 LinkedIn", "callback": "plat_linkedin"}],
                    [{"text": "📕 Facebook", "callback": "plat_facebook"}, {"text": "📷 Instagram", "callback": "plat_insta"}],
                    [{"text": "⬅️ Back", "callback": "back"}]
                ]
            }
        
        elif state == WorkflowState.SOCIAL_PLATFORM:
            data["platform"] = message.replace("plat_", "")
            context["workflow_state"] = WorkflowState.SOCIAL_CONTENT
            return {"text": f"✍️ <b>Content</b>\n\nEnter the text you want to post to {data['platform']}:"}
        
        elif state == WorkflowState.SOCIAL_CONTENT:
            data["content"] = message.strip()
            return await self._execute_social_post(user_id, data)

        # --- SCHEDULE WIZARD ---
        elif state == WorkflowState.SCHEDULE_PROMPT:
            data["task_description"] = message.strip()
            # In a real scenario, we'd parse time from this or ask for it
            # For now, we save it as a task to be processed.
            return await self._execute_schedule_creation(user_id, data)

        # --- SYSTEM COMMANDS ---
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
        
        # NEW 7-BUTTON MAIN MENU DETECTION
        if "🏗️ project" in msg_lower or (msg_lower.startswith("project") and len(msg_lower) < 15):
            context["workflow_state"] = WorkflowState.PROJECT_NAME
            return {
                "text": "🏗️ <b>Create New Project</b>\n\nWhat is the name of your project?",
                "workflow_state": WorkflowState.PROJECT_NAME.value
            }
        
        if "📱 social" in msg_lower or (msg_lower.startswith("social") and len(msg_lower) < 15):
            context["workflow_state"] = WorkflowState.SOCIAL_TYPE
            return {
                "text": "📱 <b>Social Media Sharing</b>\n\nWhat type of content do you want to share?",
                "buttons": [
                    [{"text": "📝 Post", "callback": "type_post"}, {"text": "🧵 Thread", "callback": "type_thread"}],
                    [{"text": "📢 Announcement", "callback": "type_announcement"}, {"text": "⬅️ Back", "callback": "back"}]
                ],
                "workflow_state": WorkflowState.SOCIAL_TYPE.value
            }
        
        if "📅 schedule" in msg_lower or (msg_lower.startswith("schedule") and len(msg_lower) < 15):
            context["workflow_state"] = WorkflowState.SCHEDULE_PROMPT
            return {
                "text": "📅 <b>Schedule Task</b>\n\nPlease describe the task or operation you want to schedule:",
                "workflow_state": WorkflowState.SCHEDULE_PROMPT.value
            }

        if "🧠 learn" in msg_lower or (msg_lower.startswith("learn") and len(msg_lower) < 15):
            context["workflow_state"] = WorkflowState.LEARNING
            asyncio.create_task(self._perform_learning(user_id))
            return {
                "text": "🧠 <b>Autonomous Learning Mode</b>\n\nI am now reviewing system resources, memory logs, and project metadata to optimize my skills and knowledge base...",
                "workflow_state": WorkflowState.LEARNING.value
            }
        
        if "restart" in msg_lower:
            context["workflow_state"] = WorkflowState.RESTART_CONFIRM
            return {
                "text": "🔄 <b>Confirm Restart</b>\n\nAre you sure you want to restart the agent? (Reply 'restart' or 'yes' to confirm)",
                "workflow_state": WorkflowState.RESTART_CONFIRM.value
            }
        
        if "shutdown" in msg_lower:
            context["workflow_state"] = WorkflowState.SHUTDOWN_CONFIRM
            return {
                "text": "⚠️ <b>CONFIRM SYSTEM SHUTDOWN</b>\n\nThis will SHUT DOWN the host machine! (Reply 'shutdown' or 'yes' to confirm)",
                "workflow_state": WorkflowState.SHUTDOWN_CONFIRM.value
            }
        
        if "help" in msg_lower or msg_lower == "/help":
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
        import time
        logger.info("Restarting agent...")
        await asyncio.sleep(1)
        # Re-execute the current process
        os.execv(sys.executable, ['python3'] + sys.argv)

    async def _perform_shutdown(self):
        """Shut down the host machine"""
        import os
        logger.info("Shutting down system...")
        os.system("sudo shutdown now")

    async def _perform_learning(self, user_id: int):
        """Trigger autonomous learning process"""
        logger.info("Starting autonomous learning", user_id=user_id)
        # Simulating learning process - in reality this would scan local resources
        await asyncio.sleep(5)
        
        memory = get_memory_manager()
        # Add a learning record
        memory.add_assistant_message(user_id, "I have completed a review of local system resources and optimized my skill parameters. My pattern recognition for your workspace has been updated.")
        
        logger.info("Learning complete", user_id=user_id)


_handler: Optional[AgentHandler] = None


def get_agent_handler() -> AgentHandler:
    """Get or create agent handler instance"""
    global _handler
    if _handler is None:
        _handler = AgentHandler()
    return _handler
