# Phase 3: Smart Content Resolution

## Objective

Efficiently consume mgit's three-tier content strategy (plain text, base64, file references) and provide analysis tools for content strategy distribution. Focus on optimized content resolution rather than content strategy creation.

## Problem Summary

Phase 2 assumes all content comes from file references, but mgit already provides smart content embedding using a three-tier strategy. elysiactl needs to efficiently consume mgit's JSONL output which includes plain text content, base64-encoded content, and file references. We also need analysis tools to understand the distribution of content strategies.

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/services/content_resolver.py` (NEW)

**Create content resolution service for analysis and local file processing:**

```python
"""Content resolution for analyzing mgit's three-tier strategy."""

import os
import base64
import magic
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from rich.console import Console

console = Console()

@dataclass
class ContentAnalysis:
    """Analysis of a file's content characteristics."""
    file_size: int
    mime_type: str
    is_binary: bool
    is_text: bool
    is_skippable: bool
    predicted_tier: int  # What tier mgit would likely use
    skip_reason: Optional[str] = None

class ContentResolver:
    """Content resolver for consuming mgit's three-tier output and local analysis."""
    
    # mgit's tier thresholds (for analysis compatibility)
    TIER_1_MAX = 10_000      # 10KB - mgit embeds as plain text
    TIER_2_MAX = 100_000     # 100KB - mgit embeds as base64
    TIER_3_MAX = 10_000_000  # 10MB - mgit uses references
    
    # Binary file extensions that should be skipped
    BINARY_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.mp3', '.wav', '.flac', '.ogg', '.m4a',
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
        '.exe', '.dll', '.so', '.dylib', '.bin',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.jar', '.war', '.ear', '.class', '.pyc', '.pyo',
        '.iso', '.dmg', '.img'
    }
    
    # Vendor/generated directories to skip
    SKIP_PATHS = {
        'node_modules', 'vendor', '__pycache__', '.git', '.svn', '.hg',
        'build', 'dist', 'target', 'bin', 'obj', '.vscode', '.idea',
        'coverage', '.nyc_output', '.pytest_cache'
    }
    
    # Text file extensions that are safe to embed
    TEXT_EXTENSIONS = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.c', '.cpp', '.h', '.hpp',
        '.cs', '.php', '.rb', '.go', '.rs', '.scala', '.kt', '.swift',
        '.html', '.htm', '.xml', '.css', '.scss', '.sass', '.less',
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
        '.md', '.txt', '.rst', '.asciidoc', '.tex',
        '.sql', '.sh', '.bash', '.ps1', '.bat', '.cmd',
        '.dockerfile', '.makefile', '.cmake', '.gradle',
        '.gitignore', '.dockerignore', '.editorconfig'
    }
    
    def __init__(self):
        # Initialize libmagic for MIME type detection
        try:
            self.magic_mime = magic.Magic(mime=True)
        except:
            console.print("[yellow]Warning: libmagic not available, using file extensions only[/yellow]")
            self.magic_mime = None
    
    def analyze_file(self, file_path: str) -> ContentAnalysis:
        """Analyze file characteristics for understanding mgit's likely strategy."""
        path = Path(file_path)
        
        # Check if file exists and is readable
        if not path.exists():
            return ContentAnalysis(
                file_size=0, mime_type="unknown", is_binary=False, 
                is_text=False, is_skippable=True, predicted_tier=0,
                skip_reason="File not found"
            )
        
        if not path.is_file():
            return ContentAnalysis(
                file_size=0, mime_type="unknown", is_binary=False,
                is_text=False, is_skippable=True, predicted_tier=0,
                skip_reason="Not a regular file"
            )
        
        try:
            file_size = path.stat().st_size
            file_ext = path.suffix.lower()
            
            # Get MIME type
            mime_type = self._get_mime_type(file_path)
            is_binary = self._is_binary_mime(mime_type) or file_ext in self.BINARY_EXTENSIONS
            is_text = mime_type.startswith('text/') or file_ext in self.TEXT_EXTENSIONS
            
            # Check if in skip paths
            if self._should_skip_path(path):
                return ContentAnalysis(
                    file_size=file_size, mime_type=mime_type, is_binary=is_binary,
                    is_text=is_text, is_skippable=True, predicted_tier=3,
                    skip_reason="Vendor/generated directory"
                )
            
            # Check for binary files
            if is_binary:
                return ContentAnalysis(
                    file_size=file_size, mime_type=mime_type, is_binary=True,
                    is_text=False, is_skippable=True, predicted_tier=3,
                    skip_reason=f"Binary file ({mime_type})"
                )
            
            # Predict mgit's tier based on file size
            if file_size <= self.TIER_1_MAX:
                predicted_tier = 1  # mgit would embed as plain text
            elif file_size <= self.TIER_2_MAX and is_text:
                predicted_tier = 2  # mgit would embed as base64
            elif file_size <= self.TIER_3_MAX:
                predicted_tier = 3  # mgit would use reference
            else:
                return ContentAnalysis(
                    file_size=file_size, mime_type=mime_type, is_binary=is_binary,
                    is_text=is_text, is_skippable=True, predicted_tier=3,
                    skip_reason=f"File too large ({file_size} bytes)"
                )
            
            return ContentAnalysis(
                file_size=file_size, mime_type=mime_type, is_binary=is_binary,
                is_text=is_text, is_skippable=False, predicted_tier=predicted_tier
            )
                
        except OSError as e:
            return ContentAnalysis(
                file_size=0, mime_type="unknown", is_binary=False,
                is_text=False, is_skippable=True, predicted_tier=0,
                skip_reason=f"OS error: {e}"
            )
    
    def _should_skip_path(self, path: Path) -> bool:
        """Check if path contains skip directories."""
        return any(skip_dir in path.parts for skip_dir in self.SKIP_PATHS)
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type using libmagic or fallback to mimetypes."""
        if self.magic_mime:
            try:
                return self.magic_mime.from_file(file_path)
            except:
                pass
        
        # Fallback to mimetypes module
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    
    def _is_binary_mime(self, mime_type: str) -> bool:
        """Check if MIME type indicates binary content."""
        binary_prefixes = [
            'image/', 'video/', 'audio/', 'application/octet-stream',
            'application/pdf', 'application/zip', 'application/gzip',
            'application/x-tar', 'application/x-executable'
        ]
        
        return any(mime_type.startswith(prefix) for prefix in binary_prefixes)
    
    def resolve_content_from_reference(self, content_ref: str) -> Optional[str]:
        """Resolve content from file reference (Tier 3 fallback)."""
        try:
            if not content_ref.startswith("/"):
                console.print(f"[yellow]Invalid content reference (must be absolute path): {content_ref}[/yellow]")
                return None
            
            with open(content_ref, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
        except Exception as e:
            console.print(f"[red]Failed to read reference {content_ref}: {e}[/red]")
            return None
    
    def decode_base64_content(self, base64_content: str) -> Optional[str]:
        """Decode base64 content to text (for Tier 2 processing)."""
        try:
            decoded_bytes = base64.b64decode(base64_content)
            return decoded_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            console.print(f"[red]Failed to decode base64 content: {e}[/red]")
            return None

    def get_strategy_stats(self, file_paths: list) -> Dict[str, int]:
        """Analyze files and predict mgit's strategy distribution."""
        stats = {
            'tier_1_plain': 0,      # mgit would embed as plain text
            'tier_2_base64': 0,     # mgit would embed as base64
            'tier_3_reference': 0,  # mgit would use references
            'skipped_binary': 0,    # Binary files mgit would skip
            'skipped_vendor': 0,    # Vendor directories mgit would skip
            'skipped_large': 0,     # Too large files mgit would skip
            'errors': 0             # File access errors
        }
        
        for file_path in file_paths:
            analysis = self.analyze_file(file_path)
            
            if analysis.is_skippable:
                if analysis.skip_reason and 'Binary' in analysis.skip_reason:
                    stats['skipped_binary'] += 1
                elif analysis.skip_reason and 'Vendor' in analysis.skip_reason:
                    stats['skipped_vendor'] += 1
                elif analysis.skip_reason and 'too large' in analysis.skip_reason:
                    stats['skipped_large'] += 1
                else:
                    stats['errors'] += 1
            elif analysis.predicted_tier == 1:
                stats['tier_1_plain'] += 1
            elif analysis.predicted_tier == 2:
                stats['tier_2_base64'] += 1
            elif analysis.predicted_tier == 3:
                stats['tier_3_reference'] += 1
        
        return stats
```

### File: `/opt/elysiactl/src/elysiactl/services/sync.py` (UPDATE resolve_file_content)

**Replace existing resolve_file_content function to efficiently consume mgit's three-tier format:**

```python
import base64
from .content_resolver import ContentResolver

# Add to the module level
content_resolver = ContentResolver()

def resolve_file_content(change: Dict[str, Any]) -> Optional[str]:
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
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        console.print(f"[red]Failed to read legacy path {file_path}: {e}[/red]")
        return None
```

**Update parse_input_line to handle mgit's JSONL format and legacy file paths:**

```python
def parse_input_line(line: str, line_number: int) -> Optional[Dict[str, Any]]:
    """Parse input line supporting both mgit's JSONL and legacy file paths."""
    line = line.strip()
    if not line:
        return None
    
    # Try JSON first (mgit's enhanced JSONL format)
    try:
        data = json.loads(line)
        # Ensure line number is set for checkpointing
        if 'line' not in data:
            data['line'] = line_number
        return data
    except json.JSONDecodeError:
        # Fall back to plain file path (legacy Phase 2 format)
        return {
            'line': line_number,
            'path': line,
            'op': 'modify'  # Default operation for legacy paths
        }
```

### File: `/opt/elysiactl/src/elysiactl/commands/index.py` (ADD ANALYZE COMMAND)

**Add analyze command to understand mgit's content strategy distribution:**

```python
@app.command()
def analyze(
    paths: Annotated[List[str], typer.Argument(help="File paths to analyze")],
    summary: Annotated[bool, typer.Option("--summary", help="Show predicted strategy statistics")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed analysis per file")] = False,
):
    """Analyze local files and predict mgit's content strategy."""
    from ..services.content_resolver import ContentResolver
    from rich.table import Table
    
    resolver = ContentResolver()
    
    if summary:
        stats = resolver.get_strategy_stats(paths)
        
        table = Table(title="Predicted mgit Content Strategy")
        table.add_column("Strategy", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Description", style="dim")
        
        table.add_row("Tier 1 (Plain)", str(stats['tier_1_plain']), "mgit would embed as plain text")
        table.add_row("Tier 2 (Base64)", str(stats['tier_2_base64']), "mgit would embed as base64")  
        table.add_row("Tier 3 (Reference)", str(stats['tier_3_reference']), "mgit would use file references")
        table.add_row("Skipped (Binary)", str(stats['skipped_binary']), "mgit would skip binary files")
        table.add_row("Skipped (Vendor)", str(stats['skipped_vendor']), "mgit would skip vendor dirs")
        table.add_row("Skipped (Large)", str(stats['skipped_large']), "mgit would skip large files")
        table.add_row("Errors", str(stats['errors']), "File access errors")
        
        console.print(table)
        
        total_files = sum(stats.values())
        indexed_files = stats['tier_1_plain'] + stats['tier_2_base64'] + stats['tier_3_reference']
        embedded_files = stats['tier_1_plain'] + stats['tier_2_base64']
        
        console.print(f"\n[bold]Predicted mgit Behavior:[/bold]")
        console.print(f"  Total files analyzed: {total_files}")
        console.print(f"  Would be indexed: {indexed_files} ({indexed_files/total_files*100:.1f}%)")
        console.print(f"  Content embedded: {embedded_files} ({embedded_files/total_files*100:.1f}%)")
        
    if verbose:
        table = Table(title="Detailed File Analysis (Predicted mgit Strategy)")
        table.add_column("File Path", style="cyan")
        table.add_column("Size", style="green", justify="right")
        table.add_column("Predicted Tier", style="yellow", justify="center")
        table.add_column("MIME Type", style="blue")
        table.add_column("Notes", style="dim")
        
        for file_path in paths:
            analysis = resolver.analyze_file(file_path)
            
            size_str = f"{analysis.file_size:,}" if analysis.file_size > 0 else "N/A"
            tier_name = {
                0: "Error",
                1: "Plain", 
                2: "Base64",
                3: "Ref"
            }.get(analysis.predicted_tier, "Unknown")
            
            notes = analysis.skip_reason if analysis.is_skippable else f"Binary: {analysis.is_binary}"
            
            table.add_row(file_path, size_str, tier_name, analysis.mime_type, notes)
        
        console.print(table)

@app.command() 
def inspect(
    jsonl_file: Annotated[str, typer.Argument(help="Path to mgit JSONL file")],
    show_stats: Annotated[bool, typer.Option("--stats", help="Show content strategy statistics")] = False,
    show_content: Annotated[bool, typer.Option("--content", help="Show actual resolved content")] = False,
):
    """Inspect mgit JSONL output and analyze content strategies."""
    from ..services.content_resolver import ContentResolver
    from ..services.sync import resolve_file_content, parse_input_line
    from rich.table import Table
    
    resolver = ContentResolver()
    
    strategy_counts = {1: 0, 2: 0, 3: 0, 'skipped': 0, 'errors': 0}
    total_size = {'embedded': 0, 'references': 0}
    
    try:
        with open(jsonl_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                change = parse_input_line(line, line_num)
                if not change:
                    continue
                
                # Classify the change object
                if change.get('skip_index'):
                    strategy_counts['skipped'] += 1
                elif 'content' in change:
                    strategy_counts[1] += 1
                    total_size['embedded'] += len(change['content'])
                elif 'content_base64' in change:
                    strategy_counts[2] += 1 
                    total_size['embedded'] += len(change['content_base64'])
                elif 'content_ref' in change:
                    strategy_counts[3] += 1
                    total_size['references'] += 1
                else:
                    strategy_counts['errors'] += 1
                
                if show_content and line_num <= 10:  # Show first 10 for brevity
                    content = resolve_file_content(change)
                    console.print(f"\n[bold]Line {line_num}:[/bold] {change.get('path', 'unknown')}")
                    if content:
                        preview = content[:200] + "..." if len(content) > 200 else content
                        console.print(f"  Content: {preview}")
                    else:
                        console.print("  [red]No content resolved[/red]")
        
        if show_stats:
            table = Table(title=f"mgit JSONL Analysis: {jsonl_file}")
            table.add_column("Strategy", style="cyan")
            table.add_column("Count", style="green", justify="right")
            table.add_column("Description", style="dim")
            
            table.add_row("Tier 1 (Plain)", str(strategy_counts[1]), "Plain text embedded")
            table.add_row("Tier 2 (Base64)", str(strategy_counts[2]), "Base64 encoded content")
            table.add_row("Tier 3 (Reference)", str(strategy_counts[3]), "File references")
            table.add_row("Skipped", str(strategy_counts['skipped']), "Marked for skipping")
            table.add_row("Errors", str(strategy_counts['errors']), "Parse errors")
            
            console.print(table)
            
            total_changes = sum(strategy_counts.values())
            embedded_count = strategy_counts[1] + strategy_counts[2]
            
            console.print(f"\n[bold]Summary:[/bold]")
            console.print(f"  Total changes: {total_changes}")
            console.print(f"  Content embedded: {embedded_count} ({embedded_count/total_changes*100:.1f}%)")
            console.print(f"  Embedded size: {total_size['embedded']:,} chars")
            console.print(f"  File references: {total_size['references']}")
    
    except Exception as e:
        console.print(f"[red]Failed to analyze {jsonl_file}: {e}[/red]")
```

## Agent Workflow

1. **Content Resolver Implementation:**
   - Create ContentResolver class focused on analysis and consumption
   - Implement MIME type detection with libmagic fallback for local analysis
   - Add binary file detection and vendor directory filtering for predictions
   - Create methods for base64 decoding and file reference resolution

2. **Update Existing Sync for mgit Consumption:**
   - Modify resolve_file_content to efficiently handle mgit's three-tier format
   - Update parse_input_line to consume mgit's JSONL and legacy file paths
   - Add proper error handling for content resolution failures
   - Maintain backward compatibility with Phase 2 file paths

3. **Analysis Tools:**
   - Add analyze command for predicting mgit's strategy on local files
   - Add inspect command for analyzing actual mgit JSONL output
   - Create statistics showing content strategy distribution
   - Provide insights into embedded vs referenced content

4. **Testing and Validation:**
   - Test consumption of all three mgit content tiers
   - Verify base64 decoding works correctly
   - Test file reference resolution with absolute paths  
   - Validate analysis predictions match expected mgit behavior

## Testing

### Test local file analysis (predicting mgit behavior):
```bash
# Create test files of different sizes
echo "small" > /tmp/small.txt  # mgit would use Tier 1 (plain)
python -c "print('x' * 50000)" > /tmp/medium.txt  # mgit would use Tier 2 (base64)
python -c "print('x' * 200000)" > /tmp/large.txt  # mgit would use Tier 3 (reference)

# Analyze prediction accuracy
uv run elysiactl index analyze /tmp/small.txt /tmp/medium.txt /tmp/large.txt --verbose
```

### Test strategy distribution analysis:
```bash
# Analyze real source code directory to predict mgit behavior
find /opt/elysiactl/src -type f | head -50 | xargs uv run elysiactl index analyze --summary
```

### Test mgit JSONL consumption:
```bash
# Create sample mgit JSONL output
cat > /tmp/test_mgit.jsonl << 'EOF'
{"repo": "test", "op": "modify", "path": "/tmp/small.txt", "content": "small file content"}
{"repo": "test", "op": "modify", "path": "/tmp/medium.txt", "content_base64": "bWVkaXVtIGZpbGUgY29udGVudA=="}
{"repo": "test", "op": "modify", "path": "/tmp/large.txt", "content_ref": "/tmp/large.txt"}
{"repo": "test", "op": "modify", "path": "/tmp/binary", "skip_index": true}
EOF

# Inspect the mgit output
uv run elysiactl index inspect /tmp/test_mgit.jsonl --stats --content
```

### Test content resolution from mgit formats:
```bash
# Test sync with mgit JSONL input
uv run elysiactl index sync --input /tmp/test_mgit.jsonl --dry-run --verbose
```

### Test binary file prediction:
```bash
# Create binary file and verify prediction
cp /bin/ls /tmp/binary_test
uv run elysiactl index analyze /tmp/binary_test --verbose
```

### Test base64 decoding:
```bash
# Create JSONL with base64 content and test decoding
echo '{"path": "/tmp/test.py", "content_base64": "ZGVmIHRlc3QoKToKICAgIHJldHVybiAiSGVsbG8gV29ybGQi"}' > /tmp/base64_test.jsonl
uv run elysiactl index inspect /tmp/base64_test.jsonl --content
```

## Success Criteria

- [ ] ContentResolver efficiently consumes mgit's three-tier format
- [ ] Tier 1 content (plain text) correctly processed from change objects
- [ ] Tier 2 content (base64) correctly decoded to readable text  
- [ ] Tier 3 content (file references) resolved from absolute paths
- [ ] Binary files and skip_index flags properly respected
- [ ] Local file analysis predicts mgit's likely tier classification
- [ ] MIME type detection works for analysis (libmagic + mimetypes fallback)
- [ ] Base64 decoding handles encoding errors gracefully
- [ ] `elysiactl index analyze` shows predicted mgit strategy distribution
- [ ] `elysiactl index inspect` analyzes actual mgit JSONL output
- [ ] Sync operation efficiently resolves content from all three tiers
- [ ] Error handling for missing files, invalid references, decode failures
- [ ] Backward compatibility with Phase 2 plain file path input
- [ ] All test commands execute without errors
- [ ] Performance optimized for consuming pre-embedded content

## Configuration Changes

Add content analysis settings for understanding mgit behavior:

**File: `/opt/elysiactl/src/elysiactl/config.py`**

```python
@dataclass
class ProcessingConfig:
    # ... existing fields ...
    
    # mgit tier thresholds (for analysis compatibility)
    mgit_tier_1_max: int = field(default_factory=lambda: int(os.getenv("ELYSIACTL_MGIT_TIER_1_MAX", "10000")))      # 10KB
    mgit_tier_2_max: int = field(default_factory=lambda: int(os.getenv("ELYSIACTL_MGIT_TIER_2_MAX", "100000")))    # 100KB  
    mgit_tier_3_max: int = field(default_factory=lambda: int(os.getenv("ELYSIACTL_MGIT_TIER_3_MAX", "10000000")))  # 10MB
    
    # Content analysis settings
    use_mime_detection: bool = field(default_factory=lambda: os.getenv("ELYSIACTL_USE_MIME_DETECTION", "true").lower() == "true")
    analyze_vendor_dirs: bool = field(default_factory=lambda: os.getenv("ELYSIACTL_ANALYZE_VENDOR_DIRS", "true").lower() == "true")
    
    # Content resolution timeouts
    file_read_timeout: float = field(default_factory=lambda: float(os.getenv("ELYSIACTL_FILE_READ_TIMEOUT", "30.0")))
    base64_decode_timeout: float = field(default_factory=lambda: float(os.getenv("ELYSIACTL_BASE64_TIMEOUT", "10.0")))
    
    # Custom patterns (comma-separated)
    custom_skip_paths: str = field(default_factory=lambda: os.getenv("ELYSIACTL_CUSTOM_SKIP_PATHS", ""))
    custom_binary_extensions: str = field(default_factory=lambda: os.getenv("ELYSIACTL_CUSTOM_BINARY_EXTENSIONS", ""))
```

This phase refocuses elysiactl as an efficient consumer of mgit's smart content strategy rather than a content strategy creator. It provides analysis tools to understand content distribution and optimizes the consumption pipeline for mgit's three-tier format while maintaining backward compatibility with Phase 2 file path inputs.