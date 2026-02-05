"""
Telegram-Agent Bridge - Properly connects Telegram bot to Agent Handler
Handles message formatting, keyboard building, and response processing
For SINGLE ADMIN USER (not multi-user) - simplified architecture
"""

import logging
from typing import Dict, Any, Optional, List
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from app.integrations.agent_handler import get_agent_handler
from app.core.workflow_logger import WorkflowLogger
import structlog
import traceback

logger = structlog.get_logger(__name__)


class TelegramAgentBridge:
    """
    Bridge between Telegram Bot and Agent Handler
    Optimized for single-user, local admin scenarios
    """
    
    def __init__(self):
        self.agent_handler = get_agent_handler()
        self.logger = logger.bind(component="telegram_bridge")
    
    async def process_telegram_message(
        self, 
        user_id: int, 
        message: str,
        is_admin: bool = True
    ) -> Dict[str, Any]:
        """
        Process message from Telegram and format for sending
        
        Args:
            user_id: Telegram user ID (for context)
            message: User message text
            is_admin: Whether user is admin (always True in single-user setup)
        
        Returns:
            Properly formatted response with:
            - text: Message text (HTML formatted)
            - keyboard: Optional ReplyKeyboardMarkup
            - parse_mode: HTML or None
            - action: Optional action to take
        """
        try:
            WorkflowLogger.log_step("Bridge", "Telegram Inbound", f"From: {user_id}", {"text": message})
            self.logger.info(
            
            # Call agent handler to process message
            agent_response = await self.agent_handler.process_message(
                user_id=user_id,
                message=message,
                context_type="message"
            )
            
            # Validate response
            if not agent_response or not isinstance(agent_response, dict):
                self.logger.warning("handler_returned_invalid_response", response=agent_response)
                return {
                    "text": "❌ <b>Invalid response from agent</b>",
                    "keyboard": None,
                    "parse_mode": ParseMode.HTML,
                    "action": None
                }
            
            # Extract and format text
            text = agent_response.get("text", "No response")
            if not text:
                text = "No response from agent"
            
            # Ensure HTML formatting
            if not self._has_html_tags(text):
                text = self._format_plain_text(text)
            
            # Determine parse mode
            parse_mode = ParseMode.HTML if self._has_html_tags(text) else None
            
            # Build keyboard from buttons if present
            keyboard = None
            if "buttons" in agent_response and agent_response["buttons"]:
                keyboard = self._build_keyboard(agent_response["buttons"])
            
            result = {
                "text": text,
                "keyboard": keyboard,
                "parse_mode": parse_mode,
                "workflow_state": agent_response.get("workflow_state"),
                "action": agent_response.get("action"),
                "project_data": agent_response.get("project_data"),
                "schedule_data": agent_response.get("schedule_data")
            }
            
            WorkflowLogger.log_success(f"Bridge outbound message via HTML. Text len: {len(text)}")
            self.logger.info("bridge_processed_success", text_len=len(text))
            return result
            
        except Exception as e:
            self.logger.error(
                "bridge_processing_failed",
                error=str(e),
                traceback=traceback.format_exc()
            )
            return {
                "text": f"❌ <b>Error processing request</b>\n\n<code>{str(e)[:100]}</code>",
                "keyboard": None,
                "parse_mode": ParseMode.HTML,
                "action": None
            }
    
    def _has_html_tags(self, text: str) -> bool:
        """Check if text contains HTML tags"""
        html_tags = ["<b>", "<i>", "<code>", "<pre>", "<u>", "<s>"]
        return any(tag in text for tag in html_tags)
    
    def _format_plain_text(self, text: str) -> str:
        """Add basic HTML formatting to plain text"""
        lines = text.split("\n")
        
        # Bold first line if it's short (likely a header)
        if lines and len(lines[0]) < 80:
            lines[0] = f"<b>{lines[0]}</b>"
        
        # Format code blocks with triple backticks
        formatted = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    formatted.append("<code>")
                else:
                    formatted.append("</code>")
            else:
                formatted.append(line)
        
        return "\n".join(formatted)
    
    def _build_keyboard(self, buttons: List[List[Dict]]) -> Optional[ReplyKeyboardMarkup]:
        """
        Build Telegram keyboard from button structure
        
        Expected format:
        [
            [{"text": "Button 1", "callback": "action1"}],
            [{"text": "Button 2"}, {"text": "Button 3"}]
        ]
        """
        try:
            if not buttons or not isinstance(buttons, list):
                return None
            
            keyboard = []
            for row in buttons:
                if not row or not isinstance(row, list):
                    continue
                
                button_row = []
                for btn in row:
                    if isinstance(btn, dict):
                        text = btn.get("text", "Button")
                    else:
                        # Handle string buttons
                        text = str(btn).replace("callback=", "").strip()
                    
                    if text:
                        button_row.append(KeyboardButton(text))
                
                if button_row:
                    keyboard.append(button_row)
            
            if keyboard:
                return ReplyKeyboardMarkup(
                    keyboard,
                    resize_keyboard=True,
                    one_time_keyboard=False
                )
            return None
            
        except Exception as e:
            self.logger.error("keyboard_building_failed", error=str(e))
            return None


# Global singleton instance
_bridge_instance = None


def get_telegram_bridge():
    """Get or create bridge instance (singleton pattern)"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = TelegramAgentBridge()
    return _bridge_instance
