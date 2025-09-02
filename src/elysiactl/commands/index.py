"""Index command for managing source code collections in Weaviate."""

import os
import asyncio
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Annotated
import json

import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box

from ..config import get_config
from ..services.performance import get_performance_optimizer
from ..services.sync import sync_files_from_stdin, SQLiteCheckpointManager, _resolve_content, parse_input_line, sync_files_from_stdin_async
from ..services.error_handling import get_error_handler_with_config

app = typer.Typer(help="Index source code into Weaviate collections")
console = Console()

# Common source code extensions to index
SOURCE_EXTENSIONS = {
    # Web
    '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.sass', '.less',
    '.vue', '.svelte', '.astro',
    # Python
    '.py', '.pyx', '.pyi', '.ipynb',
    # C#/.NET
    '.cs', '.csproj', '.sln', '.xaml', '.razor', '.cshtml',
    # Java/JVM
    '.java', '.kt', '.scala', '.groovy', '.clj',
    # C/C++
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',
    # Go
    '.go',
    # Rust
    '.rs',
    # Ruby
    '.rb', '.erb',
    # PHP
    '.php',
    # Swift/Objective-C
    '.swift', '.m', '.mm',
    # Shell
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
    # Config
    '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.xml', '.env', '.properties',
    # Documentation
    '.md', '.rst', '.txt', '.adoc',
    # SQL
    '.sql',
    # Docker
    'Dockerfile', '.dockerfile',
    # Build files
    'Makefile', 'CMakeLists.txt', 'package.json', 'pom.xml', 'build.gradle',
    'Cargo.toml', 'go.mod', 'requirements.txt', 'Gemfile', 'composer.json'
}

# Directories to skip
SKIP_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env',
    'build', 'dist', 'target', '.next', '.nuxt', '.svelte-kit',
    '.pytest_cache', '.mypy_cache', '.tox', 'coverage', '.coverage',
    '.idea', '.vscode', '.vs', '*.egg-info', 'bin', 'obj',
    'packages', '.nuget', 'TestResults', '.sonarqube'
}

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    '.exe', '.dll', '.so', '.dylib', '.a', '.o', '.obj',
    '.class', '.jar', '.war', '.ear',
    '.pyc', '.pyo', '.pyd',
    '.wasm', '.wat',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.bmp',
    '.mp3', '.mp4', '.avi', '.mov', '.wmv',
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
    '.db', '.sqlite', '.sqlite3', '.mdf', '.ldf'
}


def should_index_file(file_path: Path) -> bool:
    """Determine if a file should be indexed."""
    # Skip binary files
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    
    # Skip hidden files (except important ones like .env, .gitignore)
    if file_path.name.startswith('.') and file_path.suffix not in {'.env', '.gitignore', '.editorconfig'}:
        return False
    
    # Check if it's a source code file
    if file_path.suffix.lower() in SOURCE_EXTENSIONS:
        return True
    
    # Check for special files without extensions
    special_files = {'Dockerfile', 'Makefile', 'README', 'LICENSE', 'CHANGELOG', 'Jenkinsfile'}
    if file_path.name in special_files:
        return True
    
    return False


def get_language_from_extension(file_path: Path) -> str:
    """Get programming language from file extension."""
    ext_to_lang = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript',
        '.ts': 'TypeScript', 
        '.tsx': 'TypeScript',
        '.cs': 'C#',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.sh': 'Shell',
        '.ps1': 'PowerShell',
        '.sql': 'SQL',
        '.html': 'HTML',
        '.css': 'CSS',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.xml': 'XML',
        '.md': 'Markdown',
        '.toml': 'TOML',
        '.dockerfile': 'Docker',
        'Dockerfile': 'Docker',
    }
    
    # Check exact name first
    if file_path.name in ext_to_lang:
        return ext_to_lang[file_path.name]
    
    return ext_to_lang.get(file_path.suffix.lower(), 'Unknown')


async def ensure_collection_schema(collection_name: Optional[str] = None) -> bool:
    """Ensure the collection exists with proper schema."""
    config = get_config()
    if collection_name is None:
        collection_name = config.collections.default_source_collection
    
    async with httpx.AsyncClient(timeout=config.processing.medium_timeout) as client:
        try:
            # Check if collection exists
            response = await client.get(f"{config.services.weaviate_base_url}/schema/{collection_name}")
            
            if response.status_code == 200:
                # Collection exists, check replication factor
                schema = response.json()
                replication_config = schema.get("replicationConfig", {})
                factor = replication_config.get("factor", 1)
                expected_factor = config.collections.replication_factor
                
                if factor != expected_factor:
                    console.print(f"[yellow]⚠ Collection {collection_name} exists with replication factor={factor}, expected={expected_factor}[/yellow]")
                    console.print("[yellow]  Consider using 'elysiactl repair config-replication' to fix[/yellow]")
                
                return True
            
            # Collection doesn't exist, create it
            console.print(f"[bold]Creating collection {collection_name}...[/bold]")
            
            schema = {
                "class": collection_name,
                "vectorizer": config.collections.vectorizer,
                "moduleConfig": {
                    config.collections.vectorizer: {
                        "model": config.collections.embedding_model,
                        "vectorizeClassName": False
                    }
                },
                "replicationConfig": {
                    "factor": config.collections.replication_factor,
                    "asyncEnabled": config.collections.replication_async_enabled
                },
                "properties": [
                    {
                        "name": "file_path",
                        "dataType": ["text"],
                        "description": "Full path to the source file",
                        "tokenization": "field"
                    },
                    {
                        "name": "file_name",
                        "dataType": ["text"],
                        "description": "Name of the file",
                        "tokenization": "field"
                    },
                    {
                        "name": "repository",
                        "dataType": ["text"],
                        "description": "Repository name",
                        "tokenization": "field"
                    },
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Source code content",
                        "tokenization": "word",
                        "moduleConfig": {
                            "text2vec-openai": {
                                "skip": False,
                                "vectorizePropertyName": False
                            }
                        }
                    },
                    {
                        "name": "language",
                        "dataType": ["text"],
                        "description": "Programming language",
                        "tokenization": "field"
                    },
                    {
                        "name": "extension",
                        "dataType": ["text"],
                        "description": "File extension",
                        "tokenization": "field"
                    },
                    {
                        "name": "size_bytes",
                        "dataType": ["int"],
                        "description": "File size in bytes"
                    },
                    {
                        "name": "line_count",
                        "dataType": ["int"],
                        "description": "Number of lines"
                    },
                    {
                        "name": "last_modified",
                        "dataType": ["date"],
                        "description": "Last modification timestamp"
                    },
                    {
                        "name": "content_hash",
                        "dataType": ["text"],
                        "description": "SHA256 hash of content",
                        "tokenization": "field"
                    },
                    {
                        "name": "relative_path",
                        "dataType": ["text"],
                        "description": "Path relative to repository root",
                        "tokenization": "field"
                    }
                ]
            }
            
            create_response = await client.post(
                f"{config.services.weaviate_base_url}/schema",
                json=schema
            )
            
            if create_response.status_code in [200, 201]:
                console.print(f"[green]✓[/green] Created collection {collection_name} with replication factor={config.collections.replication_factor}")
                return True
            else:
                console.print(f"[red]✗ Failed to create collection: {create_response.text}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Error with collection schema: {e}[/red]")
            return False


async def index_file(file_path: Path, repo_name: str, repo_root: Path) -> Optional[Dict]:
    """Index a single source code file."""
    try:
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except:
                return None  # Skip files we can't read
        
        # Skip very large files
        config = get_config()
        if len(content) > config.processing.max_file_size:
            return None
        
        # Get file metadata
        stat = file_path.stat()
        relative_path = file_path.relative_to(repo_root)
        
        # Create object for Weaviate
        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "repository": repo_name,
            "content": content[:config.processing.max_content_size],  # Limit content size
            "language": get_language_from_extension(file_path),
            "extension": file_path.suffix or "none",
            "size_bytes": stat.st_size,
            "line_count": content.count('\n') + 1,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z",
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "relative_path": str(relative_path)
        }
        
    except Exception:
        return None


async def index_repository(repo_path: Path, collection_name: str, progress: Progress, task_id) -> tuple[int, int]:
    """Index all source files in a repository."""
    repo_name = repo_path.name
    
    # Collect all files to index
    files_to_index = []
    for root, dirs, files in os.walk(repo_path):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        root_path = Path(root)
        for file in files:
            file_path = root_path / file
            if should_index_file(file_path):
                files_to_index.append(file_path)
    
    if not files_to_index:
        return 0, 0
    
    # Update progress
    progress.update(task_id, total=len(files_to_index))
    
    # Process files and build batch
    batch_objects = []
    indexed = 0
    failed = 0
    
    for file_path in files_to_index:
        obj = await index_file(file_path, repo_name, repo_path)
        if obj:
            batch_objects.append(obj)
            indexed += 1
        else:
            failed += 1
        
        progress.update(task_id, advance=1)
        
        # Insert batch when it reaches configured size
        config = get_config()
        if len(batch_objects) >= config.processing.batch_size:
            await insert_batch(collection_name, batch_objects)
            batch_objects = []
    
    # Insert remaining objects
    if batch_objects:
        await insert_batch(collection_name, batch_objects)
    
    return indexed, failed


async def insert_batch(collection_name: str, objects: List[Dict]) -> bool:
    """Insert a batch of objects into Weaviate."""
    if not objects:
        return True
    
    config = get_config()
    async with httpx.AsyncClient(timeout=config.processing.long_timeout) as client:
        try:
            response = await client.post(
                f"{config.services.weaviate_base_url}/batch/objects",
                json={
                    "objects": [
                        {
                            "class": collection_name,
                            "properties": obj
                        }
                        for obj in objects
                    ]
                }
            )
            return response.status_code in [200, 201]
        except:
            return False


@app.command()
def enterprise(
    clear: bool = typer.Option(False, "--clear", help="Clear existing data before indexing"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be indexed without doing it"),
    collection: Optional[str] = typer.Option(None, "--collection", help="Collection name to use"),
):
    """Index Enterprise source code repositories into Weaviate.
    
    Indexes all repositories matching the configured pattern.
    
    Use elysiactl_ENTERPRISE_DIR, elysiactl_REPO_PATTERN, elysiactl_EXCLUDE_PATTERN to customize.
    """
    config = get_config()
    if collection is None:
        collection = config.collections.default_source_collection
        
    enterprise_dir = Path(config.repositories.enterprise_dir)
    
    if not enterprise_dir.exists():
        console.print(f"[red]✗ Enterprise directory not found at {enterprise_dir}[/red]")
        console.print(f"[yellow]Set elysiactl_ENTERPRISE_DIR to customize location[/yellow]")
        raise typer.Exit(1)
    
    # Find all repos matching pattern, excluding obsolete ones
    all_repos = sorted([
        d for d in enterprise_dir.iterdir()
        if d.is_dir() 
        and d.name.startswith(config.repositories.repo_pattern)
        and config.repositories.exclude_pattern not in d.name
    ])
    
    if not all_repos:
        console.print("[yellow]No repositories found matching criteria[/yellow]")
        raise typer.Exit(0)
    
    # Display what will be indexed
    info_panel = Panel(
        f"[bold]Enterprise Source Code Indexing[/bold]\n\n"
        f"• Found: [cyan]{len(all_repos)}[/cyan] repositories\n"
        f"• Collection: [cyan]{collection}[/cyan]\n"
        f"• Pattern: [dim]{config.repositories.repo_pattern}* (excluding {config.repositories.exclude_pattern})[/dim]\n"
        f"• Clear existing: [cyan]{'Yes' if clear else 'No'}[/cyan]",
        title="Index Configuration",
        border_style="blue"
    )
    console.print(info_panel)
    
    if dry_run:
        console.print("\n[yellow]DRY RUN - Repositories that would be indexed:[/yellow]")
        for i, repo in enumerate(all_repos[:10], 1):
            console.print(f"  {i}. {repo.name}")
        if len(all_repos) > 10:
            console.print(f"  ... and {len(all_repos) - 10} more")
        raise typer.Exit(0)
    
    # Confirm before proceeding
    if not typer.confirm(f"\nProceed to index {len(all_repos)} repositories?"):
        console.print("[yellow]Indexing cancelled[/yellow]")
        raise typer.Exit(0)
    
    # Run the async indexing
    asyncio.run(index_enterprise_async(all_repos, collection, clear))


async def index_enterprise_async(repos: List[Path], collection_name: str, clear: bool):
    """Async function to index all Enterprise repositories."""
    
    # Ensure collection exists with proper schema
    console.print("\n[bold]Step 1/3: Verifying collection schema...[/bold]")
    if not await ensure_collection_schema(collection_name):
        console.print("[red]Failed to ensure collection schema[/red]")
        raise typer.Exit(1)
    
    # Clear existing data if requested
    if clear:
        console.print("\n[bold]Step 2/3: Clearing existing data...[/bold]")
        config = get_config()
        async with httpx.AsyncClient(timeout=config.processing.long_timeout) as client:
            try:
                # Delete all objects in collection
                response = await client.delete(
                    f"{config.services.weaviate_base_url}/schema/{collection_name}"
                )
                if response.status_code == 200:
                    console.print(f"[green]✓[/green] Cleared collection {collection_name}")
                    # Recreate the collection
                    await ensure_collection_schema(collection_name)
            except Exception as e:
                console.print(f"[yellow]⚠ Could not clear collection: {e}[/yellow]")
    else:
        console.print("\n[bold]Step 2/3: Skipping clear (append mode)...[/bold]")
    
    # Index repositories
    console.print("\n[bold]Step 3/3: Indexing repositories...[/bold]")
    
    total_indexed = 0
    total_failed = 0
    repo_stats = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        for repo in repos:
            repo_name = repo.name.replace(config.repositories.cleanup_pattern, "")
            task_id = progress.add_task(f"[cyan]{repo_name}[/cyan]", total=None)
            
            indexed, failed = await index_repository(repo, collection_name, progress, task_id)
            
            total_indexed += indexed
            total_failed += failed
            repo_stats.append((repo_name, indexed, failed))
            
            progress.remove_task(task_id)
    
    # Display summary
    console.print("\n" + "="*60)
    
    summary_table = Table(title="Indexing Summary", show_header=True, header_style="bold blue")
    summary_table.add_column("Repository", style="cyan")
    summary_table.add_column("Indexed", justify="right", style="green")
    summary_table.add_column("Failed", justify="right", style="red")
    
    # Show top 10 repos by file count
    for repo_name, indexed, failed in sorted(repo_stats, key=lambda x: x[1], reverse=True)[:10]:
        summary_table.add_row(repo_name, str(indexed), str(failed) if failed > 0 else "0")
    
    if len(repo_stats) > 10:
        summary_table.add_row("...", "...", "...")
    
    console.print(summary_table)
    
    # Final statistics
    stats_panel = Panel(
        f"[bold green]✓ Indexing Complete[/bold green]\n\n"
        f"• Repositories processed: [cyan]{len(repos)}[/cyan]\n"
        f"• Files indexed: [green]{total_indexed:,}[/green]\n"
        f"• Files failed: [red]{total_failed:,}[/red]\n"
        f"• Collection: [cyan]{collection_name}[/cyan]",
        title="Final Statistics",
        border_style="green"
    )
    console.print(stats_panel)
    
    # Verify collection count
    config = get_config()
    async with httpx.AsyncClient(timeout=config.processing.medium_timeout) as client:
        try:
            response = await client.post(
                f"{config.services.weaviate_base_url}/graphql",
                json={
                    "query": f"""
                    {{
                        Aggregate {{
                            {collection_name} {{
                                meta {{
                                    count
                                }}
                            }}
                        }}
                    }}
                    """
                }
            )
            if response.status_code == 200:
                data = response.json()
                count = data["data"]["Aggregate"][collection_name][0]["meta"]["count"]
                console.print(f"\n[dim]Collection now contains {count:,} documents[/dim]")
        except:
            pass


@app.command()
def sync(
    stdin: Annotated[bool, typer.Option("--stdin", help="Read file paths from standard input")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be changed without modifying Weaviate")] = False,
    collection: Annotated[Optional[str], typer.Option("--collection", help="Target collection name")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed progress for each file")] = False,
    # Performance options
    parallel: Annotated[bool, typer.Option("--parallel", help="Enable parallel processing")] = True,
    workers: Annotated[int, typer.Option("--workers", help="Number of parallel workers")] = 8,
    batch_size: Annotated[int, typer.Option("--batch-size", help="Batch size for processing")] = None,
    no_optimize: Annotated[bool, typer.Option("--no-optimize", help="Disable performance optimizations")] = False,
):
    """Sync file changes from stdin to Weaviate collection.
    
    Reads JSONL formatted changes from stdin and updates the Weaviate collection.
    Supports three content formats: content, content_base64, content_ref.
    """
    asyncio.run(sync_changes_async(stdin, collection, dry_run, verbose, parallel, workers, batch_size, no_optimize))


async def sync_changes_async(use_stdin: bool, collection_name: Optional[str], dry_run: bool, verbose: bool, parallel: bool, workers: int, batch_size: Optional[int], no_optimize: bool):
    """Async function to sync changes from stdin to Weaviate."""
    config = get_config()
    if collection_name is None:
        collection_name = config.collections.default_source_collection
    
    # Ensure collection exists
    if not await ensure_collection_schema(collection_name):
        console.print("[red]Failed to ensure collection schema[/red]")
        raise typer.Exit(1)
    
    # Use the async sync function directly
    return await sync_files_from_stdin_async(
        collection=collection_name,
        dry_run=dry_run,
        verbose=verbose,
        use_stdin=use_stdin,
        batch_size=batch_size,
        parallel=parallel and not no_optimize,
        max_workers=workers
    )


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


@app.command()
def status(
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Show status for specific run"),
    summary: bool = typer.Option(False, "--summary", help="Show summary of all runs"),
    failed: bool = typer.Option(False, "--failed", help="Show failed items from last run"),
    collection: Optional[str] = typer.Option(None, "--collection", help="Collection name to check (legacy)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format (legacy)"),
):
    """Show sync status and checkpoint information."""
    # Handle legacy collection status if requested
    if collection or json_output:
        asyncio.run(check_collection_status_async(collection, json_output))
        return
    
    checkpoint = SQLiteCheckpointManager()
    
    if summary:
        # Show overall summary
        summary_data = checkpoint.get_summary()
        console.print("\n[bold]Sync Summary:[/bold]")
        console.print(f"  Total runs: {summary_data['total_runs'] or 0}")
        console.print(f"  Active runs: {summary_data['active_runs'] or 0}")
        console.print(f"  Completed runs: {summary_data['completed_runs'] or 0}")
        console.print(f"  Total success: {summary_data['total_success'] or 0}")
        console.print(f"  Total errors: {summary_data['total_errors'] or 0}")
        console.print(f"  Last run: {summary_data['last_run'] or 'Never'}")
        return
    
    # Get target run ID
    if not run_id:
        run_id = checkpoint.get_active_run()
        if not run_id:
            console.print("[yellow]No active runs found[/yellow]")
            console.print("[dim]Use --summary to see all runs or start a new sync[/dim]")
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


async def check_collection_status_async(collection_name: Optional[str], json_output: bool):
    """Legacy function to check status of the source code collection."""
    config = get_config()
    if collection_name is None:
        collection_name = config.collections.default_source_collection
    
    async with httpx.AsyncClient(timeout=config.processing.medium_timeout) as client:
        try:
            # Check if collection exists
            schema_response = await client.get(f"{config.services.weaviate_base_url}/schema/{collection_name}")
            
            if schema_response.status_code != 200:
                if json_output:
                    console.print(json.dumps({"exists": False, "count": 0}))
                else:
                    console.print(f"[yellow]Collection {collection_name} does not exist[/yellow]")
                return
            
            # Get document count
            count_response = await client.post(
                f"{config.services.weaviate_base_url}/graphql",
                json={
                    "query": f"""
                    {{
                        Aggregate {{
                            {collection_name} {{
                                meta {{
                                    count
                                }}
                            }}
                        }}
                    }}
                    """
                }
            )
            
            if count_response.status_code == 200:
                data = count_response.json()
                count = data["data"]["Aggregate"][collection_name][0]["meta"]["count"]
                
                if json_output:
                    # Get schema info
                    schema = schema_response.json()
                    replication_factor = schema.get("replicationConfig", {}).get("factor", 1)
                    
                    output = {
                        "exists": True,
                        "collection": collection_name,
                        "count": count,
                        "replication_factor": replication_factor
                    }
                    console.print(json.dumps(output, indent=2))
                else:
                    # Pretty display
                    schema = schema_response.json()
                    replication_factor = schema.get("replicationConfig", {}).get("factor", 1)
                    
                    status_panel = Panel(
                        f"[bold]Collection Status[/bold]\n\n"
                        f"• Name: [cyan]{collection_name}[/cyan]\n"
                        f"• Documents: [green]{count:,}[/green]\n"
                        f"• Replication: factor=[cyan]{replication_factor}[/cyan]\n"
                        f"• Status: [green]✓ Active[/green]",
                        title="Source Code Index",
                        border_style="green"
                    )
                    console.print(status_panel)
            
        except Exception as e:
            if json_output:
                console.print(json.dumps({"error": str(e)}))
            else:
                console.print(f"[red]✗ Error checking status: {e}[/red]")


@app.command()
def analyze(
    paths: List[str],
    summary: bool = typer.Option(False, "--summary", help="Show predicted strategy statistics"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed analysis per file"),
):
    """Analyze local files and predict mgit's content strategy."""
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
        if total_files > 0:
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
    jsonl_file: str,
    show_stats: bool = typer.Option(False, "--stats", help="Show content strategy statistics"),
    show_content: bool = typer.Option(False, "--content", help="Show actual resolved content"),
):
    """Inspect mgit JSONL output and analyze content strategies."""
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
                    content = _resolve_content(change)
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
            if total_changes > 0:
                embedded_count = strategy_counts[1] + strategy_counts[2]
                
                console.print(f"\n[bold]Summary:[/bold]")
                console.print(f"  Total changes: {total_changes}")
                console.print(f"  Content embedded: {embedded_count} ({embedded_count/total_changes*100:.1f}%)")
                console.print(f"  Embedded size: {total_size['embedded']:,} chars")
                console.print(f"  File references: {total_size['references']}")
    
    except Exception as e:
        console.print(f"[red]Failed to analyze {jsonl_file}: {e}[/red]")


@app.command()
def errors(
    recent: Annotated[int, typer.Option("--recent", help="Show N recent errors")] = 10,
    summary: Annotated[bool, typer.Option("--summary", help="Show error summary statistics")] = False,
    reset: Annotated[bool, typer.Option("--reset", help="Reset error statistics")] = False,
):
    """Show error statistics and recent failures."""
    from ..services.error_handling import get_error_handler_with_config
    from rich.table import Table
    
    error_handler = get_error_handler_with_config()
    
    if reset:
        error_handler.reset_statistics()
        console.print("[green]Error statistics reset[/green]")
        return
    
    if summary:
        summary_data = error_handler.get_error_summary()
        
        console.print("\n[bold]Error Summary:[/bold]")
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
                table.add_column(category, style="cyan")
                table.add_column(str(count), style="red", justify="right")
            
            console.print(table)
        
        # Circuit breaker status
        cb_states = summary_data['circuit_breaker_states']
        if cb_states:
            console.print("\n[bold]Circuit Breaker Status:[/bold]")
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


@app.command()
def perf(
    show_config: Annotated[bool, typer.Option("--config", help="Show performance configuration")] = False,
    benchmark: Annotated[bool, typer.Option("--benchmark", help="Run performance benchmark")] = False,
    workers: Annotated[int, typer.Option("--workers", help="Number of parallel workers")] = 8,
    batch_size: Annotated[int, typer.Option("--batch-size", help="Batch size for processing")] = 100,
):
    """Performance monitoring and tuning commands."""
    from ..services.performance import get_performance_optimizer
    
    if show_config:
        config = get_performance_optimizer().get_performance_summary()
        
        console.print("\n[bold]Performance Configuration:[/bold]")
        opt_config = config.get('optimization_config', {})
        for key, value in opt_config.items():
            console.print(f"  {key}: {value}")
        
        return
    
    if benchmark:
        console.print("[yellow]Running performance benchmark...[/yellow]")
        
        # Create test files
        import tempfile
        import os
        
        test_files = []
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files of various sizes
            for i in range(50):
                file_path = os.path.join(temp_dir, f"test_{i}.py")
                content_size = 1000 + (i * 100)  # Varying sizes
                content = f"# Test file {i}\n" + ("def func():\n    pass\n" * (content_size // 20))
                
                with open(file_path, 'w') as f:
                    f.write(content)
                test_files.append(file_path)
            
            # Run benchmark
            import time
            start_time = time.time()
            
            # Test with different configurations
            test_input = "\n".join(test_files)
            
            # Simulate sync
            result = subprocess.run([
                "uv", "run", "elysiactl", "index", "sync",
                "--stdin", "--dry-run", "--parallel", f"--workers={workers}", f"--batch-size={batch_size}"
            ], 
            input=test_input, 
            text=True, 
            capture_output=True,
            cwd=str(Path(__file__).parent.parent.parent)
            )
            
            duration = time.time() - start_time
            files_per_second = len(test_files) / duration
            
            console.print(f"\n[bold]Benchmark Results:[/bold]")
            console.print(f"  Files processed: {len(test_files)}")
            console.print(f"  Duration: {duration:.2f}s") 
            console.print(f"  Files/second: {files_per_second:.1f}")
            console.print(f"  Workers: {workers}")
            console.print(f"  Batch size: {batch_size}")


@app.command()
def tune(
    target_files: Annotated[int, typer.Option("--target-files", help="Target number of files to optimize for")] = 10000,
    target_time: Annotated[int, typer.Option("--target-time", help="Target completion time in seconds")] = 300,
):
    """Auto-tune performance parameters for target workload."""
    console.print(f"[blue]Auto-tuning for {target_files} files in {target_time}s...[/blue]")
    
    # Calculate optimal parameters
    target_files_per_second = target_files / target_time
    
    # Estimate optimal worker count (rule of thumb: 2x CPU cores, max 16)
    import os
    cpu_count = os.cpu_count() or 4
    optimal_workers = min(16, max(4, cpu_count * 2))
    
    # Estimate optimal batch size
    optimal_batch_size = max(50, min(200, target_files // (optimal_workers * 10)))
    
    console.print(f"\n[bold]Recommended Configuration:[/bold]")
    console.print(f"  Workers: {optimal_workers}")
    console.print(f"  Batch size: {optimal_batch_size}")
    console.print(f"  Expected throughput: {target_files_per_second:.1f} files/second")
    
    # Environment variable suggestions
    console.print(f"\n[bold]Environment Variables:[/bold]")
    console.print(f"  export elysiactl_MAX_WORKERS={optimal_workers}")
    console.print(f"  export elysiactl_BATCH_SIZE={optimal_batch_size}")
    console.print(f"  export elysiactl_MAX_CONNECTIONS=20")


if __name__ == "__main__":
    app()