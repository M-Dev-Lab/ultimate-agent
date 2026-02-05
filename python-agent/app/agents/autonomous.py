"""
Autonomous Agent Worker - Operates independently using Ollama Qwen3 Coder
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json

from app.core.config import settings
from app.core.workflow_logger import WorkflowLogger
from app.integrations.ollama import get_ollama_client

logger = logging.getLogger(__name__)

class AutonomousWorker:
    """
    Autonomous agent that works independently
    Monitors tasks, executes them, and reports back
    Uses Ollama Qwen3 Coder as the main AI brain
    """

    def __init__(self):
        self.ollama = get_ollama_client()
        self.is_running = False
        self.tasks_file = Path(settings.memory_dir) / "TASKS.md"
        self.schedules_file = Path(settings.config_dir) / "schedules.json"
        self.current_task = None

        WorkflowLogger.log_system("🤖 Autonomous Worker initialized with Ollama Qwen3 Coder")

    async def start(self):
        """Start autonomous operation"""
        self.is_running = True
        WorkflowLogger.log_success("▶️  Autonomous mode ACTIVE")

        while self.is_running:
            try:
                await self._check_and_execute_tasks()
                await asyncio.sleep(settings.check_interval)
            except Exception as e:
                WorkflowLogger.log_error(f"Autonomous worker error", e)
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _check_and_execute_tasks(self):
        """Check for tasks and execute them"""
        WorkflowLogger.log_step("autonomous", "check_tasks", "Scanning for pending tasks")

        # 1. Check for scheduled tasks
        scheduled = await self._get_scheduled_tasks()

        # 2. Check Telegram messages (if integrated)
        telegram_tasks = await self._check_telegram()

        # 3. Proactive checks (system health, updates, etc.)
        proactive_tasks = await self._proactive_checks()

        all_tasks = scheduled + telegram_tasks + proactive_tasks

        if all_tasks:
            WorkflowLogger.log_success(f"Found {len(all_tasks)} tasks to execute")
            for task in all_tasks[:settings.autonomous_max_tasks]:
                await self._execute_task(task)
        else:
            logger.debug("No tasks found, standing by...")

    async def _get_scheduled_tasks(self) -> List[Dict]:
        """Get tasks from schedule"""
        if not self.schedules_file.exists():
            return []

        try:
            with open(self.schedules_file) as f:
                schedules = json.load(f)

            now = datetime.now()
            due_tasks = []

            for schedule in schedules:
                # Check if task is due
                if self._is_task_due(schedule, now):
                    due_tasks.append({
                        'type': schedule['type'],
                        'description': schedule['description'],
                        'parameters': schedule.get('parameters', {}),
                        'source': 'scheduled'
                    })

            return due_tasks
        except Exception as e:
            logger.error(f"Error loading scheduled tasks: {e}")
            return []

    async def _check_telegram(self) -> List[Dict]:
        """Check for new Telegram messages/commands"""
        # This would integrate with your Telegram bot
        # to check for pending commands
        # For now, return empty list
        return []

    async def _proactive_checks(self) -> List[Dict]:
        """Perform proactive system checks"""
        tasks = []

        try:
            import psutil

            # Check system health
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Alert if resources are running low
            if memory.percent > 90:
                tasks.append({
                    'type': 'system_alert',
                    'description': f"High memory usage: {memory.percent}%",
                    'parameters': {'memory_percent': memory.percent},
                    'source': 'proactive'
                })

            if disk.percent > 90:
                tasks.append({
                    'type': 'system_alert',
                    'description': f"Low disk space: {disk.percent}% used",
                    'parameters': {'disk_percent': disk.percent},
                    'source': 'proactive'
                })

        except Exception as e:
            logger.error(f"Proactive check error: {e}")

        return tasks

    async def _execute_task(self, task: Dict):
        """Execute a single task using Ollama Qwen3 Coder"""
        WorkflowLogger.log_step(
            "autonomous_execution",
            task['type'],
            f"Source: {task.get('source', 'unknown')}"
        )

        self.current_task = task

        try:
            # Log task start
            await self._log_task_start(task)

            # Use Ollama Qwen3 to analyze and execute the task
            result = await self._execute_with_ollama(task)

            # Log result
            await self._log_task_complete(task, result)

            # Send notification if configured
            await self._notify_completion(task, result)

            WorkflowLogger.log_success(f"Task completed: {task['type']}")

        except Exception as e:
            WorkflowLogger.log_error(f"Task execution failed: {task['type']}", e)
            await self._log_task_error(task, str(e))

        finally:
            self.current_task = None

    async def _execute_with_ollama(self, task: Dict) -> Dict:
        """
        Execute task using Ollama Qwen3 Coder as the main AI
        """
        prompt = self._build_task_prompt(task)

        WorkflowLogger.log_ai_action(
            "task_execution",
            prompt,
            token_count=len(prompt.split())
        )

        try:
            # Use Ollama to generate response
            response = await self.ollama.generate(
                model=settings.ollama_model,
                prompt=prompt,
                stream=False
            )

            # Parse and execute the response
            result = self._parse_ollama_response(response, task)

            return result

        except Exception as e:
            logger.error(f"Ollama execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'task': task
            }

    def _build_task_prompt(self, task: Dict) -> str:
        """Build prompt for Ollama"""
        return f"""You are an autonomous AI coding assistant with senior developer capabilities.
You are operating on a local Linux machine helping the admin user.

## Task to Execute:
Type: {task['type']}
Description: {task['description']}
Parameters: {json.dumps(task.get('parameters', {}), indent=2)}
Source: {task.get('source', 'unknown')}

## Your Capabilities:
1. Code Generation - Create complete projects, fix bugs
2. System Operations - Execute safe commands
3. File Operations - Create/modify files in outputs directory
4. Analysis - Analyze code, data, systems

## Instructions:
Analyze this task and provide a JSON response with:
{{
  "action": "code_generation | system_command | file_operation | analysis",
  "steps": ["step 1", "step 2", ...],
  "commands": ["command 1", "command 2", ...],  # if applicable
  "code": "code to generate",  # if applicable
  "analysis": "your analysis",
  "success": true/false
}}

Be specific and actionable. Focus on completing the task efficiently.
"""

    def _parse_ollama_response(self, response: Dict, task: Dict) -> Dict:
        """Parse Ollama's response and extract action"""
        try:
            # Ollama returns {'response': '...', 'model': '...', ...}
            text = response.get('response', '')

            # Extract JSON from response
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                text = text[start:end].strip()
            elif '```' in text:
                start = text.find('```') + 3
                end = text.find('```', start)
                text = text[start:end].strip()

            # Try to parse as JSON
            try:
                parsed = json.loads(text)
                return {
                    'success': parsed.get('success', True),
                    'action': parsed.get('action', 'unknown'),
                    'steps': parsed.get('steps', []),
                    'output': parsed,
                    'task': task
                }
            except json.JSONDecodeError:
                # Return raw text if not JSON
                return {
                    'success': True,
                    'action': 'text_response',
                    'output': text,
                    'task': task
                }

        except Exception as e:
            logger.error(f"Error parsing Ollama response: {e}")
            return {
                'success': False,
                'error': str(e),
                'raw_response': response,
                'task': task
            }

    async def _log_task_start(self, task: Dict):
        """Log task to memory"""
        try:
            with open(self.tasks_file, 'a') as f:
                f.write(f"\n## Task Started: {datetime.now().isoformat()}\n")
                f.write(f"Type: {task['type']}\n")
                f.write(f"Description: {task['description']}\n")
                f.write(f"Source: {task.get('source', 'unknown')}\n\n")
        except Exception as e:
            logger.error(f"Error logging task start: {e}")

    async def _log_task_complete(self, task: Dict, result: Dict):
        """Log task completion"""
        try:
            with open(self.tasks_file, 'a') as f:
                f.write(f"## Task Completed: {datetime.now().isoformat()}\n")
                f.write(f"Success: {result.get('success', False)}\n")
                f.write(f"Action: {result.get('action', 'unknown')}\n")
                f.write(f"Result: {json.dumps(result.get('output', {}), indent=2)}\n\n")
        except Exception as e:
            logger.error(f"Error logging task complete: {e}")

    async def _log_task_error(self, task: Dict, error: str):
        """Log task error"""
        try:
            with open(self.tasks_file, 'a') as f:
                f.write(f"## Task Failed: {datetime.now().isoformat()}\n")
                f.write(f"Error: {error}\n\n")
        except Exception as e:
            logger.error(f"Error logging task error: {e}")

    async def _notify_completion(self, task: Dict, result: Dict):
        """Send notification via Telegram"""
        try:
            if settings.use_python_telegram and settings.admin_telegram_ids:
                from app.integrations.telegram_bot import get_telegram_bot
                bot = get_telegram_bot()

                message = f"✅ Task Completed\n\n"
                message += f"Type: {task['type']}\n"
                message += f"Description: {task['description']}\n"
                message += f"Status: {'Success' if result.get('success') else 'Failed'}\n"

                for admin_id in settings.admin_telegram_ids:
                    try:
                        await bot.send_message(admin_id, message)
                    except Exception as e:
                        logger.error(f"Failed to send Telegram notification: {e}")
        except Exception as e:
            logger.error(f"Notification error: {e}")

    def _is_task_due(self, schedule: Dict, now: datetime) -> bool:
        """Check if scheduled task is due"""
        # Simple time-based check
        # In production, implement proper cron-like scheduling
        last_run = schedule.get('last_run')
        interval = schedule.get('interval_minutes', 60)

        if not last_run:
            return True

        try:
            last_run_dt = datetime.fromisoformat(last_run)
            minutes_since = (now - last_run_dt).total_seconds() / 60
            return minutes_since >= interval
        except Exception:
            return True

    def stop(self):
        """Stop autonomous operation"""
        self.is_running = False
        WorkflowLogger.log_system("⏹️  Autonomous mode STOPPED")

    def get_status(self) -> Dict:
        """Get current status"""
        return {
            'running': self.is_running,
            'current_task': self.current_task,
            'check_interval': settings.check_interval,
            'max_concurrent_tasks': settings.autonomous_max_tasks
        }
