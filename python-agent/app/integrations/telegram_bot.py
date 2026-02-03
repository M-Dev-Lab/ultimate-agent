"""
Telegram bot integration for Ultimate Coding Agent
Provides chat interface and command handling via Telegram
"""

import logging
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import structlog

from app.core.config import settings
from app.models.database import User, TelegramUser, Build, BuildStatus
from app.db.session import SessionLocal
from app.agents.full_workflow import get_agent_workflow

logger = structlog.get_logger(__name__)


class TelegramBotManager:
    """Manages Telegram bot interactions and command processing"""
    
    def __init__(self):
        """Initialize Telegram bot"""
        if not settings.telegram_bot_token:
            logger.warning("Telegram bot token not configured")
            return
        
        self.token = settings.telegram_bot_token.get_secret_value()
        self.application = None
        self.db = None
    
    async def initialize(self):
        """Initialize bot application and handlers"""
        if not self.token:
            logger.warning("Telegram bot disabled: no token configured")
            return
        
        try:
            self.application = Application.builder().token(self.token).build()
            
            # Register handlers
            self._register_handlers()
            
            logger.info("Telegram bot initialized")
        except Exception as e:
            logger.error(f"Bot initialization failed: {e}")
            raise
    
    def _register_handlers(self):
        """Register command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(CommandHandler("build", self.handle_build_command))
        self.application.add_handler(CommandHandler("status", self.handle_status_command))
        self.application.add_handler(CommandHandler("history", self.handle_history_command))
        self.application.add_handler(CommandHandler("link", self.handle_link_command))
        self.application.add_handler(CommandHandler("admin", self.handle_admin_command))
        
        # Message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Callback handler
        self.application.add_handler(CallbackQueryHandler(self.handle_button_click))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            await self._ensure_user_linked(user.id, user.username, chat_id)
            
            welcome_text = f"""
Welcome to Ultimate Coding Agent 🚀

I can help you generate code, analyze projects, and automate development tasks!

Available commands:
• /build - Start a new build task
• /status - Check build status
• /history - View your builds
• /help - Show detailed help
• /link - Link your account
• /admin - Admin controls (if authorized)

What would you like to do today?
"""
            
            await update.message.reply_text(welcome_text)
            logger.info("Start command", user_id=user.id, chat_id=chat_id)
        except Exception as e:
            logger.error(f"Start command failed: {e}")
            await update.message.reply_text("❌ Error processing command")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 **Command Reference:**

*Build Commands:*
• `/build <project_name>` - Start a new build
  Example: `/build my_api`

*Status Commands:*
• `/status [build_id]` - Check build status
  Example: `/status abc123`

*History:*
• `/history` - Show recent builds

*Account:*
• `/link` - Link your Telegram to your account
• `/admin` - Admin operations

*Additional Features:*
• Send code snippets directly for analysis
• Ask questions about your projects
• Get recommendations for improvements

Need more help? Visit the documentation or contact support.
"""
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
        logger.info("Help command", user_id=update.effective_user.id)
    
    async def handle_build_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /build command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Check if user is linked
            db = SessionLocal()
            tg_user = db.query(TelegramUser).filter_by(telegram_id=user.id).first()
            
            if not tg_user:
                await update.message.reply_text(
                    "❌ Please link your account first using /link command"
                )
                return
            
            # Get project name from args
            if not context.args:
                await update.message.reply_text(
                    "📝 Please provide a project name: `/build my_project`",
                    parse_mode="Markdown"
                )
                return
            
            project_name = " ".join(context.args)
            
            # Show interactive build setup
            keyboard = [
                [
                    InlineKeyboardButton("🐍 Python", callback_data=f"build_py_{project_name}"),
                    InlineKeyboardButton("🟢 Node.js", callback_data=f"build_js_{project_name}")
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Select language for {project_name}:",
                reply_markup=reply_markup
            )
            
            logger.info("Build command", user_id=user.id, project=project_name)
        except Exception as e:
            logger.error(f"Build command failed: {e}")
            await update.message.reply_text("❌ Error processing build command")
    
    async def handle_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            db = SessionLocal()
            user = update.effective_user
            
            tg_user = db.query(TelegramUser).filter_by(telegram_id=user.id).first()
            if not tg_user:
                await update.message.reply_text("❌ Please link your account first")
                return
            
            # Get recent builds
            builds = db.query(Build)\
                .filter_by(user_id=tg_user.user_id)\
                .order_by(Build.created_at.desc())\
                .limit(5)\
                .all()
            
            if not builds:
                await update.message.reply_text("📋 No builds found")
                return
            
            status_text = "📊 **Recent Builds:**\n\n"
            for build in builds:
                status_icon = {
                    BuildStatus.COMPLETED: "✅",
                    BuildStatus.RUNNING: "⏳",
                    BuildStatus.FAILED: "❌",
                    BuildStatus.PENDING: "📝",
                    BuildStatus.CANCELLED: "⛔"
                }.get(build.status, "❓")
                
                status_text += f"{status_icon} `{build.id[:8]}` - {build.project_name}\n"
                status_text += f"   Status: {build.status.value}\n"
                if build.completed_at:
                    status_text += f"   Completed: {build.completed_at.isoformat()}\n"
                status_text += "\n"
            
            await update.message.reply_text(status_text, parse_mode="Markdown")
            logger.info("Status command", user_id=user.id)
        except Exception as e:
            logger.error(f"Status command failed: {e}")
            await update.message.reply_text("❌ Error retrieving status")
    
    async def handle_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        try:
            db = SessionLocal()
            user = update.effective_user
            
            tg_user = db.query(TelegramUser).filter_by(telegram_id=user.id).first()
            if not tg_user:
                await update.message.reply_text("❌ Please link your account first")
                return
            
            # Get builds
            builds = db.query(Build)\
                .filter_by(user_id=tg_user.user_id)\
                .order_by(Build.created_at.desc())\
                .limit(10)\
                .all()
            
            if not builds:
                await update.message.reply_text("📋 No history available")
                return
            
            history_text = "📚 **Build History:**\n\n"
            for build in builds:
                history_text += f"• {build.project_name}\n"
                history_text += f"  ID: `{build.id[:8]}`\n"
                history_text += f"  Status: {build.status.value}\n"
                if build.duration_seconds:
                    history_text += f"  Time: {build.duration_seconds:.1f}s\n"
                history_text += "\n"
            
            await update.message.reply_text(history_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"History command failed: {e}")
            await update.message.reply_text("❌ Error retrieving history")
    
    async def handle_link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /link command - link Telegram to main account"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            await self._ensure_user_linked(user.id, user.username, chat_id)
            
            await update.message.reply_text(
                "✅ Your Telegram account is now linked!\n\n"
                "You can now use all commands. Try `/build my_project` to get started!"
            )
        except Exception as e:
            logger.error(f"Link command failed: {e}")
            await update.message.reply_text("❌ Error linking account")
    
    async def handle_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command - admin operations"""
        try:
            user = update.effective_user
            
            # Check if user is admin
            if user.id not in settings.admin_telegram_ids:
                await update.message.reply_text("❌ Unauthorized")
                return
            
            admin_text = """
🔧 **Admin Commands:**

• `/admin users` - Show user statistics
• `/admin builds` - Show build statistics
• `/admin health` - System health check
• `/admin config` - Show configuration (redacted)
"""
            
            await update.message.reply_text(admin_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Admin command failed: {e}")
            await update.message.reply_text("❌ Error processing admin command")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        try:
            user = update.effective_user
            text = update.message.text
            
            db = SessionLocal()
            tg_user = db.query(TelegramUser).filter_by(telegram_id=user.id).first()
            
            if not tg_user:
                await update.message.reply_text(
                    "👋 Please link your account first using /link"
                )
                return
            
            # Process message based on current state
            if text.lower().startswith("analyze"):
                await self._handle_analysis_request(update, text)
            elif text.lower().startswith("generate"):
                await self._handle_generation_request(update, text)
            else:
                await update.message.reply_text(
                    "I don't understand that command. Try /help for available commands."
                )
            
            logger.info("Message handled", user_id=user.id, text=text[:50])
        except Exception as e:
            logger.error(f"Message handling failed: {e}")
            await update.message.reply_text("❌ Error processing message")
    
    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button clicks"""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            
            if data == "cancel":
                await query.edit_message_text("❌ Cancelled")
            elif data.startswith("build_"):
                await self._process_build_selection(query, data)
            
            logger.info("Button clicked", data=data, user_id=update.effective_user.id)
        except Exception as e:
            logger.error(f"Button click failed: {e}")
    
    async def _handle_analysis_request(self, update: Update, text: str):
        """Handle code analysis request"""
        try:
            await update.message.reply_text("🔍 Analyzing your code with Qwen3-coder cloud...")
            
            # Extract code from message (between markdown code blocks or as plain text)
            code_to_analyze = text
            if "```" in text:
                code_to_analyze = text.split("```")[1].strip()
            
            # Detect language from code blocks or ask user
            language = "python"
            if "```javascript" in text or "```js" in text or "```typescript" in text or "```ts" in text:
                language = "javascript"
            elif "```java" in text:
                language = "java"
            elif "```cpp" in text or "```c++" in text:
                language = "cpp"
            elif "```go" in text:
                language = "go"
            elif "```rust" in text:
                language = "rust"
            
            # Get agent workflow and analyze
            workflow = get_agent_workflow()
            analysis_results = await workflow.analyze_code(
                code=code_to_analyze,
                language=language,
                focus_areas=["security", "performance", "maintainability"]
            )
            
            # Format response
            response = "✅ **Code Analysis Complete**\n\n"
            response += f"**Language:** {language}\n"
            response += f"**Model:** {analysis_results.get('model', 'Qwen3-coder')}\n"
            response += f"**Lines of Code:** {analysis_results['metrics'].get('lines_of_code', 'N/A')}\n\n"
            
            if analysis_results['issues']:
                response += "**Issues Found:**\n"
                for issue in analysis_results['issues'][:5]:
                    response += f"• [{issue.get('severity', 'info').upper()}] {issue.get('type', 'Issue')}: {issue.get('description', 'N/A')}\n"
            else:
                response += "**No issues found! ✨**\n"
            
            if analysis_results['recommendations']:
                response += "\n**Recommendations:**\n"
                for rec in analysis_results['recommendations'][:3]:
                    response += f"• {rec}\n"
            
            await update.message.reply_text(response, parse_mode="Markdown")
            logger.info("Code analysis completed", user_id=update.effective_user.id, issues=len(analysis_results['issues']), model=analysis_results.get('model'))
        except Exception as e:
            logger.error(f"Analysis request failed: {e}")
            await update.message.reply_text("❌ Analysis failed. Please try again.")
    
    async def _handle_generation_request(self, update: Update, text: str):
        """Handle code generation request"""
        try:
            await update.message.reply_text("✨ Generating code with Qwen3-coder cloud...")
            
            # Extract goal from message
            goal = text.replace("generate", "").strip()
            if not goal:
                goal = "A well-structured Python function"
            
            # Detect language preference
            language = "python"
            if "javascript" in goal.lower() or "typescript" in goal.lower() or "nodejs" in goal.lower():
                language = "javascript"
            elif "java" in goal.lower():
                language = "java"
            elif "rust" in goal.lower():
                language = "rust"
            elif "go" in goal.lower() or "golang" in goal.lower():
                language = "go"
            
            logger.info("Code generation started", user_id=update.effective_user.id, goal=goal, language=language)
            
            # Get agent workflow and generate code
            workflow = get_agent_workflow()
            generated_code = await workflow.generate_code(
                specification=goal,
                language=language,
                context="Generated via Telegram bot using Qwen3-coder"
            )
            
            # Format response
            response = f"```{language}\n{generated_code}\n```\n\n✅ Code generated with Qwen3-coder!"
            response += f"\n**Language:** {language}"
            response += f"\n**Lines:** {len(generated_code.split(chr(10)))}"
            
            await update.message.reply_text(response, parse_mode="Markdown")
            logger.info("Code generation completed", user_id=update.effective_user.id, lines=len(generated_code.split('\n')))
        except Exception as e:
            logger.error(f"Generation request failed: {e}")
            await update.message.reply_text("❌ Code generation failed. Please try again.")
    
    async def _process_build_selection(self, query, data: str):
        """Process language selection for build"""
        try:
            parts = data.split("_")
            language = parts[1]
            project_name = "_".join(parts[2:])
            
            await query.edit_message_text(
                f"🚀 Starting build for `{project_name}` in {language.upper()} using Qwen3-coder...",
                parse_mode="Markdown"
            )
            
            # Create build record
            db = SessionLocal()
            build = Build(
                project_name=project_name,
                language=language,
                status=BuildStatus.PENDING,
                user_id=query.from_user.id
            )
            db.add(build)
            db.flush()
            
            logger.info(
                "Build created",
                build_id=build.id,
                project=project_name,
                language=language,
                user_id=query.from_user.id
            )
            
            # Generate build using Agent Workflow with Qwen3-coder
            try:
                workflow = get_agent_workflow()
                specification = f"Create a complete {language} project for {project_name}"
                
                generated_code = await workflow.generate_code(
                    specification=specification,
                    language=language,
                    context=f"Project: {project_name}, Type: Starter project"
                )
                
                # Update build status
                build.status = BuildStatus.COMPLETED
                build.result = generated_code[:1000]  # Store first 1000 chars as preview
                
                db.add(build)
                db.commit()
                
                response = f"✅ **Build Complete**\n\n"
                response += f"**Project:** {project_name}\n"
                response += f"**Language:** {language.upper()}\n"
                response += f"**Model:** Qwen3-coder (Ollama Cloud)\n"
                response += f"**Build ID:** `{build.id[:8]}`\n\n"
                response += f"**Generated (Preview):**\n```{language}\n{generated_code[:300]}...\n```"
                
                await query.edit_message_text(response, parse_mode="Markdown")
                
                logger.info("Build completed with Qwen3-coder", build_id=build.id, project=project_name)
            except Exception as build_error:
                logger.error(f"Build generation failed: {build_error}")
                build.status = BuildStatus.FAILED
                db.add(build)
                db.commit()
                
                await query.edit_message_text(
                    f"❌ Build failed: {str(build_error)[:100]}",
                    parse_mode="Markdown"
                )
            
            db.close()
        except Exception as e:
            logger.error(f"Build creation failed: {e}")
            await query.edit_message_text("❌ Build creation failed. Please try again.")
    
    async def _ensure_user_linked(self, telegram_id: int, username: Optional[str], chat_id: int):
        """Ensure Telegram user is linked"""
        db = SessionLocal()
        
        tg_user = db.query(TelegramUser).filter_by(telegram_id=telegram_id).first()
        
        if not tg_user:
            # Create new user entry
            user = User(
                username=username or f"telegram_{telegram_id}",
                email=f"telegram_{telegram_id}@agent.local",
                hashed_password="",
                role="user",
                is_active=True,
                is_verified=True
            )
            db.add(user)
            db.flush()
            
            tg_user = TelegramUser(
                user_id=user.id,
                telegram_id=telegram_id,
                telegram_username=username,
                chat_id=chat_id,
                is_active=True
            )
            db.add(tg_user)
            db.commit()
            
            logger.info("User linked", telegram_id=telegram_id, user_id=user.id)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle bot errors"""
        logger.error(f"Telegram error: {context.error}")
    
    async def start(self):
        """Start bot polling"""
        if not self.token:
            logger.warning("Telegram bot not started: no token configured")
            return
        
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Telegram bot started")
        except Exception as e:
            logger.error(f"Bot start failed: {e}")
            raise
    
    async def stop(self):
        """Stop bot polling"""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.warning(f"Bot stop failed: {e}")


# Global bot manager
_bot_manager: Optional[TelegramBotManager] = None


def get_telegram_bot() -> TelegramBotManager:
    """Get or initialize Telegram bot"""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = TelegramBotManager()
    return _bot_manager


async def init_telegram_bot():
    """Initialize Telegram bot on startup"""
    try:
        bot = get_telegram_bot()
        await bot.initialize()
        logger.info("Telegram bot initialized")
    except Exception as e:
        logger.warning(f"Telegram bot initialization skipped: {e}")


async def start_telegram_bot():
    """Start Telegram bot"""
    try:
        bot = get_telegram_bot()
        await bot.start()
    except Exception as e:
        logger.warning(f"Telegram bot start skipped: {e}")


async def stop_telegram_bot():
    """Stop Telegram bot"""
    try:
        bot = get_telegram_bot()
        await bot.stop()
    except Exception as e:
        logger.warning(f"Telegram bot stop failed: {e}")
