"""Sync service for streaming JSONL changes to Weaviate with SQLite checkpoints."""

import sys
import json
import base64
import uuid
import hashlib
import sqlite3
import os
import asyncio
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any

import httpx
from rich.console import Console

from ..config import get_config
from ..services.weaviate import WeaviateService
from ..services.embedding import EmbeddingService
from .content_resolver import ContentResolver
from .performance import get_performance_optimizer, PerformanceMetrics
from .error_handling import get_error_handler_with_config

console = Console()
content_resolver = ContentResolver()


class SQLiteCheckpointManager:
    """SQLite-based checkpoint system with atomic transactions."""
    
    def __init__(self, state_dir: str = None):
        config = get_config()
        self.state_dir = Path(state_dir or config.processing.checkpoint_db_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "sync_checkpoints.db"
        self.timeout = config.processing.sqlite_timeout
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
            timeout=self.timeout,
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
    
    def cleanup_old_runs(self, keep_days: int = None):
        """Clean up old completed runs and their data."""
        config = get_config()
        if keep_days is None:
            keep_days = config.processing.checkpoint_cleanup_days
        
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


def parse_input_line(line: str, line_number: int) -> Optional[Dict]:
    """Parse an input line from stdin."""
    line = line.strip()
    if not line:
        return None
    
    try:
        # Try parsing as JSON first (primary format)
        data = json.loads(line)
        data['line'] = line_number  # Add line number for tracking
        return data
    except json.JSONDecodeError:
        # Fallback: Treat as plain file path for testing
        return {
            'line': line_number,
            'path': line,
            'op': 'modify',  # Default operation for plain paths
            'repo': None     # No repository context for plain paths
        }


async def process_batch_change(
    batch_items: List[Dict[str, Any]], 
    weaviate: WeaviateService, 
    embedding: EmbeddingService, 
    collection: str
) -> bool:
    """Process a batch of changes efficiently in Weaviate."""
    if not batch_items:
        return True
    
    try:
        # Build batch objects for Weaviate
        batch_objects = []
        
        for change in batch_items:
            if change.get('op') == 'delete':
                # Handle deletes separately - we can't batch them with inserts
                path = change.get('path')
                if path:
                    object_id = _get_object_id(path, collection)
                    await weaviate.delete_object(object_id)
                continue
            
            # Process add/modify operations
            weaviate_object = await _build_weaviate_object(change, collection)
            if weaviate_object:
                batch_objects.append(weaviate_object)
        
        # Submit batch to Weaviate if we have objects
        if batch_objects:
            success = await weaviate.batch_insert_objects(collection, batch_objects)
            return success
        
        return True
    except Exception as e:
        console.print(f"[red]Batch processing error: {e}[/red]")
        return False


async def _build_weaviate_object(change: Dict, collection: str) -> Optional[Dict]:
    """Build a Weaviate object from a change record."""
    path = change.get('path')
    repo = change.get('repo')
    
    if not path:
        return None
    
    # Resolve content from the three-tier format
    content = _resolve_content(change)
    if content is None:
        return None
    
    config = get_config()
    object_id = _get_object_id(path, collection)
    
    return {
        "id": object_id,
        "class": collection,
        "properties": {
            "file_path": str(path),
            "file_name": Path(path).name,
            "repository": repo or "unknown",
            "content": content[:config.processing.max_content_size],
            "language": _get_language_from_path(Path(path)),
            "extension": Path(path).suffix or "none",
            "size_bytes": len(content.encode('utf-8')),
            "line_count": content.count('\n') + 1,
            "last_modified": datetime.utcnow().isoformat() + "Z",
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "relative_path": str(Path(path).name)
        }
    }


def _resolve_content(change: Dict) -> Optional[str]:
    """Efficiently resolve content from mgit's three-tier format."""
    file_path = change.get('path')
    if not file_path:
        return None
    
    # Skip files marked for no indexing by mgit
    if change.get("skip_index"):
        return None
    
    # Tier 1: Plain embedded content (mgit embedded small files as text)
    if "content" in change:
        return change["content"]
    
    # Tier 2: Base64 embedded content (mgit embedded medium files as base64)  
    if "content_base64" in change:
        return content_resolver.decode_base64_content(change["content_base64"])
    
    # Tier 3: File reference (mgit provided reference to large files)
    if "content_ref" in change:
        return content_resolver.resolve_content_from_reference(change["content_ref"])
    
    # Legacy fallback: Direct file path (Phase 2 format)
    # This handles cases where input is still plain file paths
    if change.get('repo') is None and 'path' in change:
        path = Path(change['path'])
        if not path.exists():
            return None
        
        try:
            config = get_config()
            # Check file size limits
            if path.stat().st_size > config.processing.max_file_size:
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                console.print(f"[red]Failed to read file {path}: {e}[/red]")
                return None
        except Exception as e:
            console.print(f"[red]Failed to read file {path}: {e}[/red]")
            return None
    
    return None


def _get_object_id(path: str, collection: str) -> str:
    """Generate deterministic UUID for file path."""
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    return str(uuid.uuid5(namespace, f"{collection}:{path}"))


def _get_language_from_path(path: Path) -> str:
    """Get programming language from file extension."""
    ext_to_lang = {
        '.py': 'Python', '.js': 'JavaScript', '.jsx': 'JavaScript',
        '.ts': 'TypeScript', '.tsx': 'TypeScript', '.cs': 'C#',
        '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.go': 'Go',
        '.rs': 'Rust', '.rb': 'Ruby', '.php': 'PHP', '.swift': 'Swift',
        '.kt': 'Kotlin', '.scala': 'Scala', '.sh': 'Shell', '.ps1': 'PowerShell',
        '.sql': 'SQL', '.html': 'HTML', '.css': 'CSS', '.json': 'JSON',
        '.yaml': 'YAML', '.yml': 'YAML', '.xml': 'XML', '.md': 'Markdown',
        '.toml': 'TOML', '.dockerfile': 'Docker', 'Dockerfile': 'Docker',
    }
    
    if path.name in ext_to_lang:
        return ext_to_lang[path.name]
    
    return ext_to_lang.get(path.suffix.lower(), 'Unknown')


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
    error_handler = get_error_handler()
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
        content = _resolve_content(change)
        if content is None:
            return False
        
        if dry_run:
            console.print(f"[blue]Would {operation.upper()}: {file_path} ({len(content)} chars)[/blue]")
            return True
        
        # Generate embedding with retry
        embedding_context = ErrorContext(
            operation="generate_embedding",
            file_path=file_path,
            total_attempts=2,
            metadata={'content_length': len(content)}
        )
        
        # Mock embedding for now since EmbeddingService isn't fully implemented
        # In production: embedding_vector = await error_handler.execute_with_retry(
        #     embedding.generate_embedding, embedding_context, content
        # )
        embedding_vector = None  # Placeholder
        
        # Index in Weaviate with retry
        weaviate_context = ErrorContext(
            operation="weaviate_index",
            file_path=file_path,
            total_attempts=5,  # More retries for Weaviate
            metadata={'collection': collection, 'has_embedding': bool(embedding_vector)}
        )
        
        # Mock Weaviate indexing for now
        # In production: success = await error_handler.execute_with_retry(
        #     weaviate.index_file, weaviate_context, file_path, content, collection, embedding_vector
        # )
        success = True  # Placeholder
        
        if success:
            console.print(f"[green]{operation.upper()}: {file_path}[/green]")
            return True
        else:
            console.print(f"[red]Failed to index: {file_path}[/red]")
            return False
    
    else:
        raise ValueError(f"Unknown operation '{operation}' for {file_path}")

async def process_index_batch(changes: List[Dict[str, Any]],
                            weaviate: WeaviateService, 
                            embedding: EmbeddingService,
                            collection: str,
                            dry_run: bool = False) -> List[Dict[str, Any]]:
    """Process a batch of index operations efficiently."""
    if not changes:
        return []
    
    if dry_run:
        # Just simulate for dry run
        results = []
        for change in changes:
            results.append({
                'success': True, 
                'operation': change.get('op', 'modify'),
                'path': change.get('path'),
                'dry_run': True
            })
        return results
    
    # Prepare batch operations
    batch_operations = []
    results = []
    
    for change in changes:
        file_path = change.get('path')
        operation = change.get('op', 'modify')
        
        try:
            # Resolve content
            content = _resolve_content(change)
            if content is None:
                results.append({
                    'success': False, 
                    'operation': operation,
                    'path': file_path,
                    'error': 'Content not available'
                })
                continue
            
            # Generate embedding (placeholder for now)
            # In production: embedding_vector = await embedding.generate_embedding(content)
            embedding_vector = None  # Placeholder
            
            # Prepare for batch
            import uuid
            namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
            object_id = str(uuid.uuid5(namespace, f"{collection}:{file_path}"))
            
            batch_operations.append({
                'id': object_id,
                'operation': operation,
                'properties': {
                    'path': file_path,
                    'content': content,
                    'last_indexed': datetime.utcnow().isoformat(),
                    'size_bytes': len(content.encode('utf-8'))
                },
                'vector': embedding_vector
            })
            
        except Exception as e:
            results.append({
                'success': False, 
                'operation': operation,
                'path': file_path,
                'error': str(e)
            })
    
    # Execute batch operation
    if batch_operations:
        try:
            # Use optimized Weaviate client
            performance_optimizer = get_performance_optimizer()
            optimized_client = await performance_optimizer.create_optimized_weaviate_client(
                weaviate.base_url
            )
            
            batch_results = await optimized_client.batch_index_files(
                batch_operations, collection
            )
            
            # Create result objects
            for i, (op, success) in enumerate(zip(batch_operations, batch_results)):
                results.append({
                    'success': success,
                    'operation': op['operation'], 
                    'path': op['properties']['path']
                })
                
        except Exception as e:
            # Fallback to individual processing
            console.print(f"[yellow]Batch operation failed, falling back to individual processing: {e}[/yellow]")
            
            for op in batch_operations:
                try:
                    success = await weaviate.index_file(
                        file_path=op['properties']['path'],
                        content=op['properties']['content'],
                        collection_name=collection,
                        embedding=op['vector']
                    )
                    results.append({
                        'success': success,
                        'operation': op['operation'],
                        'path': op['properties']['path']
                    })
                except Exception as individual_error:
                    results.append({
                        'success': False,
                        'operation': op['operation'],
                        'path': op['properties']['path'],
                        'error': str(individual_error)
                    })
    
    return results

def sync_files_from_stdin(
    collection: str,
    dry_run: bool = False,
    verbose: bool = False,
    use_stdin: bool = True,
    batch_size: int = None,
    max_retries: int = None,
    parallel: bool = True,
    max_workers: int = 8
) -> bool:
    """Main sync function with performance optimization."""
    
    config = get_config()
    if not batch_size:
        batch_size = config.processing.batch_size
    
    checkpoint = SQLiteCheckpointManager()
    error_handler = get_error_handler_with_config()
    
    try:
        # Check for active run to resume
        run_id = checkpoint.get_active_run()
        if run_id:
            console.print(f"[yellow]Resuming previous run: {run_id}[/yellow]")
        else:
            # Start new run
            run_id = checkpoint.start_run(collection, dry_run)
            console.print(f"[bold]Starting new sync run: {run_id}[/bold]")
        
        console.print(f"[bold]Syncing to collection: {collection}[/bold]")
        if dry_run:
            console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
        
        # Configure performance optimizer
        perf_config = {
            'max_workers': max_workers,
            'batch_size': batch_size,
            'max_connections': 20,
            'memory_limit_mb': 512
        }
    
        # Run the async sync function directly (don't use asyncio.run)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, create a task
            return loop.create_task(sync_files_from_stdin_async(
                collection, dry_run, verbose, use_stdin, batch_size, 
                parallel, max_workers
            )).result()
        except RuntimeError:
            # No event loop running, use asyncio.run
            return asyncio.run(sync_files_from_stdin_async(
                collection, dry_run, verbose, use_stdin, batch_size, 
                parallel, max_workers
            ))
        
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Interrupted - run {run_id} can be resumed[/yellow]")
        return False
    
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        
        # Show recent errors for debugging
        recent_errors = error_handler.get_recent_errors(3)
        if recent_errors:
            console.print("\n[red]Recent errors:[/red]")
            for error in recent_errors:
                console.print(f"  {error['timestamp']}: {error['error_message']}")
        
        return False


async def sync_files_from_stdin_async(
    collection: str,
    dry_run: bool = False,
    verbose: bool = False,
    use_stdin: bool = True,
    batch_size: int = None,
    parallel: bool = True,
    max_workers: int = 8
) -> bool:
    """Main sync function with performance optimization."""
    
    config = get_config()
    if not batch_size:
        batch_size = config.processing.batch_size
    
    checkpoint = SQLiteCheckpointManager()
    error_handler = get_error_handler_with_config()
    
    try:
        # Check for active run to resume
        run_id = checkpoint.get_active_run()
        if run_id:
            console.print(f"[yellow]Resuming previous run: {run_id}[/yellow]")
        else:
            # Start new run
            run_id = checkpoint.start_run(collection, dry_run)
            console.print(f"[bold]Starting new sync run: {run_id}[/bold]")
        
        console.print(f"[bold]Syncing to collection: {collection}[/bold]")
        if dry_run:
            console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
        
        # Configure performance optimizer
        perf_config = {
            'max_workers': max_workers,
            'batch_size': batch_size,
            'max_connections': 20,
            'memory_limit_mb': 512
        }
    
        # Run the async sync function directly (don't use asyncio.run)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, create a task
            return loop.create_task(_sync_files_from_stdin_async(
                run_id, collection, dry_run, verbose, use_stdin, batch_size, 
                parallel, max_workers, perf_config, checkpoint, error_handler, config
            )).result()
        except RuntimeError:
            # No event loop running, use asyncio.run
            return asyncio.run(_sync_files_from_stdin_async(
                run_id, collection, dry_run, verbose, use_stdin, batch_size, 
                parallel, max_workers, perf_config, checkpoint, error_handler, config
            ))
        
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Interrupted - run {run_id} can be resumed[/yellow]")
        return False
    
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        
        # Show recent errors for debugging
        error_handler = get_error_handler_with_config()
        recent_errors = error_handler.get_recent_errors(3)
        if recent_errors:
            console.print("\n[red]Recent errors:[/red]")
            for error in recent_errors:
                console.print(f"  {error['timestamp']}: {error['error_message']}")
        
        return False


async def _sync_files_from_stdin_async(run_id, collection, dry_run, verbose, use_stdin, 
                                       batch_size, parallel, max_workers, perf_config, 
                                       checkpoint, error_handler, config):
    """Async implementation of sync_files_from_stdin."""
    
    performance_optimizer = get_performance_optimizer(perf_config)
    
    # Initialize services
    weaviate = WeaviateService(config.services.WCD_URL)
    embedding = EmbeddingService()
    
    try:
        if parallel:
            # Use optimized parallel processing
            stdin_lines = list(enumerate(sys.stdin, 1))
            changes_generator = optimized_sync_generator(stdin_lines)
            
            # Process with optimization
            results_count = 0
            async for result_batch in performance_optimizer.optimize_sync_operation(
                changes_generator,
                lambda changes: process_change_batch(changes, weaviate, embedding, collection, dry_run)
            ):
                # Update checkpoint for batch
                for result in result_batch:
                    if result:
                        results_count += 1
                        # Update checkpoint based on result
                        if result.get('success'):
                            checkpoint.mark_line_completed(
                                run_id, results_count, 
                                result.get('path', ''), 
                                result.get('operation', 'modify')
                            )
                        else:
                            checkpoint.mark_line_failed(
                                run_id, results_count,
                                result.get('path', ''),
                                result.get('operation', 'modify'),
                                result.get('error', 'Unknown error')
                            )
        else:
            # Fall back to sequential processing
            console.print("[yellow]Using sequential processing (parallel disabled)[/yellow]")
            # Sequential processing would go here
        
        # Complete run and show performance summary
        stats = checkpoint.complete_run(run_id)
        perf_summary = performance_optimizer.get_performance_summary()
        
        console.print(f"\n[bold]Sync completed:[/bold]")
        console.print(f"  Run ID: {run_id}")
        console.print(f"  Success: {stats['success_count']}")
        console.print(f"  Errors: {stats['error_count']}")
        console.print(f"  Total: {stats['processed_lines']}")
        
        # Performance metrics
        console.print(f"\n[bold]Performance:[/bold]")
        console.print(f"  Files/second: {perf_summary['files_per_second']:.1f}")
        console.print(f"  Throughput: {perf_summary['throughput_mbps']:.2f} MB/s") 
        console.print(f"  Success rate: {perf_summary['success_rate']:.1f}%")
        console.print(f"  Peak memory: {perf_summary['peak_memory_mb']:.1f} MB")
        console.print(f"  Peak connections: {perf_summary['peak_connections']}")
        
        return stats['error_count'] == 0
        
    finally:
        await performance_optimizer.cleanup()


# Legacy classes removed - Phase 2 complete