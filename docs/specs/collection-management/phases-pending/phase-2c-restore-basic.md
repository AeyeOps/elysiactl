# Phase 2B: Collection Backup with Data
## Objective
Extend Phase 2A to include object data backup with batch processing and progress tracking.

## Commands to Implement
### Enhanced col backup (Schema + Data)

**Extend existing command with data backup capability:**

```python
@app.command("backup", help="Backup a collection")
def backup_collection(
    name: str = typer.Argument(..., help="Collection name to backup"),
    output: Path = typer.Option("./backups", "--output", "-o", help="Output directory"),
    include_data: bool = typer.Option(True, "--include-data/--schema-only", help="Include object data"),
    batch_size: int = typer.Option(100, "--batch-size", help="Objects per batch"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be backed up")
):
    """Backup collection schema and optionally data."""
```

## Enhanced Implementation

### Enhanced BackupManager
```python
class BackupManager:  # Extend from Phase 2A
    """Handle collection backup operations."""
    
    def backup_collection(self, collection_name: str, options: BackupOptions) -> Path:
        """Create complete backup including data if requested."""
        
        if options.dry_run:
            return self.dry_run_backup(collection_name, options.output)
        
        # 1. Validate collection exists
        if not self.collection_exists(collection_name):
            raise CollectionNotFoundError(f"Collection '{collection_name}' not found")
        
        # 2. Fetch schema
        schema = self.get_collection_schema(collection_name)
        object_count = self.get_object_count(collection_name)
        
        # 3. Create backup metadata
        backup_meta = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "collection": collection_name,
            "weaviate_version": self.get_weaviate_version(),
            "type": "full" if options.include_data else "schema-only",
            "object_count": object_count,
            "batch_size": options.batch_size
        }
        
        objects = []
        if options.include_data and object_count > 0:
            objects = self.backup_objects_with_progress(collection_name, object_count, options.batch_size)
        
        # 4. Create backup structure
        backup_data = {
            "metadata": backup_meta,
            "schema": schema,
            "objects": objects
        }
        
        # 5. Save backup
        return self.save_backup(backup_data, options.output, collection_name, options.include_data)
    
    def backup_objects_with_progress(self, collection_name: str, total_count: int, batch_size: int) -> List[dict]:
        """Backup all objects with progress tracking."""
        objects = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            console=console
        ) as progress:
            
            task = progress.add_task(f"Backing up {total_count:,} objects", total=total_count)
            
            after = None
            while len(objects) < total_count:
                batch = self.fetch_object_batch(collection_name, batch_size, after)
                if not batch:
                    break
                
                objects.extend(batch)
                progress.update(task, advance=len(batch))
                
                if len(batch) == batch_size:
                    after = batch[-1]["id"]
        
        return objects
    
    def fetch_object_batch(self, collection_name: str, batch_size: int, after: str = None) -> List[dict]:
        """Fetch a batch of objects from Weaviate."""
        params = {
            "class": collection_name,
            "limit": batch_size,
            "include": "vector"  # Include vectors for complete backup
        }
        
        if after:
            params["after"] = after
        
        response = self.client.get(f"{self.base_url}/v1/objects", params=params)
        response.raise_for_status()
        
        return response.json().get("objects", [])
    
    def save_backup(self, backup_data: dict, output_dir: Path, collection_name: str, include_data: bool) -> Path:
        """Save backup to JSON file with better naming."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        data_indicator = "full" if include_data else "schema"
        filename = f"{collection_name}_{data_indicator}_{timestamp}.json"
        backup_path = output_dir / filename
        
        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2)
        
        file_size = backup_path.stat().st_size
        console.print(f"[green]✓ Backup saved: {backup_path} ({file_size:,} bytes)[/green]")
        
        return backup_path
```

## Enhanced Backup File Structure
```json
{
  "metadata": {
    "version": "1.0",
    "timestamp": "2024-02-01T10:30:00Z",
    "collection": "UserDocuments",
    "weaviate_version": "1.23.0",
    "type": "full",
    "object_count": 1250,
    "batch_size": 100
  },
  "schema": {
    "class": "UserDocuments",
    "properties": [...],
    "replicationConfig": {...}
  },
  "objects": [
    {
      "id": "uuid-1",
      "class": "UserDocuments",
      "properties": {
        "title": "Document 1",
        "content": "Content here...",
        "author": "John Doe"
      },
      "vector": [0.1, 0.2, 0.3, ...]
    }
  ]
}
```

## Risk Mitigation Features

### Memory Management
```python
def backup_large_collection(self, collection_name: str, output_dir: Path) -> Path:
    """Stream backup for very large collections to avoid memory issues."""
    
    object_count = self.get_object_count(collection_name)
    
    if object_count > 10000:  # Threshold for streaming
        return self.stream_backup_to_file(collection_name, output_dir)
    else:
        return self.in_memory_backup(collection_name, output_dir)

def stream_backup_to_file(self, collection_name: str, output_dir: Path) -> Path:
    """Stream backup directly to file for memory efficiency."""
    
    # Implementation streams JSON directly to file
    # instead of building in memory
    pass
```

## Testing Strategy

### Unit Tests
```python
def test_backup_with_data_small():
    """Test backup with small amount of data."""
    
def test_backup_with_data_large():
    """Test backup with large dataset."""
    
def test_backup_progress_reporting():
    """Test progress reporting during backup."""
```

### Integration Tests
```python
def test_full_backup_restore_cycle():
    """Test complete backup and restore with data."""
    
def test_backup_resume_after_failure():
    """Test resuming backup after network failure."""
```

## Performance Targets
- Small collections (< 1K objects): < 10 seconds
- Medium collections (1K-100K objects): < 5 minutes
- Large collections (> 100K objects): < 15 minutes (with streaming)

## Success Criteria
- Can backup collections with up to 100K objects
- Progress indicator shows accurate progress
- Backup files are valid JSON with proper structure
- Memory usage stays reasonable for large datasets
- Can resume backup operations after interruption

## Effort Estimate: 6 hours
## Risk Level: Medium (memory management for large datasets)</content>
<parameter name="file_path">/opt/elysiactl/phase2b_spec.md