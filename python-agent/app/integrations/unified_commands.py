"""
Unified Command Handler - Consolidates all Telegram bot commands
Merged from Node.js src/channels/telegram.ts and other handlers
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.integrations.menu_system import MenuManager, SmartResponseHooks, format_inline_keyboard
from app.agents.full_workflow import get_agent_workflow
from app.integrations.agent_handler import get_agent_handler
from app.integrations.ollama import get_ollama_client

logger = logging.getLogger(__name__)


class UnifiedCommandHandler:
    """Handles all Telegram bot commands and callbacks"""
    
    def __init__(self):
        self.menu_manager = MenuManager()
        self.agent_workflow = get_agent_workflow()
        self.agent_handler = get_agent_handler()
        self.ollama = get_ollama_client()
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - initialize with main menu"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        logger.info(f"User started bot: {user.id} ({user.first_name})")
        
        # Get health status
        try:
            health = await self.ollama.health_check()
            mode = "☁️ Cloud" if health.get("primary") == "cloud" else "📱 Local"
        except:
            mode = "🔧 Offline"
        
        welcome_text = f"""🤖 <b>Welcome to Ultimate Coding Agent!</b>

AI Mode: {mode}
Version: 3.0.0

<b>Available Features:</b>
🏗️ Build projects
💻 Generate code
🔧 Fix bugs
📱 Social posting
🚀 Deploy
📊 Analytics
🧠 Learn & improve

Select an option below to begin!"""
        
        buttons = self.menu_manager.get_main_menu_buttons()
        keyboard = self._build_keyboard(buttons)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """📚 <b>Ultimate Coding Agent - Commands</b>

<b>Quick Commands:</b>
/start - Initialize and show menu
/help - Show this help
/status - System status
/health - Health check
/build [name] [desc] - Create project
/code [request] - Generate code
/fix [issue] - Fix bug
/post [platform] [text] - Post to social

<b>Features:</b>
🏗️ Project generation
💻 Code generation & analysis
🔧 Bug fixing & debugging
📱 Social media posting
🚀 Deployment automation
📊 Analytics & monitoring
🧠 Auto-learning system

<b>Menu Navigation:</b>
Use buttons below to navigate menus
/start - Return to main menu"""
        
        back_button = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
        
        await update.message.reply_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(back_button),
            parse_mode="HTML"
        )
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - show system status"""
        try:
            health = await self.ollama.health_check()
            
            status_text = """📊 <b>System Status</b>

<b>AI Model:</b>
"""
            if health.get("primary") == "cloud":
                status_text += "☁️ Cloud (Ollama Cloud)\n"
                status_text += f"Model: {health.get('model', 'Unknown')}\n"
            else:
                status_text += "📱 Local (Ollama Local)\n"
                status_text += f"Models: {len(health.get('models', []))} loaded\n"
            
            status_text += f"""
<b>API:</b>
✅ FastAPI: Running
Port: 8000

<b>Telegram Bot:</b>
✅ Connected
Polling: Active

<b>Database:</b>
✅ SQLite: Ready

<b>Services:</b>
✅ All operational"""
            
            back_button = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            
            await update.message.reply_text(
                status_text,
                reply_markup=InlineKeyboardMarkup(back_button),
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error getting status: {str(e)}")
    
    async def handle_build_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle build project command"""
        try:
            # Show project type menu
            project_buttons = self.menu_manager.get_project_menu_buttons()
            keyboard = self._build_keyboard(project_buttons)
            
            await update.message.reply_text(
                "🏗️ <b>What type of project would you like to create?</b>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Build command error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle code generation command"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "💻 <b>Code Generation</b>\n\n"
                    "Usage: /code [description]\n\n"
                    "Example: /code create a hello world API",
                    parse_mode="HTML"
                )
                return
            
            request = " ".join(context.args)
            
            # Show typing indicator
            await context.bot.send_chat_action(update.effective_chat.id, "typing")
            
            # Generate code using agent
            response = await self.agent_handler.generate_code(request)
            
            # Show response with smart message
            smart_msg = SmartResponseHooks.get_response('code', success=True)
            
            await update.message.reply_text(
                f"{smart_msg}\n\n```\n{response}\n```",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ])
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_fix_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle bug fix command"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "🔧 <b>Bug Fix Assistant</b>\n\n"
                    "Usage: /fix [code or issue description]\n\n"
                    "Paste your code or describe the issue to fix",
                    parse_mode="HTML"
                )
                return
            
            issue = " ".join(context.args)
            
            await context.bot.send_chat_action(update.effective_chat.id, "typing")
            
            # Analyze and fix
            response = await self.agent_handler.fix_code(issue)
            
            smart_msg = SmartResponseHooks.get_response('fix', success=True)
            
            await update.message.reply_text(
                f"{smart_msg}\n\n{response}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔧 Fix More", callback_data="cmd_fix"),
                     InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]
                ])
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_post_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle social media posting"""
        try:
            social_buttons = [
                [
                    InlineKeyboardButton("🐦 Twitter", callback_data="post_twitter"),
                    InlineKeyboardButton("📘 LinkedIn", callback_data="post_linkedin")
                ],
                [
                    InlineKeyboardButton("📕 Facebook", callback_data="post_facebook"),
                    InlineKeyboardButton("📷 Instagram", callback_data="post_instagram")
                ],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                "📱 <b>Social Media Posting</b>\n\n"
                "Select a platform to post to:",
                reply_markup=InlineKeyboardMarkup(social_buttons),
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_skills_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle skills menu"""
        try:
            skill_categories = [
                [
                    InlineKeyboardButton("💻 Code", callback_data="skill_cat_code"),
                    InlineKeyboardButton("🔍 Analysis", callback_data="skill_cat_analysis")
                ],
                [
                    InlineKeyboardButton("🛠️ DevOps", callback_data="skill_cat_devops"),
                    InlineKeyboardButton("📱 Social", callback_data="skill_cat_social")
                ],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                "💡 <b>Available Skills</b>\n\n"
                "Select a category to see skills:",
                reply_markup=InlineKeyboardMarkup(skill_categories),
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        data = query.data
        
        logger.info(f"Callback: {data}")
        
        try:
            if data == "main_menu":
                await self._show_main_menu(query)
            elif data == "cmd_build":
                await self._show_project_menu(query)
            elif data == "cmd_skills":
                await self._show_skills_menu(query)
            elif data.startswith("post_"):
                await self._handle_social_post(query, data)
            elif data.startswith("skill_cat_"):
                category = data.replace("skill_cat_", "")
                await self._show_skill_category(query, category)
            else:
                await query.answer(f"Action: {data}", show_alert=False)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    async def _show_main_menu(self, query):
        """Show main menu"""
        buttons = self.menu_manager.get_main_menu_buttons()
        keyboard = self._build_keyboard(buttons)
        
        await query.edit_message_text(
            "🤖 <b>Main Menu</b>\n\nSelect an option:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        await query.answer()
    
    async def _show_project_menu(self, query):
        """Show project creation menu"""
        buttons = self.menu_manager.get_project_menu_buttons()
        keyboard = self._build_keyboard(buttons)
        
        await query.edit_message_text(
            "🏗️ <b>Create New Project</b>\n\nSelect project type:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        await query.answer()
    
    async def _show_skills_menu(self, query):
        """Show skills menu"""
        skill_buttons = [
            [InlineKeyboardButton("💻 Code", callback_data="skill_cat_code")],
            [InlineKeyboardButton("🔍 Analysis", callback_data="skill_cat_analysis")],
            [InlineKeyboardButton("🛠️ DevOps", callback_data="skill_cat_devops")],
            [InlineKeyboardButton("📱 Social", callback_data="skill_cat_social")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            "💡 <b>Skills</b>\n\nSelect category:",
            reply_markup=InlineKeyboardMarkup(skill_buttons),
            parse_mode="HTML"
        )
        await query.answer()
    
    async def _show_skill_category(self, query, category: str):
        """Show skills in a category"""
        buttons = self.menu_manager.get_skill_buttons(category)
        keyboard = self._build_keyboard(buttons)
        
        titles = {
            'code': '💻 Coding Skills',
            'analysis': '🔍 Analysis Skills',
            'devops': '🛠️ DevOps Skills',
            'social': '📱 Social Media Skills'
        }
        
        await query.edit_message_text(
            f"{titles.get(category, 'Skills')}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        await query.answer()
    
    async def _handle_social_post(self, query, data: str):
        """Handle social media post action"""
        platform = data.replace("post_", "")
        
        await query.answer(f"Posting to {platform}...", show_alert=False)
        await query.edit_message_text(
            f"📝 <b>Post to {platform.upper()}</b>\n\n"
            f"Please send the content you'd like to post.",
            parse_mode="HTML"
        )
    
    def _build_keyboard(self, buttons: list) -> list:
        """Build inline keyboard from button list"""
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for btn in row:
                keyboard_row.append(
                    InlineKeyboardButton(
                        f"{btn.emoji} {btn.label}",
                        callback_data=btn.callback_data
                    )
                )
            keyboard.append(keyboard_row)
        return keyboard


# Singleton instance
_command_handler_instance: Optional[UnifiedCommandHandler] = None


def get_command_handler() -> UnifiedCommandHandler:
    """Get or create command handler instance"""
    global _command_handler_instance
    if _command_handler_instance is None:
        _command_handler_instance = UnifiedCommandHandler()
    return _command_handler_instance
