# Phase 2: Data Operations Implementation

## Objective
Implement backup, restore, and data management operations for Weaviate collections, enabling data preservation and migration capabilities.

## Commands to Implement

### 1. Collection Backup (`col backup`)

**File**: `/opt/elysiactl/src/elysiactl/commands/collection.py` (extend)

```python
@app.command("backup", help="Backup a collection")
def backup_collection(
    name: str = typer.Argument(..., help="Collection name to backup"),
    output: Path = typer.Option("./backups", "--output", "-o", help="Output directory"),
    include_data: bool = typer.Option(True, "--include-data/--schema-only", help="Include object data"),
    format: str = typer.Option("json", "--format", help="Backup format: json, parquet"),
    batch_size: int = typer.Option(100, "--batch-size", help="Objects per batch"),
    compress: bool = typer.Option(False, "--compress", "-z", help="Compress backup file")
):
    """Backup collection schema and optionally data."""
```

**Implementation Details**:

```python
class BackupManager:
    """Handle collection backup operations."""
    
    def backup_collection(self, collection_name: str, options: BackupOptions) -> Path:
        """Create a complete backup of a collection."""
        
        # 1. Create backup metadata
        backup_meta = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "collection": collection_name,
            "weaviate_version": self.get_weaviate_version(),
            "options": options.dict()
        }
        
        # 2. Fetch and save schema
        schema = self.get_collection_schema(collection_name)
        
        # 3. Fetch data if requested
        if options.include_data:
            objects = self.fetch_all_objects(collection_name, options.batch_size)
        else:
            objects = []
        
        # 4. Create backup structure
        backup_data = {
            "metadata": backup_meta,
            "schema": schema,
            "objects": objects,
            "object_count": len(objects)
        }
        
        # 5. Save to file
        backup_path = self.save_backup(backup_data, options)
        return backup_path
    
    def fetch_all_objects(self, collection_name: str, batch_size: int) -> List[dict]:
        """Fetch all objects from collection with pagination."""
        objects = []
        after = None
        
        with show_progress(f"Backing up {collection_name}") as progress:
            task = progress.add_task("Fetching objects...", total=None)
            
            while True:
                batch = self.fetch_batch(collection_name, batch_size, after)
                if not batch:
                    break
                    
                objects.extend(batch)
                progress.update(task, advance=len(batch))
                
                if len(batch) < batch_size:
                    break
                after = batch[-1]["id"]
        
        return objects
    
    def fetch_batch(self, collection_name: str, limit: int, after: str = None) -> List[dict]:
        """Fetch a batch of objects."""
        params = {
            "class": collection_name,
            "limit": limit,
            "include": "vector"
        }
        if after:
            params["after"] = after
            
        response = self.client.get(f"{self.base_url}/v1/objects", params=params)
        response.raise_for_status()
        return response.json().get("objects", [])
```

**Backup File Structure**:
```json
{
  "metadata": {
    "version": "1.0",
    "timestamp": "2024-02-01T10:30:00Z",
    "collection": "UserDocuments",
    "weaviate_version": "1.23.0",
    "options": {
      "include_data": true,
      "format": "json"
    }
  },
  "schema": {
    "class": "UserDocuments",
    "properties": [...],
    "replicationConfig": {...}
  },
  "objects": [
    {
      "id": "uuid",
      "class": "UserDocuments",
      "properties": {...},
      "vector": [...]
    }
  ],
  "object_count": 1250
}
```

### 2. Collection Restore (`col restore`)

```python
@app.command("restore", help="Restore a collection from backup")
def restore_collection(
    backup_file: Path = typer.Argument(..., help="Path to backup file"),
    name: str = typer.Option(None, "--name", help="Override collection name"),
    skip_data: bool = typer.Option(False, "--skip-data", help="Restore schema only"),
    merge: bool = typer.Option(False, "--merge", help="Merge with existing collection"),
    batch_size: int = typer.Option(100, "--batch-size", help="Objects per batch")
):
    """Restore collection from backup file."""
```

**Restore Process**:
```python
class RestoreManager:
    """Handle collection restore operations."""
    
    def restore_collection(self, backup_path: Path, options: RestoreOptions) -> bool:
        """Restore a collection from backup."""
        
        # 1. Load and validate backup
        backup_data = self.load_backup(backup_path)
        self.validate_backup(backup_data)
        
        # 2. Determine target collection name
        collection_name = options.name or backup_data["schema"]["class"]
        
        # 3. Check existing collection
        if self.collection_exists(collection_name):
            if not options.merge:
                raise CollectionExistsError(f"Collection '{collection_name}' already exists")
            console.print(f"[yellow]Merging with existing collection '{collection_name}'[/yellow]")
        else:
            # Create collection with schema
            self.create_collection_from_schema(backup_data["schema"], collection_name)
        
        # 4. Restore data if requested
        if not options.skip_data and backup_data.get("objects"):
            self.restore_objects(collection_name, backup_data["objects"], options.batch_size)
        
        return True
    
    def restore_objects(self, collection_name: str, objects: List[dict], batch_size: int):
        """Restore objects to collection in batches."""
        total = len(objects)
        
        with show_progress(f"Restoring {total:,} objects") as progress:
            task = progress.add_task("Restoring...", total=total)
            
            for i in range(0, total, batch_size):
                batch = objects[i:i + batch_size]
                self.import_batch(collection_name, batch)
                progress.update(task, advance=len(batch))
    
    def import_batch(self, collection_name: str, objects: List[dict]):
        """Import a batch of objects."""
        # Prepare batch import payload
        batch_payload = {
            "objects": [
                {
                    "class": collection_name,
                    "id": obj.get("id"),
                    "properties": obj.get("properties", {}),
                    "vector": obj.get("vector")
                }
                for obj in objects
            ]
        }
        
        response = self.client.post(
            f"{self.base_url}/v1/batch/objects",
            json=batch_payload
        )
        response.raise_for_status()
```

### 3. Collection Clear (`col clear`)

```python
@app.command("clear", help="Clear all data from a collection")
def clear_collection(
    name: str = typer.Argument(..., help="Collection name"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    keep_schema: bool = typer.Option(True, "--keep-schema", help="Preserve collection schema")
):
    """Clear all objects from a collection while preserving schema."""
```

**Implementation**:
```python
def clear_collection_data(collection_name: str, keep_schema: bool) -> bool:
    """Clear all data from a collection."""
    
    if keep_schema:
        # Method 1: Delete all objects (preserves schema)
        return delete_all_objects(collection_name)
    else:
        # Method 2: Delete and recreate collection
        schema = get_collection_schema(collection_name)
        delete_collection(collection_name)
        create_collection(schema)
        return True

def delete_all_objects(collection_name: str) -> bool:
    """Delete all objects from collection in batches."""
    
    with show_progress(f"Clearing {collection_name}") as progress:
        task = progress.add_task("Deleting objects...", total=None)
        
        while True:
            # Fetch batch of object IDs
            objects = fetch_object_ids(collection_name, limit=100)
            if not objects:
                break
            
            # Delete batch
            delete_batch(collection_name, [obj["id"] for obj in objects])
            progress.update(task, advance=len(objects))
    
    return True

def delete_batch(collection_name: str, object_ids: List[str]):
    """Delete a batch of objects by ID."""
    
    batch_delete = {
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
    
    response = client.delete(
        f"{base_url}/v1/batch/objects",
        json=batch_delete
    )
    response.raise_for_status()
```

## Backup Formats

### JSON Format (Default)
- Human-readable
- Easy to inspect and modify
- Larger file size
- Suitable for small to medium collections

### Parquet Format (Optional)
```python
def save_as_parquet(backup_data: dict, output_path: Path):
    """Save backup in Parquet format for large datasets."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    
    # Convert objects to Arrow table
    if backup_data.get("objects"):
        df = pd.DataFrame(backup_data["objects"])
        table = pa.Table.from_pandas(df)
        
        # Save to Parquet
        pq.write_table(table, output_path / "objects.parquet")
    
    # Save metadata and schema as JSON
    meta_path = output_path / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump({
            "metadata": backup_data["metadata"],
            "schema": backup_data["schema"]
        }, f, indent=2)
```

### Compressed Format
```python
def save_compressed(backup_data: dict, output_path: Path):
    """Save compressed backup using gzip."""
    import gzip
    
    json_str = json.dumps(backup_data, indent=2)
    
    with gzip.open(f"{output_path}.gz", "wt", encoding="utf-8") as f:
        f.write(json_str)
```

## Progress Indicators

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

def show_progress(description: str):
    """Create a progress bar for long operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        console=console
    )
```

## Error Recovery

### Partial Restore Handling
```python
class RestoreCheckpoint:
    """Track restore progress for recovery."""
    
    def __init__(self, backup_file: Path):
        self.backup_file = backup_file
        self.checkpoint_file = backup_file.with_suffix(".checkpoint")
        self.processed_ids = set()
        self.load_checkpoint()
    
    def load_checkpoint(self):
        """Load existing checkpoint if available."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file) as f:
                data = json.load(f)
                self.processed_ids = set(data.get("processed_ids", []))
    
    def save_checkpoint(self):
        """Save current progress."""
        with open(self.checkpoint_file, "w") as f:
            json.dump({
                "processed_ids": list(self.processed_ids),
                "timestamp": datetime.utcnow().isoformat()
            }, f)
    
    def mark_processed(self, object_id: str):
        """Mark object as processed."""
        self.processed_ids.add(object_id)
    
    def is_processed(self, object_id: str) -> bool:
        """Check if object was already processed."""
        return object_id in self.processed_ids
    
    def cleanup(self):
        """Remove checkpoint file after successful completion."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
```

## Storage Management

### Backup Directory Structure
```
backups/
├── UserDocuments_2024-02-01_103000.json
├── UserDocuments_2024-02-01_103000.json.gz
├── ProductCatalog_2024-02-01/
│   ├── metadata.json
│   ├── schema.json
│   └── objects.parquet
└── .backup_catalog.json  # Catalog of all backups
```

### Backup Catalog
```python
class BackupCatalog:
    """Manage backup inventory."""
    
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.catalog_file = backup_dir / ".backup_catalog.json"
        self.catalog = self.load_catalog()
    
    def register_backup(self, backup_info: dict):
        """Register a new backup in catalog."""
        self.catalog.append({
            "id": str(uuid.uuid4()),
            "collection": backup_info["collection"],
            "timestamp": backup_info["timestamp"],
            "file": backup_info["file"],
            "size": backup_info["size"],
            "object_count": backup_info["object_count"],
            "format": backup_info["format"]
        })
        self.save_catalog()
    
    def list_backups(self, collection: str = None) -> List[dict]:
        """List available backups."""
        if collection:
            return [b for b in self.catalog if b["collection"] == collection]
        return self.catalog
    
    def cleanup_old_backups(self, keep_last: int = 5):
        """Remove old backups keeping most recent."""
        by_collection = {}
        for backup in self.catalog:
            col = backup["collection"]
            if col not in by_collection:
                by_collection[col] = []
            by_collection[col].append(backup)
        
        for col, backups in by_collection.items():
            # Sort by timestamp, newest first
            backups.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Remove old backups
            for backup in backups[keep_last:]:
                self.remove_backup(backup)
```

## Testing Strategy

### Unit Tests
```python
# tests/test_backup_restore.py

def test_backup_schema_only():
    """Test backing up collection schema without data."""

def test_backup_with_data():
    """Test full backup including objects."""

def test_restore_to_new_collection():
    """Test restoring to a collection with different name."""

def test_restore_merge_existing():
    """Test merging restore with existing collection."""

def test_clear_collection_keep_schema():
    """Test clearing data while preserving schema."""

def test_backup_compression():
    """Test compressed backup creation and restore."""

def test_restore_checkpoint_recovery():
    """Test resuming failed restore from checkpoint."""
```

### Integration Tests
```python
# tests/integration/test_backup_restore_cycle.py

def test_full_backup_restore_cycle():
    """Test complete backup and restore cycle."""
    
    # 1. Create test collection with data
    create_test_collection("TestBackup", object_count=1000)
    
    # 2. Create backup
    backup_path = backup_collection("TestBackup")
    
    # 3. Delete original collection
    delete_collection("TestBackup")
    
    # 4. Restore from backup
    restore_collection(backup_path)
    
    # 5. Verify restored data
    assert get_object_count("TestBackup") == 1000
    assert verify_schema_match("TestBackup", original_schema)
```

## Performance Considerations

### Batch Sizes
```python
BATCH_SIZE_DEFAULTS = {
    "small": 100,      # < 1K objects
    "medium": 500,     # 1K - 100K objects
    "large": 1000,     # > 100K objects
}

def get_optimal_batch_size(object_count: int) -> int:
    """Determine optimal batch size based on collection size."""
    if object_count < 1000:
        return BATCH_SIZE_DEFAULTS["small"]
    elif object_count < 100000:
        return BATCH_SIZE_DEFAULTS["medium"]
    else:
        return BATCH_SIZE_DEFAULTS["large"]
```

### Memory Management
```python
def stream_large_backup(collection_name: str, output_file: Path):
    """Stream backup directly to file for large collections."""
    
    with open(output_file, "w") as f:
        # Write header
        f.write('{"metadata":')
        json.dump(create_metadata(), f)
        
        # Write schema
        f.write(',"schema":')
        json.dump(get_schema(collection_name), f)
        
        # Stream objects
        f.write(',"objects":[')
        
        first = True
        for batch in fetch_objects_generator(collection_name):
            for obj in batch:
                if not first:
                    f.write(",")
                json.dump(obj, f)
                first = False
        
        f.write("]}")
```

## Success Metrics

1. **Reliability**
   - 100% data integrity after restore
   - Checkpoint recovery for failed operations
   - No data loss during clear operations

2. **Performance**
   - Backup: >1000 objects/second
   - Restore: >500 objects/second
   - Memory usage < 500MB for large collections

3. **Usability**
   - Clear progress indicators
   - Resumable operations
   - Automatic backup cataloging