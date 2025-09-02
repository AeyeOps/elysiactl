# Phase 2A: Basic Collection Backup (Schema-Only)
## Objective
Implement basic collection backup functionality starting with schema-only backups.

## Commands to Implement
### col backup (Schema-Only Version)

**File**: `/opt/elysiactl/src/elysiactl/commands/collection.py`

```python
@app.command("backup", help="Backup a collection")
def backup_collection(
    name: str = typer.Argument(..., help="Collection name to backup"),
    output: Path = typer.Option("./backups", "--output", "-o", help="Output directory"),
    include_data: bool = typer.Option(False, "--include-data", help="Include object data (Phase 2B)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be backed up")
):
    """Backup collection schema."""
```

## Implementation Details

### BackupManager Class
```python
class BackupManager:
    """Handle collection backup operations."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
    
    def backup_schema_only(self, collection_name: str, output_dir: Path, dry_run: bool) -> Path:
        """Create schema-only backup."""
        
        if dry_run:
            return self.dry_run_backup(collection_name, output_dir)
        
        # 1. Validate collection exists
        if not self.collection_exists(collection_name):
            raise CollectionNotFoundError(f"Collection '{collection_name}' not found")
        
        # 2. Fetch schema
        schema = self.get_collection_schema(collection_name)
        
        # 3. Create backup metadata
        backup_meta = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "collection": collection_name,
            "weaviate_version": self.get_weaviate_version(),
            "type": "schema-only",
            "object_count": self.get_object_count(collection_name)
        }
        
        # 4. Create backup structure
        backup_data = {
            "metadata": backup_meta,
            "schema": schema,
            "objects": []  # Empty for schema-only
        }
        
        # 5. Save backup
        return self.save_backup(backup_data, output_dir, collection_name)
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            response = self.client.get(f"{self.base_url}/v1/schema/{collection_name}")
            return response.status_code == 200
        except:
            return False
    
    def get_collection_schema(self, collection_name: str) -> dict:
        """Get collection schema."""
        response = self.client.get(f"{self.base_url}/v1/schema/{collection_name}")
        response.raise_for_status()
        return response.json()
    
    def get_object_count(self, collection_name: str) -> int:
        """Get object count for collection."""
        try:
            response = self.client.get(
                f"{self.base_url}/v1/objects",
                params={"class": collection_name, "limit": 0}
            )
            response.raise_for_status()
            return response.json().get("totalResults", 0)
        except:
            return 0
    
    def get_weaviate_version(self) -> str:
        """Get Weaviate version."""
        try:
            response = self.client.get(f"{self.base_url}/v1/meta")
            response.raise_for_status()
            return response.json().get("version", "unknown")
        except:
            return "unknown"
    
    def save_backup(self, backup_data: dict, output_dir: Path, collection_name: str) -> Path:
        """Save backup to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{collection_name}_schema_{timestamp}.json"
        backup_path = output_dir / filename
        
        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2)
        
        return backup_path
    
    def dry_run_backup(self, collection_name: str, output_dir: Path) -> Path:
        """Show what would be backed up without creating files."""
        console.print(f"[bold]Dry Run: Backup of '{collection_name}'[/bold]")
        console.print(f"Output directory: {output_dir}")
        console.print(f"Backup type: Schema-only")
        
        if self.collection_exists(collection_name):
            schema = self.get_collection_schema(collection_name)
            obj_count = self.get_object_count(collection_name)
            
            console.print(f"[green]✓ Collection exists: {collection_name}[/green]")
            console.print(f"  Object count: {obj_count}")
            console.print(f"  Properties: {len(schema.get('properties', []))}")
            console.print(f"  Replication factor: {schema.get('replicationConfig', {}).get('factor', 1)}")
        else:
            console.print(f"[red]✗ Collection not found: {collection_name}[/red]")
        
        return None
```

## Backup File Structure (Schema-Only)
```json
{
  "metadata": {
    "version": "1.0",
    "timestamp": "2024-02-01T10:30:00Z",
    "collection": "UserDocuments",
    "weaviate_version": "1.23.0",
    "type": "schema-only",
    "object_count": 1250
  },
  "schema": {
    "class": "UserDocuments",
    "properties": [...],
    "replicationConfig": {...}
  },
  "objects": []
}
```

## Testing Strategy

### Unit Tests
```python
def test_backup_schema_only():
    """Test schema-only backup creation."""
    
def test_backup_nonexistent_collection():
    """Test backup of non-existent collection."""
    
def test_backup_dry_run():
    """Test dry-run backup functionality."""
```

### Integration Tests
```python
def test_backup_restore_cycle_schema_only():
    """Test backup and restore of schema-only backup."""
```

## Success Criteria
- Can backup collection schema to JSON file
- Can restore schema to create new collection
- Dry-run shows what would be backed up
- Proper error handling for missing collections
- Backup files include metadata (timestamp, version, etc.)

## Effort Estimate: 4 hours
## Risk Level: Low</content>
<parameter name="file_path">/opt/elysiactl/phase2a_spec.md