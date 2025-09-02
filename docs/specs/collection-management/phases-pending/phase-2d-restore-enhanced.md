# Phase 2C: Collection Restore
## Objective
Implement collection restore functionality, starting with restore to new collections.

## Commands to Implement
### col restore

**File**: `/opt/elysiactl/src/elysiactl/commands/collection.py`

```python
@app.command("restore", help="Restore a collection from backup")
def restore_collection(
    backup_file: Path = typer.Argument(..., help="Path to backup file"),
    name: str = typer.Option(None, "--name", help="Override collection name"),
    skip_data: bool = typer.Option(False, "--skip-data", help="Restore schema only"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be restored")
):
    """Restore collection from backup file."""
```

## Implementation Details

### RestoreManager Class
```python
class RestoreManager:
    """Handle collection restore operations."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
    
    def restore_collection(self, backup_path: Path, options: RestoreOptions) -> bool:
        """Restore a collection from backup."""
        
        # 1. Load and validate backup
        backup_data = self.load_backup(backup_path)
        self.validate_backup(backup_data)
        
        # 2. Determine target collection name
        collection_name = options.name or backup_data["schema"]["class"]
        
        if options.dry_run:
            return self.dry_run_restore(backup_data, collection_name, options.skip_data)
        
        # 3. Check if collection already exists
        if self.collection_exists(collection_name):
            console.print(f"[red]✗ Collection '{collection_name}' already exists[/red]")
            console.print("[yellow]Use --merge option when implemented (Phase 2D)[/yellow]")
            return False
        
        # 4. Create collection with schema
        console.print(f"[bold]Creating collection '{collection_name}'...[/bold]")
        self.create_collection_from_schema(backup_data["schema"], collection_name)
        
        # 5. Restore data if requested and available
        if not options.skip_data and backup_data.get("objects"):
            self.restore_objects_with_progress(collection_name, backup_data["objects"])
        
        console.print(f"[green]✓ Collection '{collection_name}' restored successfully[/green]")
        return True
    
    def load_backup(self, backup_path: Path) -> dict:
        """Load backup file."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        with open(backup_path, "r") as f:
            return json.load(f)
    
    def validate_backup(self, backup_data: dict):
        """Validate backup file structure."""
        required_keys = ["metadata", "schema"]
        
        for key in required_keys:
            if key not in backup_data:
                raise ValueError(f"Invalid backup file: missing '{key}' section")
        
        # Validate metadata
        meta = backup_data["metadata"]
        if meta.get("version") != "1.0":
            console.print(f"[yellow]⚠ Backup version {meta.get('version')} may not be fully compatible[/yellow]")
    
    def create_collection_from_schema(self, schema: dict, collection_name: str):
        """Create collection using schema from backup."""
        
        # Update schema with new collection name
        create_schema = schema.copy()
        create_schema["class"] = collection_name
        
        response = self.client.post(
            f"{self.base_url}/v1/schema",
            json=create_schema
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create collection: {response.text}")
    
    def restore_objects_with_progress(self, collection_name: str, objects: List[dict]):
        """Restore objects with progress tracking."""
        
        total_objects = len(objects)
        console.print(f"[bold]Restoring {total_objects:,} objects...[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Restoring objects", total=total_objects)
            
            # Process in batches for performance
            batch_size = 100
            for i in range(0, total_objects, batch_size):
                batch = objects[i:i + batch_size]
                self.restore_object_batch(collection_name, batch)
                progress.update(task, advance=len(batch))
    
    def restore_object_batch(self, collection_name: str, objects: List[dict]):
        """Restore a batch of objects."""
        
        # Prepare batch for Weaviate
        batch_objects = []
        for obj in objects:
            batch_objects.append({
                "class": collection_name,
                "id": obj.get("id"),
                "properties": obj.get("properties", {}),
                "vector": obj.get("vector")
            })
        
        batch_payload = {"objects": batch_objects}
        
        response = self.client.post(
            f"{self.base_url}/v1/batch/objects",
            json=batch_payload
        )
        
        response.raise_for_status()
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            response = self.client.get(f"{self.base_url}/v1/schema/{collection_name}")
            return response.status_code == 200
        except:
            return False
    
    def dry_run_restore(self, backup_data: dict, collection_name: str, skip_data: bool) -> bool:
        """Show what would be restored without making changes."""
        
        console.print(f"[bold]Dry Run: Restore to '{collection_name}'[/bold]")
        
        meta = backup_data["metadata"]
        schema = backup_data["schema"]
        
        console.print(f"Backup version: {meta.get('version')}")
        console.print(f"Original collection: {meta.get('collection')}")
        console.print(f"Object count: {meta.get('object_count', 0)}")
        console.print(f"Target collection: {collection_name}")
        
        # Check if target collection exists
        if self.collection_exists(collection_name):
            console.print(f"[yellow]⚠ Target collection '{collection_name}' already exists[/yellow]")
        else:
            console.print(f"[green]✓ Target collection '{collection_name}' available[/green]")
        
        # Show schema info
        properties = schema.get("properties", [])
        console.print(f"Schema properties: {len(properties)}")
        for prop in properties[:5]:  # Show first 5
            console.print(f"  - {prop['name']}: {prop['dataType']}")
        
        if len(properties) > 5:
            console.print(f"  ... and {len(properties) - 5} more")
        
        if not skip_data and backup_data.get("objects"):
            console.print(f"Objects to restore: {len(backup_data['objects'])}")
        
        return True
```

## Restore Process Flow

1. **Load Backup**: Read and validate backup file
2. **Validate Schema**: Ensure backup is compatible
3. **Check Target**: Verify target collection doesn't exist (Phase 2C)
4. **Create Collection**: Use backup schema to create new collection
5. **Restore Data**: Batch restore objects with progress tracking
6. **Verify**: Confirm restore completed successfully

## Error Handling

### Validation Errors
```python
class BackupValidationError(Exception):
    """Backup file validation error."""
    pass

class CollectionExistsError(Exception):
    """Target collection already exists."""
    pass
```

## Testing Strategy

### Unit Tests
```python
def test_restore_schema_only():
    """Test restoring schema without data."""
    
def test_restore_with_data():
    """Test restoring schema and data."""
    
def test_restore_nonexistent_backup():
    """Test restore with missing backup file."""
    
def test_restore_invalid_backup():
    """Test restore with corrupted backup file."""
    
def test_restore_existing_collection():
    """Test restore when collection already exists."""
```

### Integration Tests
```python
def test_full_backup_restore_cycle():
    """Test complete backup and restore cycle."""
    
def test_restore_different_name():
    """Test restoring with different collection name."""
```

## Success Criteria
- Can restore schema-only backups to new collections
- Can restore full backups (schema + data) to new collections
- Progress indicator shows restore progress accurately
- Proper error handling for missing/invalid backups
- Dry-run shows what would be restored
- Batch processing for efficient data restore

## Effort Estimate: 6 hours
## Risk Level: Medium (batch restore performance, error handling)</content>
<parameter name="file_path">/opt/elysiactl/phase2c_spec.md