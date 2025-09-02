# Phase 2: Checkpoint and Recovery System

## Objective

Replace simple file-based checkpoints with SQLite database for atomic transactions, batch processing, and resilient failure recovery with detailed error tracking.

## Problem Summary

Phase 1's append-only checkpoint file works for basic scenarios but cannot handle batch failures, retry logic, or atomic operations. At enterprise scale with thousands of files, we need transactional checkpoint management that can recover from any failure scenario without data loss or corruption.

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/services/sync.py` (REPLACE StreamCheckpoint)

**Replace existing StreamCheckpoint class:**

```python
import sqlite3
import json
import os
import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

class SQLiteCheckpointManager:
    """SQLite-based checkpoint system with atomic transactions."""
    
    def __init__(self, state_dir: str = "/var/lib/elysiactl"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "sync_checkpoints.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize checkpoint database with WAL mode for concurrent access."""
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            
            # Main checkpoint tables
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sync_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    input_source TEXT,
                    total_lines INTEGER DEFAULT 0,
                    processed_lines INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    collection_name TEXT,
                    dry_run BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    changeset_info TEXT
                );
                
                CREATE TABLE IF NOT EXISTS completed_lines (
                    run_id TEXT,
                    line_number INTEGER,
                    file_path TEXT,
                    operation TEXT,
                    repository TEXT,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms INTEGER,
                    PRIMARY KEY (run_id, line_number),
                    FOREIGN KEY (run_id) REFERENCES sync_runs(run_id)
                );
                
                CREATE TABLE IF NOT EXISTS failed_lines (
                    run_id TEXT,
                    line_number INTEGER,
                    file_path TEXT,
                    operation TEXT,
                    repository TEXT,
                    error_message TEXT,
                    payload TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (run_id, line_number),
                    FOREIGN KEY (run_id) REFERENCES sync_runs(run_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_completed_lines_run ON completed_lines(run_id);
                CREATE INDEX IF NOT EXISTS idx_failed_lines_run ON failed_lines(run_id);
                CREATE INDEX IF NOT EXISTS idx_failed_retry ON failed_lines(retry_count, last_attempt);
            """)
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def start_run(self, collection_name: str, dry_run: bool = False, input_source: str = "stdin") -> str:
        """Start a new sync run and return run_id."""
        run_id = f"sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO sync_runs (run_id, collection_name, dry_run, input_source)
                VALUES (?, ?, ?, ?)
            """, (run_id, collection_name, dry_run, input_source))
        
        return run_id
    
    def get_active_run(self) -> Optional[str]:
        """Get the most recent active run ID."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT run_id FROM sync_runs 
                WHERE status = 'running'
                ORDER BY started_at DESC
                LIMIT 1
            """).fetchone()
            return row['run_id'] if row else None
    
    def is_line_completed(self, run_id: str, line_number: int) -> bool:
        """Check if a line was already completed successfully."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT 1 FROM completed_lines 
                WHERE run_id = ? AND line_number = ?
            """, (run_id, line_number)).fetchone()
            return bool(row)
    
    def get_failed_lines(self, run_id: str, max_retries: int = 3) -> List[sqlite3.Row]:
        """Get failed lines that should be retried."""
        with self._get_connection() as conn:
            return conn.execute("""
                SELECT line_number, file_path, operation, repository, payload, retry_count, error_message
                FROM failed_lines 
                WHERE run_id = ? AND retry_count < ?
                ORDER BY line_number
            """, (run_id, max_retries)).fetchall()
    
    def store_changeset(self, run_id: str, changeset_data: Dict[str, Any]):
        """Store mgit changeset information for the run."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sync_runs 
                SET changeset_info = ?
                WHERE run_id = ?
            """, (json.dumps(changeset_data), run_id))
    
    def mark_line_completed(
        self, 
        run_id: str, 
        line_number: int, 
        file_path: str, 
        operation: str,
        repository: str = "",
        processing_time_ms: int = 0
    ):
        """Mark a line as successfully completed."""
        with self._get_connection() as conn:
            # Remove from failed if exists
            conn.execute("""
                DELETE FROM failed_lines 
                WHERE run_id = ? AND line_number = ?
            """, (run_id, line_number))
            
            # Add to completed
            conn.execute("""
                INSERT OR REPLACE INTO completed_lines 
                (run_id, line_number, file_path, operation, repository, processing_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (run_id, line_number, file_path, operation, repository, processing_time_ms))
            
            # Update run statistics
            conn.execute("""
                UPDATE sync_runs 
                SET success_count = success_count + 1,
                    processed_lines = processed_lines + 1
                WHERE run_id = ?
            """, (run_id,))
    
    def mark_line_failed(
        self, 
        run_id: str, 
        line_number: int, 
        file_path: str, 
        operation: str,
        error_message: str,
        repository: str = "",
        payload: str = ""
    ):
        """Mark a line as failed with error details."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO failed_lines
                (run_id, line_number, file_path, operation, repository, error_message, payload, retry_count, last_attempt)
                VALUES (?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT retry_count + 1 FROM failed_lines WHERE run_id = ? AND line_number = ?), 1),
                    CURRENT_TIMESTAMP)
            """, (run_id, line_number, file_path, operation, repository, error_message, payload, run_id, line_number))
            
            # Update run statistics
            conn.execute("""
                UPDATE sync_runs 
                SET error_count = error_count + 1,
                    processed_lines = processed_lines + 1
                WHERE run_id = ?
            """, (run_id,))
    
    def complete_run(self, run_id: str) -> Dict[str, int]:
        """Mark run as completed and return statistics."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sync_runs 
                SET completed_at = CURRENT_TIMESTAMP,
                    status = 'completed'
                WHERE run_id = ?
            """, (run_id,))
            
            # Get final statistics
            row = conn.execute("""
                SELECT success_count, error_count, processed_lines
                FROM sync_runs 
                WHERE run_id = ?
            """, (run_id,)).fetchone()
            
            return {
                'success_count': row['success_count'],
                'error_count': row['error_count'], 
                'processed_lines': row['processed_lines']
            }
    
    def cleanup_old_runs(self, keep_days: int = 7):
        """Clean up old completed runs and their data."""
        cutoff = datetime.utcnow() - timedelta(days=keep_days)
        
        with self._get_connection() as conn:
            # Get old run IDs
            old_runs = conn.execute("""
                SELECT run_id FROM sync_runs 
                WHERE completed_at < ? OR (status = 'running' AND started_at < ?)
            """, (cutoff, cutoff)).fetchall()
            
            for row in old_runs:
                run_id = row['run_id']
                
                # Delete associated data
                conn.execute("DELETE FROM completed_lines WHERE run_id = ?", (run_id,))
                conn.execute("DELETE FROM failed_lines WHERE run_id = ?", (run_id,))
                conn.execute("DELETE FROM sync_runs WHERE run_id = ?", (run_id,))
            
            # VACUUM to reclaim space
            conn.execute("VACUUM")
    
    def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a sync run."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM sync_runs WHERE run_id = ?
            """, (run_id,)).fetchone()
            
            if not row:
                return None
            
            return dict(row)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all sync runs."""
        with self._get_connection() as conn:
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_runs,
                    COUNT(CASE WHEN status = 'running' THEN 1 END) as active_runs,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_runs,
                    SUM(success_count) as total_success,
                    SUM(error_count) as total_errors,
                    MAX(started_at) as last_run
                FROM sync_runs
            """).fetchone()
            
            return dict(stats)
```

**Update sync_files_from_stdin function:**

```python
def sync_files_from_stdin(
    collection: str,
    dry_run: bool = False,
    verbose: bool = False,
    use_stdin: bool = True,
    batch_size: int = None,
    max_retries: int = 3
) -> bool:
    """Main sync function with SQLite checkpoint management."""
    
    if not batch_size:
        batch_size = get_config().processing.batch_size
    
    checkpoint = SQLiteCheckpointManager()
    config = get_config()
    
    # Check for active run to resume
    run_id = checkpoint.get_active_run()
    if run_id:
        console.print(f"[yellow]Resuming previous run: {run_id}[/yellow]")
        
        # Process any failed lines that can be retried
        failed_lines = checkpoint.get_failed_lines(run_id, max_retries)
        if failed_lines:
            console.print(f"[blue]Found {len(failed_lines)} failed items to retry[/blue]")
    else:
        # Start new run
        run_id = checkpoint.start_run(collection, dry_run)
        console.print(f"[bold]Starting new sync run: {run_id}[/bold]")
    
    console.print(f"[bold]Syncing to collection: {collection}[/bold]")
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
    
    # Initialize services
    weaviate = WeaviateService(config.services.WCD_URL)
    embedding = EmbeddingService()
    
    batch_items = []
    batch_line_numbers = []
    
    def process_batch():
        """Process a batch of changes with atomic checkpoint."""
        nonlocal batch_items, batch_line_numbers
        
        if not batch_items:
            return
        
        batch_start_time = datetime.utcnow()
        batch_success_count = 0
        
        # Process batch in Weaviate for efficiency
        try:
            # Build batch request
            weaviate_batch = []
            for change in batch_items:
                if change.get('op') == 'delete':
                    continue  # Handle deletes separately
                weaviate_batch.append(change)
            
            # Submit batch to Weaviate if not empty
            if weaviate_batch and not dry_run:
                batch_success = asyncio.run(process_batch_change(
                    weaviate_batch, weaviate, embedding, collection
                ))
            else:
                batch_success = True
            
            # Mark individual items based on batch result
            for i, (change, line_number) in enumerate(zip(batch_items, batch_line_numbers)):
                item_start_time = datetime.utcnow()
                repository = change.get('repo', '')
                
                try:
                    if batch_success or change.get('op') == 'delete':
                        processing_time = int((datetime.utcnow() - item_start_time).total_seconds() * 1000)
                        
                        checkpoint.mark_line_completed(
                            run_id, line_number, change.get('path', ''), 
                            change.get('op', 'modify'), repository, processing_time
                        )
                        batch_success_count += 1
                    else:
                        checkpoint.mark_line_failed(
                            run_id, line_number, change.get('path', ''), 
                            change.get('op', 'modify'), "Batch processing failed",
                            repository, json.dumps(change)
                        )
                    
                except Exception as e:
                    checkpoint.mark_line_failed(
                        run_id, line_number, change.get('path', ''), 
                        change.get('op', 'modify'), str(e), repository,
                        json.dumps(change)
                    )
                    
        except Exception as e:
            # Mark entire batch as failed
            for change, line_number in zip(batch_items, batch_line_numbers):
                repository = change.get('repo', '')
                checkpoint.mark_line_failed(
                    run_id, line_number, change.get('path', ''), 
                    change.get('op', 'modify'), f"Batch error: {str(e)}", repository,
                    json.dumps(change)
                )
        
        batch_time = (datetime.utcnow() - batch_start_time).total_seconds()
        if verbose:
            console.print(f"[dim]Batch completed: {batch_success_count}/{len(batch_items)} success in {batch_time:.2f}s[/dim]")
        
        batch_items.clear()
        batch_line_numbers.clear()
    
    try:
        # First, retry any failed lines from previous run
        if run_id:
            failed_lines = checkpoint.get_failed_lines(run_id, max_retries)
            for failed_line in failed_lines:
                if failed_line['payload']:
                    change = json.loads(failed_line['payload'])
                    batch_items.append(change)
                    batch_line_numbers.append(failed_line['line_number'])
                    
                    if len(batch_items) >= batch_size:
                        process_batch()
        
        # Process new input from stdin
        for line_number, line in enumerate(sys.stdin, 1):
            # Skip if already completed
            if checkpoint.is_line_completed(run_id, line_number):
                if verbose:
                    console.print(f"[dim]Skipping completed line {line_number}[/dim]")
                continue
            
            # Parse input line
            change = parse_input_line(line, line_number)
            if not change:
                continue
            
            # Handle mgit's special changeset records
            if 'new_changeset' in change:
                # Store changeset info and skip processing as a file
                checkpoint.store_changeset(run_id, change['new_changeset'])
                checkpoint.mark_line_completed(
                    run_id, line_number, 'changeset', 'changeset', 
                    change.get('repo', ''), 0
                )
                if verbose:
                    console.print(f"[dim]Stored changeset from {change.get('repo', 'unknown')} line {line_number}[/dim]")
                continue
            
            batch_items.append(change)
            batch_line_numbers.append(line_number)
            
            # Process batch when full
            if len(batch_items) >= batch_size:
                process_batch()
        
        # Process final partial batch
        process_batch()
        
        # Complete the run
        stats = checkpoint.complete_run(run_id)
        
        console.print(f"\n[bold]Sync completed:[/bold]")
        console.print(f"  Run ID: {run_id}")
        console.print(f"  Success: {stats['success_count']}")
        console.print(f"  Errors: {stats['error_count']}")
        console.print(f"  Total: {stats['processed_lines']}")
        
        # Clean up old runs
        checkpoint.cleanup_old_runs()
        
        return stats['error_count'] == 0
        
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Interrupted - run {run_id} can be resumed[/yellow]")
        return False
    
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        return False

async def process_batch_change(
    batch_items: List[Dict[str, Any]], 
    weaviate: WeaviateService, 
    embedding: EmbeddingService, 
    collection: str
) -> bool:
    """Process a batch of changes efficiently in Weaviate.
    
    This function needs to be implemented to handle batch API calls
    instead of processing items individually.
    """
    # Implementation needed: Build Weaviate batch request
    # and submit all changes at once for efficiency
    pass
```

### File: `/opt/elysiactl/src/elysiactl/commands/index.py` (ADD STATUS COMMAND)

**Add status command to index app:**

```python
@app.command()
def status(
    run_id: Annotated[Optional[str], typer.Option("--run-id", help="Show status for specific run")] = None,
    summary: Annotated[bool, typer.Option("--summary", help="Show summary of all runs")] = False,
    failed: Annotated[bool, typer.Option("--failed", help="Show failed items from last run")] = False,
):
    """Show sync status and checkpoint information."""
    from ..services.sync import SQLiteCheckpointManager
    
    checkpoint = SQLiteCheckpointManager()
    
    if summary:
        # Show overall summary
        summary_data = checkpoint.get_summary()
        console.print("\n[bold]Sync Summary:[/bold]")
        console.print(f"  Total runs: {summary_data['total_runs']}")
        console.print(f"  Active runs: {summary_data['active_runs']}")
        console.print(f"  Completed runs: {summary_data['completed_runs']}")
        console.print(f"  Total success: {summary_data['total_success']}")
        console.print(f"  Total errors: {summary_data['total_errors']}")
        console.print(f"  Last run: {summary_data['last_run']}")
        return
    
    # Get target run ID
    if not run_id:
        run_id = checkpoint.get_active_run()
        if not run_id:
            console.print("[yellow]No active runs found[/yellow]")
            return
    
    # Show run status
    status_data = checkpoint.get_run_status(run_id)
    if not status_data:
        console.print(f"[red]Run {run_id} not found[/red]")
        return
    
    console.print(f"\n[bold]Run {run_id}:[/bold]")
    console.print(f"  Collection: {status_data['collection_name']}")
    console.print(f"  Started: {status_data['started_at']}")
    console.print(f"  Status: {status_data['status']}")
    console.print(f"  Processed: {status_data['processed_lines']}")
    console.print(f"  Success: {status_data['success_count']}")
    console.print(f"  Errors: {status_data['error_count']}")
    
    if failed:
        failed_lines = checkpoint.get_failed_lines(run_id)
        if failed_lines:
            console.print(f"\n[red]Failed items ({len(failed_lines)}):[/red]")
            for failed_line in failed_lines[:10]:  # Show first 10
                console.print(f"  Line {failed_line['line_number']}: {failed_line['file_path']} - {failed_line['error_message']}")
            if len(failed_lines) > 10:
                console.print(f"  ... and {len(failed_lines) - 10} more")
```

## Agent Workflow

1. **Database Schema Setup:**
   - Replace StreamCheckpoint with SQLiteCheckpointManager
   - Create database initialization with proper indexes
   - Set up WAL mode for concurrent access

2. **Core Functionality:**
   - Implement run management (start, complete, cleanup)
   - Add batch processing with atomic checkpoints
   - Implement retry logic for failed items
   - Add detailed error tracking and statistics

3. **Command Integration:**
   - Update sync command to use batch processing
   - Add status command for checkpoint inspection
   - Add resume functionality for interrupted runs

4. **Performance Optimization:**
   - Implement proper database connection management
   - Add batch processing to reduce I/O overhead
   - Create efficient indexes for checkpoint queries

## Testing

### Test new checkpoint system:
```bash
# Start sync and interrupt after a few items
echo -e "file1.py\nfile2.py\nfile3.py\nfile4.py\nfile5.py" | uv run elysiactl index sync --stdin --verbose
# Interrupt with Ctrl+C, then resume
echo -e "file1.py\nfile2.py\nfile3.py\nfile4.py\nfile5.py" | uv run elysiactl index sync --stdin --verbose
```

### Test status commands:
```bash
# Show summary of all runs
uv run elysiactl index status --summary

# Show status of active run
uv run elysiactl index status

# Show failed items
uv run elysiactl index status --failed
```

### Test batch processing:
```bash
# Test with custom batch size
find /opt/elysiactl -name "*.py" | head -20 | uv run elysiactl index sync --stdin --verbose

# Test with mgit-style input including changeset records
echo '{"line": 1, "path": "src/file1.py", "op": "modify", "repo": "ServiceA"}
{"line": 2, "path": "src/file2.py", "op": "add", "repo": "ServiceA"}  
{"line": 999, "repo": "ServiceA", "new_changeset": {"commit": "abc123", "parent": "def456"}}' | uv run elysiactl index sync --stdin --verbose
```

### Test database integrity:
```bash
# Verify checkpoint database exists and has data
sqlite3 /var/lib/elysiactl/sync_checkpoints.db "SELECT COUNT(*) FROM sync_runs;"
sqlite3 /var/lib/elysiactl/sync_checkpoints.db ".tables"

# Check changeset storage
sqlite3 /var/lib/elysiactl/sync_checkpoints.db "SELECT run_id, changeset_info FROM sync_runs WHERE changeset_info IS NOT NULL;"

# Check repository tracking
sqlite3 /var/lib/elysiactl/sync_checkpoints.db "SELECT repository, COUNT(*) FROM completed_lines GROUP BY repository;"
```

### Test retry logic:
```bash
# Create failing scenario and verify retry behavior
echo '{"path": "/nonexistent/file.py", "op": "add"}' | uv run elysiactl index sync --stdin --verbose
uv run elysiactl index status --failed
```

## Success Criteria

- [ ] SQLite checkpoint database created at `/var/lib/elysiactl/sync_checkpoints.db`
- [ ] Changeset tracking: `changeset_info` column stores mgit changeset JSON
- [ ] Repository tracking: `repository` column populated from mgit's "repo" field
- [ ] mgit special records: Detect and store `new_changeset` records without processing as files
- [ ] Actual batch processing: Accumulate batch_size changes and process as Weaviate batch
- [ ] Batch processing works with configurable batch sizes
- [ ] Interrupted sync runs can be resumed from exact position
- [ ] Failed items are tracked with error messages and retry counts
- [ ] `elysiactl index status` shows current run information
- [ ] `elysiactl index status --summary` shows overall statistics
- [ ] `elysiactl index status --failed` shows failed items
- [ ] Database automatically cleans up old runs (7 days default)
- [ ] Concurrent access works with WAL mode
- [ ] Atomic transactions prevent partial checkpoint corruption
- [ ] Retry logic processes failed items up to max_retries limit
- [ ] Run completion updates statistics and status correctly
- [ ] All test commands execute without errors
- [ ] Changeset records properly stored and retrieved
- [ ] Repository information tracked across completed and failed lines
- [ ] Batch API efficiency: Multiple changes submitted in single Weaviate request

## Configuration Changes

Add checkpoint-specific configuration to existing config:

**File: `/opt/elysiactl/src/elysiactl/config.py`**

```python
@dataclass
class ProcessingConfig:
    # ... existing fields ...
    
    # Checkpoint system settings
    checkpoint_db_dir: str = field(default_factory=lambda: os.getenv("elysiactl_CHECKPOINT_DB_DIR", "/var/lib/elysiactl"))
    max_retry_attempts: int = field(default_factory=lambda: int(os.getenv("elysiactl_MAX_RETRY_ATTEMPTS", "3")))
    checkpoint_cleanup_days: int = field(default_factory=lambda: int(os.getenv("elysiactl_CHECKPOINT_CLEANUP_DAYS", "7")))
    sqlite_timeout: float = field(default_factory=lambda: float(os.getenv("elysiactl_SQLITE_TIMEOUT", "30.0")))
```

This phase transforms the sync system from simple append-only checkpoints to enterprise-grade transactional recovery. The SQLite backend provides atomic operations, detailed error tracking, and efficient resume capabilities that scale to thousands of files while maintaining data integrity under any failure scenario.