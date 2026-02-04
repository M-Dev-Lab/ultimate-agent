"""
Task Scheduler Skill for Ultimate Coding Agent
Schedules and manages recurring tasks
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.skills.base_skill import BaseSkill, SkillResult
import structlog

logger = structlog.get_logger(__name__)


class TaskSchedulerSkill(BaseSkill):
    """Schedule and manage tasks"""
    
    name = "task_scheduler"
    description = "Schedule tasks with cron expressions or intervals"
    category = "automation"
    
    def __init__(self):
        super().__init__()
        self.scheduler = AsyncIOScheduler()
        self.tasks_file = Path("./data/scheduled_tasks.json")
        self.tasks: Dict[str, Dict] = {}
        self._load_tasks()
    
    async def _execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute task scheduling"""
        action = params.get("action", "list")
        
        if action == "schedule":
            return await self._schedule_task(params)
        elif action == "list":
            return self._list_tasks()
        elif action == "delete":
            return self._delete_task(params)
        elif action == "execute":
            return await self._execute_task_now(params)
        else:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown action: {action}"
            )
    
    async def _schedule_task(self, params: Dict[str, Any]) -> SkillResult:
        """Schedule a new task"""
        task_name = params.get("task_name", "").strip()
        schedule = params.get("schedule", "")
        skill = params.get("skill", "")
        skill_params = params.get("params", {})
        
        if not task_name or not schedule or not skill:
            return SkillResult(
                success=False,
                output="",
                error="Missing required parameters: task_name, schedule, skill"
            )
        
        trigger = self._parse_schedule(schedule)
        if not trigger:
            return SkillResult(
                success=False,
                output="",
                error=f"Invalid schedule: {schedule}"
            )
        
        task_id = f"task_{len(self.tasks) + 1}"
        
        task_data = {
            "id": task_id,
            "name": task_name,
            "schedule": schedule,
            "skill": skill,
            "params": skill_params,
            "created_at": datetime.utcnow().isoformat(),
            "enabled": True,
            "last_run": None,
            "next_run": None,
        }
        
        try:
            job_id = f"scheduled_{task_id}"
            
            self.scheduler.add_job(
                self._run_skill,
                trigger=trigger,
                id=job_id,
                name=task_name,
                replace_existing=True,
                kwargs={"skill": skill, "params": skill_params}
            )
            
            if not self.scheduler.running:
                self.scheduler.start()
            
            task_data["next_run"] = str(self.scheduler.get_job(job_id).next_run_time)
            self.tasks[task_id] = task_data
            self._save_tasks()
            
            logger.info(f"Task scheduled: {task_name}")
            
            return SkillResult(
                success=True,
                output=f"✅ Task '{task_name}' scheduled!\n\n"
                       f"Schedule: {schedule}\n"
                       f"Skill: {skill}\n"
                       f"Task ID: {task_id}\n"
                       f"Next run: {task_data['next_run']}",
                data=task_data
            )
            
        except Exception as e:
            logger.error(f"Task scheduling failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _parse_schedule(self, schedule: str):
        """Parse schedule string into APScheduler trigger"""
        try:
            if schedule.startswith("every "):
                interval_str = schedule[6:]
                parts = interval_str.split()
                
                if len(parts) >= 2:
                    value = int(parts[0])
                    unit = parts[1].lower()
                    
                    if "second" in unit:
                        return IntervalTrigger(seconds=value)
                    elif "minute" in unit:
                        return IntervalTrigger(minutes=value)
                    elif "hour" in unit:
                        return IntervalTrigger(hours=value)
                    elif "day" in unit:
                        return IntervalTrigger(days=value)
            
            if " " in schedule and not any(x in schedule for x in ["*", "/", ","]):
                try:
                    dt = datetime.strptime(schedule, "%Y-%m-%d %H:%M")
                    return IntervalTrigger(start_date=dt)
                except ValueError:
                    pass
            
            return CronTrigger.from_crontab(schedule)
            
        except Exception as e:
            logger.warning(f"Failed to parse schedule: {schedule} - {e}")
            return None
    
    def _list_tasks(self) -> SkillResult:
        """List all scheduled tasks"""
        if not self.tasks:
            return SkillResult(
                success=True,
                output="📅 <b>Scheduled Tasks</b>\n\nNo tasks scheduled yet.",
                data={"tasks": []}
            )
        
        task_list = []
        for task_id, task in self.tasks.items():
            status = "✅" if task.get("enabled", True) else "❌"
            last_run = task.get("last_run", "Never")
            next_run = task.get("next_run", "Unknown")
            
            task_list.append(
                f"{status} <b>{task['name']}</b>\n"
                f"   Schedule: {task['schedule']}\n"
                f"   Skill: {task['skill']}\n"
                f"   Last: {last_run}\n"
                f"   Next: {next_run}\n"
            )
        
        output = "📅 <b>Scheduled Tasks</b>\n\n" + "\n".join(task_list)
        
        return SkillResult(
            success=True,
            output=output,
            data={"tasks": list(self.tasks.values())}
        )
    
    def _delete_task(self, params: Dict[str, Any]) -> SkillResult:
        """Delete a scheduled task"""
        task_name = params.get("task_name", "")
        
        task_id = None
        for tid, task in self.tasks.items():
            if task["name"] == task_name:
                task_id = tid
                break
        
        if not task_id:
            return SkillResult(
                success=False,
                output="",
                error=f"Task not found: {task_name}"
            )
        
        try:
            job_id = f"scheduled_{task_id}"
            self.scheduler.remove_job(job_id)
            
            del self.tasks[task_id]
            self._save_tasks()
            
            logger.info(f"Task deleted: {task_name}")
            
            return SkillResult(
                success=True,
                output=f"✅ Task '{task_name}' deleted!",
                data={"deleted_task": task_name}
            )
            
        except Exception as e:
            logger.error(f"Task deletion failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    async def _execute_task_now(self, params: Dict[str, Any]) -> SkillResult:
        """Execute a task immediately"""
        task_name = params.get("task_name", "")
        
        task = None
        for t in self.tasks.values():
            if t["name"] == task_name:
                task = t
                break
        
        if not task:
            return SkillResult(
                success=False,
                output="",
                error=f"Task not found: {task_name}"
            )
        
        result = await self._run_skill(task["skill"], task.get("params", {}))
        
        task["last_run"] = datetime.utcnow().isoformat()
        self._save_tasks()
        
        return result
    
    async def _run_skill(self, skill: str, params: Dict[str, Any]):
        """Run a skill as part of scheduled task"""
        from app.skills.registry import get_skill_registry
        
        logger.info(f"Running scheduled task skill: {skill}")
        
        try:
            registry = get_skill_registry()
            result = await registry.execute_skill(skill, params)
            
            logger.info(
                "Scheduled task completed",
                skill=skill,
                success=result.success
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Scheduled task failed: {e}")
            return SkillResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def _load_tasks(self):
        """Load tasks from file"""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r') as f:
                    self.tasks = json.load(f)
                logger.info(f"Loaded {len(self.tasks)} scheduled tasks")
        except Exception as e:
            logger.warning(f"Failed to load tasks: {e}")
            self.tasks = {}
    
    def _save_tasks(self):
        """Save tasks to file"""
        try:
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tasks_file, 'w') as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
    
    async def start_scheduler(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Task scheduler started")
    
    async def stop_scheduler(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Task scheduler stopped")
