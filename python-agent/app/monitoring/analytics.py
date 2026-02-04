"""
Analytics System - Migrated from TypeScript src/analytics/
Tracks message metrics, response times, skill usage, and system health
"""

import structlog
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import json
from pathlib import Path

logger = structlog.get_logger(__name__)


@dataclass
class MessageMetrics:
    """Metrics for a single message interaction"""
    timestamp: datetime
    user_id: int
    message_length: int
    response_length: int
    response_time_ms: float
    skill_used: Optional[str]
    success: bool
    error: Optional[str] = None


@dataclass
class SkillMetrics:
    """Metrics for skill usage"""
    skill_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    avg_response_time_ms: float = 0.0
    last_used: Optional[datetime] = None


class AnalyticsTracker:
    """
    Comprehensive analytics tracking system
    Monitors system performance, usage patterns, and errors
    """
    
    def __init__(self, persist_file: Optional[Path] = None):
        self.message_history: List[MessageMetrics] = []
        self.skill_metrics: Dict[str, SkillMetrics] = {}
        self.daily_stats: Dict[str, Dict] = defaultdict(lambda: {
            "messages": 0,
            "errors": 0,
            "avg_response_time": 0.0
        })
        
        # Corrected: Use absolute path if not provided
        self.persist_file = persist_file or Path(__file__).parent.parent.parent / "data" / "analytics.json"
        self._load_persisted_data()
        
        logger.info("analytics_tracker_initialized")
    
    def _load_persisted_data(self):
        """Load persisted analytics data"""
        try:
            if self.persist_file.exists():
                data = json.loads(self.persist_file.read_text())
                # Reconstruct skill metrics
                for skill_name, metrics_dict in data.get("skill_metrics", {}).items():
                    # Handle timestamp conversion if needed
                    if metrics_dict.get("last_used"):
                        try:
                            metrics_dict["last_used"] = datetime.fromisoformat(metrics_dict["last_used"])
                        except (ValueError, TypeError):
                            metrics_dict["last_used"] = None
                    self.skill_metrics[skill_name] = SkillMetrics(**metrics_dict)
                logger.info("analytics_data_loaded", file=str(self.persist_file))
        except Exception as e:
            logger.error("analytics_load_failed", error=str(e))
    
    def persist_data(self):
        """Persist analytics data to disk"""
        try:
            self.persist_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "skill_metrics": {
                    name: asdict(metrics)
                    for name, metrics in self.skill_metrics.items()
                },
                "daily_stats": dict(self.daily_stats)
            }
            # Custom encoder for datetime
            def json_serial(obj):
                if isinstance(obj, (datetime, timedelta)):
                    return obj.isoformat()
                raise TypeError ("Type %s not serializable" % type(obj))

            self.persist_file.write_text(json.dumps(data, default=json_serial, indent=2))
            logger.debug("analytics_persisted")
        except Exception as e:
            logger.error("analytics_persist_failed", error=str(e))
    
    def record_message(
        self,
        user_id: int,
        message: str,
        response: str,
        response_time_ms: float,
        skill_used: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record message interaction"""
        metrics = MessageMetrics(
            timestamp=datetime.now(),
            user_id=user_id,
            message_length=len(message),
            response_length=len(response),
            response_time_ms=response_time_ms,
            skill_used=skill_used,
            success=success,
            error=error
        )
        
        self.message_history.append(metrics)
        
        # Update daily stats
        date_key = metrics.timestamp.strftime("%Y-%m-%d")
        daily = self.daily_stats[date_key]
        daily["messages"] += 1
        if not success:
            daily["errors"] += 1
        
        # Update skill metrics
        if skill_used:
            self._update_skill_metrics(skill_used, response_time_ms, success)
        
        # Keep only last 1000 messages in memory
        if len(self.message_history) > 1000:
            self.message_history = self.message_history[-1000:]
        
        logger.debug(
            "message_recorded",
            user_id=user_id,
            skill=skill_used,
            success=success,
            response_time=response_time_ms
        )
        # Proactively persist data
        self.persist_data()
    
    def _update_skill_metrics(self, skill_name: str, response_time_ms: float, success: bool):
        """Update metrics for a skill"""
        if skill_name not in self.skill_metrics:
            self.skill_metrics[skill_name] = SkillMetrics(skill_name=skill_name)
        
        metrics = self.skill_metrics[skill_name]
        metrics.total_calls += 1
        if success:
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1
        
        # Update average response time
        total_time = metrics.avg_response_time_ms * (metrics.total_calls - 1)
        metrics.avg_response_time_ms = (total_time + response_time_ms) / metrics.total_calls
        metrics.last_used = datetime.now()
    
    def get_summary(self, days: int = 7) -> Dict:
        """Get analytics summary"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_messages = [m for m in self.message_history if m.timestamp > cutoff]
        
        total_messages = len(recent_messages)
        successful = sum(1 for m in recent_messages if m.success)
        failed = total_messages - successful
        
        avg_response_time = sum(m.response_time_ms for m in recent_messages) / total_messages if total_messages > 0 else 0
        
        # Skill usage breakdown
        skill_usage = defaultdict(int)
        for m in recent_messages:
            if m.skill_used:
                skill_usage[m.skill_used] += 1
        
        return {
            "period_days": days,
            "total_messages": total_messages,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_messages * 100) if total_messages > 0 else 0,
            "avg_response_time_ms": round(avg_response_time, 2),
            "skill_usage": dict(skill_usage),
            "skill_metrics": {
                name: asdict(metrics)
                for name, metrics in self.skill_metrics.items()
            }
        }
    
    def get_health_status(self) -> Dict:
        """Get system health status based on analytics"""
        recent_summary = self.get_summary(days=1)
        
        health_score = 100
        issues = []
        
        # Check error rate
        if recent_summary["total_messages"] > 0:
            error_rate = (recent_summary["failed"] / recent_summary["total_messages"]) * 100
            if error_rate > 20:
                health_score -= 30
                issues.append(f"High error rate: {error_rate:.1f}%")
            elif error_rate > 10:
                health_score -= 15
                issues.append(f"Elevated error rate: {error_rate:.1f}%")
        
        # Check response time
        if recent_summary["avg_response_time_ms"] > 5000:
            health_score -= 20
            issues.append(f"Slow responses: {recent_summary['avg_response_time_ms']:.0f}ms")
        elif recent_summary["avg_response_time_ms"] > 3000:
            health_score -= 10
            issues.append(f"Delayed responses: {recent_summary['avg_response_time_ms']:.0f}ms")
        
        status = "healthy" if health_score > 80 else "degraded" if health_score > 50 else "unhealthy"
        
        return {
            "status": status,
            "health_score": max(0, health_score),
            "issues": issues,
            "metrics": recent_summary
        }


# Global analytics tracker
_analytics_tracker = None

def get_analytics_tracker() -> AnalyticsTracker:
    """Get or create global analytics tracker"""
    global _analytics_tracker
    if _analytics_tracker is None:
        _analytics_tracker = AnalyticsTracker()
    return _analytics_tracker
