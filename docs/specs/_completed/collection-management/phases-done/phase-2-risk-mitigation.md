# Phase 2D: Collection Clear + Advanced Restore
## Objective
Implement collection clear functionality and enhanced restore features.

## Commands to Implement

### Enhanced col restore (with merge)
### col clear

## Implementation Details

### Enhanced RestoreManager (Merge Support)
```python
class RestoreManager:  # Extend from Phase 2C
    """Handle collection restore operations with merge support."""
    
    def restore_collection(self, backup_path: Path, options: RestoreOptions) -> bool:
        """Restore a collection from backup with merge support."""
        
        # ... (Phase 2C logic) ...
        
        # 3. Check if collection already exists
        if self.collection_exists(collection_name):
            if not options.merge:
                console.print(f"[red]✗ Collection '{collection_name}' already exists[/red]")
                console.print("[yellow]Use --merge to merge with existing collection[/yellow]")
                return False
            else:
                console.print(f"[yellow]Merging with existing collection '{collection_name}'[/yellow]")
                # For merge, we skip schema creation and just restore data
        
        # 4. Create collection OR verify existing
        if not self.collection_exists(collection_name):
            self.create_collection_from_schema(backup_data["schema"], collection_name)
        
        # 5. Restore data if requested and available
        if not options.skip_data and backup_data.get("objects"):
            if options.merge:
                self.merge_objects_with_progress(collection_name, backup_data["objects"])
            else:
                self.restore_objects_with_progress(collection_name, backup_data["objects"])
        
        return True
    
    def merge_objects_with_progress(self, collection_name: str, objects: List[dict]):
        """Merge objects with existing collection (update existing, add new)."""
        
        total_objects = len(objects)
        console.print(f"[bold]Merging {total_objects:,} objects...[/bold]")
        
        # For merge, we need to check which objects exist
        # This is more complex - may need to implement in Phase 3
        console.print("[yellow]⚠ Merge functionality partially implemented[/yellow]")
        
        # For now, just add all objects (may create duplicates)
        self.restore_objects_with_progress(collection_name, objects)
```

### ClearManager Class
```python
class ClearManager:
    """Handle collection clear operations."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
    
    def clear_collection(self, collection_name: str, options: ClearOptions) -> bool:
        """Clear all data from a collection."""
        
        # 1. Validate collection exists
        if not self.collection_exists(collection_name):
            raise CollectionNotFoundError(f"Collection '{collection_name}' not found")
        
        # 2. Check protection
        if self.is_protected_collection(collection_name):
            if not options.force:
                raise CollectionProtectedError(f"Collection '{collection_name}' is protected")
        
        if options.dry_run:
            return self.dry_run_clear(collection_name, options.keep_schema)
        
        # 3. Confirm destructive operation
        if not options.force:
            object_count = self.get_object_count(collection_name)
            if not self.confirm_clear(collection_name, object_count):
                console.print("[yellow]Clear operation cancelled[/yellow]")
                return False
        
        # 4. Clear data
        if options.keep_schema:
            return self.clear_data_keep_schema(collection_name)
        else:
            return self.clear_data_and_schema(collection_name)
    
    def clear_data_keep_schema(self, collection_name: str) -> bool:
        """Clear all objects but keep the collection schema."""
        
        console.print(f"[bold]Clearing data from '{collection_name}'...[/bold]")
        
        # Method: Delete objects in batches
        batch_size = 100
        total_deleted = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Deleting objects", total=None)
            
            while True:
                # Get batch of object IDs
                object_ids = self.get_object_ids_batch(collection_name, batch_size)
                if not object_ids:
                    break
                
                # Delete batch
                self.delete_objects_batch(collection_name, object_ids)
                total_deleted += len(object_ids)
                progress.update(task, advance=len(object_ids))
        
        console.print(f"[green]✓ Cleared {total_deleted:,} objects from '{collection_name}'[/green]")
        return True
    
    def clear_data_and_schema(self, collection_name: str) -> bool:
        """Clear all data and delete the collection schema."""
        
        console.print(f"[bold]Deleting collection '{collection_name}'...[/bold]")
        
        # Method: Delete entire collection
        response = self.client.delete(f"{self.base_url}/v1/schema/{collection_name}")
        
        if response.status_code == 200:
            console.print(f"[green]✓ Collection '{collection_name}' deleted[/green]")
            return True
        else:
            raise Exception(f"Failed to delete collection: {response.text}")
    
    def get_object_ids_batch(self, collection_name: str, batch_size: int) -> List[str]:
        """Get a batch of object IDs."""
        
        response = self.client.get(
            f"{self.base_url}/v1/objects",
            params={"class": collection_name, "limit": batch_size}
        )
        
        if response.status_code == 200:
            objects = response.json().get("objects", [])
            return [obj["id"] for obj in objects]
        
        return []
    
    def delete_objects_batch(self, collection_name: str, object_ids: List[str]):
        """Delete a batch of objects."""
        
        # Weaviate batch delete format
        delete_query = {
            "match": {
                "class": collection_name,
                "where": {
                    "operator": "Or",
                    "operands": [
                        {
                            "path": ["id"],
                            "operator": "Equal",
                            "valueString": obj_id
                        }
                        for obj_id in object_ids
                    ]
                }
            }
        }
        
        response = self.client.delete(
            f"{self.base_url}/v1/batch/objects",
            json=delete_query
        )
        
        response.raise_for_status()
    
    def confirm_clear(self, collection_name: str, object_count: int) -> bool:
        """Get user confirmation for clear operation."""
        
        console.print(f"[red]⚠ About to clear {object_count:,} objects from '{collection_name}'[/red]")
        return typer.confirm("Are you sure you want to continue?")
    
    def dry_run_clear(self, collection_name: str, keep_schema: bool) -> bool:
        """Show what would be cleared without making changes."""
        
        object_count = self.get_object_count(collection_name)
        
        console.print(f"[bold]Dry Run: Clear '{collection_name}'[/bold]")
        console.print(f"Objects to delete: {object_count:,}")
        console.print(f"Keep schema: {keep_schema}")
        
        if keep_schema:
            console.print(f"Result: Collection remains, data cleared")
        else:
            console.print(f"Result: Collection completely deleted")
        
        return True
```

## Enhanced Command Interface

### col restore (enhanced)
```python
@app.command("restore", help="Restore a collection from backup")
def restore_collection(
    backup_file: Path = typer.Argument(..., help="Path to backup file"),
    name: str = typer.Option(None, "--name", help="Override collection name"),
    skip_data: bool = typer.Option(False, "--skip-data", help="Restore schema only"),
    merge: bool = typer.Option(False, "--merge", help="Merge with existing collection"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be restored")
):
    """Restore collection from backup file."""
```

### col clear
```python
@app.command("clear", help="Clear all data from a collection")
def clear_collection(
    name: str = typer.Argument(..., help="Collection name"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    keep_schema: bool = typer.Option(True, "--keep-schema/--delete-schema", help="Preserve collection schema"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be cleared")
):
    """Clear all objects from a collection while optionally preserving schema."""
```

## Success Criteria
- Can merge restore with existing collections
- Can clear collection data while keeping schema
- Can delete entire collections (schema + data)
- All operations support dry-run mode
- Proper confirmation prompts for destructive operations
- Progress indicators for long-running operations

## Effort Estimate: 8 hours
## Risk Level: Medium-High (complex merge logic, destructive operations)</content>
<parameter name="file_path">/opt/elysiactl/phase2d_spec.md