# Phase 1: Core Collection Commands Implementation

## Objective
Implement fundamental CRUD operations for Weaviate collections through elysiactl, providing essential collection management capabilities.

## Commands to Implement

### 1. Collection List (`col ls`)

**File**: `/opt/elysiactl/src/elysiactl/commands/collection.py`

```python
@app.command("ls", help="List all collections")
def list_collections(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    format: str = typer.Option("table", "--format", help="Output format: table, json, yaml"),
    filter: str = typer.Option(None, "--filter", help="Filter collections by pattern")
):
    """List all Weaviate collections with optional filtering."""
```

**Implementation Details**:
- Query Weaviate API: `GET http://localhost:8080/v1/schema`
- Parse collection metadata (name, object count, replication, shards)
- Apply filtering using fnmatch patterns
- Format output based on selected format

**API Response Structure**:
```json
{
  "classes": [
    {
      "class": "CollectionName",
      "properties": [...],
      "replicationConfig": {
        "factor": 3
      },
      "shardingConfig": {
        "desiredCount": 1
      }
    }
  ]
}
```

### 2. Collection Show (`col show`)

**Command Signature**:
```python
@app.command("show", help="Show detailed collection information")
def show_collection(
    name: str = typer.Argument(..., help="Collection name or ID"),
    schema: bool = typer.Option(False, "--schema", help="Include schema information"),
    stats: bool = typer.Option(False, "--stats", help="Include detailed statistics"),
    format: str = typer.Option("table", "--format", help="Output format")
):
    """Display detailed information about a specific collection."""
```

**Implementation Details**:
- Query: `GET http://localhost:8080/v1/schema/{className}`
- Fetch object count: `GET http://localhost:8080/v1/objects?class={className}&limit=0`
- Display schema properties if requested
- Show replication and sharding configuration

### 3. Collection Remove (`col rm`)

**Command Signature**:
```python
@app.command("rm", help="Remove a collection")
def remove_collection(
    name: str = typer.Argument(..., help="Collection name or ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted")
):
    """Remove a Weaviate collection with safety checks."""
```

**Safety Implementation**:
```python
PROTECTED_PATTERNS = [
    "ELYSIACTL_*",      # Elysia system collections
    "*_SYSTEM",      # System suffix
    ".internal*",    # Internal prefix
]

def is_protected(collection_name: str) -> bool:
    """Check if collection matches protected patterns."""
    for pattern in PROTECTED_PATTERNS:
        if fnmatch.fnmatch(collection_name, pattern):
            return True
    return False

def confirm_deletion(collection_info: dict) -> bool:
    """Interactive confirmation for collection deletion."""
    console.print(f"[yellow]⚠ WARNING: This will permanently delete collection '{collection_info['name']}'[/yellow]")
    console.print(f"  Objects: {collection_info['object_count']:,}")
    console.print(f"  Replicas: {collection_info['replicas']}")
    console.print(f"  Created: {collection_info['created']}")
    
    response = typer.prompt("\nType 'yes' to confirm deletion")
    return response.lower() == 'yes'
```

**API Call**:
- Delete: `DELETE http://localhost:8080/v1/schema/{className}`

### 4. Collection Create (`col create`)

**Command Signature**:
```python
@app.command("create", help="Create a new collection")
def create_collection(
    name: str = typer.Argument(..., help="Collection name"),
    schema_file: Path = typer.Option(None, "--schema-file", help="Path to JSON schema"),
    replication: int = typer.Option(3, "--replication", help="Replication factor"),
    shards: int = typer.Option(1, "--shards", help="Number of shards"),
    from_template: str = typer.Option(None, "--from-template", help="Copy schema from existing collection")
):
    """Create a new Weaviate collection with specified configuration."""
```

**Schema Template**:
```python
def create_default_schema(name: str, replication: int, shards: int) -> dict:
    """Generate default collection schema."""
    return {
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
        "vectorizer": "text2vec-transformers"
    }
```

**API Call**:
- Create: `POST http://localhost:8080/v1/schema`

## Service Integration

### Weaviate Service Helper
**File**: `/opt/elysiactl/src/elysiactl/services/weaviate_collections.py`

```python
class WeaviateCollectionManager:
    """Manage Weaviate collections through REST API."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """Get all collections from Weaviate."""
        response = self.client.get(f"{self.base_url}/v1/schema")
        response.raise_for_status()
        return response.json().get("classes", [])
    
    def get_collection(self, name: str) -> Dict[str, Any]:
        """Get specific collection details."""
        response = self.client.get(f"{self.base_url}/v1/schema/{name}")
        if response.status_code == 404:
            raise CollectionNotFoundError(f"Collection '{name}' not found")
        response.raise_for_status()
        return response.json()
    
    def get_object_count(self, class_name: str) -> int:
        """Get object count for a collection."""
        response = self.client.get(
            f"{self.base_url}/v1/objects",
            params={"class": class_name, "limit": 0, "include": "vector"}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("totalResults", 0)
    
    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        response = self.client.delete(f"{self.base_url}/v1/schema/{name}")
        return response.status_code == 200
    
    def create_collection(self, schema: dict) -> bool:
        """Create a new collection."""
        response = self.client.post(
            f"{self.base_url}/v1/schema",
            json=schema
        )
        response.raise_for_status()
        return response.status_code == 200
```

## Error Handling

### Custom Exceptions
```python
class CollectionError(Exception):
    """Base exception for collection operations."""
    pass

class CollectionNotFoundError(CollectionError):
    """Collection does not exist."""
    pass

class CollectionProtectedError(CollectionError):
    """Collection is protected from modification."""
    pass

class CollectionExistsError(CollectionError):
    """Collection already exists."""
    pass
```

### Error Messages
```python
ERROR_MESSAGES = {
    "not_found": "Collection '{name}' not found. Use 'elysiactl col ls' to see available collections.",
    "protected": "Collection '{name}' is protected and cannot be modified.",
    "exists": "Collection '{name}' already exists. Use --force to overwrite.",
    "connection": "Cannot connect to Weaviate. Ensure the service is running with 'elysiactl status'.",
    "permission": "Permission denied. Check your Weaviate authentication settings."
}
```

## Testing Requirements

### Unit Tests
```python
# tests/test_collection_commands.py

def test_list_collections_empty():
    """Test listing collections in empty cluster."""
    
def test_list_collections_with_filter():
    """Test filtering collections by pattern."""
    
def test_create_collection_default():
    """Test creating collection with defaults."""
    
def test_remove_protected_collection():
    """Test that protected collections cannot be removed."""
    
def test_remove_collection_with_confirmation():
    """Test interactive confirmation flow."""
```

### Integration Tests
```python
# tests/integration/test_collection_lifecycle.py

def test_collection_lifecycle():
    """Test complete create, list, show, delete cycle."""
    
def test_collection_with_data():
    """Test operations on collections containing data."""
```

## CLI Output Examples

### List Collections
```bash
$ elysiactl col ls
Collections (3 total)
────────────────────
Name                 Objects  Replicas  Shards  Status
ELYSIACTL_CONFIG__      0        3         1       READY
UserDocuments        1,250    3         2       READY  
ProductCatalog       45,320   3         4       READY
```

### Show Collection (Verbose)
```bash
$ elysiactl col show UserDocuments --verbose
Collection: UserDocuments
─────────────────────────
Status:       READY
Objects:      1,250
Replicas:     3
Shards:       2
Vectorizer:   text2vec-transformers
Created:      2024-01-15 10:30:00

Properties (5):
  - title (text)
  - content (text)
  - author (string)
  - created_at (date)
  - tags (text[])
```

### Remove Collection
```bash
$ elysiactl col rm TestCollection
⚠ WARNING: This will permanently delete collection 'TestCollection'
  Objects: 0
  Replicas: 3
  Created: 2024-02-01

Type 'yes' to confirm deletion: yes
✓ Collection 'TestCollection' deleted successfully
```

## Dependencies

### Required Packages
- Already included in elysiactl:
  - `httpx` - HTTP client
  - `typer` - CLI framework
  - `rich` - Terminal formatting

### New Imports
```python
import fnmatch  # Pattern matching for filters
import json     # Schema file parsing
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
```

## Implementation Timeline

### Week 1: Core Infrastructure
- [ ] Create `collection.py` command file
- [ ] Implement `WeaviateCollectionManager` service
- [ ] Add error handling and exceptions
- [ ] Create protected patterns configuration

### Week 2: Command Implementation
- [ ] Implement `col ls` command
- [ ] Implement `col show` command
- [ ] Implement `col rm` command with safety
- [ ] Implement `col create` command

### Week 3: Testing and Polish
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update README documentation
- [ ] Add command help text

## Success Metrics

1. **Functionality**
   - All 4 core commands working
   - Protected collections cannot be deleted
   - Proper error messages for all failure cases

2. **Safety**
   - No accidental data loss
   - Clear confirmation prompts
   - Dry-run mode functional

3. **Usability**
   - Commands complete in <2 seconds
   - Clear, formatted output
   - Helpful error messages

## Next Steps
After Phase 1 completion:
1. Gather user feedback
2. Refine safety mechanisms
3. Proceed to Phase 2 (backup/restore)