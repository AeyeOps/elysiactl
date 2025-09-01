# Index Sync Specification: Living Code Intelligence

## Executive Summary

Transform elysiactl's static indexing into a living, breathing code intelligence system through Unix-philosophy-compliant incremental synchronization. By leveraging standard pipes and text streams, we enable seamless integration with mgit and other Git tools while maintaining complete architectural independence.

## Core Concept

```bash
# The Unix Way: Small tools, composed beautifully
git diff --name-only HEAD~1 | elysiactl index sync --stdin
mgit status /opt/pdi/Enterprise --format=files | elysiactl index sync --stdin  
find . -newer /tmp/last-sync -type f | elysiactl index sync --stdin
```

## Architectural Principles

1. **Standard Input First**: Primary interface is stdin, making it composable with any tool
2. **Deterministic IDs**: Use file path hashes as Weaviate object IDs for reliable updates
3. **Idempotent Operations**: Running sync multiple times produces identical state
4. **Fail-Safe Defaults**: Never delete unless explicitly confirmed
5. **Observable Operations**: Clear reporting of what changed and why

## Command Design

### Primary Interface: Pipe-Friendly Sync

```bash
elysiactl index sync [OPTIONS]

Options:
  --stdin              Read file paths from standard input (default if no input specified)
  --json               Read JSON-formatted change list from stdin or file
  --changes PATH       Read changes from file instead of stdin
  --detect-changes     Auto-detect changes since last sync using git
  --collection NAME    Target collection (default: SRC_ENTERPRISE__)
  --delete-missing     Remove files from index that no longer exist on disk
  --dry-run           Show what would be changed without modifying Weaviate
  --verbose           Show detailed progress for each file
```

### Input Formats

**Simple file list** (one per line):
```
/opt/pdi/Enterprise/ServiceA/src/main.py
/opt/pdi/Enterprise/ServiceA/src/utils.py
/opt/pdi/Enterprise/ServiceB/config.yaml
```

**JSON change format** (from mgit status --json):
```json
{
  "repositories": [
    {
      "path": "/opt/pdi/Enterprise/ServiceA",
      "modified": ["src/main.py", "src/utils.py"],
      "added": ["tests/test_main.py"],
      "deleted": ["old_module.py"]
    }
  ]
}
```

### Output Format

```
Syncing to collection: SRC_ENTERPRISE__
Processing 4 changes...

[UPDATE] /opt/pdi/Enterprise/ServiceA/src/main.py (2.3kb)
[UPDATE] /opt/pdi/Enterprise/ServiceA/src/utils.py (1.1kb)
[ADD]    /opt/pdi/Enterprise/ServiceA/tests/test_main.py (3.2kb)
[DELETE] /opt/pdi/Enterprise/ServiceA/old_module.py

Summary:
  Updated: 2 files (3.4kb)
  Added:   1 file (3.2kb)
  Deleted: 1 file
  Errors:  0
  Time:    2.3s
```

## Integration Patterns

### Pattern 1: Direct Git Integration
```bash
# After pull, sync only changed files
cd /opt/pdi/Enterprise/ServiceA
git pull
git diff --name-only HEAD@{1}..HEAD | elysiactl index sync --stdin
```

### Pattern 2: mgit Orchestration
```bash
# Update all repos and sync changes
mgit pull-all /opt/pdi/Enterprise
mgit status /opt/pdi/Enterprise --format=files --modified --added | \
  elysiactl index sync --stdin
```

### Pattern 3: Time-Based Sync
```bash
# Find files modified in last hour
find /opt/pdi/Enterprise -type f -mmin -60 -name "*.py" | \
  elysiactl index sync --stdin
```

### Pattern 4: Watch Mode (Future)
```bash
# Continuous monitoring with inotify
inotifywait -m -r /opt/pdi/Enterprise -e modify,create,delete --format '%w%f' | \
  elysiactl index sync --stdin --continuous
```

## Implementation Strategy

### Deterministic Object IDs

```python
def get_object_id(file_path: str, collection: str) -> str:
    """Generate stable UUID for file path."""
    # Use relative path from repo root for stability
    relative_path = get_relative_path(file_path)
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # URL namespace
    return str(uuid.uuid5(namespace, f"{collection}:{relative_path}"))
```

### Incremental Update Logic

```python
async def sync_file(file_path: str, collection: str, operation: str):
    """Sync single file to Weaviate."""
    object_id = get_object_id(file_path, collection)
    
    if operation == "delete":
        await weaviate_client.data_object.delete(
            uuid=object_id,
            class_name=collection
        )
    elif operation in ["add", "update"]:
        content = read_file_with_limits(file_path)
        embedding = generate_embedding(content)
        
        await weaviate_client.data_object.put(
            uuid=object_id,
            class_name=collection,
            data_object={
                "path": file_path,
                "content": content,
                "metadata": extract_metadata(file_path),
                "last_indexed": datetime.utcnow()
            }
        )
```

### Change Detection Strategies

1. **Git-based**: Use git diff/status for repository changes
2. **Timestamp-based**: Track last sync time, find newer files
3. **Checksum-based**: Store file hashes, detect content changes
4. **External-provided**: Accept change lists from other tools

## Configuration Integration

```python
# Uses existing config.py patterns
@dataclass
class SyncConfig:
    """Configuration for sync operations."""
    
    # Sync behavior
    auto_delete: bool = field(default_factory=lambda: 
        os.getenv("ELYSIACTL_SYNC_AUTO_DELETE", "false").lower() == "true")
    
    # Change detection
    state_file: str = field(default_factory=lambda: 
        os.getenv("ELYSIACTL_STATE_FILE", "~/.elysiactl/last_sync.json"))
    
    # Performance tuning  
    sync_batch_size: int = field(default_factory=lambda: 
        int(os.getenv("ELYSIACTL_SYNC_BATCH_SIZE", "50")))
```

## Error Handling

- **File not found**: Log warning, continue with other files
- **Weaviate errors**: Retry with exponential backoff
- **Encoding issues**: Skip file with warning, track in error summary
- **Large files**: Respect existing max_file_size config
- **Permission denied**: Log error, continue processing

## Testing Strategy

```bash
# Test pipes with echo
echo -e "file1.py\nfile2.py" | elysiactl index sync --stdin --dry-run

# Test with find
find . -name "*.py" | head -5 | elysiactl index sync --stdin --dry-run

# Test JSON format
mgit status --json | elysiactl index sync --json --dry-run

# Test deletion safety
echo "deleted_file.py" | elysiactl index sync --stdin --delete-missing
```

## Automation Examples

### Cron Job
```bash
#!/bin/bash
# /usr/local/bin/sync-enterprise.sh
cd /opt/pdi/Enterprise
mgit pull-all . > /var/log/elysiactl/pull.log 2>&1
mgit status . --format=files | \
  elysiactl index sync --stdin >> /var/log/elysiactl/sync.log 2>&1
```

### Systemd Service
```ini
[Unit]
Description=ElysiaCtl Enterprise Sync
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'mgit status /opt/pdi/Enterprise --format=files | elysiactl index sync --stdin'
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Git Hook
```bash
#!/bin/bash
# .git/hooks/post-merge
git diff --name-only HEAD@{1}..HEAD | elysiactl index sync --stdin
```

## Success Metrics

- **Sync time**: < 5 seconds for 100 changed files
- **Memory usage**: Constant regardless of repo size (streaming)
- **Accuracy**: 100% of changes reflected in Weaviate
- **Composability**: Works with any tool that outputs file paths
- **Reliability**: Idempotent, resumable, fault-tolerant

## Future Enhancements

- **Parallel processing**: Multiple workers for large change sets
- **Incremental embeddings**: Update only changed portions of files
- **Change subscription**: WebSocket endpoint for real-time updates
- **Conflict resolution**: Handle concurrent modifications
- **Collection versioning**: Support for A/B index testing

## Summary

The index sync command transforms elysiactl from a batch indexing tool into a continuous intelligence system. By embracing Unix pipes and standard text formats, we create a powerful yet simple solution that integrates naturally with existing Git workflows while remaining completely decoupled from any specific Git tool.

The design prioritizes composability, reliability, and operational simplicity - making it equally suitable for manual updates, cron jobs, or sophisticated CI/CD pipelines.