"""Production-grade error handling for sync operations."""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from rich.console import Console

console = Console()


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"  # Transient, will retry
    MEDIUM = "medium"  # May require intervention
    HIGH = "high"  # Immediate attention needed
    CRITICAL = "critical"  # System failure


class ErrorCategory(Enum):
    """Error categories for handling strategy."""

    NETWORK = "network"  # Network connectivity issues
    WEAVIATE = "weaviate"  # Weaviate service errors
    FILE_SYSTEM = "filesystem"  # File read/write errors
    ENCODING = "encoding"  # Text encoding issues
    RATE_LIMIT = "rate_limit"  # API rate limiting
    MEMORY = "memory"  # Memory exhaustion
    TIMEOUT = "timeout"  # Operation timeouts
    VALIDATION = "validation"  # Data validation errors
    UNKNOWN = "unknown"  # Unclassified errors


@dataclass
class ErrorContext:
    """Context information for error handling decisions."""

    operation: str
    file_path: str | None = None
    line_number: int | None = None
    attempt: int = 1
    total_attempts: int = 3
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if attempt <= 1:
            return 0.0

        delay = self.base_delay * (self.exponential_base ** (attempt - 2))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add ±25% jitter to prevent thundering herd
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)


class CircuitBreaker:
    """Circuit breaker for handling cascade failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half_open

    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if (
                self.last_failure_time
                and (datetime.now(UTC) - self.last_failure_time).total_seconds()
                >= self.recovery_timeout
            ):
                self.state = "half_open"
                return True
            return False

        # half_open state
        return True

    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None

    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
        elif self.state == "half_open":
            self.state = "open"


class ErrorClassifier:
    """Classify errors and determine handling strategy."""

    # Error patterns for classification
    NETWORK_PATTERNS = [
        "connection",
        "network",
        "timeout",
        "unreachable",
        "refused",
        "reset",
        "dns",
        "resolve",
    ]

    WEAVIATE_PATTERNS = ["weaviate", "400", "401", "403", "404", "422", "500", "502", "503"]

    RATE_LIMIT_PATTERNS = ["rate limit", "too many requests", "429", "quota exceeded"]

    FILESYSTEM_PATTERNS = ["no such file", "permission denied", "disk full", "i/o error"]

    ENCODING_PATTERNS = ["encoding", "decode", "unicode", "utf-8", "ascii"]

    MEMORY_PATTERNS = ["memory", "out of memory", "oom", "malloc"]

    def classify_error(
        self, error: Exception, context: ErrorContext
    ) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error and determine severity."""
        error_text = str(error).lower()

        # Check patterns
        if any(pattern in error_text for pattern in self.RATE_LIMIT_PATTERNS):
            return ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM

        if any(pattern in error_text for pattern in self.NETWORK_PATTERNS):
            return (
                ErrorCategory.NETWORK,
                ErrorSeverity.LOW if context.attempt < 3 else ErrorSeverity.MEDIUM,
            )

        if any(pattern in error_text for pattern in self.WEAVIATE_PATTERNS):
            return ErrorCategory.WEAVIATE, ErrorSeverity.MEDIUM

        if any(pattern in error_text for pattern in self.FILESYSTEM_PATTERNS):
            return (
                ErrorCategory.FILE_SYSTEM,
                ErrorSeverity.LOW if "no such file" in error_text else ErrorSeverity.MEDIUM,
            )

        if any(pattern in error_text for pattern in self.ENCODING_PATTERNS):
            return ErrorCategory.ENCODING, ErrorSeverity.LOW

        if any(pattern in error_text for pattern in self.MEMORY_PATTERNS):
            return ErrorCategory.MEMORY, ErrorSeverity.HIGH

        # Check for timeout
        if isinstance(error, asyncio.TimeoutError) or "timeout" in error_text:
            return ErrorCategory.TIMEOUT, ErrorSeverity.LOW

        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM


class ProductionErrorHandler:
    """Production-grade error handler with circuit breaker and retry logic."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.classifier = ErrorClassifier()
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.error_counts: dict[str, int] = {}
        self.last_errors: list[dict[str, Any]] = []

        # Configure logging
        self.logger = logging.getLogger("elysiactl.error_handler")
        self.logger.setLevel(logging.INFO)

        # Default retry policies by category
        self.retry_policies = {
            ErrorCategory.NETWORK: RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=30.0),
            ErrorCategory.WEAVIATE: RetryPolicy(max_attempts=3, base_delay=2.0, max_delay=60.0),
            ErrorCategory.RATE_LIMIT: RetryPolicy(max_attempts=5, base_delay=10.0, max_delay=300.0),
            ErrorCategory.TIMEOUT: RetryPolicy(max_attempts=3, base_delay=5.0, max_delay=120.0),
            ErrorCategory.FILE_SYSTEM: RetryPolicy(max_attempts=2, base_delay=0.5, max_delay=5.0),
            ErrorCategory.ENCODING: RetryPolicy(max_attempts=1, base_delay=0.0, max_delay=0.0),
            ErrorCategory.MEMORY: RetryPolicy(max_attempts=1, base_delay=0.0, max_delay=0.0),
            ErrorCategory.VALIDATION: RetryPolicy(max_attempts=1, base_delay=0.0, max_delay=0.0),
            ErrorCategory.UNKNOWN: RetryPolicy(max_attempts=2, base_delay=1.0, max_delay=10.0),
        }

    def get_circuit_breaker(self, operation: str) -> CircuitBreaker:
        """Get or create circuit breaker for operation."""
        if operation not in self.circuit_breakers:
            self.circuit_breakers[operation] = CircuitBreaker()
        return self.circuit_breakers[operation]

    async def execute_with_retry(
        self, operation: Callable, context: ErrorContext, *args, **kwargs
    ) -> Any:
        """Execute operation with retry logic and circuit breaker."""
        circuit_breaker = self.get_circuit_breaker(context.operation)

        for attempt in range(1, context.total_attempts + 1):
            context.attempt = attempt

            # Check circuit breaker
            if not circuit_breaker.can_attempt():
                error_msg = f"Circuit breaker open for {context.operation}"
                self._log_error(error_msg, context, ErrorCategory.NETWORK, ErrorSeverity.HIGH)
                raise Exception(error_msg)

            try:
                start_time = time.time()
                result = await operation(*args, **kwargs)

                # Record success
                circuit_breaker.record_success()
                self._record_success(context, time.time() - start_time)
                return result

            except Exception as error:
                category, severity = self.classifier.classify_error(error, context)
                self._record_error(error, context, category, severity)

                # Always record failure for circuit breaker
                circuit_breaker.record_failure()

                # Check if we should retry
                if not self._should_retry(error, context, category, severity, attempt):
                    raise

                # Calculate delay and wait
                policy = self.retry_policies[category]
                delay = policy.get_delay(attempt)
                if delay > 0:
                    self.logger.info(
                        f"Retrying {context.operation} in {delay:.2f}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise Exception(f"All retry attempts exhausted for {context.operation}")

    def _should_retry(
        self,
        error: Exception,
        context: ErrorContext,
        category: ErrorCategory,
        severity: ErrorSeverity,
        attempt: int,
    ) -> bool:
        """Determine if operation should be retried."""
        policy = self.retry_policies[category]

        # Don't retry if max attempts reached
        if attempt >= policy.max_attempts:
            return False

        # Don't retry critical errors
        if severity == ErrorSeverity.CRITICAL:
            return False

        # Don't retry certain categories
        if category in [ErrorCategory.ENCODING, ErrorCategory.VALIDATION, ErrorCategory.MEMORY]:
            return False

        return True

    def _record_error(
        self,
        error: Exception,
        context: ErrorContext,
        category: ErrorCategory,
        severity: ErrorSeverity,
    ):
        """Record error for tracking and reporting."""
        error_info = {
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": context.operation,
            "file_path": context.file_path,
            "line_number": context.line_number,
            "attempt": context.attempt,
            "category": category.value,
            "severity": severity.value,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "metadata": context.metadata,
        }

        # Add to recent errors (keep last 100)
        self.last_errors.append(error_info)
        if len(self.last_errors) > 100:
            self.last_errors.pop(0)

        # Update error counts
        key = f"{category.value}:{severity.value}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

        self._log_error(str(error), context, category, severity)

    def _record_success(self, context: ErrorContext, duration: float):
        """Record successful operation."""
        self.logger.debug(f"Success: {context.operation} completed in {duration:.3f}s")

    def _log_error(
        self,
        error_message: str,
        context: ErrorContext,
        category: ErrorCategory,
        severity: ErrorSeverity,
    ):
        """Log error with appropriate level."""
        log_msg = f"[{severity.value.upper()}] {context.operation}"
        if context.file_path:
            log_msg += f" ({context.file_path})"
        if context.line_number:
            log_msg += f" line {context.line_number}"
        log_msg += f" - {error_message}"

        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_msg)
            console.print(f"[bold red]CRITICAL: {log_msg}[/bold red]")
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_msg)
            console.print(f"[red]ERROR: {log_msg}[/red]")
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_msg)
            console.print(f"[yellow]WARNING: {log_msg}[/yellow]")
        else:
            self.logger.info(log_msg)
            if context.attempt > 1:  # Only show retries
                console.print(f"[dim]Retry {context.attempt}: {log_msg}[/dim]")

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of error statistics."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": dict(self.error_counts),
            "circuit_breaker_states": {
                op: {"state": cb.state, "failures": cb.failure_count}
                for op, cb in self.circuit_breakers.items()
            },
            "recent_errors_count": len(self.last_errors),
        }

    def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent errors for debugging."""
        return self.last_errors[-limit:]

    def reset_statistics(self):
        """Reset error statistics and circuit breakers."""
        self.error_counts.clear()
        self.last_errors.clear()
        self.circuit_breakers.clear()


# Global error handler instance
_error_handler: ProductionErrorHandler | None = None


def get_error_handler(config: dict[str, Any] | None = None) -> ProductionErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ProductionErrorHandler(config)
    return _error_handler


# Convenience function for getting error handler with config
def get_error_handler_with_config() -> ProductionErrorHandler:
    """Get error handler with configuration from config module."""
    from ..config import get_config

    config = get_config()

    # Build error handler config from processing config
    error_config = {
        "circuit_breaker_failure_threshold": config.processing.circuit_breaker_failure_threshold,
        "circuit_breaker_recovery_timeout": config.processing.circuit_breaker_recovery_timeout,
        "retry_policies": {
            "NETWORK": {
                "max_attempts": 5,
                "base_delay": config.processing.retry_base_delay,
                "max_delay": config.processing.retry_max_delay,
            },
            "WEAVIATE": {
                "max_attempts": 3,
                "base_delay": config.processing.retry_base_delay,
                "max_delay": config.processing.retry_max_delay,
            },
            "RATE_LIMIT": {"max_attempts": 5, "base_delay": 10.0, "max_delay": 300.0},
        },
    }

    return get_error_handler(error_config)
