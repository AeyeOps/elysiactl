# elysiactl Collection Management Specification

## Overview
Add collection management capabilities to elysiactl for managing Weaviate collections through a simple CLI interface.

## Command Structure

```
elysiactl collection <subcommand> [options]
elysiactl col <subcommand> [options]  # Short alias
```

## Subcommands

### 1. List Collections
```bash
elysiactl col ls [options]
elysiactl collection list [options]

Options:
  --verbose, -v     Show detailed information (object count, replication, sharding)
  --format          Output format: table (default), json, yaml
  --filter          Filter by pattern (supports wildcards)
```

Example output:
```
Collections (3 total)
────────────────────
Name                 Objects  Replicas  Shards  Status
ELYSIA_CONFIG__      0        3         1       READY
UserDocuments        1,250    3         2       READY  
ProductCatalog       45,320   3         4       READY
```

### 2. Show Collection Details
```bash
elysiactl col show <name_or_id>
elysiactl collection describe <name_or_id>

Options:
  --schema          Include schema information
  --stats           Include detailed statistics
  --format          Output format: table (default), json, yaml
```

### 3. Remove Collection
```bash
elysiactl col rm <name_or_id> [options]
elysiactl collection remove <name_or_id> [options]
elysiactl collection delete <name_or_id> [options]

Options:
  --force           Skip confirmation prompt
  --dry-run         Show what would be deleted without doing it
  --cascade         Remove dependent objects (future)

Behavior:
  - Accepts collection name or UUID
  - Shows object count and asks for confirmation
  - Prevents deletion of system collections (configurable)
  - Can protect collections with naming patterns
```

Example:
```bash
$ elysiactl col rm UserDocuments
⚠ WARNING: This will permanently delete collection 'UserDocuments'
  Objects: 1,250
  Replicas: 3
  Created: 2024-01-15

Type 'yes' to confirm deletion: yes
✓ Collection 'UserDocuments' deleted successfully
```

### 4. Create Collection
```bash
elysiactl col create <name> [options]
elysiactl collection create <name> [options]

Options:
  --schema-file     Path to JSON schema file
  --replication     Replication factor (default: 3)
  --shards          Number of shards (default: 1)
  --from-template   Use existing collection as template
```

### 5. Backup Collection
```bash
elysiactl col backup <name_or_id> [options]
elysiactl collection backup <name_or_id> [options]

Options:
  --output, -o      Output directory (default: ./backups)
  --include-data    Include object data (default: schema only)
  --format          Backup format: json (default), parquet
```

### 6. Restore Collection
```bash
elysiactl col restore <backup_file> [options]
elysiactl collection restore <backup_file> [options]

Options:
  --name            Override collection name
  --skip-data       Restore schema only
  --merge           Merge with existing collection
```

### 7. Collection Statistics
```bash
elysiactl col stats [name_or_id]
elysiactl collection statistics [name_or_id]

Options:
  --watch, -w       Live update statistics
  --interval        Update interval in seconds (default: 5)
```

### 8. Clear Collection Data
```bash
elysiactl col clear <name_or_id> [options]
elysiactl collection truncate <name_or_id> [options]

Options:
  --force           Skip confirmation
  --keep-schema     Preserve schema (default: true)
```

## Implementation Plan

### Phase 1: Core Commands (Priority)
1. `col ls` - List all collections
2. `col show` - Show collection details
3. `col rm` - Remove collection
4. `col create` - Create collection

### Phase 2: Data Operations
1. `col backup` - Backup collection
2. `col restore` - Restore from backup
3. `col clear` - Clear collection data

### Phase 3: Advanced Features
1. `col stats` - Real-time statistics
2. `col copy` - Copy collection
3. `col rename` - Rename collection
4. `col migrate` - Migrate between clusters

## Safety Features

### Protected Collections
```python
PROTECTED_PATTERNS = [
    "ELYSIA_*",      # Elysia system collections
    "*_SYSTEM",      # System collections
    ".internal*",    # Internal collections
]
```

### Confirmation Requirements
- Deleting collections with data
- Clearing data from collections
- Modifying system collections

### Dry Run Mode
All destructive operations support `--dry-run` to preview changes

## Error Handling

### Common Scenarios
1. **Collection not found**: Suggest similar names
2. **Permission denied**: Check authentication
3. **Collection in use**: Show active connections
4. **Replication issues**: Provide repair suggestions

## Configuration

### Settings in CLAUDE.md
```yaml
collection_management:
  protected_patterns:
    - "ELYSIA_*"
    - "*_SYSTEM"
  require_confirmation:
    delete: true
    clear: true
    modify_system: true
  default_replication: 3
  default_shards: 1
```

## API Integration Points

### Weaviate APIs
- `GET /v1/schema` - List collections
- `GET /v1/schema/{className}` - Get collection details
- `DELETE /v1/schema/{className}` - Delete collection
- `POST /v1/schema` - Create collection
- `GET /v1/objects?class={className}` - Get object count

### Elysia APIs
- Collection usage tracking
- User permission checks
- Audit logging

## Testing Strategy

### Unit Tests
- Command parsing
- Safety checks
- Pattern matching

### Integration Tests
- Create/delete cycles
- Backup/restore operations
- Error handling

### Manual Testing Checklist
- [ ] List empty cluster
- [ ] Create collection with schema
- [ ] List with verbose output
- [ ] Delete empty collection
- [ ] Delete collection with data (with confirmation)
- [ ] Attempt to delete protected collection
- [ ] Backup and restore collection
- [ ] Clear collection data

## Future Enhancements

### Version 2.0
- Collection versioning
- Schema migration tools
- Cross-cluster replication
- Collection templates library

### Version 3.0
- Collection access control
- Usage analytics
- Performance profiling
- Automated optimization

## Example Usage Scenarios

### Scenario 1: Development Cleanup
```bash
# List all test collections
elysiactl col ls --filter "test_*"

# Remove all test collections
for col in $(elysiactl col ls --filter "test_*" --format json | jq -r '.[].name'); do
  elysiactl col rm $col --force
done
```

### Scenario 2: Production Backup
```bash
# Backup critical collections
elysiactl col backup ProductCatalog --include-data
elysiactl col backup UserDocuments --include-data
elysiactl col backup Orders --include-data
```

### Scenario 3: Schema Update
```bash
# Backup existing collection
elysiactl col backup UserProfile --output ./backup

# Delete and recreate with new schema
elysiactl col rm UserProfile --force
elysiactl col create UserProfile --schema-file ./new-schema.json

# Restore data
elysiactl col restore ./backup/UserProfile.json --skip-schema
```

## Documentation Requirements

### README.md Update
- Add collection management section
- Include common examples
- Safety warnings for destructive operations

### Help Text
Each command must have:
- Clear description
- All options documented
- At least 2 examples
- Safety warnings where applicable

### Man Pages (Future)
Generate man pages for system-wide installation