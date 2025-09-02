# Phase 1: Basic stdin Stream Consumption

## Objective

Implement `elysiactl index sync --stdin` command that consumes mgit JSONL output with smart three-tier content strategy and line-number checkpointing for resumable operations.

## Problem Summary

The elysiactl tool currently only supports batch indexing of entire directories. We need Unix-pipe compatibility to consume mgit's structured output for selective synchronization, while maintaining the ability to recover from failures without losing progress.

**Key Integration**: This phase consumes output from mgit (multi-repository Git tool), not direct Git commands. mgit produces JSONL with smart content embedding based on file size.

## mgit Integration Architecture

**Pipeline**: `mgit diff /opt/pdi/Enterprise --format=jsonl | elysiactl index sync --stdin`

**mgit Output Format**: JSONL with smart three-tier content strategy:
```jsonl
{"line": 1, "repo": "ServiceA", "op": "modify", "path": "src/main.py", "content": "...small file content..."}
{"line": 2, "repo": "ServiceB", "op": "add", "path": "config.json", "content_base64": "...medium file base64..."}
{"line": 3, "repo": "ServiceC", "op": "add", "path": "large.dat", "content_ref": "/opt/pdi/Enterprise/ServiceC/large.dat", "size": 5242880}
{"line": 4, "repo": "ServiceD", "op": "add", "path": "image.png", "content_ref": "/opt/pdi/Enterprise/ServiceD/image.png", "skip_index": true}
```

**Content Strategy**:
- **Tier 1** (0-10KB): Plain text in `content` field for fast processing
- **Tier 2** (10-100KB): Base64 in `content_base64` field to reduce I/O operations  
- **Tier 3** (100KB+): File path in `content_ref` field to avoid memory issues
- **Skip Flag**: `skip_index: true` for binary/huge files that shouldn't be indexed

**Multi-Repository Context**: Each entry includes `repo` field for proper namespace isolation and deterministic UUID generation per repository.

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/commands/index.py`

**Add sync command to existing index app:**

```python
@app.command()
def sync(
    stdin: Annotated[bool, typer.Option("--stdin", help="Read file paths from standard input")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be changed without modifying Weaviate")] = False,
    collection: Annotated[str, typer.Option("--collection", help="Target collection name")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed progress for each file")] = False,
):
    """Synchronize files from stdin or detect changes."""
    from ..services.sync import sync_files_from_stdin
    
    if not collection:
        collection = get_config().collections.default_source_collection
    
    return sync_files_from_stdin(
        collection=collection,
        dry_run=dry_run,
        verbose=verbose,
        use_stdin=stdin or True  # Default to stdin if no other input specified
    )
```

### File: `/opt/elysiactl/src/elysiactl/services/sync.py` (NEW)

**Create sync service module:**

```python
"""Synchronization service for incremental file indexing."""

import sys
import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Iterator, Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, TaskID

from ..config import get_config
from .weaviate import WeaviateService
from .vector_embedding import EmbeddingService

console = Console()

class StreamCheckpoint:
    """Handle line-by-line checkpoint recovery for stdin streams."""
    
    def __init__(self, state_dir: str = "/tmp/elysiactl"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        self.checkpoint_file = self.state_dir / "sync_checkpoint.txt"
        self.completed_lines = self._load_completed_lines()
    
    def _load_completed_lines(self) -> set[int]:
        """Load completed line numbers from checkpoint file."""
        if not self.checkpoint_file.exists():
            return set()
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                return set(int(line.strip()) for line in f if line.strip().isdigit())
        except (IOError, ValueError):
            console.print("[yellow]Warning: Corrupted checkpoint file, starting fresh[/yellow]")
            return set()
    
    def mark_completed(self, line_number: int):
        """Mark a line as completed - append-only for crash safety."""
        with open(self.checkpoint_file, 'a') as f:
            f.write(f"{line_number}\n")
        self.completed_lines.add(line_number)
    
    def is_completed(self, line_number: int) -> bool:
        """Check if line was already processed."""
        return line_number in self.completed_lines
    
    def clear(self):
        """Clear checkpoint on successful completion."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        self.completed_lines.clear()

def parse_input_line(line: str, line_number: int) -> Optional[Dict[str, Any]]:
    """Parse mgit JSONL output - primary format with fallback to plain paths."""
    line = line.strip()
    if not line:
        return None
    
    # Primary: mgit JSONL format
    try:
        data = json.loads(line)
        # Ensure line number is set for checkpointing
        if 'line' not in data:
            data['line'] = line_number
        return data
    except json.JSONDecodeError:
        # Fallback: Plain file path for testing/debugging
        return {
            'line': line_number,
            'path': line,
            'op': 'modify',  # Default operation for plain paths
            'repo': None     # No repository context for plain paths
        }

def resolve_file_content(change: Dict[str, Any]) -> Optional[str]:
    """Resolve file content using smart three-tier strategy from mgit output."""
    file_path = change.get('path')
    if not file_path:
        return None
    
    # Check skip_index flag for binary/huge files
    if change.get('skip_index', False):
        console.print(f"[yellow]Skipping non-indexable file: {file_path}[/yellow]")
        return None
    
    # Tier 1: Plain text content (0-10KB) - directly embedded
    if 'content' in change:
        return change['content']
    
    # Tier 2: Base64 content (10-100KB) - embedded to reduce I/O
    if 'content_base64' in change:
        import base64
        try:
            return base64.b64decode(change['content_base64']).decode('utf-8')
        except Exception as e:
            console.print(f"[red]Failed to decode base64 for {file_path}: {e}[/red]")
            return None
    
    # Tier 3: File reference (100KB+) - read from mgit-provided path
    if 'content_ref' in change:
        content_ref_path = change['content_ref']
        try:
            ref_path = Path(content_ref_path)
            if not ref_path.exists():
                console.print(f"[red]Content reference not found: {content_ref_path}[/red]")
                return None
            
            # Verify size limits before reading
            file_size = ref_path.stat().st_size
            config = get_config()
            if file_size > config.processing.max_file_size:
                console.print(f"[yellow]File too large, skipping: {content_ref_path} ({file_size} bytes)[/yellow]")
                return None
            
            with open(ref_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
        except Exception as e:
            console.print(f"[red]Failed to read content_ref {content_ref_path}: {e}[/red]")
            return None
    
    # Fallback: Try to read from original path (for plain path testing)
    if change.get('repo') is None:  # Only for non-mgit input
        try:
            path = Path(file_path)
            if not path.exists():
                console.print(f"[yellow]File not found: {file_path}[/yellow]")
                return None
            
            # Check file size limits
            config = get_config()
            if path.stat().st_size > config.processing.max_file_size:
                console.print(f"[yellow]File too large, skipping: {file_path}[/yellow]")
                return None
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            console.print(f"[red]Failed to read {file_path}: {e}[/red]")
            return None
    
    console.print(f"[yellow]No content available for: {file_path}[/yellow]")
    return None

async def process_single_change(
    change: Dict[str, Any], 
    weaviate: WeaviateService, 
    embedding: EmbeddingService,
    collection: str,
    dry_run: bool = False
) -> bool:
    """Process a single file change from mgit output."""
    operation = change.get('op', 'modify')
    file_path = change.get('path')
    repo_name = change.get('repo')  # Repository context from mgit
    
    if not file_path:
        console.print(f"[red]Missing path in change: {change}[/red]")
        return False
    
    try:
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
                repo_prefix = f"[{repo_name}] " if repo_name else ""
                console.print(f"[blue]Would {operation.upper()}: {repo_prefix}{file_path} ({len(content)} chars)[/blue]")
                return True
            
            # Generate embedding
            embedding_vector = embedding.generate_embedding(content)
            
            # Index in Weaviate with repository context
            success = await weaviate.index_file(
                file_path=file_path,
                content=content,
                collection_name=collection,
                embedding=embedding_vector,
                repository=repo_name
            )
            
            if success:
                repo_prefix = f"[{repo_name}] " if repo_name else ""
                console.print(f"[green]{operation.upper()}: {repo_prefix}{file_path}[/green]")
                return True
            else:
                repo_prefix = f"[{repo_name}] " if repo_name else ""
                console.print(f"[red]Failed to index: {repo_prefix}{file_path}[/red]")
                return False
        
        else:
            console.print(f"[yellow]Unknown operation '{operation}' for {file_path}[/yellow]")
            return False
    
    except Exception as e:
        console.print(f"[red]Error processing {file_path}: {e}[/red]")
        return False

def sync_files_from_stdin(
    collection: str,
    dry_run: bool = False,
    verbose: bool = False,
    use_stdin: bool = True
) -> bool:
    """Main sync function that processes stdin stream."""
    
    checkpoint = StreamCheckpoint()
    config = get_config()
    
    # Initialize services
    weaviate = WeaviateService(config.services.WCD_URL)
    embedding = EmbeddingService()
    
    console.print(f"[bold]Syncing to collection: {collection}[/bold]")
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")
    
    processed_count = 0
    success_count = 0
    error_count = 0
    
    try:
        # Process stdin line by line
        for line_number, line in enumerate(sys.stdin, 1):
            # Skip if already completed
            if checkpoint.is_completed(line_number):
                if verbose:
                    console.print(f"[dim]Skipping completed line {line_number}[/dim]")
                continue
            
            # Parse input line
            change = parse_input_line(line, line_number)
            if not change:
                continue
            
            processed_count += 1
            
            # Process the change
            success = asyncio.run(process_single_change(
                change, weaviate, embedding, collection, dry_run
            ))
            
            if success:
                success_count += 1
                # Mark as completed
                checkpoint.mark_completed(line_number)
            else:
                error_count += 1
                # Don't mark failed items as completed for retry
            
            if verbose:
                console.print(f"[dim]Processed line {line_number}: {'✓' if success else '✗'}[/dim]")
    
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Interrupted after processing {processed_count} items[/yellow]")
        console.print(f"[dim]Resume with same command - checkpoint saved at line {processed_count + 1}[/dim]")
        return False
    
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        return False
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Processed: {processed_count} items")
    console.print(f"  Success: {success_count}")
    console.print(f"  Errors: {error_count}")
    
    if error_count == 0:
        checkpoint.clear()
        console.print("[green]Sync completed successfully[/green]")
        return True
    else:
        console.print(f"[yellow]Sync completed with {error_count} errors - checkpoint preserved[/yellow]")
        return False
```

### File: `/opt/elysiactl/src/elysiactl/services/weaviate.py` (MODIFICATIONS)

**Add async index_file method:**

```python
# Add to existing WeaviateService class
async def index_file(
    self, 
    file_path: str, 
    content: str, 
    collection_name: str,
    embedding: Optional[List[float]] = None,
    repository: Optional[str] = None
) -> bool:
    """Index a single file with deterministic UUID and repository context."""
    import uuid
    from urllib.parse import urljoin
    from datetime import datetime
    
    try:
        # Generate deterministic UUID from repo + file path
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # URL namespace
        unique_key = f"{collection_name}:{repository}:{file_path}" if repository else f"{collection_name}:{file_path}"
        object_id = str(uuid.uuid5(namespace, unique_key))
        
        # Prepare object data with repository context
        data_object = {
            "path": file_path,
            "content": content,
            "repository": repository,
            "last_indexed": datetime.utcnow().isoformat(),
            "size_bytes": len(content.encode('utf-8'))
        }
        
        # Use PUT for upsert behavior (create or update)
        url = urljoin(self.base_url, f"objects/{collection_name}/{object_id}")
        
        payload = {
            "class": collection_name,
            "id": object_id,
            "properties": data_object
        }
        
        if embedding:
            payload["vector"] = embedding
        
        response = requests.put(url, json=payload, timeout=30)
        response.raise_for_status()
        
        return True
        
    except Exception as e:
        console.print(f"[red]Failed to index {file_path}: {e}[/red]")
        return False
```

## Agent Workflow

1. **Setup Phase:**
   - Create `/opt/elysiactl/src/elysiactl/services/sync.py` with complete implementation
   - Add sync command to existing index app in `index.py`
   - Add async `index_file` method to `WeaviateService` class

2. **Core Implementation:**
   - Implement `StreamCheckpoint` class for line-based recovery
   - Implement `parse_input_line` for JSONL/plain path support
   - Implement `resolve_file_content` for multi-tier content strategy
   - Implement `process_single_change` for individual file operations

3. **Integration:**
   - Add sync command registration to index typer app
   - Ensure proper error handling and progress reporting
   - Add proper async support for Weaviate operations

4. **Testing Phase:**
   - Test with simple file paths
   - Test with JSONL format
   - Test checkpoint recovery
   - Verify dry-run functionality

## Testing

### Primary: mgit integration (recommended pipeline):
```bash
# Full multi-repository diff 
mgit diff /opt/pdi/Enterprise --format=jsonl | uv run elysiactl index sync --stdin --dry-run

# Specific repositories
mgit diff /opt/pdi/Enterprise --repos=ServiceA,ServiceB --format=jsonl | uv run elysiactl index sync --stdin

# Since last commit with checkpointing
mgit diff /opt/pdi/Enterprise --since=HEAD~1 --format=jsonl | uv run elysiactl index sync --stdin --verbose
```

### mgit JSONL format examples:
```bash
# Small file (Tier 1: plain text)
echo '{"line": 1, "repo": "ServiceA", "op": "modify", "path": "src/main.py", "content": "print(\"hello\")"}' | uv run elysiactl index sync --stdin --dry-run

# Medium file (Tier 2: base64)
echo '{"line": 2, "repo": "ServiceB", "op": "add", "path": "config.json", "content_base64": "ewogICJuYW1lIjogInRlc3QiCn0K"}' | uv run elysiactl index sync --stdin --dry-run

# Large file (Tier 3: file reference)
echo '{"line": 3, "repo": "ServiceC", "op": "add", "path": "large.dat", "content_ref": "/opt/pdi/Enterprise/ServiceC/large.dat", "size": 5242880}' | uv run elysiactl index sync --stdin --dry-run

# Binary file (skip indexing)
echo '{"line": 4, "repo": "ServiceD", "op": "add", "path": "image.png", "content_ref": "/opt/pdi/Enterprise/ServiceD/image.png", "size": 1048576, "skip_index": true}' | uv run elysiactl index sync --stdin --dry-run
```

### Checkpoint recovery test:
```bash
# Interrupt during mgit processing, then resume
mgit diff /opt/pdi/Enterprise --format=jsonl | uv run elysiactl index sync --stdin --verbose
# Should resume from last completed line number
```

### Fallback: Plain file paths (for testing/debugging):
```bash
echo -e "src/main.py\nsrc/utils.py" | uv run elysiactl index sync --stdin --dry-run
```

### Collection parameter:
```bash
mgit diff /opt/pdi/Enterprise --format=jsonl | uv run elysiactl index sync --stdin --collection TEST_COLLECTION --dry-run
```

## Success Criteria

- [ ] Command `elysiactl index sync --stdin` exists and accepts mgit JSONL input
- [ ] **Smart Three-Tier Content Strategy**:
  - [ ] Handles `content` field (Tier 1: 0-10KB plain text)
  - [ ] Handles `content_base64` field (Tier 2: 10-100KB base64)  
  - [ ] Handles `content_ref` field (Tier 3: 100KB+ file references)
- [ ] **Multi-repository Support**:
  - [ ] Processes `repo` field from mgit output
  - [ ] Generates deterministic UUIDs with repository context
  - [ ] Displays repository names in output
- [ ] **Reliability Features**:
  - [ ] Creates checkpoint file at `/tmp/elysiactl/sync_checkpoint.txt`
  - [ ] Resumes from checkpoint on restart after interruption
  - [ ] Respects `skip_index` flag for binary files
  - [ ] Handles `content_ref` path not found gracefully
- [ ] **Operational Requirements**:
  - [ ] Dry-run mode shows actions without modifying Weaviate
  - [ ] Respects max_file_size configuration limits
  - [ ] Provides clear progress feedback with repo context
  - [ ] Checkpoint is cleared on successful completion
  - [ ] Failed items are not marked as completed for retry
- [ ] **Integration Testing**:
  - [ ] Works with `mgit diff --format=jsonl` pipeline
  - [ ] All mgit JSONL format examples process correctly
  - [ ] Fallback plain file path mode works for debugging
  - [ ] Base64 decoding works correctly for medium files
  - [ ] Content reference reading works for large files

## Configuration Changes

Add sync-specific settings to existing config classes:

**File: `/opt/elysiactl/src/elysiactl/config.py`**

```python
@dataclass
class ProcessingConfig:
    # ... existing fields ...
    
    # Sync-specific settings
    checkpoint_dir: str = field(default_factory=lambda: os.getenv("elysiactl_CHECKPOINT_DIR", "/tmp/elysiactl"))
    auto_clear_checkpoint: bool = field(default_factory=lambda: os.getenv("elysiactl_AUTO_CLEAR_CHECKPOINT", "true").lower() == "true")
```

This phase establishes the foundation for Unix-pipe compatibility while maintaining safety through checkpointing. The implementation supports both simple file paths and structured JSONL input, setting the stage for more advanced content strategies in later phases.