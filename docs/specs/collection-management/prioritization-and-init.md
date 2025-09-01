# Collection Management - Prioritization and Initialization

## Implementation Priority Matrix

### Immediate Priority (Sprint 1 - Days 1-6)

#### Must Have - Core Functionality
1. **`col ls`** - List collections
   - Basic listing without filtering
   - Object count display
   - Simple table output
   - **Effort**: 2 hours
   - **Dependencies**: None
   - **Risk**: Low

2. **`col show <name>`** - Show collection details
   - Basic schema display
   - Object count
   - Replication info
   - **Effort**: 2 hours
   - **Dependencies**: `col ls` foundation
   - **Risk**: Low

3. **`col rm <name>`** - Remove collection
   - Protected pattern checking
   - Basic confirmation prompt
   - Dry-run support
   - **Effort**: 3 hours
   - **Dependencies**: Protection config
   - **Risk**: Medium (data loss potential)

4. **Protection System**
   - ELYSIA_* pattern protection
   - Configuration loading
   - **Effort**: 2 hours
   - **Dependencies**: None
   - **Risk**: Low

**Total Sprint 1**: 9 hours core development + 3 hours testing

### High Priority (Sprint 2 - Days 7-12)

#### Should Have - Enhanced Core
1. **`col create`** - Create collection
   - Default schema generation
   - Basic property types
   - **Effort**: 3 hours
   - **Risk**: Low

2. **Enhanced `col ls`**
   - Filter patterns
   - Verbose mode
   - JSON output format
   - **Effort**: 2 hours
   - **Risk**: Low

3. **`col backup`** - Basic backup
   - JSON format only
   - Schema + data
   - Local filesystem
   - **Effort**: 4 hours
   - **Risk**: Medium

4. **`col restore`** - Basic restore
   - From JSON backup
   - New collection only
   - **Effort**: 4 hours
   - **Risk**: Medium

**Total Sprint 2**: 13 hours + 4 hours testing

### Medium Priority (Sprint 3 - Days 13-18)

#### Nice to Have - Data Operations
1. **`col clear`** - Clear data
   - Keep schema option
   - Batch deletion
   - **Effort**: 3 hours
   - **Risk**: Medium

2. **`col stats`** - Basic statistics
   - Static snapshot
   - Current metrics only
   - **Effort**: 4 hours
   - **Risk**: Low

3. **Backup Enhancements**
   - Compression support
   - Backup catalog
   - **Effort**: 3 hours
   - **Risk**: Low

4. **Template System**
   - Save as template
   - Create from template
   - **Effort**: 4 hours
   - **Risk**: Low

**Total Sprint 3**: 14 hours + 4 hours testing

### Future Priority (Post-MVP)

#### Advanced Features
- Real-time monitoring (`col stats --watch`)
- Cross-cluster migration (`col migrate`)
- Performance optimization (`col optimize`)
- Health diagnostics (`col health`)
- Batch operations
- Parquet format support
- Cloud storage backends

## Initialization Checklist

### Project Setup

#### 1. File Structure Creation
```bash
# Create necessary directories
mkdir -p /opt/elysiactl/src/elysiactl/commands
mkdir -p /opt/elysiactl/src/elysiactl/services
mkdir -p /opt/elysiactl/src/elysiactl/config
mkdir -p /opt/elysiactl/tests/commands
mkdir -p /opt/elysiactl/tests/services

# Create initial files
touch /opt/elysiactl/src/elysiactl/commands/collection.py
touch /opt/elysiactl/src/elysiactl/services/weaviate_collections.py
touch /opt/elysiactl/src/elysiactl/config/collection_config.yaml
```

#### 2. Configuration File
```yaml
# /opt/elysiactl/src/elysiactl/config/collection_config.yaml
collection_management:
  # Patterns that cannot be deleted without override
  protected_patterns:
    - "ELYSIA_*"
    - "*_SYSTEM"
    - ".internal*"
  
  # Confirmation requirements
  confirmations:
    delete_with_data: true
    clear_data: true
    modify_protected: true
  
  # Default values
  defaults:
    replication_factor: 3
    shard_count: 1
    batch_size: 100
  
  # Output settings
  output:
    default_format: "table"
    truncate_strings: 50
    show_vectors: false
```

#### 3. Base Implementation Template
```python
# /opt/elysiactl/src/elysiactl/commands/collection.py
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

from ..services.weaviate_collections import WeaviateCollectionManager
from ..utils.display import show_progress, print_success, print_error

app = typer.Typer(help="Manage Weaviate collections")
console = Console()

# Initialize service
manager = WeaviateCollectionManager()

@app.command("ls", help="List all collections")
def list_collections(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    format: str = typer.Option("table", "--format")
):
    """List all Weaviate collections."""
    try:
        collections = manager.list_collections()
        
        if format == "table":
            display_collections_table(collections, verbose)
        elif format == "json":
            console.print_json(data=collections)
        
    except Exception as e:
        print_error(f"Failed to list collections: {e}")
        raise typer.Exit(1)

# Additional commands...
```

#### 4. Service Implementation Base
```python
# /opt/elysiactl/src/elysiactl/services/weaviate_collections.py
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

class CollectionNotFoundError(Exception):
    """Collection does not exist."""
    pass

class CollectionProtectedError(Exception):
    """Collection is protected from modification."""
    pass

class WeaviateCollectionManager:
    """Manage Weaviate collections through REST API."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """Get all collections from Weaviate."""
        response = self.client.get(f"{self.base_url}/v1/schema")
        response.raise_for_status()
        
        classes = response.json().get("classes", [])
        
        # Enrich with object counts
        for cls in classes:
            cls["object_count"] = self.get_object_count(cls["class"])
        
        return classes
    
    def get_object_count(self, class_name: str) -> int:
        """Get object count for a collection."""
        try:
            response = self.client.get(
                f"{self.base_url}/v1/objects",
                params={"class": class_name, "limit": 0}
            )
            response.raise_for_status()
            return response.json().get("totalResults", 0)
        except:
            return 0
    
    # Additional methods...
```

### Development Workflow

#### Day 1: Foundation
- [ ] Create file structure
- [ ] Set up configuration
- [ ] Implement WeaviateCollectionManager base
- [ ] Create protection system

#### Day 2: Core Commands
- [ ] Implement `col ls` basic
- [ ] Implement `col show`
- [ ] Add table formatting

#### Day 3: Safety Features
- [ ] Implement `col rm` with confirmations
- [ ] Add dry-run mode
- [ ] Test protection patterns

#### Day 4: Testing & Documentation
- [ ] Write unit tests for core commands
- [ ] Integration tests with test cluster
- [ ] Update README with examples

#### Day 5: Enhancement
- [ ] Add `col create` basic
- [ ] Implement filtering for `col ls`
- [ ] Add JSON output format

#### Day 6: Polish & Release
- [ ] Error handling improvements
- [ ] Performance optimization
- [ ] Final testing
- [ ] Documentation review

### Testing Strategy

#### Unit Test Setup
```python
# tests/commands/test_collection.py
import pytest
from unittest.mock import Mock, patch
from elysiactl.commands.collection import list_collections

def test_list_collections_empty():
    """Test listing when no collections exist."""
    with patch('elysiactl.services.weaviate_collections.WeaviateCollectionManager') as mock:
        mock.return_value.list_collections.return_value = []
        
        result = list_collections()
        assert result == []

def test_list_collections_with_data():
    """Test listing with collections."""
    # Test implementation
```

#### Integration Test Setup
```python
# tests/integration/test_collection_integration.py
import pytest
import httpx
from elysiactl.services.weaviate_collections import WeaviateCollectionManager

@pytest.fixture
def test_cluster():
    """Ensure test Weaviate cluster is running."""
    # Setup test cluster
    yield "http://localhost:8080"
    # Cleanup

def test_real_collection_operations(test_cluster):
    """Test against real Weaviate instance."""
    manager = WeaviateCollectionManager(test_cluster)
    
    # Create test collection
    # Verify operations
    # Cleanup
```

### Catalog System Integration

Since you mentioned having a catalog system, here's how to integrate:

#### Catalog Integration Points

1. **Backup Catalog**
```python
class BackupCatalog:
    """Integration with existing catalog system."""
    
    def __init__(self, catalog_path: str = "/opt/elysiactl/catalog"):
        self.catalog_path = Path(catalog_path)
        self.ensure_structure()
    
    def register_collection(self, collection_info: dict):
        """Register collection in catalog."""
        entry = {
            "id": str(uuid.uuid4()),
            "name": collection_info["name"],
            "created": datetime.utcnow().isoformat(),
            "schema_version": collection_info.get("version", "1.0"),
            "metadata": collection_info
        }
        
        catalog_file = self.catalog_path / "collections.json"
        # Update catalog
    
    def get_collection_history(self, name: str):
        """Get collection history from catalog."""
        # Retrieve history
```

2. **Operation Logging**
```python
class OperationLogger:
    """Log all collection operations to catalog."""
    
    def log_operation(self, operation: str, details: dict):
        """Log operation to catalog."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "details": details,
            "user": os.environ.get("USER", "unknown"),
            "status": "success"
        }
        
        # Write to catalog
```

### Deployment Configuration

#### elysiactl Updates Required

1. **Update CLI Registration**
```python
# /opt/elysiactl/src/elysiactl/cli.py
# Add to existing file
from .commands import collection

app.add_typer(collection.app, name="collection", help="Manage collections")
app.add_typer(collection.app, name="col", help="Manage collections (alias)")
```

2. **Update Dependencies** (if needed)
```toml
# /opt/elysiactl/pyproject.toml
# Already includes required: httpx, typer, rich, psutil
```

3. **Update Version**
```python
# /opt/elysiactl/src/elysiactl/__init__.py
__version__ = "0.2.0"  # Bump for new feature
```

### Quick Start Commands

```bash
# After implementation, test with:
elysiactl col ls
elysiactl col show ELYSIA_CONFIG__
elysiactl col create TestCollection
elysiactl col rm TestCollection --dry-run
elysiactl col rm TestCollection

# Verify protection
elysiactl col rm ELYSIA_CONFIG__  # Should fail
elysiactl col rm ELYSIA_CONFIG__ --force  # Should prompt
```

### Risk Mitigation

#### High-Risk Areas
1. **Data Deletion** - Multiple confirmation layers
2. **Protected Collections** - Hard-coded patterns + config
3. **Backup Integrity** - Checksum validation
4. **Concurrent Operations** - Lock mechanisms

#### Mitigation Strategies
1. **Dry-Run Everything** - Default for destructive ops
2. **Audit Trail** - Log every operation
3. **Rollback Support** - Keep operation history
4. **Progressive Rollout** - Start with read-only commands

### Success Criteria

#### Sprint 1 Success
- [ ] Can list all collections
- [ ] Can view collection details
- [ ] Can safely delete test collections
- [ ] Protected collections cannot be deleted
- [ ] All commands have --help

#### Sprint 2 Success
- [ ] Can create collections
- [ ] Can backup collections
- [ ] Can restore from backup
- [ ] Filtering works correctly
- [ ] JSON output available

#### Sprint 3 Success
- [ ] Can clear collection data
- [ ] Statistics are accurate
- [ ] Templates work
- [ ] Compression reduces backup size
- [ ] Catalog tracks all operations

### Communication Plan

#### User Notification
```markdown
## elysiactl v0.2.0 - Collection Management

New collection management commands:
- `elysiactl col ls` - List all collections
- `elysiactl col show <name>` - Show collection details
- `elysiactl col rm <name>` - Remove collection (with safety)
- `elysiactl col create <name>` - Create new collection

Safety features:
- Protected system collections
- Confirmation prompts
- Dry-run mode
- Operation logging

Run `elysiactl col --help` for full documentation.
```

## Next Steps

1. **Immediate Action** (Today)
   - Create file structure
   - Implement `col ls` command
   - Test with existing Weaviate cluster

2. **Tomorrow**
   - Add `col show` command
   - Implement protection system
   - Begin `col rm` implementation

3. **This Week**
   - Complete Sprint 1 features
   - Write comprehensive tests
   - Update documentation

4. **Next Week**
   - User feedback collection
   - Sprint 2 implementation
   - Performance optimization

## Conclusion

This prioritization focuses on delivering immediate value with safe, core operations first, then expanding to more advanced features. The phased approach ensures each component is thoroughly tested before moving to the next, minimizing risk while maximizing user benefit.