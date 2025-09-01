"""Index command for managing source code collections in Weaviate."""

import os
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import json

import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box

from ..config import get_config

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
def status(
    collection: Optional[str] = typer.Option(None, "--collection", help="Collection name to check"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Check the status of indexed source code collections."""
    asyncio.run(check_status_async(collection, json_output))


async def check_status_async(collection_name: Optional[str], json_output: bool):
    """Check status of the source code collection."""
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


if __name__ == "__main__":
    app()