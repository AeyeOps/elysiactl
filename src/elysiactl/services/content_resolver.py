"""Content resolution for analyzing mgit's three-tier strategy."""

import os
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from rich.console import Console

from ..config import get_config

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
    embed_content: bool = False  # Whether mgit would embed content
    use_base64: bool = False     # Whether mgit would use base64 encoding

class ContentResolver:
    """Content resolver for consuming mgit's three-tier output and local analysis."""
    
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
        config = get_config()
        # mgit's tier thresholds (from configuration)
        self.TIER_1_MAX = config.processing.mgit_tier_1_max      # 10KB - mgit embeds as plain text
        self.TIER_2_MAX = config.processing.mgit_tier_2_max      # 100KB - mgit embeds as base64
        self.TIER_3_MAX = config.processing.mgit_tier_3_max      # 10MB - mgit uses references
        
        # Configuration flags
        self.use_mime_detection = config.processing.use_mime_detection
        self.analyze_vendor_dirs = config.processing.analyze_vendor_dirs
        
        # Custom patterns
        if config.processing.custom_skip_paths:
            custom_paths = set(config.processing.custom_skip_paths.split(','))
            self.SKIP_PATHS = self.SKIP_PATHS | custom_paths
        if config.processing.custom_binary_extensions:
            custom_exts = set(config.processing.custom_binary_extensions.split(','))
            self.BINARY_EXTENSIONS = self.BINARY_EXTENSIONS | custom_exts
        
        # Initialize libmagic for MIME type detection (optional dependency)
        self.magic_mime = None
        if self.use_mime_detection:
            try:
                import magic
                self.magic_mime = magic.Magic(mime=True)
            except ImportError:
                console.print("[dim]libmagic not available, using file extension-based MIME detection[/dim]")
            except Exception:
                pass  # Silently fall back to mimetypes
    
    def analyze_file(self, file_path: str) -> ContentAnalysis:
        """Analyze file characteristics for understanding mgit's likely strategy."""
        path = Path(file_path)
        
        # Check if file exists and is readable
        if not path.exists():
            return ContentAnalysis(
                file_size=0, mime_type="unknown", is_binary=False, 
                is_text=False, is_skippable=True, predicted_tier=0,
                skip_reason="File not found", embed_content=False, use_base64=False
            )
        
        if not path.is_file():
            return ContentAnalysis(
                file_size=0, mime_type="unknown", is_binary=False,
                is_text=False, is_skippable=True, predicted_tier=0,
                skip_reason="Not a regular file", embed_content=False, use_base64=False
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
                    skip_reason="Vendor/generated directory", embed_content=False, use_base64=False
                )
            
            # Check for binary files
            if is_binary:
                return ContentAnalysis(
                    file_size=file_size, mime_type=mime_type, is_binary=True,
                    is_text=False, is_skippable=True, predicted_tier=3,
                    skip_reason=f"Binary file ({mime_type})", embed_content=False, use_base64=False
                )
            
            # Predict mgit's tier based on file size
            if file_size <= self.TIER_1_MAX:
                predicted_tier = 1  # mgit would embed as plain text
                embed_content = True
                use_base64 = False
            elif file_size <= self.TIER_2_MAX and is_text:
                predicted_tier = 2  # mgit would embed as base64
                embed_content = True
                use_base64 = True
            elif file_size <= self.TIER_3_MAX:
                predicted_tier = 3  # mgit would use reference
                embed_content = False
                use_base64 = False
            else:
                return ContentAnalysis(
                    file_size=file_size, mime_type=mime_type, is_binary=is_binary,
                    is_text=is_text, is_skippable=True, predicted_tier=3,
                    skip_reason=f"File too large ({file_size} bytes)",
                    embed_content=False, use_base64=False
                )
            
            return ContentAnalysis(
                file_size=file_size, mime_type=mime_type, is_binary=is_binary,
                is_text=is_text, is_skippable=False, predicted_tier=predicted_tier,
                embed_content=embed_content, use_base64=use_base64
            )
                
        except OSError as e:
            return ContentAnalysis(
                file_size=0, mime_type="unknown", is_binary=False,
                is_text=False, is_skippable=True, predicted_tier=0,
                skip_reason=f"OS error: {e}", embed_content=False, use_base64=False
            )
    
    def _should_skip_path(self, path: Path) -> bool:
        """Check if path contains skip directories."""
        return any(skip_dir in path.parts for skip_dir in self.SKIP_PATHS)
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type using libmagic or fallback to mimetypes."""
        if self.magic_mime and self.use_mime_detection:
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

    def create_optimized_change(self, file_path: str, operation: str, line_number: int) -> Dict[str, Any]:
        """Create an optimized change object for mgit consumption."""
        analysis = self.analyze_file(file_path)
        path_obj = Path(file_path)
        
        change = {
            'path': str(path_obj),
            'op': operation,
            'line': line_number,
            'size': analysis.file_size
        }
        
        # For large files, use content_ref instead of embedding
        if analysis.predicted_tier == 3:
            change['content_ref'] = str(path_obj)
        elif analysis.predicted_tier == 2:
            # For medium files, use base64 encoding
            try:
                with open(file_path, 'rb') as f:
                    content_bytes = f.read()
                    change['content_base64'] = base64.b64encode(content_bytes).decode('utf-8')
            except Exception:
                change['content_ref'] = str(path_obj)
        else:
            # For small files, embed content directly
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    change['content'] = f.read()
            except UnicodeDecodeError:
                # Fallback to base64 for non-UTF8 text files
                try:
                    with open(file_path, 'rb') as f:
                        content_bytes = f.read()
                        change['content_base64'] = base64.b64encode(content_bytes).decode('utf-8')
                except Exception:
                    change['content_ref'] = str(path_obj)
        
        return change