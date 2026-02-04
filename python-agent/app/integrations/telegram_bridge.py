"""
Telegram-Agent Bridge - Properly connects Telegram bot to Agent Handler
Handles message formatting, keyboard building, and response processing
"""

import logging
from typing import Dict, Any, Optional
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from app.integrations.agent_handler import get_agent_handler
import structlog

logger = structlog.get_logger(__name__)


class TelegramAgentBridge:
    """Bridge between Telegram Bot and Agent Handler"""
    
    def __init__(self):
        self.agent_handler = get_agent_handler()
    
    async def process_telegram_message(
        self, 
        user_id: int, 
        message: str
    ) -> Dict[str, Any]:
        """
        Process message from Telegram and format for sending
        
        Returns properly formatted response with:
        - text: Message text (HTML formatted)
        - keyboard: Optional ReplyKeyboardMarkup
        - parse_mode: HTML or None
        """
        try:
            agent_response = await self.agent_handler.process_message(user_id, message)
            
            text = agent_response.get("text", "No response")
            
            if not any(tag in text for tag in ["<b>", "<i>", "<code>", "<pre>"]):
                text = self._format_plain_text(text)
            
            parse_mode = ParseMode.HTML if ("<b>" in text or "<code>" in text) else None
            
            keyboard = None
            if "buttons" in agent_response:
                keyboard = self._build_keyboard(agent_response["buttons"])
            
            return {
                "text": text,
                "keyboard": keyboard,
                "parse_mode": parse_mode,
                "workflow_state": agent_response.get("workflow_state"),
                "action": agent_response.get("action"),
                "project_data": agent_response.get("project_data"),
                "schedule_data": agent_response.get("schedule_data")
            }
            
        except Exception as e:
            logger.error(f"Bridge processing failed: {e}")
            return {
                "text": f"❌ <b>Error processing request</b>\n\n{str(e)}",
                "keyboard": None,
                "parse_mode": ParseMode.HTML
            }
    
    def _format_plain_text(self, text: str) -> str:
        lines = text.split("\n")
        if lines and len(lines[0]) < 80:
            lines[0] = f"<b>{lines[0]}</b>"
        return "\n".join(lines)
    
    def _build_keyboard(self, buttons: list) -> Optional[ReplyKeyboardMarkup]:
        try:
            keyboard = []
            for row in buttons:
                button_row = []
                for btn in row:
                    if isinstance(btn, dict):
                        button_row.append(KeyboardButton(btn.get("text", "Button")))
                    else:
                        button_row.append(KeyboardButton(str(btn).replace("callback=", "")))
                keyboard.append(button_row)
            
            if keyboard:
                return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        except Exception as e:
            logger.error(f"Keyboard building failed: {e}")
        
        return None


_bridge = None

def get_telegram_bridge():
    global _bridge
    if _bridge is None:
        _bridge = TelegramAgentBridge()
    return _bridge
