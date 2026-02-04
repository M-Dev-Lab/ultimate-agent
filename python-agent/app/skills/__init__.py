"""
Skills package for Ultimate Coding Agent
"""

from app.skills.base_skill import BaseSkill, SkillResult
from app.skills.project_manager import ProjectManagerSkill
from app.skills.social_poster import SocialPosterSkill
from app.skills.task_scheduler import TaskSchedulerSkill
from app.skills.system_controller import SystemControllerSkill

__all__ = [
    "BaseSkill",
    "SkillResult",
    "ProjectManagerSkill",
    "SocialPosterSkill",
    "TaskSchedulerSkill",
    "SystemControllerSkill",
]
