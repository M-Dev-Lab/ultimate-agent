"""
System Controller Skill for Ultimate Coding Agent
Controls agent and system operations
"""

import os
import signal
import subprocess
from typing import Dict, Any
from app.skills.base_skill import BaseSkill, SkillResult
import structlog

logger = structlog.get_logger(__name__)


class SystemControllerSkill(BaseSkill):
    """Control system and agent operations"""
    
    name = "system_controller"
    description = "Control agent and system operations"
    category = "system"
    
    async def _execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute system control action"""
        action = params.get("action", "status")
        
        if action == "restart":
            return await self._restart_agent()
        elif action == "shutdown":
            return self._shutdown_system()
        elif action == "status":
            return self._get_status()
        elif action == "logs":
            return self._get_logs(params)
        elif action == "health":
            return self._health_check()
        else:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown action: {action}"
            )
    
    async def _restart_agent(self) -> SkillResult:
        """Restart the agent service"""
        try:
            logger.info("Agent restart requested")
            
            return SkillResult(
                success=True,
                output="🔄 <b>Restarting Agent...</b>\n\n"
                       "The agent will be back online in a few seconds.\n"
                       "You can send /start to reconnect.",
                data={"action": "restart"}
            )
            
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _shutdown_system(self) -> SkillResult:
        """Shutdown the agent (WARNING: This stops the service)"""
        try:
            logger.warning("Agent shutdown requested")
            
            return SkillResult(
                success=True,
                output="⚡ <b>⚠️ SHUTDOWN INITIATED ⚠️</b>\n\n"
                       "The agent is shutting down.\n\n"
                       "To restart:\n"
                       "• Run: systemctl start ultimate-agent\n"
                       "• Or: python -m app.main\n\n"
                       "Use /start when ready to reconnect.",
                data={"action": "shutdown"}
            )
            
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _get_status(self) -> SkillResult:
        """Get system status"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            status = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "running": True,
            }
            
            output = f"""📊 <b>System Status</b>

🖥️ CPU: {cpu_percent}%
💾 Memory: {memory.percent}%
💿 Disk: {disk.percent}%

✅ Agent: Running"""

            return SkillResult(
                success=True,
                output=output,
                data=status
            )
            
        except ImportError:
            return SkillResult(
                success=True,
                output="📊 <b>System Status</b>\n\n✅ Agent: Running\n\n(Detailed stats unavailable)",
                data={"running": True}
            )
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _get_logs(self, params: Dict[str, Any]) -> SkillResult:
        """Get recent logs"""
        log_lines = int(params.get("lines", 50))
        log_file = params.get("file", "./logs/agent.log")
        
        try:
            if Path(log_file).exists():
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-log_lines:]
                    logs = ''.join(lines)
                    
                return SkillResult(
                    success=True,
                    output=f"📋 <b>Recent Logs</b> ({log_lines} lines)\n\n```{logs}```",
                    data={"lines": log_lines}
                )
            else:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Log file not found: {log_file}"
                )
                
        except Exception as e:
            logger.error(f"Log retrieval failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _health_check(self) -> SkillResult:
        """Perform health check"""
        checks = []
        
        try:
            from app.integrations.ollama import get_ollama_client
            ollama = get_ollama_client()
            
            health = asyncio.run(ollama.health_check())
            checks.append({
                "name": "Ollama AI",
                "status": "healthy" if health.get("local") or health.get("cloud") else "unhealthy",
                "details": health
            })
        except Exception as e:
            checks.append({
                "name": "Ollama AI",
                "status": "error",
                "error": str(e)
            })
        
        all_healthy = all(c["status"] == "healthy" for c in checks)
        
        output = "🔍 <b>Health Check</b>\n\n"
        for check in checks:
            icon = "✅" if check["status"] == "healthy" else "❌"
            output += f"{icon} {check['name']}: {check['status']}\n"
        
        overall = "✅ All systems healthy" if all_healthy else "⚠️ Some systems degraded"
        output += f"\n<b>{overall}</b>"
        
        return SkillResult(
            success=all_healthy,
            output=output,
            data={"checks": checks, "overall": all_healthy}
        )
    
    def _get_uptime(self) -> str:
        """Get system uptime"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
                
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
                
        except Exception:
            return "Unknown"
