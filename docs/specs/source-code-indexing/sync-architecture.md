# ElysiaCtl Sync Architecture: Scale, Recovery, and Reliability

## Context: Multi-Provider Scale

We're designing for enterprise scale:
- **76+ Git repositories** across multiple providers
- **4 different Git platforms** (GitHub, Azure DevOps, 2x BitBucket)
- **Potentially millions of files** to track
- **Batch scheduled operations** (not real-time)
- **Recovery from partial failures** is critical

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Scheduled Batch Job                      │
│                    (cron/systemd timer)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                         mgit                                 │
│  - Pulls all 76 repos across providers                       │
│  - Generates change manifest                                 │
│  - Outputs to checkpoint file                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼ changes.jsonl (checkpoint file)
┌─────────────────────────────────────────────────────────────┐
│                    elysiactl index sync                      │
│  - Reads from checkpoint file                                │
│  - Processes in batches                                      │
│  - Tracks progress in state file                             │
│  - Resumes from last position on failure                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                        Weaviate                              │
│            SRC_ENTERPRISE__ Collection                       │
└─────────────────────────────────────────────────────────────┘
```

## Why Not Pure Pipes at Scale

While pipes are elegant for small operations, at scale they have issues:

### Pipe Problems
1. **No recovery**: If processing fails at file 50,000 of 100,000, you start over
2. **Memory pressure**: Some tools buffer entire pipe content
3. **No progress visibility**: Can't tell if it's stuck or working
4. **Timeout issues**: Long-running pipes can hit system limits

### Solution: Checkpoint Files

```bash
# Instead of pure pipe:
mgit status | elysiactl index sync  # ❌ No recovery

# Use checkpoint file:
mgit status --output /tmp/changes.jsonl
elysiactl index sync --input /tmp/changes.jsonl  # ✅ Resumable
```

## File Format: JSONL for Streaming

Using JSON Lines format - one JSON object per line, streamable:

```jsonl
{"op":"add","repo":"ServiceA","path":"/opt/pdi/Enterprise/ServiceA/src/main.py","size":2453}
{"op":"update","repo":"ServiceA","path":"/opt/pdi/Enterprise/ServiceA/src/utils.py","size":1234}
{"op":"delete","repo":"ServiceB","path":"/opt/pdi/Enterprise/ServiceB/old.py","size":0}
{"op":"update","repo":"ServiceC","path":"/opt/pdi/Enterprise/ServiceC/config.yaml","size":453}
```

## State Management for Recovery

```
┌─────────────────────────────────────────────────────────────┐
│                    State File Structure                      │
├─────────────────────────────────────────────────────────────┤
│ /var/lib/elysiactl/sync-state.json                          │
│                                                              │
│ {                                                            │
│   "last_run": "2025-01-01T10:30:00Z",                      │
│   "last_successful_run": "2025-01-01T04:30:00Z",           │
│   "current_batch": {                                        │
│     "input_file": "/tmp/changes.jsonl",                     │
│     "total_lines": 145000,                                  │
│     "processed_lines": 87650,                               │
│     "last_position": 87650,                                 │
│     "failures": [                                           │
│       {"line": 45321, "path": "...", "error": "..."},      │
│       {"line": 67890, "path": "...", "error": "..."}       │
│     ]                                                        │
│   }                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
```

## Batch Processing Flow

```
Start
  │
  ▼
┌─────────────────┐
│ Check for       │──── Yes ──→ ┌──────────────────┐
│ state file?     │              │ Resume from      │
└─────────────────┘              │ last position    │
  │ No                           └──────────────────┘
  ▼                                       │
┌─────────────────┐                       │
│ Start from      │◄──────────────────────┘
│ beginning       │
└─────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│         Process in batches of 100        │
│                                          │
│  ┌────────────────────────────────┐     │
│  │ Read 100 lines from JSONL      │     │
│  │ ▼                               │     │
│  │ Process each operation:        │     │
│  │ - add: index new file          │     │
│  │ - update: reindex file         │     │
│  │ - delete: remove from index    │     │
│  │ ▼                               │     │
│  │ Update state file              │     │
│  │ ▼                               │     │
│  │ Continue or handle error       │     │
│  └────────────────────────────────┘     │
│                                          │
└─────────────────────────────────────────┘
  │
  ▼
End (or Error → Will resume next run)
```

## Command Design

```bash
# Primary usage - scheduled batch
elysiactl index sync --input /tmp/changes.jsonl \
                    --state-dir /var/lib/elysiactl \
                    --batch-size 100 \
                    --on-error continue

# Options:
#   --input FILE         JSONL file with changes (required)
#   --state-dir DIR      Directory for state files (default: ~/.elysiactl)
#   --batch-size N       Process N items at a time (default: 100)
#   --on-error ACTION    continue|stop|retry (default: continue)
#   --max-retries N      Retry failed items N times (default: 3)
#   --from-line N        Start from specific line (for manual recovery)
```

## Error Handling Strategy

### Three-Level Recovery

1. **Item Level**: Individual file failures don't stop batch
   ```
   [PROCESSED] Line 1-100: 98 success, 2 failed (will retry)
   [PROCESSED] Line 101-200: 100 success
   ```

2. **Batch Level**: Batch failures trigger resume on next run
   ```
   [ERROR] Batch failed at line 5000, will resume here next run
   ```

3. **Run Level**: Complete failure logs state for investigation
   ```
   [FATAL] Cannot connect to Weaviate, state saved to /var/lib/elysiactl/failed-run-xyz.json
   ```

## Scale Considerations

### Memory Efficiency
- **Stream processing**: Never load entire file list into memory
- **Batch sizing**: Process in configurable chunks (default 100)
- **Garbage collection**: Explicitly free resources after each batch

### Time Management
```python
# Rough performance estimates
FILES_PER_SECOND = 10  # Conservative estimate
TOTAL_FILES = 145000   # Example scale

ESTIMATED_TIME = TOTAL_FILES / FILES_PER_SECOND / 60  # ~240 minutes
```

### Weaviate Optimization
- Use batch API for updates
- Implement connection pooling
- Add exponential backoff for rate limits

## Integration Script Example

```bash
#!/bin/bash
# /usr/local/bin/sync-all-repos.sh

set -euo pipefail

LOG_DIR="/var/log/elysiactl"
STATE_DIR="/var/lib/elysiactl"
CHANGE_FILE="/tmp/repo-changes-$(date +%Y%m%d-%H%M%S).jsonl"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$STATE_DIR"

echo "[$(date)] Starting repository sync" >> "$LOG_DIR/sync.log"

# Step 1: Update all repositories
echo "[$(date)] Pulling all repositories..." >> "$LOG_DIR/sync.log"
if ! mgit pull-all /opt/pdi/Enterprise >> "$LOG_DIR/mgit-pull.log" 2>&1; then
    echo "[$(date)] WARNING: Some repos failed to pull, continuing..." >> "$LOG_DIR/sync.log"
fi

# Step 2: Generate change manifest
echo "[$(date)] Detecting changes..." >> "$LOG_DIR/sync.log"
if ! mgit status /opt/pdi/Enterprise --format=jsonl --output "$CHANGE_FILE"; then
    echo "[$(date)] ERROR: Failed to generate change list" >> "$LOG_DIR/sync.log"
    exit 1
fi

# Step 3: Count changes
CHANGE_COUNT=$(wc -l < "$CHANGE_FILE")
echo "[$(date)] Found $CHANGE_COUNT changes to process" >> "$LOG_DIR/sync.log"

# Step 4: Run sync with recovery
echo "[$(date)] Starting index sync..." >> "$LOG_DIR/sync.log"
if elysiactl index sync \
    --input "$CHANGE_FILE" \
    --state-dir "$STATE_DIR" \
    --batch-size 100 \
    --on-error continue \
    >> "$LOG_DIR/sync.log" 2>&1; then
    
    echo "[$(date)] Sync completed successfully" >> "$LOG_DIR/sync.log"
    
    # Clean up old change files (keep last 7 days)
    find /tmp -name "repo-changes-*.jsonl" -mtime +7 -delete
else
    echo "[$(date)] Sync failed or partially completed, will resume next run" >> "$LOG_DIR/sync.log"
    exit 1
fi
```

## Monitoring and Alerting

### Key Metrics to Track

```bash
# Prometheus metrics format
elysiactl_sync_last_run_timestamp{status="success"} 1735650600
elysiactl_sync_files_processed_total{operation="add"} 1523
elysiactl_sync_files_processed_total{operation="update"} 8934
elysiactl_sync_files_processed_total{operation="delete"} 234
elysiactl_sync_failures_total{reason="file_not_found"} 12
elysiactl_sync_failures_total{reason="weaviate_error"} 3
elysiactl_sync_duration_seconds 4320
```

### Health Check Endpoint

```bash
elysiactl index sync --status
```

Output:
```json
{
  "last_run": "2025-01-01T10:30:00Z",
  "status": "partially_complete",
  "processed": 87650,
  "total": 145000,
  "errors": 15,
  "next_resume_position": 87651
}
```

## Failure Scenarios and Recovery

### Scenario 1: Network Partition
**Problem**: Lost connection to Weaviate mid-sync  
**Recovery**: State file preserves position, resume on next run

### Scenario 2: OOM Kill
**Problem**: Process killed due to memory pressure  
**Recovery**: State file updated every batch, lose maximum 100 items

### Scenario 3: Corrupted Input File
**Problem**: Malformed JSON in change file  
**Recovery**: Skip bad lines, log errors, continue processing

### Scenario 4: Disk Full
**Problem**: Can't write state file  
**Recovery**: Fall back to in-memory state, alert operators

## Decision Summary

Based on our requirements:

1. **Checkpoint files over pure pipes** - For recovery and visibility
2. **JSONL format** - Streamable, debuggable, standard
3. **State management** - Essential for resume capability  
4. **Batch processing** - Manages memory and provides checkpoints
5. **Scheduled runs** - Simple cron/systemd timer
6. **Conservative defaults** - Better to be slow and reliable

This architecture prioritizes **reliability over speed** and **debuggability over elegance**, which is appropriate for enterprise-scale batch operations where recovery from failure is more important than real-time updates.