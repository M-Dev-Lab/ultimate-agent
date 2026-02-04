"""
Advanced Error Handler - Migrated from TypeScript telegram-error-handler.ts
Provides exponential backoff, circuit breaker, and detailed error categorization
"""

import structlog
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = structlog.get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better handling"""
    NETWORK = "network"
    OLLAMA = "ollama"
    TELEGRAM = "telegram"
    SKILL = "skill"
    DATABASE = "database"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorMetrics:
    """Track error metrics for monitoring"""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    last_error_time: Optional[datetime] = None
    consecutive_errors: int = 0


class CircuitBreaker:
    """Circuit breaker to prevent cascade failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        
    def record_failure(self):
        """Record a failure"""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "circuit_breaker_opened",
                failures=self.failures,
                threshold=self.failure_threshold
            )
    
    def record_success(self):
        """Record a success"""
        self.failures = 0
        self.state = "closed"
        logger.info("circuit_breaker_closed")
    
    def can_proceed(self) -> bool:
        """Check if operations can proceed"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                time_since_failure = (datetime.now() - self.last_failure_time).seconds
                if time_since_failure >= self.recovery_timeout:
                    self.state = "half-open"
                    logger.info("circuit_breaker_half_open", attempting_recovery=True)
                    return True
            return False
        
        # half-open state
        return True


class AdvancedErrorHandler:
    """
    Comprehensive error handling system
    Ported from TypeScript implementation with Python improvements
    """
    
    def __init__(self):
        self.metrics = ErrorMetrics()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_delays = [1, 2, 5, 10, 30]  # Exponential backoff
        
    def get_circuit_breaker(self, category: str) -> CircuitBreaker:
        """Get or create circuit breaker for category"""
        if category not in self.circuit_breakers:
            self.circuit_breakers[category] = CircuitBreaker()
        return self.circuit_breakers[category]
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error for better handling"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        if "connection" in error_str or "timeout" in error_str:
            return ErrorCategory.NETWORK
        elif "ollama" in error_str or "model" in error_str:
            return ErrorCategory.OLLAMA
        elif "telegram" in error_str or "bot" in error_str:
            return ErrorCategory.TELEGRAM
        elif "skill" in error_str:
            return ErrorCategory.SKILL
        elif "database" in error_str or "sqlite" in error_str:
            return ErrorCategory.DATABASE
        elif "permission" in error_str or "system" in error_str:
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.UNKNOWN
    
    def get_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity"""
        if category == ErrorCategory.UNKNOWN: # Note: Plan had ErrorCategory.CRITICAL which isn't defined in the Enum provided in the same plan, but ErrorSeverity.CRITICAL exists.
            # Correction: Looking at the plan, ErrorCategory.CRITICAL was used in a way that implies it should be checked. 
            # But the Enum defined only: NETWORK, OLLAMA, TELEGRAM, SKILL, DATABASE, SYSTEM, UNKNOWN.
            # I'll stick to what was defined in the Enum or adjust the Enum.
            pass
        
        if category == ErrorCategory.SYSTEM:
            return ErrorSeverity.CRITICAL
        elif category in [ErrorCategory.OLLAMA, ErrorCategory.DATABASE]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.TELEGRAM, ErrorCategory.SKILL]:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def record_error(self, error: Exception, category: Optional[ErrorCategory] = None):
        """Record error in metrics"""
        if category is None:
            category = self.categorize_error(error)
        
        severity = self.get_severity(error, category)
        
        self.metrics.total_errors += 1
        self.metrics.consecutive_errors += 1
        self.metrics.last_error_time = datetime.now()
        
        # Update category count
        cat_name = category.value
        self.metrics.errors_by_category[cat_name] = \
            self.metrics.errors_by_category.get(cat_name, 0) + 1
        
        # Update severity count
        sev_name = severity.value
        self.metrics.errors_by_severity[sev_name] = \
            self.metrics.errors_by_severity.get(sev_name, 0) + 1
        
        # Update circuit breaker
        breaker = self.get_circuit_breaker(cat_name)
        breaker.record_failure()
        
        logger.error(
            "error_recorded",
            category=cat_name,
            severity=sev_name,
            error=str(error),
            consecutive=self.metrics.consecutive_errors
        )
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry
        Includes circuit breaker protection
        """
        breaker = self.get_circuit_breaker(category.value)
        
        if not breaker.can_proceed():
            raise Exception(f"Circuit breaker open for {category.value}")
        
        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) \
                    else func(*args, **kwargs)
                
                # Success - reset metrics
                self.metrics.consecutive_errors = 0
                breaker.record_success()
                return result
                
            except Exception as e:
                self.record_error(e, category)
                
                if attempt < max_retries - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.warning(
                        "retry_attempt",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "max_retries_exceeded",
                        max_retries=max_retries,
                        error=str(e)
                    )
                    raise
    
    def format_user_error(self, error: Exception, category: Optional[ErrorCategory] = None) -> str:
        """Format error message for user display"""
        if category is None:
            category = self.categorize_error(error)
        
        error_messages = {
            ErrorCategory.NETWORK: "🌐 Network connection issue. Please check your internet and try again.",
            ErrorCategory.OLLAMA: "🤖 AI model is temporarily unavailable. Retrying...",
            ErrorCategory.TELEGRAM: "📱 Telegram connection issue. Please try again.",
            ErrorCategory.SKILL: "⚙️ Feature temporarily unavailable. Our team has been notified.",
            ErrorCategory.DATABASE: "💾 Data access issue. Please try again in a moment.",
            ErrorCategory.SYSTEM: "💻 System resource issue. Please contact admin.",
            ErrorCategory.UNKNOWN: "❌ An unexpected error occurred. Please try again."
        }
        
        base_message = error_messages.get(category, error_messages[ErrorCategory.UNKNOWN])
        
        if self.metrics.consecutive_errors > 3:
            base_message += "\n\n⚠️ Multiple errors detected. System may need attention."
        
        return base_message
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get error metrics summary"""
        return {
            "total_errors": self.metrics.total_errors,
            "consecutive_errors": self.metrics.consecutive_errors,
            "errors_by_category": self.metrics.errors_by_category,
            "errors_by_severity": self.metrics.errors_by_severity,
            "last_error": self.metrics.last_error_time.isoformat() if self.metrics.last_error_time else None,
            "circuit_breakers": {
                name: {
                    "state": breaker.state,
                    "failures": breaker.failures
                }
                for name, breaker in self.circuit_breakers.items()
            }
        }


# Global error handler instance
_error_handler = None

def get_error_handler() -> AdvancedErrorHandler:
    """Get or create global error handler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = AdvancedErrorHandler()
    return _error_handler
