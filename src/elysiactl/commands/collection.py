"""Collection management commands for elysiactl."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path

from ..services.weaviate_collections import (
    WeaviateCollectionManager,
    CollectionNotFoundError
)
from ..services.backup_restore import BackupManager, RestoreManager, ClearManager

app = typer.Typer(help="Manage Weaviate collections")
console = Console()

# Initialize services
manager = WeaviateCollectionManager()
backup_manager = BackupManager()
restore_manager = RestoreManager()
clear_manager = ClearManager()


def print_error(message: str):
    """Print error message in red."""
    console.print(f"[red]✗ {message}[/red]")


def print_success(message: str):
    """Print success message in green."""
    console.print(f"[green]✓ {message}[/green]")


@app.command("ls", help="List all collections")
def list_collections(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
    filter: str = typer.Option(None, "--filter", help="Filter collections by pattern")
):
    """List all Weaviate collections with optional filtering."""
    try:
        collections = manager.list_collections(filter_pattern=filter)

        if format == "json":
            import json
            console.print(json.dumps(collections, indent=2))
            return

        if not collections:
            console.print("[yellow]No collections found[/yellow]")
            return

        # Create table
        table = Table(title=f"Collections ({len(collections)} total)")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Objects", style="green", justify="right")
        table.add_column("Replicas", style="blue", justify="center")
        table.add_column("Shards", style="magenta", justify="center")
        table.add_column("Status", style="yellow")

        if verbose:
            table.add_column("Vectorizer", style="dim")
            table.add_column("Properties", style="dim", justify="center")

        for col in collections:
            name = col["class"]
            objects = f"{col['object_count']:,}"
            replicas = str(col.get("replicationConfig", {}).get("factor", 1))
            shards = str(col.get("shardingConfig", {}).get("desiredCount", 1))
            status = "READY"  # Assume ready if we can see it

            row = [name, objects, replicas, shards, status]

            if verbose:
                vectorizer = col.get("vectorizer", "unknown")[:20]  # Truncate
                properties = str(len(col.get("properties", [])))
                row.extend([vectorizer, properties])

            table.add_row(*row)

        console.print(table)

    except Exception as e:
        print_error(f"Failed to list collections: {e}")
        raise typer.Exit(1)


@app.command("show", help="Show detailed collection information")
def show_collection(
    name: str = typer.Argument(..., help="Collection name"),
    schema: bool = typer.Option(False, "--schema", help="Include schema information"),
    stats: bool = typer.Option(False, "--stats", help="Include detailed statistics"),
    format: str = typer.Option("table", "--format", help="Output format")
):
    """Display detailed information about a specific collection."""
    try:
        collection_info = manager.get_collection_info(name)

        if format == "json":
            import json
            console.print(json.dumps(collection_info, indent=2))
            return

        # Create info panel
        info_lines = [
            f"[bold]Collection:[/bold] {collection_info['name']}",
            "[bold]Status:[/bold] READY",
            f"[bold]Objects:[/bold] {collection_info['object_count']:,}",
            f"[bold]Replicas:[/bold] {collection_info['replicas']}",
            f"[bold]Shards:[/bold] {collection_info['shards']}",
            f"[bold]Vectorizer:[/bold] {collection_info['vectorizer']}",
            f"[bold]Properties:[/bold] {collection_info['properties']}",
            f"[bold]Protected:[/bold] {'Yes' if collection_info['protected'] else 'No'}",
        ]

        panel = Panel(
            "\n".join(info_lines),
            title="Collection Details",
            border_style="blue"
        )
        console.print(panel)

        if schema:
            # Show schema details
            collection = manager.get_collection(name)
            console.print("\n[bold]Schema Properties:[/bold]")

            schema_table = Table()
            schema_table.add_column("Property", style="cyan")
            schema_table.add_column("Type", style="green")
            schema_table.add_column("Description", style="dim")

            for prop in collection.get("properties", []):
                prop_name = prop["name"]
                prop_type = ", ".join(prop["dataType"])
                prop_desc = prop.get("description", "")[:50]
                schema_table.add_row(prop_name, prop_type, prop_desc)

            console.print(schema_table)

    except CollectionNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Failed to show collection: {e}")
        raise typer.Exit(1)


@app.command("backup", help="Backup a collection")
def backup_collection(
    name: str = typer.Argument(..., help="Collection name to backup"),
    output: Path = typer.Option("./backups", "--output", "-o", help="Output directory"),
    include_data: bool = typer.Option(False, "--include-data", help="Include object data in backup"),
    include_vectors: bool = typer.Option(False, "--include-vectors", help="Include vector embeddings (increases size significantly)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be backed up")
):
    """Backup collection schema or full data."""
    try:
        if include_data:
            result = backup_manager.backup_with_data(name, output, dry_run, include_vectors)
            if result and not dry_run:
                print_success(f"Full backup completed: {result}")
        else:
            result = backup_manager.backup_schema_only(name, output, dry_run)
            if result and not dry_run:
                print_success(f"Schema backup completed: {result}")

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Backup failed: {e}")
        raise typer.Exit(1)


@app.command("restore", help="Restore a collection from backup")
def restore_collection(
    backup_file: Path = typer.Argument(..., help="Path to backup file"),
    name: str = typer.Option(None, "--name", help="Override collection name"),
    skip_data: bool = typer.Option(False, "--skip-data", help="Restore schema only"),
    merge: bool = typer.Option(False, "--merge", help="Merge with existing collection (Phase 2D)"),
):
    """Restore collection from backup file."""
    try:
        success = restore_manager.restore_collection(backup_file, name, skip_data, merge, dry_run)

        if success and not dry_run:
            collection_name = name or "original name"
            if skip_data:
                print_success(f"Schema-only restore completed to '{collection_name}'")
            elif merge:
                print_success(f"Merge restore completed to '{collection_name}'")
            else:
                print_success(f"Full restore completed to '{collection_name}'")
        elif dry_run:
            console.print("[blue]Dry run completed - no changes made[/blue]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except ValueError as e:
        print_error(f"Invalid backup file: {e}")
        raise typer.Exit(1)
@app.command("clear", help="Clear all objects from a collection")
def clear_collection(
    name: str = typer.Argument(..., help="Collection name to clear"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompts"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be cleared")
):
    """Clear all objects from a collection with safety checks."""
    try:
        success = clear_manager.clear_collection(name, force, dry_run)
        
        if success and not dry_run:
            print_success(f"Collection '{name}' cleared successfully")
        elif dry_run:
            console.print("[blue]Dry run completed - no changes made[/blue]")
            
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Clear failed: {e}")
        raise typer.Exit(1)


@app.command("create", help="Create a new collection")
def create_collection(
    name: str = typer.Argument(..., help="Collection name"),
    replication: int = typer.Option(3, "--replication", help="Replication factor"),
    shards: int = typer.Option(1, "--shards", help="Number of shards"),
    vectorizer: str = typer.Option("text2vec-openai", "--vectorizer", help="Vectorizer to use")
):
    """Create a new Weaviate collection with specified configuration."""
    try:
        # Check if collection already exists
        try:
            manager.get_collection(name)
            print_error(f"Collection '{name}' already exists")
            raise typer.Exit(1)
        except CollectionNotFoundError:
            pass  # Good, it doesn't exist

        # Create default schema
        schema = {
            "class": name,
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Main content field"
                }
            ],
            "replicationConfig": {
                "factor": replication
            },
            "shardingConfig": {
                "desiredCount": shards
            },
            "vectorizer": vectorizer
        }

        # Create collection
        success = manager.create_collection(schema)

        if success:
            print_success(f"Collection '{name}' created successfully")
            console.print(f"  Replicas: {replication}")
            console.print(f"  Shards: {shards}")
            console.print(f"  Vectorizer: {vectorizer}")
        else:
            print_error(f"Failed to create collection '{name}'")

    except Exception as e:
        print_error(f"Failed to create collection: {e}")
        raise typer.Exit(1)


@app.command("rm", help="Remove a collection")
def remove_collection(
    name: str = typer.Argument(..., help="Collection name"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation and override protection"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted")
):
    """Remove a Weaviate collection with safety checks."""
    try:
        # Get collection info first
        try:
            collection_info = manager.get_collection_info(name)
        except CollectionNotFoundError as e:
            print_error(str(e))
            console.print("[dim]Use 'elysiactl col ls' to see available collections[/dim]")
            raise typer.Exit(1)

        # Check protection
        if not force and collection_info["protected"]:
            print_error(f"Collection '{name}' is protected and cannot be modified")
            console.print("[dim]Use --force to override protection[/dim]")
            raise typer.Exit(1)

        # Dry run mode
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would delete collection '{name}'[/yellow]")
            console.print(f"  Objects: {collection_info['object_count']:,}")
            console.print(f"  Replicas: {collection_info['replicas']}")
            console.print(f"  Shards: {collection_info['shards']}")
            console.print(f"  Protected: {'Yes' if collection_info['protected'] else 'No'}")
            return

        # Interactive confirmation
        if not force:
            console.print(f"[yellow]⚠ WARNING: This will permanently delete collection '{name}'[/yellow]")
            console.print(f"  Objects: {collection_info['object_count']:,}")
            console.print(f"  Replicas: {collection_info['replicas']}")
            console.print(f"  Shards: {collection_info['shards']}")
            console.print(f"  Protected: {'Yes' if collection_info['protected'] else 'No'}")

            response = typer.prompt("\nType 'yes' to confirm deletion", default="no")
            if response.lower() != 'yes':
                console.print("[blue]Deletion cancelled[/blue]")
                return

        # Delete collection
        success = manager.delete_collection(name)

        if success:
            print_success(f"Collection '{name}' deleted successfully")
        else:
            print_error(f"Failed to delete collection '{name}'")

    except Exception as e:
        print_error(f"Failed to delete collection: {e}")
        raise typer.Exit(1)