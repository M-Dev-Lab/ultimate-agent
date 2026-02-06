"""
Telegram bot integration for Ultimate Coding Agent
Interactive bot with skills, filesystem, and social media capabilities
Unified command handler consolidates all Node.js telegram.ts functionality
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ApplicationBuilder
from telegram.request import HTTPXRequest
import structlog

from app.core.config import settings
from app.models.database import User, TelegramUser, Build, BuildStatus
from app.db.session import SessionLocal
from app.skills.registry import get_skill_registry
from app.agents.full_workflow import get_agent_workflow
from app.integrations.ollama import get_ollama_client
from app.integrations.file_manager import get_file_manager
from app.integrations.browser_controller import get_browser_controller
from app.integrations.agent_handler import get_agent_handler
from app.integrations.unified_commands import get_command_handler

logger = structlog.get_logger(__name__)


class TelegramBotManager:
    """Telegram bot with full capabilities"""
    
    # NEW 7-Button Main Menu (as per plan)
    MAIN_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🏗️ Project"), KeyboardButton("📱 Social")],
            [KeyboardButton("📅 Schedule"), KeyboardButton("🧠 Learn")],
            [KeyboardButton("🔄 Restart Agent"), KeyboardButton("⚡ Shutdown")],
            [KeyboardButton("❓ Help"), KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # Skill categories
    SKILL_CATEGORIES = ReplyKeyboardMarkup(
        [
            [KeyboardButton("💻 Code"), KeyboardButton("🔍 Analysis")],
            [KeyboardButton("🛠️ DevOps"), KeyboardButton("📝 Docs")],
            [KeyboardButton("🧪 Testing"), KeyboardButton("📱 Social")],
            [KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # Code skills
    CODE_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🐍 Python API"), KeyboardButton("🟢 Node.js API")],
            [KeyboardButton("⚛️ React Component"), KeyboardButton("🔵 TypeScript")],
            [KeyboardButton("⬅️ Skills")],
        ],
        resize_keyboard=True,
    )
    
    # Analysis skills
    ANALYSIS_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔒 Security Audit"), KeyboardButton("⚡ Performance")],
            [KeyboardButton("🐛 Bug Finding"), KeyboardButton("📊 Code Review")],
            [KeyboardButton("⬅️ Skills")],
        ],
        resize_keyboard=True,
    )
    
    # DevOps skills
    DEVOPS_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🐳 Docker"), KeyboardButton("🔄 CI/CD")],
            [KeyboardButton("☸️ Kubernetes"), KeyboardButton("📦 Deployment")],
            [KeyboardButton("⬅️ Skills")],
        ],
        resize_keyboard=True,
    )
    
    # Social posting
    SOCIAL_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🐦 Tweet"), KeyboardButton("📘 LinkedIn")],
            [KeyboardButton("📕 Facebook"), KeyboardButton("📷 Instagram")],
            [KeyboardButton("🤖 Reddit"), KeyboardButton("📝 Medium")],
            [KeyboardButton("📢 Announcement"), KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # File operations
    FILE_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("📄 Create File"), KeyboardButton("📖 Read File")],
            [KeyboardButton("✏️ Edit File"), KeyboardButton("🗑️ Delete File")],
            [KeyboardButton("📁 New Folder"), KeyboardButton("📂 List Folder")],
            [KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # Browser operations
    BROWSER_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🌐 Open URL"), KeyboardButton("📸 Screenshot")],
            [KeyboardButton("🌐 Check Browsers"), KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # Project creation menu
    PROJECT_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🐍 Python"), KeyboardButton("🟢 JavaScript")],
            [KeyboardButton("🔵 TypeScript"), KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # Schedule menu
    SCHEDULE_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("📋 List Tasks"), KeyboardButton("➕ New Task")],
            [KeyboardButton("🗑️ Delete Task"), KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # Help menu
    HELP_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("📖 Commands"), KeyboardButton("💡 Tips")],
            [KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # Analysis menu
    ANALYSIS_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔒 Security Audit"), KeyboardButton("⚡ Performance")],
            [KeyboardButton("🐛 Bug Finding"), KeyboardButton("📊 Code Review")],
            [KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    def __init__(self):
        self.token = None
        self.application = None
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        
        if settings.telegram_bot_token:
            self.token = settings.telegram_bot_token.get_secret_value()
        else:
            logger.warning("Telegram bot token not configured")
    
    async def initialize(self):
        """Initialize bot"""
        if not self.token:
            logger.warning("Telegram bot disabled")
            return
        
        try:
            request = HTTPXRequest(connection_pool_size=8)
            self.application = (
                ApplicationBuilder()
                .token(self.token)
                .request(request)
                .build()
            )
            self._register_handlers()
            await self.application.initialize()
            logger.info("Telegram bot initialized")
        except Exception as e:
            logger.error(f"Bot initialization failed: {e}")
            raise
    
    def _register_handlers(self):
        """Register command handlers - simplified and unified"""
        command_handler = get_command_handler()
        
        # Command handlers - preferably from unified_commands (Inline UI)
        self.application.add_handler(CommandHandler("start", command_handler.handle_start))
        self.application.add_handler(CommandHandler("help", command_handler.handle_help))
        self.application.add_handler(CommandHandler("status", command_handler.handle_status))
        self.application.add_handler(CommandHandler("build", command_handler.handle_build_command))
        self.application.add_handler(CommandHandler("code", command_handler.handle_code_command))
        self.application.add_handler(CommandHandler("fix", command_handler.handle_fix_command))
        self.application.add_handler(CommandHandler("post", command_handler.handle_post_command))
        self.application.add_handler(CommandHandler("skill", command_handler.handle_skills_command))
        
        # Map additional legacy commands to existing local handlers
        self.application.add_handler(CommandHandler("file", self.handle_file))
        self.application.add_handler(CommandHandler("open", self.handle_open_url))
        self.application.add_handler(CommandHandler("link", self.handle_link))
        
        # Note: /schedule is handled by the natural language bridge or menu buttons
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(command_handler.handle_callback_query))
        
        # Message handler for text
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            await self._ensure_user_linked(user.id, user.username, chat_id)
            
            ollama = get_ollama_client()
            health = await ollama.health_check()
            mode = "☁️ Cloud" if health.get("primary") == "cloud" else "📱 Local"
            
            welcome = f"""
🤖 <b>Welcome to Ultimate Coding Agent!</b>

🤖 AI Mode: {mode}

<b>Available Features:</b>
🏗️ <b>New Project</b> - Generate complete projects
💡 <b>Use Skill</b> - Execute specialized skills
📁 <b>Files</b> - Create, edit, delete files
🌐 <b>Browser</b> - Control browser
📱 <b>Social</b> - Post to social media
📊 <b>My Builds</b> - View your builds

<i>Select an option below!</i>
"""
            
            await update.message.reply_text(welcome, reply_markup=self.MAIN_KEYBOARD, parse_mode="HTML")
            logger.info("User started bot", user_id=user.id)
            
        except Exception as e:
            logger.error(f"Start failed: {e}")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 <b>Help - Ultimate Coding Agent</b>

<b>Commands:</b>
/start - Start the bot
/help - Show this help
/build [name] [desc] - Create project
/skill [name] - Execute a skill
/file [operation] [path] - File operations
/post [platform] [text] - Social posting
/open [url] - Open URL in browser
/status - System status
/health - Check AI connection

<b>Buttons:</b>
🏗️ New Project - Generate projects
💡 Use Skill - Open skill menu
📁 Files - File operations
🌐 Browser - Browser control
📱 Social - Social media posting

<b>Examples:</b>
/build my_api A REST API
/file create test.py "content"
/post twitter Hello world!
/open https://google.com
"""
        
        await update.message.reply_text(help_text, reply_markup=self.MAIN_KEYBOARD, parse_mode="HTML")
    
    async def handle_build(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /build command"""
        try:
            user = update.effective_user
            args = context.args
            
            if not args:
                await update.message.reply_text(
                    "📦 <b>Create New Project</b>\n\nUsage: /build [name] [description]\n\nExample: /build my_api A REST API",
                    reply_markup=self.MAIN_KEYBOARD,
                    parse_mode="HTML"
                )
                return
            
            project_name = args[0]
            description = " ".join(args[1:]) if len(args) > 1 else project_name
            
            db = SessionLocal()
            tg_user = db.query(TelegramUser).filter_by(telegram_id=user.id).first()
            
            if not tg_user:
                db.close()
                await update.message.reply_text("❌ Please link your account first!", reply_markup=self.MAIN_KEYBOARD)
                return
            
            build = Build(
                project_name=project_name,
                language="python",
                status=BuildStatus.PENDING,
                user_id=tg_user.user_id,
            )
            db.add(build)
            db.commit()
            db.close()
            
            await update.message.reply_text(
                f"🚀 <b>Building {project_name}</b>...\n\n⏳ Generating with Qwen3-coder...",
                parse_mode="HTML"
            )
            
            workflow = get_agent_workflow()
            result = await workflow.execute({
                "user_id": tg_user.user_id,
                "build_id": build.id,
                "project_name": project_name,
                "requirements": description,
            })
            
            if result.get("status") == "completed":
                code_preview = (result.get("generated_code", "") or "")[:300]
                await update.message.reply_text(
                    f"✅ <b>Build Complete!</b>\n\n📦 {project_name}\n🆔 <code>{build.id[:8]}</code>\n\n<code>{code_preview}...</code>",
                    reply_markup=self.MAIN_KEYBOARD,
                    parse_mode="HTML",
                )
            else:
                await update.message.reply_text(
                    f"❌ Build failed: {result.get('error', 'Unknown')}",
                    reply_markup=self.MAIN_KEYBOARD
                )
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def handle_skill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /skill command"""
        await update.message.reply_text(
            "💡 <b>Select a Skill Category:</b>",
            reply_markup=self.SKILL_CATEGORIES,
            parse_mode="HTML"
        )
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            ollama = get_ollama_client()
            health = await ollama.health_check()
            
            status = f"""
📊 <b>System Status</b>

🤖 Bot: Online ✅
"""
            if health.get("cloud"):
                status += "☁️ Ollama Cloud: Connected ✅\n"
            if health.get("local"):
                status += f"📱 Ollama Local: Connected ✅\n"
                models = health.get("models", [])[:3]
                if models:
                    status += f"📦 Models: {', '.join(models)}\n"
            
            status += f"\n🎯 Primary: {health.get('primary', 'none').upper()}"
            
            await update.message.reply_text(status, reply_markup=self.MAIN_KEYBOARD, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def handle_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /health command - check AI"""
        try:
            ollama = get_ollama_client()
            await update.message.reply_text("🔄 Checking AI connection...", reply_markup=self.MAIN_KEYBOARD)
            
            health = await ollama.health_check()
            
            if health.get("primary"):
                msg = f"✅ <b>AI Connected!</b>\n\nMode: {health['primary'].title()}\n"
                if health.get("models"):
                    msg += f"Models: {', '.join(health['models'][:5])}"
            else:
                msg = "❌ <b>No AI connection!</b>\n\nCheck Ollama configuration."
            
            await update.message.reply_text(msg, reply_markup=self.MAIN_KEYBOARD, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /file command"""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "📁 <b>File Operations</b>\n\n"
                "Commands:\n"
                "/file create [path] [content]\n"
                "/file read [path]\n"
                "/file delete [path]\n"
                "/file list [path]\n"
                "/file folder [path]",
                reply_markup=self.FILE_KEYBOARD,
                parse_mode="HTML"
            )
            return
        
        await update.message.reply_text("📁 Use the file menu buttons!", reply_markup=self.FILE_KEYBOARD)
    
    async def handle_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /post command"""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "📱 <b>Social Media Posting</b>\n\n"
                "Commands:\n"
                "/post twitter [message]\n"
                "/post linkedin [message]\n"
                "/post facebook [message]\n"
                "/post reddit [title] [subreddit]\n"
                "/post medium [title]\n\n"
                "Or use the Social menu!",
                reply_markup=self.SOCIAL_KEYBOARD,
                parse_mode="HTML"
            )
            return
        
        platform = args[0].lower()
        text = " ".join(args[1:])
        
        browser = get_browser_controller()
        result = await browser.create_social_post(platform, text)
        
        await update.message.reply_text(
            result.message,
            reply_markup=self.SOCIAL_KEYBOARD,
            parse_mode="HTML" if "<b>" in result.message else None
        )
    
    async def handle_open_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /open command"""
        args = context.args
        
        if not args:
            await update.message.reply_text("🌐 Usage: /open [URL]", reply_markup=self.BROWSER_KEYBOARD)
            return
        
        url = args[0]
        browser = get_browser_controller()
        result = await browser.open_url(url)
        
        await update.message.reply_text(result.message, reply_markup=self.BROWSER_KEYBOARD)
    
    async def handle_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /link command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            await self._ensure_user_linked(user.id, user.username, chat_id)
            
            await update.message.reply_text(
                "✅ <b>Account Linked!</b>",
                reply_markup=self.MAIN_KEYBOARD,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Link failed: {e}")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all text messages - BRIDGED to Agent AI Brain"""
        try:
            user = update.effective_user
            text = update.message.text
            chat_id = update.effective_chat.id

            logger.info(f"Telegram message received: {text[:50]}...", user_id=user.id)

            from app.integrations.telegram_bridge import get_telegram_bridge
            bridge = get_telegram_bridge()

            result = await bridge.process_telegram_message(chat_id, text)

            # Use inline keyboard if available (for callbacks), otherwise reply keyboard
            reply_markup = result.get("inline_keyboard") or result.get("keyboard") or self.MAIN_KEYBOARD
            parse_mode = result.get("parse_mode")

            await update.message.reply_text(
                text=result["text"],
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            
            action = result.get("action")
            if action == "restart":
                logger.info("Restart action triggered")
            elif action == "shutdown":
                logger.info("Shutdown action triggered")
                
        except Exception as e:
            logger.error(f"Text handling failed: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ <b>Error</b>\n\n{str(e)}",
                reply_markup=self.MAIN_KEYBOARD,
                parse_mode="HTML"
            )
    
    async def _send_response(self, chat_id: int, result: Dict, buttons=None):
        """Send response with optional buttons"""
        text = result.get("text", "No response")
        reply_markup = buttons or self.MAIN_KEYBOARD
        
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    # Menu methods
    async def _main_menu(self, chat_id: int):
        """Show main menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🏠 <b>Main Menu</b>",
            reply_markup=self.MAIN_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _new_project(self, chat_id: int):
        """New project menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📦 <b>Create New Project</b>\n\nSend: /build [name] [description]\n\nExample: /build my_api REST API for users",
            reply_markup=self.MAIN_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _skill_menu(self, chat_id: int):
        """Skill categories menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="💡 <b>Select Skill Category:</b>",
            reply_markup=self.SKILL_CATEGORIES,
            parse_mode="HTML"
        )
    
    async def _file_menu(self, chat_id: int):
        """File operations menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📁 <b>File Operations</b>\n\nSelect an operation:",
            reply_markup=self.FILE_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _browser_menu(self, chat_id: int):
        """Browser menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🌐 <b>Browser Control</b>\n\nSelect an operation:",
            reply_markup=self.BROWSER_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _social_menu(self, chat_id: int):
        """Social media menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📱 <b>Social Media</b>\n\nSelect a platform:",
            reply_markup=self.SOCIAL_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _code_skills(self, chat_id: int):
        """Code skills menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="💻 <b>Code Generation Skills</b>",
            reply_markup=self.CODE_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _analysis_skills(self, chat_id: int):
        """Analysis skills menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🔍 <b>Analysis Skills</b>",
            reply_markup=self.ANALYSIS_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _devops_skills(self, chat_id: int):
        """DevOps skills menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🛠️ <b>DevOps Skills</b>",
            reply_markup=self.DEVOPS_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _docs_skills(self, chat_id: int):
        """Docs skills"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📝 <b>Documentation Skills</b>\n\nComing soon!",
            reply_markup=self.SKILL_CATEGORIES,
            parse_mode="HTML"
        )
    
    async def _testing_skills(self, chat_id: int):
        """Testing skills"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🧪 <b>Testing Skills</b>\n\nComing soon!",
            reply_markup=self.SKILL_CATEGORIES,
            parse_mode="HTML"
        )
    
    # NEW 7-Button Menu Methods
    async def _project_menu(self, chat_id: int):
        """Project creation menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🏗️ <b>Create New Project</b>\n\nSelect programming language:",
            reply_markup=self.PROJECT_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _schedule_menu(self, chat_id: int):
        """Schedule menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📅 <b>Task Scheduler</b>\n\nSelect an operation:",
            reply_markup=self.SCHEDULE_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _restart_agent(self, chat_id: int):
        """Restart agent confirmation"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🔄 <b>Restart Agent</b>\n\nThe agent will restart and be back online in a few seconds.",
            reply_markup=self.MAIN_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _shutdown_agent(self, chat_id: int):
        """Shutdown agent confirmation"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="⚡ <b>⚠️ SHUTDOWN AGENT ⚠️</b>\n\nThis will stop the agent completely!\n\nTo restart, run: systemctl start ultimate-agent",
            reply_markup=self.MAIN_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _help_menu(self, chat_id: int):
        """Help menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="❓ <b>Help & Commands</b>\n\nSelect a topic:",
            reply_markup=self.HELP_KEYBOARD,
            parse_mode="HTML"
        )
    
    async def _analysis_menu(self, chat_id: int):
        """Analysis skills menu"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🔍 <b>Analysis Skills</b>",
            reply_markup=self.ANALYSIS_KEYBOARD,
            parse_mode="HTML"
        )
    
    # File operation handlers
    async def _create_file_input(self, chat_id: int):
        """Request file creation"""
        self.user_sessions[chat_id] = {"action": "create_file"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📄 <b>Create File</b>\n\nSend in format:\n<code>filename.txt:content here</code>",
            parse_mode="HTML",
            reply_markup=self.FILE_KEYBOARD
        )
    
    async def _read_file_input(self, chat_id: int):
        """Request file read"""
        self.user_sessions[chat_id] = {"action": "read_file"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📖 <b>Read File</b>\n\nSend the file path:",
            parse_mode="HTML",
            reply_markup=self.FILE_KEYBOARD
        )
    
    async def _edit_file_input(self, chat_id: int):
        """Request file edit"""
        self.user_sessions[chat_id] = {"action": "edit_file"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="✏️ <b>Edit File</b>\n\nSend: <code>path:old_text:new_text</code>",
            parse_mode="HTML",
            reply_markup=self.FILE_KEYBOARD
        )
    
    async def _delete_file_input(self, chat_id: int):
        """Request file delete"""
        self.user_sessions[chat_id] = {"action": "delete_file"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🗑️ <b>Delete File</b>\n\nSend the file path:",
            parse_mode="HTML",
            reply_markup=self.FILE_KEYBOARD
        )
    
    async def _create_folder_input(self, chat_id: int):
        """Request folder create"""
        self.user_sessions[chat_id] = {"action": "create_folder"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📁 <b>Create Folder</b>\n\nSend the folder path:",
            parse_mode="HTML",
            reply_markup=self.FILE_KEYBOARD
        )
    
    async def _list_folder_input(self, chat_id: int):
        """Request folder list"""
        self.user_sessions[chat_id] = {"action": "list_folder"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📂 <b>List Folder</b>\n\nSend the folder path (or 'workspace'):",
            parse_mode="HTML",
            reply_markup=self.FILE_KEYBOARD
        )
    
    # Browser handlers
    async def _open_url_input(self, chat_id: int):
        """Request URL to open"""
        self.user_sessions[chat_id] = {"action": "open_url"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🌐 <b>Open URL</b>\n\nSend the URL to open:",
            parse_mode="HTML",
            reply_markup=self.BROWSER_KEYBOARD
        )
    
    async def _take_screenshot(self, chat_id: int):
        """Take screenshot"""
        browser = get_browser_controller()
        result = await browser.take_screenshot()
        await self.application.bot.send_message(
            chat_id=chat_id,
            text=result.message,
            reply_markup=self.BROWSER_KEYBOARD
        )
    
    async def _check_browsers(self, chat_id: int):
        """Check available browsers"""
        browser = get_browser_controller()
        result = await browser.list_browsers()
        await self.application.bot.send_message(
            chat_id=chat_id,
            text=result.message,
            reply_markup=self.BROWSER_KEYBOARD
        )
    
    # Social handlers
    async def _tweet_input(self, chat_id: int):
        """Request tweet text"""
        self.user_sessions[chat_id] = {"action": "tweet"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🐦 <b>Post Tweet</b>\n\nSend your tweet (max 280 chars):",
            parse_mode="HTML",
            reply_markup=self.SOCIAL_KEYBOARD
        )
    
    async def _linkedin_input(self, chat_id: int):
        """Request LinkedIn post"""
        self.user_sessions[chat_id] = {"action": "linkedin"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📘 <b>Post to LinkedIn</b>\n\nSend your post:",
            parse_mode="HTML",
            reply_markup=self.SOCIAL_KEYBOARD
        )
    
    async def _facebook_input(self, chat_id: int):
        """Request Facebook post"""
        self.user_sessions[chat_id] = {"action": "facebook"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📕 <b>Post to Facebook</b>\n\nSend your post:",
            parse_mode="HTML",
            reply_markup=self.SOCIAL_KEYBOARD
        )
    
    async def _instagram_input(self, chat_id: int):
        """Instagram"""
        self.user_sessions[chat_id] = {"action": "instagram"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📷 <b>Instagram</b>\n\nOpening Instagram web...",
            parse_mode="HTML",
            reply_markup=self.SOCIAL_KEYBOARD
        )
        browser = get_browser_controller()
        await browser.open_url("https://instagram.com")
    
    async def _reddit_input(self, chat_id: int):
        """Request Reddit post"""
        self.user_sessions[chat_id] = {"action": "reddit"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="🤖 <b>Post to Reddit</b>\n\nSend: <code>title:r/subreddit</code>",
            parse_mode="HTML",
            reply_markup=self.SOCIAL_KEYBOARD
        )
    
    async def _medium_input(self, chat_id: int):
        """Medium post"""
        self.user_sessions[chat_id] = {"action": "medium"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📝 <b>Post to Medium</b>\n\nSend: <code>title:content</code>",
            parse_mode="HTML",
            reply_markup=self.SOCIAL_KEYBOARD
        )
    
    async def _announcement_input(self, chat_id: int):
        """Announcement"""
        self.user_sessions[chat_id] = {"action": "announcement"}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text="📢 <b>Post Announcement</b>\n\nSend your announcement (will post to Twitter & LinkedIn):",
            parse_mode="HTML",
            reply_markup=self.SOCIAL_KEYBOARD
        )
    
    # Execute skills
    async def _execute_skill(self, chat_id: int, skill_slug: str, params: Dict):
        """Execute a skill"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text=f"⚡ Executing <b>{skill_slug}</b>...",
            parse_mode="HTML"
        )
        
        result = await get_skill_registry().execute_skill(skill_slug, params)
        
        if result.success:
            output = result.output[:3500]
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=f"✅ <b>Done!</b>\n\n⏱️ {result.duration_ms:.0f}ms\n\n{output}",
                reply_markup=self.SKILL_CATEGORIES,
                parse_mode="HTML"
            )
        else:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Failed: {result.error}",
                reply_markup=self.SKILL_CATEGORIES
            )
    
    async def _request_code(self, chat_id: int, skill: str, prompt: str):
        """Request code for analysis"""
        self.user_sessions[chat_id] = {"action": "analyze_code", "skill": skill}
        await self.application.bot.send_message(
            chat_id=chat_id,
            text=f"📝 {prompt}\n\nSend code in a code block (```language ... ```)",
            parse_mode="HTML",
            reply_markup=self.ANALYSIS_KEYBOARD
        )
    
    async def _process_input(self, user_id: int, text: str):
        """Process user input for pending actions"""
        session = self.user_sessions.get(user_id, {})
        action = session.get("action")
        
        if not action:
            await self.application.bot.send_message(
                chat_id=user_id,
                text="🤔 Use the menu buttons or /help!",
                reply_markup=self.MAIN_KEYBOARD
            )
            return
        
        del self.user_sessions[user_id]
        
        # Process based on action
        if action == "create_file":
            if ":" in text:
                path, content = text.split(":", 1)
                result = await get_file_manager().create_file(path.strip(), content.strip())
            else:
                result = await get_file_manager().create_file(f"{text}.txt", f"Content: {text}")
        
        elif action == "read_file":
            result = await get_file_manager().read_file(text.strip())
        
        elif action == "edit_file":
            if ":" in text:
                parts = text.split(":")
                if len(parts) >= 3:
                    path, old_text, new_text = parts[0], parts[1], ":".join(parts[2:])
                    result = await get_file_manager().edit_file(path.strip(), old_text, new_text)
                else:
                    result = await get_file_manager().edit_file(parts[0], None, parts[1] if len(parts) > 1 else "")
            else:
                result = await get_file_manager().edit_file(text, None, text)
        
        elif action == "delete_file":
            result = await get_file_manager().delete_file(text.strip())
        
        elif action == "create_folder":
            result = await get_file_manager().create_folder(text.strip())
        
        elif action == "list_folder":
            path = text.strip() if text.strip() not in ["workspace", "."] else "."
            result = await get_file_manager().list_directory(path)
        
        elif action == "open_url":
            result = await get_browser_controller().open_url(text.strip())
        
        elif action == "tweet":
            result = await get_browser_controller().post_to_twitter(text[:280])
        
        elif action == "linkedin":
            result = await get_browser_controller().post_to_linkedin(text)
        
        elif action == "facebook":
            result = await get_browser_controller().post_to_facebook(text)
        
        elif action == "reddit":
            if "r/" in text:
                parts = text.split("r/")
                title = parts[0].strip()
                subreddit = parts[1].strip() if len(parts) > 1 else "all"
                result = await get_browser_controller().post_to_reddit(title, subreddit=subreddit)
            else:
                result = await get_browser_controller().post_to_reddit(text)
        
        elif action == "medium":
            if ":" in text:
                title, content = text.split(":", 1)
                result = await get_browser_controller().post_to_medium(title.strip(), content.strip())
            else:
                result = await get_browser_controller().post_to_medium(text.strip())
        
        elif action == "announcement":
            result = await get_browser_controller().post_announcement(text, text, ["twitter", "linkedin"])
        
        elif action == "analyze_code":
            # Extract code from markdown
            code = text
            language = "python"
            if "```" in text:
                parts = text.split("```")
                if len(parts) >= 2:
                    first = parts[0].strip()
                    code_part = parts[1]
                    if "\n" in code_part:
                        language, code = code_part.split("\n", 1)
                    else:
                        code = code_part
            result = await get_skill_registry().execute_skill(
                session.get("skill", "security-audit"),
                {"code": code, "language": language}
            )
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"✅ Analysis complete!\n\n{result.output[:2000] if result.output else result.error}",
                reply_markup=self.ANALYSIS_KEYBOARD,
                parse_mode="HTML" if result.success else None
            )
            return
        
        else:
            result = None
        
        if result:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=result.message,
                reply_markup=self.MAIN_KEYBOARD
            )
    
    async def _my_builds(self, chat_id: int, user_id: int):
        """Show user's builds"""
        db = SessionLocal()
        tg_user = db.query(TelegramUser).filter_by(telegram_id=user_id).first()
        
        if not tg_user:
            db.close()
            await self.application.bot.send_message(chat_id=chat_id, text="❌ Please link your account first!", reply_markup=self.MAIN_KEYBOARD)
            return
        
        builds = db.query(Build).filter_by(user_id=tg_user.user_id).order_by(Build.created_at.desc()).limit(5).all()
        db.close()
        
        if not builds:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text="📊 <b>No builds yet!</b>\n\nUse /build to create one!",
                reply_markup=self.MAIN_KEYBOARD,
                parse_mode="HTML"
            )
            return
        
        text = "📊 <b>Your Builds</b>\n\n"
        for build in builds:
            icon = {"completed": "✅", "running": "⏳", "failed": "❌", "pending": "📝"}.get(build.status.value, "❓")
            text += f"{icon} <b>{build.project_name}</b>\n   📅 {build.created_at.strftime('%Y-%m-%d')}\n\n"
        
        await self.application.bot.send_message(chat_id=chat_id, text=text, reply_markup=self.MAIN_KEYBOARD, parse_mode="HTML")
    
    async def _history(self, chat_id: int, user_id: int):
        """Show history"""
        await self._my_builds(chat_id, user_id)
    
    async def _link_account(self, chat_id: int, user):
        """Link account"""
        await self._ensure_user_linked(user.id, user.username, chat_id)
        await self.application.bot.send_message(chat_id=chat_id, text="✅ <b>Account Linked!</b>", parse_mode="HTML", reply_markup=self.MAIN_KEYBOARD)
    
    async def _ensure_user_linked(self, telegram_id: int, username: Optional[str], chat_id: int):
        """Ensure user is linked"""
        db = SessionLocal()
        tg_user = db.query(TelegramUser).filter_by(telegram_id=telegram_id).first()
        
        if not tg_user:
            user = User(
                username=username or f"telegram_{telegram_id}",
                email=f"telegram_{telegram_id}@agent.local",
                hashed_password="",
                role="user",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.flush()
            
            tg_user = TelegramUser(
                user_id=user.id,
                telegram_id=telegram_id,
                telegram_username=username,
                chat_id=chat_id,
                is_active=True,
            )
            db.add(tg_user)
            db.commit()
            logger.info("User linked", telegram_id=telegram_id)
        
        db.close()
    
    async def start(self):
        """Start bot"""
        if not self.token or not self.application:
            logger.warning("Bot not initialized")
            return
        
        try:
            webhook_url = f"{settings.telegram_webhook_url}/telegram/webhook" if settings.telegram_webhook_url else None
            
            # Components must be started first
            await self.application.start()
            
            if webhook_url:
                await self.application.bot.set_webhook(webhook_url)
                logger.info(f"Webhook set to {webhook_url}")
            else:
                # Local development - use polling
                logger.info("Starting Telegram bot in polling mode...")
                # In v20+, we start the updater explicitly for background polling
                await self.application.updater.start_polling()
            
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Bot start failed: {e}")
            raise
    
    async def stop(self):
        """Stop bot"""
        if self.application:
            try:
                if self.application.updater and self.application.updater.running:
                    await self.application.updater.stop()
                
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.warning(f"Bot stop failed: {e}")


_bot_manager: Optional[TelegramBotManager] = None


def get_telegram_bot() -> TelegramBotManager:
    """Get or create bot"""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = TelegramBotManager()
    return _bot_manager


async def init_telegram_bot():
    """Initialize bot"""
    try:
        bot = get_telegram_bot()
        await bot.initialize()
        logger.info("Telegram bot initialized")
    except Exception as e:
        logger.warning(f"Bot initialization skipped: {e}")


async def start_telegram_bot():
    """Start bot"""
    try:
        bot = get_telegram_bot()
        await bot.start()
    except Exception as e:
        logger.warning(f"Bot start skipped: {e}")


async def stop_telegram_bot():
    """Stop bot"""
    try:
        bot = get_telegram_bot()
        await bot.stop()
    except Exception as e:
        logger.warning(f"Bot stop failed: {e}")


async def notify_admin_on_startup():
    """Send startup notification"""
    try:
        bot = get_telegram_bot()
        if bot.application and settings.admin_telegram_ids:
            ollama = get_ollama_client()
            health = await ollama.health_check()
            mode = health.get("primary", "unknown").upper()
            
            for admin_id in settings.admin_telegram_ids:
                msg = f"""🚀 <b>Ultimate Coding Agent Started</b>

✅ Status: Online
🤖 Mode: {mode}
🌐 API: http://localhost:8000

Commands:
/build [name] [desc] - Create project
/file [operation] - File operations
/post [platform] [text] - Social posting
/skill - Open skills menu
"""
                
                await bot.application.bot.send_message(chat_id=admin_id, text=msg, reply_markup=bot.MAIN_KEYBOARD, parse_mode="HTML")
                logger.info(f"Startup notification sent to admin {admin_id}")
    except Exception as e:
        logger.warning(f"Failed to send admin notification: {e}")
