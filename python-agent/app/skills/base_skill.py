"""
Base Skill Class for Ultimate Coding Agent
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SkillResult:
    """Result of skill execution"""
    success: bool
    output: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class BaseSkill:
    """Base class for all skills"""
    
    name: str = "base_skill"
    description: str = "Base skill"
    category: str = "general"
    
    def __init__(self):
        self.started_at = None
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """
        Execute the skill
        
        Args:
            params: Skill parameters
            
        Returns:
            SkillResult with success status and output
        """
        import time
        self.started_at = time.time()
        
        try:
            logger.info(
                "Skill execution started",
                skill=self.name,
                params_keys=list(params.keys()) if params else []
            )
            
            result = await self._execute(params)
            
            duration_ms = (time.time() - self.started_at) * 1000
            
            logger.info(
                "Skill execution completed",
                skill=self.name,
                success=result.success,
                duration_ms=duration_ms
            )
            
            return SkillResult(
                success=result.success,
                output=result.output,
                data=result.data,
                error=result.error,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.time() - self.started_at) * 1000
            logger.error(
                "Skill execution failed",
                skill=self.name,
                error=str(e),
                duration_ms=duration_ms
            )
            
            return SkillResult(
                success=False,
                output="",
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def _execute(self, params: Dict[str, Any]) -> SkillResult:
        """Internal execution - override in subclasses"""
        raise NotImplementedError(f"Skill '{self.name}' must implement _execute()")
    
    def validate_params(self, params: Dict[str, Any], required: list) -> tuple:
        """
        Validate required parameters exist
        
        Returns:
            (is_valid, missing_params)
        """
        missing = [p for p in required if p not in params or params[p] is None]
        return (len(missing) == 0, missing)
