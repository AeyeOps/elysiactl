# Phase 4: Production Error Handling

## Objective

Implement comprehensive error handling with exponential backoff, circuit breaker patterns, detailed logging, and graceful degradation for production-scale deployments.

## Problem Summary

Phase 3 handles basic errors but lacks enterprise-grade error recovery mechanisms. Production deployments need robust handling of network failures, Weaviate unavailability, rate limiting, memory pressure, and transient errors with automatic recovery and operational visibility.

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/services/error_handling.py` (NEW)

**Create comprehensive error handling service:**

```python
"""Production-grade error handling for sync operations."""

import asyncio
import time
import random
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from rich.console import Console

console = Console()

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"          # Transient, will retry
    MEDIUM = "medium"    # May require intervention
    HIGH = "high"        # Immediate attention needed
    CRITICAL = "critical"  # System failure

class ErrorCategory(Enum):
    """Error categories for handling strategy."""
    NETWORK = "network"          # Network connectivity issues
    WEAVIATE = "weaviate"       # Weaviate service errors
    FILE_SYSTEM = "filesystem"  # File read/write errors
    ENCODING = "encoding"       # Text encoding issues
    RATE_LIMIT = "rate_limit"   # API rate limiting
    MEMORY = "memory"           # Memory exhaustion
    TIMEOUT = "timeout"         # Operation timeouts
    VALIDATION = "validation"   # Data validation errors
    UNKNOWN = "unknown"         # Unclassified errors

@dataclass
class ErrorContext:
    """Context information for error handling decisions."""
    operation: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    attempt: int = 1
    total_attempts: int = 3
    start_time: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

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
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
    
    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).total_seconds() >= self.recovery_timeout:
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
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
        elif self.state == "half_open":
            self.state = "open"

class ErrorClassifier:
    """Classify errors and determine handling strategy."""
    
    # Error patterns for classification
    NETWORK_PATTERNS = [
        "connection", "network", "timeout", "unreachable", 
        "refused", "reset", "dns", "resolve"
    ]
    
    WEAVIATE_PATTERNS = [
        "weaviate", "400", "401", "403", "404", "422", "500", "502", "503"
    ]
    
    RATE_LIMIT_PATTERNS = [
        "rate limit", "too many requests", "429", "quota exceeded"
    ]
    
    FILESYSTEM_PATTERNS = [
        "no such file", "permission denied", "disk full", "i/o error"
    ]
    
    ENCODING_PATTERNS = [
        "encoding", "decode", "unicode", "utf-8", "ascii"
    ]
    
    MEMORY_PATTERNS = [
        "memory", "out of memory", "oom", "malloc"
    ]
    
    def classify_error(self, error: Exception, context: ErrorContext) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error and determine severity."""
        error_text = str(error).lower()
        
        # Check patterns
        if any(pattern in error_text for pattern in self.RATE_LIMIT_PATTERNS):
            return ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM
        
        if any(pattern in error_text for pattern in self.NETWORK_PATTERNS):
            return ErrorCategory.NETWORK, ErrorSeverity.LOW if context.attempt < 3 else ErrorSeverity.MEDIUM
        
        if any(pattern in error_text for pattern in self.WEAVIATE_PATTERNS):
            return ErrorCategory.WEAVIATE, ErrorSeverity.MEDIUM
        
        if any(pattern in error_text for pattern in self.FILESYSTEM_PATTERNS):
            return ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW if "no such file" in error_text else ErrorSeverity.MEDIUM
        
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
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.classifier = ErrorClassifier()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_counts: Dict[str, int] = {}
        self.last_errors: List[Dict[str, Any]] = []
        
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
        self, 
        operation: Callable,
        context: ErrorContext,
        *args, 
        **kwargs
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
                    self.logger.info(f"Retrying {context.operation} in {delay:.2f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        raise Exception(f"All retry attempts exhausted for {context.operation}")
    
    def _should_retry(
        self, 
        error: Exception, 
        context: ErrorContext, 
        category: ErrorCategory,
        severity: ErrorSeverity, 
        attempt: int
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
        severity: ErrorSeverity
    ):
        """Record error for tracking and reporting."""
        error_info = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': context.operation,
            'file_path': context.file_path,
            'line_number': context.line_number,
            'attempt': context.attempt,
            'category': category.value,
            'severity': severity.value,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'metadata': context.metadata
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
        severity: ErrorSeverity
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
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error statistics."""
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_counts': dict(self.error_counts),
            'circuit_breaker_states': {
                op: {'state': cb.state, 'failures': cb.failure_count} 
                for op, cb in self.circuit_breakers.items()
            },
            'recent_errors_count': len(self.last_errors)
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors for debugging."""
        return self.last_errors[-limit:]
    
    def reset_statistics(self):
        """Reset error statistics and circuit breakers."""
        self.error_counts.clear()
        self.last_errors.clear()
        self.circuit_breakers.clear()

# Global error handler instance
_error_handler: Optional[ProductionErrorHandler] = None

def get_error_handler() -> ProductionErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ProductionErrorHandler()
    return _error_handler
```

### File: `/opt/elysiactl/src/elysiactl/services/sync.py` (INTEGRATE ERROR HANDLING)

**Update process_single_change with error handling:**

```python
from .error_handling import get_error_handler, ErrorContext

async def process_single_change(
    change: Dict[str, Any], 
    weaviate: WeaviateService, 
    embedding: EmbeddingService,
    collection: str,
    dry_run: bool = False
) -> bool:
    """Process a single file change with production error handling."""
    error_handler = get_error_handler()
    
    operation = change.get('op', 'modify')
    file_path = change.get('path')
    line_number = change.get('line', 0)
    
    if not file_path:
        console.print(f"[red]Missing path in change: {change}[/red]")
        return False
    
    context = ErrorContext(
        operation=f"sync_{operation}",
        file_path=file_path,
        line_number=line_number,
        total_attempts=3,
        metadata={'collection': collection, 'dry_run': dry_run}
    )
    
    try:
        return await error_handler.execute_with_retry(
            _process_change_inner,
            context,
            change, weaviate, embedding, collection, dry_run
        )
    except Exception as e:
        console.print(f"[red]Failed to process {file_path} after all retries: {e}[/red]")
        return False

async def _process_change_inner(
    change: Dict[str, Any], 
    weaviate: WeaviateService, 
    embedding: EmbeddingService,
    collection: str,
    dry_run: bool = False
) -> bool:
    """Inner processing function for retry wrapper."""
    operation = change.get('op', 'modify')
    file_path = change.get('path')
    
    if operation == 'delete':
        if not dry_run:
            # TODO: Implement deletion with deterministic UUID lookup
            console.print(f"[yellow]DELETE not yet implemented: {file_path}[/yellow]")
        else:
            console.print(f"[red]Would delete: {file_path}[/red]")
        return True
    
    elif operation in ['add', 'modify']:
        content = resolve_file_content(change)
        if content is None:
            return False
        
        if dry_run:
            console.print(f"[blue]Would {operation.upper()}: {file_path} ({len(content)} chars)[/blue]")
            return True
        
        # Generate embedding with retry
        error_handler = get_error_handler()
        embedding_context = ErrorContext(
            operation="generate_embedding",
            file_path=file_path,
            total_attempts=2,
            metadata={'content_length': len(content)}
        )
        
        embedding_vector = await error_handler.execute_with_retry(
            embedding.generate_embedding,
            embedding_context,
            content
        )
        
        # Index in Weaviate with retry
        weaviate_context = ErrorContext(
            operation="weaviate_index",
            file_path=file_path,
            total_attempts=5,  # More retries for Weaviate
            metadata={'collection': collection, 'has_embedding': bool(embedding_vector)}
        )
        
        success = await error_handler.execute_with_retry(
            weaviate.index_file,
            weaviate_context,
            file_path, content, collection, embedding_vector
        )
        
        if success:
            console.print(f"[green]{operation.upper()}: {file_path}[/green]")
            return True
        else:
            console.print(f"[red]Failed to index: {file_path}[/red]")
            return False
    
    else:
        raise ValueError(f"Unknown operation '{operation}' for {file_path}")
```

**Update sync_files_from_stdin with error monitoring:**

```python
def sync_files_from_stdin(
    collection: str,
    dry_run: bool = False,
    verbose: bool = False,
    use_stdin: bool = True,
    batch_size: int = None,
    max_retries: int = 3
) -> bool:
    """Main sync function with production error handling."""
    
    if not batch_size:
        batch_size = get_config().processing.batch_size
    
    checkpoint = SQLiteCheckpointManager()
    error_handler = get_error_handler()
    config = get_config()
    
    # ... existing code ...
    
    try:
        # ... existing processing loop ...
        
        # Complete the run with error summary
        stats = checkpoint.complete_run(run_id)
        error_summary = error_handler.get_error_summary()
        
        console.print(f"\n[bold]Sync completed:[/bold]")
        console.print(f"  Run ID: {run_id}")
        console.print(f"  Success: {stats['success_count']}")
        console.print(f"  Errors: {stats['error_count']}")
        console.print(f"  Total: {stats['processed_lines']}")
        
        # Show error summary if there were issues
        if error_summary['total_errors'] > 0:
            console.print(f"\n[yellow]Error Summary:[/yellow]")
            console.print(f"  Total errors: {error_summary['total_errors']}")
            
            # Show top error categories
            sorted_errors = sorted(
                error_summary['error_counts'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            for category, count in sorted_errors[:5]:
                console.print(f"  {category}: {count}")
            
            # Show circuit breaker status
            for op, status in error_summary['circuit_breaker_states'].items():
                if status['state'] != 'closed':
                    console.print(f"  Circuit breaker {op}: {status['state']} ({status['failures']} failures)")
        
        return stats['error_count'] == 0
        
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        
        # Show recent errors for debugging
        recent_errors = error_handler.get_recent_errors(3)
        if recent_errors:
            console.print("\n[red]Recent errors:[/red]")
            for error in recent_errors:
                console.print(f"  {error['timestamp']}: {error['error_message']}")
        
        return False
```

### File: `/opt/elysiactl/src/elysiactl/commands/index.py` (ADD ERROR MONITORING)

**Add error monitoring commands:**

```python
@app.command()
def errors(
    recent: Annotated[int, typer.Option("--recent", help="Show N recent errors")] = 10,
    summary: Annotated[bool, typer.Option("--summary", help="Show error summary statistics")] = False,
    reset: Annotated[bool, typer.Option("--reset", help="Reset error statistics")] = False,
):
    """Show error statistics and recent failures."""
    from ..services.error_handling import get_error_handler
    from rich.table import Table
    
    error_handler = get_error_handler()
    
    if reset:
        error_handler.reset_statistics()
        console.print("[green]Error statistics reset[/green]")
        return
    
    if summary:
        summary_data = error_handler.get_error_summary()
        
        console.print(f"\n[bold]Error Summary:[/bold]")
        console.print(f"  Total errors: {summary_data['total_errors']}")
        
        if summary_data['error_counts']:
            table = Table(title="Error Categories")
            table.add_column("Category", style="cyan")
            table.add_column("Count", style="red", justify="right")
            
            sorted_errors = sorted(
                summary_data['error_counts'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            for category, count in sorted_errors:
                table.add_row(category, str(count))
            
            console.print(table)
        
        # Circuit breaker status
        cb_states = summary_data['circuit_breaker_states']
        if cb_states:
            console.print(f"\n[bold]Circuit Breaker Status:[/bold]")
            for operation, status in cb_states.items():
                state_color = "green" if status['state'] == 'closed' else "red"
                console.print(f"  {operation}: [{state_color}]{status['state']}[/{state_color}] ({status['failures']} failures)")
    
    # Show recent errors
    recent_errors = error_handler.get_recent_errors(recent)
    if recent_errors:
        table = Table(title=f"Recent Errors (last {len(recent_errors)})")
        table.add_column("Time", style="dim")
        table.add_column("Operation", style="cyan") 
        table.add_column("File", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Message", style="white")
        
        for error in recent_errors:
            time_str = error['timestamp'].split('T')[1][:8]  # HH:MM:SS
            file_path = error['file_path'] or ''
            if file_path and len(file_path) > 30:
                file_path = '...' + file_path[-27:]
            
            table.add_row(
                time_str,
                error['operation'],
                file_path,
                error['severity'],
                error['error_message'][:50] + ('...' if len(error['error_message']) > 50 else '')
            )
        
        console.print(table)
    else:
        console.print("[green]No recent errors[/green]")
```

## Agent Workflow

1. **Core Error Handling Implementation:**
   - Create comprehensive error classification system
   - Implement circuit breaker pattern for cascade failure prevention
   - Add exponential backoff with jitter for retry logic
   - Create detailed error context and logging

2. **Integration with Existing Services:**
   - Wrap all external operations (Weaviate, embedding) with error handlers
   - Add retry logic to file processing operations
   - Integrate error statistics with checkpoint system
   - Create operational visibility tools

3. **Monitoring and Observability:**
   - Add error monitoring commands to CLI
   - Create error summary and recent error viewing
   - Implement circuit breaker status monitoring
   - Add error reset capability for testing

4. **Production Configuration:**
   - Configure appropriate retry policies per error type
   - Set up proper logging levels and formats
   - Add error handling configuration options
   - Test error scenarios and recovery

## Testing

### Test network error handling:
```bash
# Simulate network issues (requires network manipulation)
# Test with invalid Weaviate URL
WCD_URL="http://invalid-host:8080" echo "test.py" | uv run elysiactl index sync --stdin --dry-run --verbose
```

### Test retry logic:
```bash
# Create a file that will cause encoding issues
python -c "import os; open('/tmp/bad_encoding.txt', 'wb').write(b'\xff\xfe\x00\x00invalid')"
echo "/tmp/bad_encoding.txt" | uv run elysiactl index sync --stdin --verbose
```

### Test error monitoring:
```bash
# Show error summary
uv run elysiactl index errors --summary

# Show recent errors
uv run elysiactl index errors --recent 5

# Reset error statistics
uv run elysiactl index errors --reset
```

### Test circuit breaker:
```bash
# Generate multiple failures to trigger circuit breaker
for i in {1..10}; do
    echo "/nonexistent/file$i.py" | uv run elysiactl index sync --stdin --verbose
done

# Check circuit breaker status
uv run elysiactl index errors --summary
```

### Test with large batch:
```bash
# Test error handling under load
find /opt/elysiactl -name "*.py" | head -50 | uv run elysiactl index sync --stdin --verbose
```

### Test timeout handling:
```bash
# Test with very small timeout (requires configuration)
elysiactl_SHORT_TIMEOUT=0.001 echo "test.py" | uv run elysiactl index sync --stdin --verbose
```

## Success Criteria

- [ ] Error classification correctly identifies network, Weaviate, filesystem, and other error types
- [ ] Exponential backoff with jitter prevents thundering herd problems
- [ ] Circuit breaker opens after 5 failures and recovers after 30 seconds
- [ ] Retry policies are appropriate for each error category
- [ ] Operations fail gracefully without crashing the entire sync process
- [ ] Error statistics track failure counts by category and severity
- [ ] Recent errors list provides debugging information
- [ ] `elysiactl index errors` commands work correctly
- [ ] Circuit breaker status is visible and accurate
- [ ] Memory errors and validation errors are not retried
- [ ] Network and Weaviate errors retry with appropriate backoff
- [ ] All test scenarios execute without unexpected failures
- [ ] Error logs contain sufficient detail for troubleshooting

## Configuration Changes

Add error handling configuration to existing config:

**File: `/opt/elysiactl/src/elysiactl/config.py`**

```python
@dataclass
class ProcessingConfig:
    # ... existing fields ...
    
    # Error handling configuration
    max_retry_attempts: int = field(default_factory=lambda: int(os.getenv("elysiactl_MAX_RETRY_ATTEMPTS", "3")))
    retry_base_delay: float = field(default_factory=lambda: float(os.getenv("elysiactl_RETRY_BASE_DELAY", "1.0")))
    retry_max_delay: float = field(default_factory=lambda: float(os.getenv("elysiactl_RETRY_MAX_DELAY", "60.0")))
    
    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = field(default_factory=lambda: int(os.getenv("elysiactl_CB_FAILURE_THRESHOLD", "5")))
    circuit_breaker_recovery_timeout: float = field(default_factory=lambda: float(os.getenv("elysiactl_CB_RECOVERY_TIMEOUT", "30.0")))
    
    # Error tracking
    error_history_limit: int = field(default_factory=lambda: int(os.getenv("elysiactl_ERROR_HISTORY_LIMIT", "100")))
    log_level: str = field(default_factory=lambda: os.getenv("elysiactl_LOG_LEVEL", "INFO"))
```

This phase transforms elysiactl from a basic tool into a production-ready system that can handle enterprise-scale deployments with robust error recovery, comprehensive monitoring, and graceful degradation under failure conditions.