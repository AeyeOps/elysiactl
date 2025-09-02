"""Sync service for streaming JSONL changes to Weaviate."""

import sys
import json
import base64
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

import httpx
from rich.console import Console

from ..config import get_config

console = Console()


class StreamCheckpoint:
    """File-based checkpoint tracking for stream processing."""
    
    def __init__(self, checkpoint_path: str = "/tmp/elysiactl/sync_checkpoint.txt"):
        self.checkpoint_path = Path(checkpoint_path)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.completed_lines = self._load_completed_lines()
    
    def _load_completed_lines(self) -> set:
        """Load completed line numbers from checkpoint file."""
        if not self.checkpoint_path.exists():
            return set()
        
        completed = set()
        try:
            with open(self.checkpoint_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.isdigit():
                        completed.add(int(line))
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load checkpoint file: {e}[/yellow]")
        
        return completed
    
    def mark_completed(self, line_number: int):
        """Mark a line number as completed."""
        if line_number in self.completed_lines:
            return
        
        try:
            with open(self.checkpoint_path, 'a') as f:
                f.write(f"{line_number}\n")
            self.completed_lines.add(line_number)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not write checkpoint: {e}[/yellow]")
    
    def is_completed(self, line_number: int) -> bool:
        """Check if a line number has been completed."""
        return line_number in self.completed_lines
    
    def clear(self):
        """Clear the checkpoint file."""
        try:
            if self.checkpoint_path.exists():
                self.checkpoint_path.unlink()
            self.completed_lines.clear()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not clear checkpoint: {e}[/yellow]")


class StreamSync:
    """Stream processor for syncing JSONL changes to Weaviate."""
    
    def __init__(self, collection_name: str, dry_run: bool = False, verbose: bool = False):
        self.collection_name = collection_name
        self.dry_run = dry_run
        self.verbose = verbose
        self.config = get_config()
        self.checkpoint = StreamCheckpoint()
        
        # Stats tracking
        self.stats = {
            'processed': 0,
            'added': 0,
            'updated': 0,
            'deleted': 0,
            'failed': 0,
            'skipped': 0
        }
    
    async def process_stdin(self):
        """Process JSONL changes from stdin."""
        console.print(f"[bold]Syncing changes to collection: {self.collection_name}[/bold]")
        
        if self.dry_run:
            console.print("[yellow]DRY RUN MODE - No changes will be written[/yellow]")
        
        try:
            # Process each line from stdin with line numbers
            for line_number, line in enumerate(sys.stdin, 1):
                # Skip if already processed
                if self.checkpoint.is_completed(line_number):
                    if self.verbose:
                        console.print(f"[dim]Line {line_number}: Skipping (already completed)[/dim]")
                    self.stats['skipped'] += 1
                    continue
                
                # Parse and process the line
                try:
                    line = line.strip()
                    if not line:
                        continue
                        
                    data = json.loads(line)
                    data['line'] = line_number  # Add line number for tracking
                    
                    await self._process_change(data)
                    
                    # Mark as completed
                    if not self.dry_run:
                        self.checkpoint.mark_completed(line_number)
                    
                    self.stats['processed'] += 1
                    
                except json.JSONDecodeError as e:
                    console.print(f"[red]Line {line_number}: Invalid JSON - {e}[/red]")
                    self.stats['failed'] += 1
                    continue
                except Exception as e:
                    console.print(f"[red]Line {line_number}: Error processing - {e}[/red]")
                    self.stats['failed'] += 1
                    continue
            
            # Print final stats
            self._print_summary()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted - checkpoint saved, can resume later[/yellow]")
            self._print_summary()
        except Exception as e:
            console.print(f"[red]Fatal error: {e}[/red]")
            raise
    
    async def _process_change(self, change: Dict):
        """Process a single change record."""
        operation = change.get('op', 'unknown')
        path = change.get('path', 'unknown')
        repo = change.get('repo', 'unknown')
        line_number = change.get('line', 0)
        
        if self.verbose:
            console.print(f"[cyan]Line {line_number}[/cyan]: [{operation.upper()}] {repo}/{path}")
        
        try:
            if operation == 'delete':
                await self._handle_delete(change)
                self.stats['deleted'] += 1
            elif operation in ['add', 'modify']:
                await self._handle_add_modify(change)
                if operation == 'add':
                    self.stats['added'] += 1
                else:
                    self.stats['updated'] += 1
            else:
                console.print(f"[yellow]Line {line_number}: Unknown operation '{operation}'[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Line {line_number}: Failed to process - {e}[/red]")
            self.stats['failed'] += 1
            raise
    
    async def _handle_delete(self, change: Dict):
        """Handle delete operation."""
        path = change.get('path')
        if not path:
            return
        
        object_id = self._get_object_id(path)
        
        if self.dry_run:
            console.print(f"[red]DELETE[/red] {path} (id: {object_id[:8]}...)")
            return
        
        async with httpx.AsyncClient(timeout=self.config.processing.medium_timeout) as client:
            try:
                response = await client.delete(
                    f"{self.config.services.weaviate_base_url}/objects/{object_id}"
                )
                if response.status_code not in [200, 204, 404]:  # 404 is OK for delete
                    console.print(f"[yellow]Warning: Delete failed with status {response.status_code}[/yellow]")
            except Exception as e:
                console.print(f"[red]Delete request failed: {e}[/red]")
                raise
    
    async def _handle_add_modify(self, change: Dict):
        """Handle add/modify operations."""
        path = change.get('path')
        repo = change.get('repo')
        
        if not path:
            return
        
        # Resolve content from the three-tier format
        content = self._resolve_content(change)
        if content is None:
            if self.verbose:
                console.print(f"[yellow]Skipping {path} (no readable content)[/yellow]")
            return
        
        # Create Weaviate object
        object_id = self._get_object_id(path)
        weaviate_object = {
            "id": object_id,
            "class": self.collection_name,
            "properties": {
                "file_path": str(path),
                "file_name": Path(path).name,
                "repository": repo or "unknown",
                "content": content[:self.config.processing.max_content_size],
                "language": self._get_language_from_path(Path(path)),
                "extension": Path(path).suffix or "none",
                "size_bytes": len(content.encode('utf-8')),
                "line_count": content.count('\n') + 1,
                "last_modified": datetime.utcnow().isoformat() + "Z",
                "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                "relative_path": str(Path(path).name)
            }
        }
        
        if self.dry_run:
            op_name = "ADD" if change.get('op') == 'add' else "UPDATE"
            console.print(f"[green]{op_name}[/green] {path} ({len(content)} chars)")
            return
        
        # Send to Weaviate
        async with httpx.AsyncClient(timeout=self.config.processing.medium_timeout) as client:
            try:
                response = await client.put(
                    f"{self.config.services.weaviate_base_url}/objects/{object_id}",
                    json=weaviate_object
                )
                if response.status_code not in [200, 201]:
                    console.print(f"[red]Weaviate error {response.status_code}: {response.text}[/red]")
                    raise Exception(f"Weaviate request failed with {response.status_code}")
            except Exception as e:
                console.print(f"[red]Weaviate request failed: {e}[/red]")
                raise
    
    def _resolve_content(self, change: Dict) -> Optional[str]:
        """Resolve content from three-tier format: content, content_base64, content_ref."""
        # Priority 1: Plain embedded content (0-10KB files)
        if "content" in change:
            return change["content"]
        
        # Priority 2: Base64 embedded content (10-100KB files)
        if "content_base64" in change:
            try:
                return base64.b64decode(change["content_base64"]).decode('utf-8')
            except Exception as e:
                console.print(f"[red]Failed to decode base64 content: {e}[/red]")
                return None
        
        # Priority 3: Local file reference (100KB+ files)
        if "content_ref" in change:
            try:
                with open(change["content_ref"], 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Try with latin-1 encoding as fallback
                try:
                    with open(change["content_ref"], 'r', encoding='latin-1') as f:
                        return f.read()
                except Exception as e:
                    console.print(f"[red]Failed to read file {change['content_ref']}: {e}[/red]")
                    return None
            except Exception as e:
                console.print(f"[red]Failed to read file {change['content_ref']}: {e}[/red]")
                return None
        
        # No content available
        return None
    
    def _get_object_id(self, path: str) -> str:
        """Generate deterministic UUID for file path."""
        # Use UUID5 with URL namespace for stable IDs
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        return str(uuid.uuid5(namespace, f"{self.collection_name}:{path}"))
    
    def _get_language_from_path(self, path: Path) -> str:
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
        
        # Check exact name first
        if path.name in ext_to_lang:
            return ext_to_lang[path.name]
        
        return ext_to_lang.get(path.suffix.lower(), 'Unknown')
    
    def _print_summary(self):
        """Print processing summary."""
        console.print("\n" + "="*50)
        console.print("[bold]Sync Summary[/bold]")
        console.print(f"• Processed: [cyan]{self.stats['processed']}[/cyan] lines")
        console.print(f"• Added: [green]{self.stats['added']}[/green] files")
        console.print(f"• Updated: [blue]{self.stats['updated']}[/blue] files")
        console.print(f"• Deleted: [red]{self.stats['deleted']}[/red] files")
        console.print(f"• Skipped: [yellow]{self.stats['skipped']}[/yellow] lines (checkpoint)")
        console.print(f"• Failed: [red]{self.stats['failed']}[/red] lines")
        console.print(f"• Collection: [cyan]{self.collection_name}[/cyan]")