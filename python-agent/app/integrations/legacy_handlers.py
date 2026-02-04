"""
Legacy handlers for backward compatibility
Consolidates remaining file, browser, and other operations from Node.js
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from app.integrations.file_manager import get_file_manager
from app.integrations.browser_controller import get_browser_controller
from app.models.database import TelegramUser, Build
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class LegacyHandler:
    """Handles legacy operations for backward compatibility"""
    
    # File operations keyboard
    FILE_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("📄 Create File"), KeyboardButton("📖 Read File")],
            [KeyboardButton("✏️ Edit File"), KeyboardButton("🗑️ Delete File")],
            [KeyboardButton("📁 New Folder"), KeyboardButton("📂 List Folder")],
            [KeyboardButton("⬅️ Back")],
        ],
        resize_keyboard=True,
    )
    
    # Browser operations keyboard
    BROWSER_KEYBOARD = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🌐 Open URL"), KeyboardButton("📸 Screenshot")],
            [KeyboardButton("🌐 Check Browsers"), KeyboardButton("⬅️ Back")],
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
    
    def __init__(self):
        self.file_manager = get_file_manager()
        self.browser = get_browser_controller()
    
    async def handle_file_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /file command"""
        try:
            user = update.effective_user
            args = context.args
            
            if not args:
                await update.message.reply_text(
                    "📁 <b>File Operations</b>\n\n"
                    "Usage: /file [operation] [path] [content?]\n\n"
                    "Operations:\n"
                    "• create [path] [content]\n"
                    "• read [path]\n"
                    "• edit [path] [content]\n"
                    "• delete [path]\n"
                    "• mkdir [path]\n"
                    "• ls [path]",
                    reply_markup=self.FILE_KEYBOARD,
                    parse_mode="HTML"
                )
                return
            
            operation = args[0].lower()
            
            if operation == "create" and len(args) >= 2:
                path = args[1]
                content = " ".join(args[2:]) if len(args) > 2 else ""
                
                result = await self.file_manager.create_file(path, content)
                await update.message.reply_text(
                    f"✅ File created: {path}",
                    reply_markup=self.FILE_KEYBOARD
                )
            
            elif operation == "read" and len(args) >= 2:
                path = args[1]
                content = await self.file_manager.read_file(path)
                
                if content:
                    await update.message.reply_text(
                        f"📖 <b>{path}</b>\n\n```\n{content[:500]}...\n```" if len(content) > 500 else f"📖 <b>{path}</b>\n\n```\n{content}\n```",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(f"❌ Could not read file: {path}")
            
            elif operation == "delete" and len(args) >= 2:
                path = args[1]
                result = await self.file_manager.delete_file(path)
                
                if result:
                    await update.message.reply_text(f"✅ File deleted: {path}")
                else:
                    await update.message.reply_text(f"❌ Could not delete file: {path}")
            
            elif operation == "mkdir" and len(args) >= 2:
                path = args[1]
                result = await self.file_manager.create_directory(path)
                
                if result:
                    await update.message.reply_text(f"✅ Directory created: {path}")
                else:
                    await update.message.reply_text(f"❌ Could not create directory: {path}")
            
            elif operation == "ls" and len(args) >= 2:
                path = args[1]
                files = await self.file_manager.list_directory(path)
                
                if files:
                    file_list = "\n".join([f"📄 {f}" for f in files])
                    await update.message.reply_text(f"📁 <b>{path}</b>\n\n{file_list}", parse_mode="HTML")
                else:
                    await update.message.reply_text(f"❌ Could not list directory: {path}")
            
            else:
                await update.message.reply_text(
                    "❌ Invalid operation. See /file for usage.",
                    reply_markup=self.FILE_KEYBOARD
                )
        
        except Exception as e:
            logger.error(f"File command error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_browser_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle browser operations"""
        try:
            user = update.effective_user
            args = context.args
            
            if not args:
                await update.message.reply_text(
                    "🌐 <b>Browser Control</b>\n\n"
                    "Usage: /open [url]\n\n"
                    "Example: /open https://google.com",
                    reply_markup=self.BROWSER_KEYBOARD,
                    parse_mode="HTML"
                )
                return
            
            url = " ".join(args)
            
            # Check if URL starts with http
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            await update.message.reply_text(f"🌐 Opening {url}...", parse_mode="HTML")
            
            # Open browser
            result = await self.browser.open_url(url)
            
            if result:
                await update.message.reply_text(
                    f"✅ Opened: {url}",
                    reply_markup=self.BROWSER_KEYBOARD
                )
            else:
                await update.message.reply_text(
                    f"❌ Could not open URL: {url}",
                    reply_markup=self.BROWSER_KEYBOARD
                )
        
        except Exception as e:
            logger.error(f"Browser command error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedule command"""
        try:
            await update.message.reply_text(
                "📅 <b>Task Scheduling</b>\n\n"
                "Schedule tasks for automated execution.\n\n"
                "Usage: /schedule [task] [time]\n\n"
                "Example: /schedule 'build my_app' '09:00 daily'",
                reply_markup=self.SCHEDULE_KEYBOARD,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Schedule command error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /link command - link Telegram to user account"""
        try:
            user = update.effective_user
            args = context.args
            
            if not args:
                await update.message.reply_text(
                    "🔗 <b>Link Account</b>\n\n"
                    "Link your Telegram account to the system.\n\n"
                    "Usage: /link [username]\n\n"
                    "Example: /link john_doe",
                    parse_mode="HTML"
                )
                return
            
            username = args[0]
            
            db = SessionLocal()
            try:
                # Find or create TelegramUser
                tg_user = db.query(TelegramUser).filter_by(
                    telegram_id=user.id
                ).first()
                
                if not tg_user:
                    tg_user = TelegramUser(
                        telegram_id=user.id,
                        username=user.username or username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                    )
                    db.add(tg_user)
                
                db.commit()
                
                await update.message.reply_text(
                    f"✅ Account linked!\n\n"
                    f"Telegram: @{user.username or username}\n"
                    f"User ID: {user.id}",
                    parse_mode="HTML"
                )
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Link command error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")


# Singleton instance
_legacy_handler: Optional[LegacyHandler] = None


def get_legacy_handler() -> LegacyHandler:
    """Get or create legacy handler instance"""
    global _legacy_handler
    if _legacy_handler is None:
        _legacy_handler = LegacyHandler()
    return _legacy_handler
