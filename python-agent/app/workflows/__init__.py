"""
Workflows Package

Multi-step conversation workflows for Telegram bot
Based on ConversationHandler pattern from python-telegram-bot
"""

from app.workflows.workflow_manager import WorkflowManager
from app.workflows.base_workflow import BaseWorkflow, WorkflowState

__all__ = [
    "WorkflowManager",
    "BaseWorkflow",
    "WorkflowState",
]
