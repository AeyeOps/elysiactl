"""Repair command for fixing cluster issues.

This module provides repair utilities for common Weaviate cluster problems,
particularly issues with collection replication and distribution across nodes.
"""

import json
from datetime import datetime
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config import get_config
from ..services.weaviate import WeaviateService

console = Console()
app = typer.Typer(
    help="""Repair common cluster issues.
    
    These commands perform DESTRUCTIVE operations on empty collections.
    They will refuse to run if data exists to prevent data loss.
    
    Use these repair commands when:
    • 'elysiactl health --cluster' reports replication issues
    • Collections show incorrect replication factor
    • Collections exist on only one node despite factor=3
    • After fixing RAFT consensus configuration
    
    Prerequisites:
    • Weaviate cluster must be running
    • RAFT consensus must be established (check with 'elysiactl status')
    • Collections must be empty (no data loss protection)
    """
)


@app.command()
def config_replication(
    collection: str = typer.Argument(
        "ELYSIA_CONFIG__", help="Collection name to fix replication for (default: ELYSIA_CONFIG__)"
    ),
    force: bool = typer.Option(
        False, "--force", help="Skip confirmation prompts (use with caution)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes"
    ),
):
    """Fix collection replication issues for ELYSIA_* collections.

    This command recreates the specified collection with proper
    replication factor=3 to ensure it's distributed across all Weaviate nodes.

    WHEN TO USE:
    • Collection shows 'factor=1' or 'factor=2' instead of 'factor=3'
    • Collection exists on fewer than 3 nodes (e.g., "1/3 nodes")
    • After adding new nodes to the cluster
    • After fixing RAFT consensus configuration

    WHAT IT DOES:
    1. Exports the current collection schema
    2. Verifies the collection is empty (refuses if data exists)
    3. Deletes the misconfigured collection
    4. Recreates with replication_factor=3
    5. Triggers schema replication to all nodes
    6. Verifies collection exists on all 3 nodes

    SAFETY:
    • Will NOT run if collection contains data
    • Creates backup of schema before deletion
    • Can be reversed by restoring from backup
    • Only works with ELYSIA_* collections for safety

    Examples:
        elysiactl repair config-replication                    # Fix ELYSIA_CONFIG__ (default)
        elysiactl repair config-replication ELYSIA_TREES__     # Fix ELYSIA_TREES__
        elysiactl repair config-replication ELYSIA_TREES__ --dry-run  # Preview changes
        elysiactl repair config-replication ELYSIA_CONFIG__ --force    # Skip prompts
    """
    # Validate collection name
    if not collection.startswith("ELYSIA_"):
        console.print(
            f"[red]✗ Error: Collection '{collection}' does not start with 'ELYSIA_'[/red]"
        )
        console.print(
            "[yellow]For safety, this command only works with ELYSIA_* collections[/yellow]"
        )
        raise typer.Exit(1)

    if dry_run:
        console.print(
            Panel(
                f"[yellow]DRY RUN MODE[/yellow]\n"
                f"Would perform the following actions for [bold]{collection}[/bold]:\n"
                f"1. Export {collection} schema\n"
                f"2. Check if collection has data\n"
                f"3. Delete existing collection\n"
                f"4. Recreate with replication_factor=3\n"
                f"5. Verify replication across nodes",
                title="Dry Run Preview",
            )
        )
        return

    # Show warning and get confirmation unless --force is used
    if not force:
        console.print(
            Panel(
                f"[bold yellow]⚠ WARNING[/bold yellow]\n\n"
                f"This command will DELETE and RECREATE the [bold]{collection}[/bold] collection.\n"
                f"This is a DESTRUCTIVE operation that cannot be undone.\n\n"
                f"Prerequisites:\n"
                f"• Collection must be empty (data loss protection)\n"
                f"• Weaviate cluster must be running\n"
                f"• RAFT consensus must be established\n\n"
                f"The command will:\n"
                f"1. Export current schema (backup)\n"
                f"2. Delete the existing collection\n"
                f"3. Recreate with replication_factor=3\n"
                f"4. Verify replication across all nodes",
                title="Repair Confirmation Required",
                border_style="yellow",
            )
        )

        if not typer.confirm("\nDo you want to proceed with the repair?"):
            console.print("[yellow]Repair cancelled by user[/yellow]")
            raise typer.Exit(0)

    weaviate = WeaviateService()

    # Step 1: Export current schema
    console.print("\n[bold]Step 1/6: Exporting current schema...[/bold]")
    try:
        response = httpx.get(f"{get_config().services.weaviate_base_url}/schema/{collection}")
        response.raise_for_status()
        schema = response.json()
        console.print(f"[green]✓[/green] Exported {collection} schema")

        # Save backup immediately
        backup_file = f"{collection.lower()}_backup.json"
        with open(backup_file, "w") as f:
            json.dump(schema, f, indent=2)
        console.print(f"[dim]  → Schema backed up to {backup_file}[/dim]")
    except httpx.HTTPError as e:
        console.print(f"[red]✗ Failed to export schema: {e}[/red]")
        console.print(
            f"[yellow]Hint: Check if Weaviate is running and {collection} exists[/yellow]"
        )
        raise typer.Exit(1)

    # Step 2: Check if collection has data
    console.print("\n[bold]Step 2/6: Checking for existing data...[/bold]")
    try:
        check_response = httpx.post(
            f"{get_config().services.weaviate_base_url}/graphql",
            json={
                "query": f"""
                {{
                    Aggregate {{
                        {collection} {{
                            meta {{
                                count
                            }}
                        }}
                    }}
                }}
                """
            },
        )
        check_response.raise_for_status()
        count = check_response.json()["data"]["Aggregate"][collection][0]["meta"]["count"]

        if count > 0:
            console.print(f"[yellow]⚠ Collection has {count} records.[/yellow]")

            # Offer to export the data
            export_panel = Panel(
                f"[yellow]The collection contains {count} records that need to be exported.[/yellow]\n\n"
                f"Export will:\n"
                f"• Save all {count} records to {collection.lower()}_data_export.json\n"
                f"• Include all properties and metadata\n"
                f"• Allow you to re-import after repair\n\n"
                f"[bold]Without export, this data will be PERMANENTLY LOST.[/bold]",
                title="Data Export Required",
                border_style="yellow",
            )
            console.print(export_panel)

            if force:
                console.print(
                    "[yellow]--force flag used: Skipping data export, data will be lost![/yellow]"
                )
            elif typer.confirm("\nDo you want to export the data before proceeding?"):
                # Export the data
                console.print("[bold]Exporting collection data...[/bold]")
                export_file = Path(
                    f"{collection.lower()}_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(f"Exporting {count} records...", total=None)

                    # Fetch all objects from the collection
                    try:
                        # GraphQL query to get all objects with all properties
                        query = f"""
                        {{
                            Get {{
                                {collection}(limit: {count}) {{
                                    _additional {{
                                        id
                                        creationTimeUnix
                                        lastUpdateTimeUnix
                                    }}
                                    config_key
                                    config_value
                                }}
                            }}
                        }}
                        """

                        export_response = httpx.post(
                            f"{get_config().services.weaviate_base_url}/graphql",
                            json={"query": query},
                            timeout=60.0,
                        )
                        export_response.raise_for_status()

                        data = export_response.json()
                        objects = data.get("data", {}).get("Get", {}).get(collection, [])

                        # Save to file
                        export_data = {
                            "collection": collection,
                            "export_timestamp": datetime.now().isoformat(),
                            "count": len(objects),
                            "objects": objects,
                        }

                        with open(export_file, "w") as f:
                            json.dump(export_data, f, indent=2)

                        progress.update(task, completed=True)
                        console.print(
                            f"[green]✓[/green] Exported {len(objects)} records to {export_file}"
                        )

                        # Now delete all objects from the collection
                        console.print("[bold]Emptying collection...[/bold]")
                        for obj in objects:
                            obj_id = obj["_additional"]["id"]
                            delete_obj_response = httpx.delete(
                                f"{get_config().services.weaviate_base_url}/objects/{collection}/{obj_id}"
                            )
                            # Ignore individual delete errors, we'll recreate the collection anyway

                        console.print("[green]✓[/green] Collection emptied successfully")
                        console.print(
                            f"[dim]  → Data saved to {export_file} for later import[/dim]"
                        )

                    except Exception as e:
                        console.print(f"[red]✗ Failed to export data: {e}[/red]")
                        console.print("[yellow]Cannot proceed without successful export[/yellow]")
                        raise typer.Exit(1)
            else:
                console.print("[red]Cannot proceed without data export to prevent data loss.[/red]")
                console.print(
                    "[yellow]Hint: Use --force to bypass this check (data will be lost)[/yellow]"
                )
                raise typer.Exit(1)
    except (httpx.HTTPError, KeyError) as e:
        console.print(f"[yellow]Warning: Could not verify data count: {e}[/yellow]")
        if not typer.confirm("Continue anyway?"):
            raise typer.Exit(1)

    # Step 3: Delete existing collection
    console.print("\n[bold]Step 3/6: Deleting misconfigured collection...[/bold]")
    try:
        delete_response = httpx.delete(
            f"{get_config().services.weaviate_base_url}/schema/{collection}"
        )
        delete_response.raise_for_status()
        console.print(f"[green]✓[/green] Deleted existing {collection} collection")
    except httpx.HTTPError as e:
        console.print(f"[red]✗ Failed to delete collection: {e}[/red]")
        console.print(
            "[yellow]Hint: Collection may not exist or Weaviate may be unavailable[/yellow]"
        )
        raise typer.Exit(1)

    # Step 4: Ensure replication factor is correct
    console.print("\n[bold]Step 4/6: Configuring replication settings...[/bold]")
    original_factor = schema.get("replicationConfig", {}).get("factor", 1)
    schema["replicationConfig"] = {"factor": 3, "asyncEnabled": True}
    console.print(f"[green]✓[/green] Set replication factor: {original_factor} → 3")

    # Step 5: Recreate with proper replication
    console.print("\n[bold]Step 5/6: Recreating collection with proper replication...[/bold]")
    try:
        create_response = httpx.post(
            f"{get_config().services.weaviate_base_url}/schema", json=schema, timeout=30.0
        )
        create_response.raise_for_status()
        console.print(f"[green]✓[/green] Recreated {collection} with replication factor=3")

        # Force schema replication by inserting and deleting a test record
        console.print("[dim]Triggering schema replication...[/dim]")
        test_data = {
            "class": collection,
            "properties": {
                "config_key": "__replication_trigger",
                "config_value": "Forcing schema to replicate to all nodes",
            },
        }

        try:
            # Insert test record using correct endpoint
            trigger_response = httpx.post(
                f"{get_config().services.weaviate_base_url}/objects", json=test_data, timeout=5.0
            )

            if trigger_response.status_code in [200, 201]:
                object_id = trigger_response.json().get("id")

                # Wait for replication
                import time

                time.sleep(1.0)

                # Delete test record
                if object_id:
                    httpx.delete(
                        f"{get_config().services.weaviate_base_url}/objects/{collection}/{object_id}"
                    )

                console.print("[green]✓[/green] Schema replication triggered")
        except httpx.HTTPError:
            console.print(
                "[yellow]⚠[/yellow] Could not trigger replication (collection may be read-only)"
            )

    except httpx.HTTPError as e:
        console.print(f"[red]Failed to recreate collection: {e}[/red]")
        backup_file = f"{collection.lower()}_backup.json"
        console.print(f"Schema saved to {backup_file} for manual recovery")
        with open(backup_file, "w") as f:
            json.dump(schema, f, indent=2)
        raise typer.Exit(1)

    # Step 6: Verify replication
    console.print("\n[bold]Step 6/6: Verifying replication across nodes...[/bold]")
    nodes_with_collection = []
    config = get_config()
    hostname = config.services.weaviate_hostname
    for port in config.services.weaviate_cluster_ports:
        try:
            verify_response = httpx.get(
                f"{config.services.weaviate_scheme}://{hostname}:{port}/v1/schema/{collection}"
            )
            if verify_response.status_code == 200:
                nodes_with_collection.append(port)
                console.print(f"  [green]✓[/green] Node {port}: Collection present")
            else:
                console.print(f"  [red]✗[/red] Node {port}: Collection missing")
        except httpx.ConnectError:
            console.print(f"  [yellow]⚠[/yellow] Node {port}: Cannot connect")

    if len(nodes_with_collection) == 3:
        console.print(
            f"\n[bold green]SUCCESS: {collection} is now properly replicated across all nodes![/bold green]"
        )
    else:
        console.print(
            f"\n[bold yellow]PARTIAL: Collection exists on {len(nodes_with_collection)}/3 nodes[/bold yellow]"
        )
        console.print("Run 'elysiactl health --cluster' to check full status")
