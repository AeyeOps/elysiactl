# Phase 1: Fix ELYSIA_CONFIG__ Replication

## Objective
Recreate ELYSIA_CONFIG__ collection with proper replication factor to ensure it's distributed across all three Weaviate nodes.

## Problem Summary
The ELYSIA_CONFIG__ collection has replication factor=3 configured but only exists on node 8080 (port). This creates a single point of failure. The collection is currently empty, making it safe to recreate.

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/commands/repair.py` (NEW)

**Change 1: Create repair command**
**Location:** New file
**Code:**
```python
"""Repair command for fixing cluster issues."""
import typer
import httpx
import json
from rich.console import Console
from ..services.weaviate import WeaviateService

console = Console()
app = typer.Typer()

@app.command()
def config_replication():
    """Fix ELYSIA_CONFIG__ replication by recreating with proper factor."""
    weaviate = WeaviateService()
    
    # Step 1: Export current schema
    try:
        response = httpx.get("http://localhost:8080/v1/schema/ELYSIA_CONFIG__")
        response.raise_for_status()
        schema = response.json()
        console.print("[green]✓[/green] Exported ELYSIA_CONFIG__ schema")
    except httpx.HTTPError as e:
        console.print(f"[red]Failed to export schema: {e}[/red]")
        raise typer.Exit(1)
    
    # Step 2: Check if collection has data
    try:
        check_response = httpx.post(
            "http://localhost:8080/v1/graphql",
            json={
                "query": """
                {
                    Aggregate {
                        ELYSIA_CONFIG__ {
                            meta {
                                count
                            }
                        }
                    }
                }
                """
            }
        )
        check_response.raise_for_status()
        count = check_response.json()["data"]["Aggregate"]["ELYSIA_CONFIG__"][0]["meta"]["count"]
        
        if count > 0:
            console.print(f"[yellow]⚠ Collection has {count} records. Aborting to prevent data loss.[/yellow]")
            console.print("Use manual export/import for collections with data.")
            raise typer.Exit(1)
    except (httpx.HTTPError, KeyError) as e:
        console.print(f"[yellow]Warning: Could not verify data count: {e}[/yellow]")
        if not typer.confirm("Continue anyway?"):
            raise typer.Exit(1)
    
    # Step 3: Delete existing collection
    try:
        delete_response = httpx.delete("http://localhost:8080/v1/schema/ELYSIA_CONFIG__")
        delete_response.raise_for_status()
        console.print("[green]✓[/green] Deleted existing ELYSIA_CONFIG__ collection")
    except httpx.HTTPError as e:
        console.print(f"[red]Failed to delete collection: {e}[/red]")
        raise typer.Exit(1)
    
    # Step 4: Ensure replication factor is correct
    schema["replicationConfig"]["factor"] = 3
    
    # Step 5: Recreate with proper replication
    try:
        create_response = httpx.post(
            "http://localhost:8080/v1/schema",
            json=schema,
            timeout=30.0
        )
        create_response.raise_for_status()
        console.print("[green]✓[/green] Recreated ELYSIA_CONFIG__ with replication factor=3")
    except httpx.HTTPError as e:
        console.print(f"[red]Failed to recreate collection: {e}[/red]")
        console.print("Schema saved to elysia_config_backup.json for manual recovery")
        with open("elysia_config_backup.json", "w") as f:
            json.dump(schema, f, indent=2)
        raise typer.Exit(1)
    
    # Step 6: Verify replication
    console.print("\n[bold]Verifying replication across nodes...[/bold]")
    nodes_with_collection = []
    for port in [8080, 8081, 8082]:
        try:
            verify_response = httpx.get(f"http://localhost:{port}/v1/schema/ELYSIA_CONFIG__")
            if verify_response.status_code == 200:
                nodes_with_collection.append(port)
                console.print(f"  [green]✓[/green] Node {port}: Collection present")
            else:
                console.print(f"  [red]✗[/red] Node {port}: Collection missing")
        except httpx.ConnectError:
            console.print(f"  [yellow]⚠[/yellow] Node {port}: Cannot connect")
    
    if len(nodes_with_collection) == 3:
        console.print("\n[bold green]SUCCESS: ELYSIA_CONFIG__ is now properly replicated across all nodes![/bold green]")
    else:
        console.print(f"\n[bold yellow]PARTIAL: Collection exists on {len(nodes_with_collection)}/3 nodes[/bold yellow]")
        console.print("Run 'elysiactl health --cluster' to check full status")
```

### File: `/opt/elysiactl/src/elysiactl/cli.py`

**Change 2: Add repair command to CLI**
**Location:** Line 10 (after health import)
**Current Code:**
```python
from .commands.health import health_command
```

**New Code:**
```python
from .commands.health import health_command
from .commands.repair import app as repair_app
```

**Change 3: Register repair command**
**Location:** Line 16 (after app initialization)
**Current Code:**
```python
app = typer.Typer(
    name="elysiactl",
    help="Control utility for managing Elysia AI and Weaviate services",
    no_args_is_help=True,
)
```

**New Code:**
```python
app = typer.Typer(
    name="elysiactl",
    help="Control utility for managing Elysia AI and Weaviate services",
    no_args_is_help=True,
)

app.add_typer(repair_app, name="repair", help="Repair cluster issues")
```

## Agent Workflow

### Step 1: Create repair command file
1. Create `/opt/elysiactl/src/elysiactl/commands/repair.py` with the code above
2. Ensure proper imports are present
3. Save the file

### Step 2: Update CLI to include repair command
1. Open `/opt/elysiactl/src/elysiactl/cli.py`
2. Add import for repair command after line 10
3. Register the repair subcommand after line 16
4. Save the file

### Step 3: Test the implementation
1. Verify cluster is running: `uv run elysiactl status`
2. Check current state: `uv run elysiactl health --cluster`
3. Run the repair: `uv run elysiactl repair config-replication`
4. Verify success: `uv run elysiactl health --cluster`

## Testing

### Pre-conditions
```bash
# Ensure Weaviate cluster is running
uv run elysiactl status

# Verify the issue exists
uv run elysiactl health --cluster | grep "ELYSIA_CONFIG__"
# Should show: "1/3 nodes"
```

### Execution
```bash
# Run the repair command
uv run elysiactl repair config-replication
```

### Post-conditions
```bash
# Verify the fix
uv run elysiactl health --cluster | grep "ELYSIA_CONFIG__"
# Should show: "3/3 nodes" or "factor=3 ✓"

# Check each node directly
curl -s http://localhost:8080/v1/schema | grep ELYSIA_CONFIG__
curl -s http://localhost:8081/v1/schema | grep ELYSIA_CONFIG__
curl -s http://localhost:8082/v1/schema | grep ELYSIA_CONFIG__
```

## Success Criteria
- [ ] `repair config-replication` command executes without errors
- [ ] ELYSIA_CONFIG__ exists on all three nodes (8080, 8081, 8082)
- [ ] Collection has replication factor=3
- [ ] `elysiactl health --cluster` shows no replication issues for ELYSIA_CONFIG__
- [ ] Command safely aborts if collection has data
- [ ] Backup schema is saved if recreation fails

## Rollback Plan
If the repair fails:
1. Schema is automatically saved to `elysia_config_backup.json`
2. Manually recreate using: `curl -X POST http://localhost:8080/v1/schema -H "Content-Type: application/json" -d @elysia_config_backup.json`
3. The original collection is only deleted if it's empty, preventing data loss

## Notes
- This is a safe operation because ELYSIA_CONFIG__ is currently empty
- The command includes safety checks to prevent data loss
- Creates a focused repair command rather than generic "fix everything"
- Follows the "explicit over magic" principle from ADR-001