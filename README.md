A command-line utility for managing Elysia AI and Weaviate services in development and production environments. Provides unified control, monitoring, and maintenance for multi-node Weaviate clusters and Elysia AI services.

## Overview

elysiactl simplifies the orchestration of complex AI infrastructure by providing a single interface to manage both Weaviate vector database clusters and Elysia AI services. It handles service dependencies, monitors cluster health, and provides repair utilities for common configuration issues.

## Key Features

### Service Management
- Production-grade error handling with circuit breaker pattern
- High-performance indexing with 119.7 files/second throughput
- Real-time performance monitoring and auto-tuning capabilities

### Cluster Operations
- Real-time cluster health verification
- Replication factor validation across nodes
- RAFT consensus monitoring
- Collection distribution analysis

### Maintenance Tools
- Automated repair commands for replication issues
- Safe collection recreation with data loss protection
- Schema backup and recovery capabilities
- Dry-run mode for risk-free operation preview

## Requirements

- Python 3.8 or higher
- UV package manager ([Installation Guide](https://github.com/astral-sh/uv))
- Docker and Docker Compose
- Conda environment (for Elysia AI service)

## Installation

### Using UV (Recommended)

```bash
git clone https://github.com/your-org/elysiactl.git
cd elysiactl
uv sync
uv build
uv pip install dist/elysiactl-*.whl
```

### Development Setup

```bash
git clone https://github.com/your-org/elysiactl.git
cd elysiactl
uv sync
uv run elysiactl --version
```

## Quick Start

```bash
# Check version
elysiactl --version

# Start all services
elysiactl start

# Check status
elysiactl status

# Verify cluster health
elysiactl health --cluster

# Stop all services
elysiactl stop
```

## MGIT Index + Elysia Control Integration

### Overview

This section provides a quick reference for using MGIT Index to source repositories and have Elysia Control automatically ingest them with cron job automation for differentials.

### Quick Setup (3 Steps)

#### Step 1: Configure MGIT Index
```bash
export MGIT_INDEX_PATH="/path/to/your/mgit/index"
export MGIT_REPOS_LIST="repos-to-index.txt"
export MGIT_UPDATE_INTERVAL="3600"  # 1 hour
```

#### Step 2: Configure Elysia Control
```bash
export ELYSIA_CONTROL_HOST="localhost"
export ELYSIA_CONTROL_PORT="8000"
export ELYSIA_INGEST_BATCH_SIZE="50"
export ELYSIA_DIFF_THRESHOLD="100"  # Min changes to trigger processing
```

#### Step 3: Set Up Cron Job
```bash
# Add to crontab (crontab -e)
*/30 * * * * /path/to/scripts/mgit-elysia-sync.sh
```

### Directory Structure

```bash
/your/project/
├── scripts/
│   ├── mgit-elysia-sync.sh    # Main sync script
│   ├── mgit-index-update.sh   # Update MGIT index
│   └── elysia-ingest.sh       # Elysia ingestion script
├── config/
│   ├── mgit-config.env        # MGIT configuration
│   └── elysia-config.env      # Elysia Control config
├── logs/
│   ├── mgit-updates.log       # MGIT update logs
│   └── elysia-ingest.log      # Elysia ingestion logs
└── data/
    ├── mgit-index/            # MGIT index data
    └── elysia-processed/      # Processed repo data
```

### Configuration Files

#### mgit-config.env
```bash
# MGIT Index Configuration
MGIT_INDEX_PATH=/data/mgit-index
MGIT_REPOS_FILE=/config/repos-to-index.txt
MGIT_UPDATE_INTERVAL=3600
MGIT_MAX_REPOS=1000
MGIT_CLONE_DEPTH=1
MGIT_BRANCH=main
```

#### elysia-config.env
```bash
# Elysia Control Configuration
ELYSIA_HOST=localhost
ELYSIA_PORT=8000
ELYSIA_API_KEY=your-api-key-here
ELYSIA_BATCH_SIZE=50
ELYSIA_TIMEOUT=300
ELYSIA_RETRY_ATTEMPTS=3
```

### Scripts

#### mgit-elysia-sync.sh (Main Sync Script)
```bash
#!/bin/bash
# MGIT Index to Elysia Control Sync Script

set -e

# Load configurations
source /config/mgit-config.env
source /config/elysia-config.env

LOG_FILE="/logs/mgit-elysia-sync.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "Starting MGIT-Elysia sync process"

# Step 1: Update MGIT index
log "Updating MGIT index..."
/scripts/mgit-index-update.sh

# Step 2: Check for changes
CHANGES=$(find "$MGIT_INDEX_PATH" -name "*.diff" -newer "$MGIT_INDEX_PATH/.last_sync" | wc -l)

if [ "$CHANGES" -gt "$ELYSIA_DIFF_THRESHOLD" ]; then
    log "Found $CHANGES changes, triggering Elysia ingestion..."

    # Step 3: Run Elysia ingestion
    /scripts/elysia-ingest.sh

    # Step 4: Update sync timestamp
    touch "$MGIT_INDEX_PATH/.last_sync"

    log "Sync process completed successfully"
else
    log "Only $CHANGES changes found (threshold: $ELYSIA_DIFF_THRESHOLD), skipping ingestion"
fi
```

#### mgit-index-update.sh
```bash
#!/bin/bash
# Update MGIT Index Script

source /config/mgit-config.env

log "Updating MGIT index from repos list..."

# Update existing repos
mgit update --index "$MGIT_INDEX_PATH"

# Add new repos from list
while IFS= read -r repo; do
    if [ -n "$repo" ] && [[ $repo != \#* ]]; then
        mgit add "$repo" --index "$MGIT_INDEX_PATH"
    fi
done < "$MGIT_REPOS_FILE"

# Generate differentials
mgit diff --index "$MGIT_INDEX_PATH" --output "$MGIT_INDEX_PATH/diffs/"

log "MGIT index update completed"
```

#### elysia-ingest.sh
```bash
#!/bin/bash
# Elysia Control Ingestion Script

source /config/elysia-config.env

log "Starting Elysia Control ingestion..."

# Find new/changed repos
find "$MGIT_INDEX_PATH/diffs/" -name "*.json" -type f | while read -r diff_file; do
    log "Processing $diff_file"

    # Extract repo information
    REPO_NAME=$(basename "$diff_file" .json)
    REPO_PATH="$MGIT_INDEX_PATH/repos/$REPO_NAME"

    # Ingest into Elysia Control
    curl -X POST "$ELYSIA_HOST:$ELYSIA_PORT/api/ingest/repo" \
         -H "Authorization: Bearer $ELYSIA_API_KEY" \
         -H "Content-Type: application/json" \
         -d @- << EOF
{
    "repo_path": "$REPO_PATH",
    "repo_name": "$REPO_NAME",
    "source": "mgit-index",
    "batch_size": $ELYSIA_BATCH_SIZE,
    "generate_embeddings": true,
    "create_collections": true
}
EOF

    # Check response
    if [ $? -eq 0 ]; then
        log "Successfully ingested $REPO_NAME"
        mv "$diff_file" "$diff_file.processed"
    else
        log "Failed to ingest $REPO_NAME"
    fi
done

log "Elysia Control ingestion completed"
```

### Cron Job Setup

#### Add to Crontab
```bash
# Edit crontab
crontab -e

# Add this line for 30-minute sync intervals
*/30 * * * * /path/to/scripts/mgit-elysia-sync.sh >> /logs/cron.log 2>&1

# Or for hourly sync
0 * * * * /path/to/scripts/mgit-elysia-sync.sh >> /logs/cron.log 2>&1
```

#### Cron Job Options
```bash
# Every 30 minutes
*/30 * * * * /scripts/mgit-elysia-sync.sh

# Every hour
0 * * * * /scripts/mgit-elysia-sync.sh

# Every 6 hours
0 */6 * * * /scripts/mgit-elysia-sync.sh

# Daily at 2 AM
0 2 * * * /scripts/mgit-elysia-sync.sh
```

### Monitoring & Troubleshooting

#### Check Sync Status
```bash
# View recent sync logs
tail -f /logs/mgit-elysia-sync.log

# Check MGIT index status
mgit status --index /data/mgit-index

# Check Elysia Control health
curl $ELYSIA_HOST:$ELYSIA_PORT/health
```

#### Common Issues

**Issue: No changes detected**
```bash
# Check if repos are being updated
ls -la /data/mgit-index/.git/FETCH_HEAD

# Force update
/scripts/mgit-index-update.sh
```

**Issue: Elysia ingestion fails**
```bash
# Check Elysia Control logs
tail -f /logs/elysia-control.log

# Test API connection
curl -H "Authorization: Bearer $ELYSIA_API_KEY" $ELYSIA_HOST:$ELYSIA_PORT/api/status
```

**Issue: Cron job not running**
```bash
# Check cron status
crontab -l

# Check system logs
grep CRON /var/log/syslog

# Test script manually
/scripts/mgit-elysia-sync.sh
```

### Performance Tuning

#### MGIT Index Settings
```bash
# For faster updates (shallower clones)
MGIT_CLONE_DEPTH=1

# For more comprehensive indexing
MGIT_CLONE_DEPTH=50

# Limit concurrent operations
MGIT_MAX_CONCURRENT=5
```

#### Elysia Control Settings
```bash
# Larger batches for better throughput
ELYSIA_BATCH_SIZE=100

# Smaller batches for memory efficiency
ELYSIA_BATCH_SIZE=25

# Adjust timeout for large repos
ELYSIA_TIMEOUT=600
```

### Quick Commands Reference

| Command | Purpose |
|---------|---------|
| `mgit update` | Update all indexed repos |
| `mgit add <repo>` | Add new repo to index |
| `mgit diff` | Generate change differentials |
| `curl -X POST /api/ingest/repo` | Ingest repo into Elysia |
| `crontab -e` | Edit cron jobs |
| `tail -f /logs/*.log` | Monitor sync process |

---

## Command Reference

### Service Management

```bash
elysiactl start              # Start Weaviate and Elysia services
elysiactl stop               # Stop all services gracefully
elysiactl restart            # Restart all services
elysiactl status             # Display current service status
```

### Index Operations

```bash
elysiactl index sync         # Synchronize source code with Weaviate collections
elysiactl index errors       # Monitor and manage indexing errors
elysiactl index perf         # Display real-time performance metrics
elysiactl index tune         # Auto-tune indexing configuration for optimal performance
```

### Health Monitoring

```bash
elysiactl health                          # Basic health check
elysiactl health --verbose                # Detailed diagnostics
elysiactl health --verbose --last-errors 5   # Show recent logs
elysiactl health --cluster                # Verify cluster replication
elysiactl health --cluster --json         # JSON output for automation
```

### Maintenance Operations

```bash
elysiactl repair --help                      # View repair commands
elysiactl repair config-replication          # Fix replication issues
elysiactl repair config-replication --dry-run   # Preview changes
elysiactl repair config-replication --force     # Skip confirmations
```

## Detailed Documentation

### Cluster Verification

elysiactl provides comprehensive cluster verification to ensure proper replication across Weaviate nodes:

- **Replication Factor Validation**: Verifies collections are replicated according to configuration
- **Node Distribution**: Ensures shards are properly distributed across all nodes
- **RAFT Consensus**: Monitors cluster consensus for metadata synchronization
- **Collection Health**: Validates system collections (ELYSIA_CONFIG__, ELYSIA_FEEDBACK__, ELYSIA_METADATA__)

### Repair Operations

The repair system is designed to fix common cluster configuration issues while protecting data:

#### When to Use Repair

- Cluster health check reports replication issues
- Collections show incorrect replication factor
- After modifying RAFT consensus configuration
- When adding or removing cluster nodes

#### Safety Mechanisms

1. **Data Protection**: Operations refused if collections contain data
2. **Automatic Backups**: Schema exported before any modifications
3. **Confirmation Required**: Explicit user approval for destructive operations
4. **Dry Run Support**: Preview all changes before execution

### Verbose Diagnostics

The verbose mode (`--verbose` or `-v`) provides detailed system insights:

- Individual node health status with connection metrics
- Docker container statistics and resource usage
- Recent error logs from each service (configurable with `--last-errors`)
- Collection replication details and shard distribution
- Process information including PIDs and ports

## Architecture

### System Components

elysiactl manages a complex AI infrastructure consisting of:

#### Weaviate Cluster
- Three-node distributed configuration
- Docker Compose orchestration
- RAFT consensus for metadata synchronization
- Ports: 8080 (node1), 8081 (node2), 8082 (node3)
- Persistent volume storage per node

#### Elysia AI Service
- FastAPI-based application
- Conda environment isolation
- Process lifecycle management via PID tracking
- Port: 8000 (default)

### Technical Implementation

- **Process Control**: PID-based tracking with automatic cleanup
- **Container Management**: Docker API integration for monitoring
- **Health Monitoring**: Asynchronous HTTP health checks
- **Configuration Management**: Environment-based configuration
- **Error Handling**: Comprehensive error recovery and reporting
- **Performance Optimization**: Connection pooling, batch operations, and monitoring

## Development

### Building and Testing

```bash
# Setup development environment
uv sync

# Run the tool in development
uv run elysiactl --version

# Build distribution package
uv build

# Run tests (when available)
uv run pytest tests/
```

### Code Structure

```
elysiactl/
├── pyproject.toml       # Package configuration (version, dependencies)
├── README.md            # User documentation
├── CHANGELOG.md         # Version history
├── ROADMAP.md           # Future development plans
├── src/
│   └── elysiactl/
│       ├── __init__.py  # Package initialization, version management
│       ├── cli.py       # CLI entry point and command routing
│       ├── commands/    # Command implementations
│       │   ├── health.py
│       │   ├── repair.py
│       │   ├── start.py
│       │   ├── status.py
│       │   ├── stop.py
│       │   └── index.py
│       ├── services/    # Service management logic
│       │   ├── cluster_verification.py
│       │   ├── elysia.py
│       │   ├── weaviate.py
│       │   ├── error_handling.py
│       │   ├── performance.py
│       │   ├── sync.py
│       │   └── embedding.py
│       └── utils/       # Utility functions
│           ├── display.py
│           └── process.py
└── docs/                # Additional documentation
```

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

## Contributing

Contributions are welcome. Please ensure:
- Code follows existing patterns and conventions
- Changes include appropriate error handling
- Documentation is updated for new features
- Tests are added for new functionality

## License

Copyright 2025 - Licensed under appropriate terms (to be specified)

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/elysiactl/issues)
- **Documentation**: [GitHub Wiki](https://github.com/your-org/elysiactl/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/elysiactl/discussions)

## Acknowledgments

- Weaviate team for the vector database platform
- Elysia AI team for the AI service framework
- UV team for modern Python package management
- Open source community for the excellent tooling ecosystem

---

# Appendix: Development Roadmap

## Completed Features

### Phase 4: Production Error Handling (v0.2.0) ✅ COMPLETED
- **Comprehensive error handling system** with circuit breaker pattern
- **9 error categories**: Network, Weaviate, File System, Rate Limit, Memory, Encoding, Timeout, Validation, Unknown
- **Retry logic with exponential backoff** and jitter to prevent thundering herd
- **CLI error monitoring commands**: `elysiactl index errors --summary`, `--recent`, `--reset`
- **Integration with sync pipeline** for production reliability

### Phase 5: Performance Optimization (v0.2.0) ✅ COMPLETED
- **Achieved 119.7 files/second** in performance benchmarks
- **7 optimization categories**: Parallel processing, connection pooling, batch operations, streaming, monitoring, auto-tuning, optimized client
- **90% API call reduction** through batch operations
- **Real-time performance monitoring** with throughput, memory, and connection metrics
- **Auto-tuning capabilities**: `elysiactl index tune` recommends optimal configurations

## Cluster Repair Guide

When `elysiactl health --cluster` detects replication issues, manual intervention is required. The `--fix` flag was intentionally removed to avoid "magic" fixes that could cause data loss or unexpected behavior.

### Understanding ELYSIA_CONFIG__

- **Purpose**: Key-value configuration store for Elysia
- **Schema**: Simple with `config_key` and `config_value` text fields  
- **Expected State**: Replication factor=3, distributed across all nodes

### Fixing Replication Issues Without Data Loss

#### Method 1: Replica Movement API (Weaviate v1.32+) - RECOMMENDED

Use Weaviate's shard-level replica movement to copy existing data to other nodes:

```bash
# 1. Check current shard state
curl http://localhost:8080/v1/cluster/shards/ELYSIA_CONFIG__

# 2. Use replica COPY operations (non-destructive)
# This increments replication factor per shard while preserving data
# Refer to Weaviate docs for exact API endpoints
```

#### Method 2: Export/Recreate (Only for Empty Collections)

Since ELYSIA_CONFIG__ is currently empty, this is safe:

```bash
# 1. Export schema
curl http://localhost:8080/v1/schema/ELYSIA_CONFIG__ > config_schema.json

# 2. Delete collection  
curl -X DELETE http://localhost:8080/v1/schema/ELYSIA_CONFIG__

# 3. Edit config_schema.json to ensure:
#    "replicationConfig": {"factor": 3}

# 4. Recreate with proper replication
curl -X POST http://localhost:8080/v1/schema \
  -H "Content-Type: application/json" \
  -d @config_schema.json
```

### Creating Missing System Collections

For ELYSIA_FEEDBACK__ and ELYSIA_METADATA__ (should be created by Elysia app):

```bash
# Example structure - adjust properties based on Elysia requirements
curl -X POST http://localhost:8080/v1/schema \
  -H "Content-Type: application/json" \
  -d '{
    "class": "ELYSIA_FEEDBACK__",
    "properties": [
      {"name": "feedback_id", "dataType": ["text"]},
      {"name": "content", "dataType": ["text"]},
      {"name": "timestamp", "dataType": ["date"]}
    ],
    "replicationConfig": {"factor": 3}
  }'
```

### Why No Automatic Fix?

1. **Data Safety**: Automated fixes could cause data loss
2. **Context Matters**: Each situation needs different approaches
3. **Complexity**: Too many edge cases to handle automatically
4. **User Control**: Admins should understand and approve changes

## Current Features (v0.2.0)
- Basic service orchestration (start/stop/restart)
- Simple status reporting
- Health checks with verbose diagnostics
- Individual node health monitoring
- Collection replication status
- Docker container statistics
- Recent log viewing with --last-errors
- **Production error handling with circuit breaker pattern**
- **High-performance indexing (119.7 files/second)**
- **Real-time performance monitoring and auto-tuning**
- **Source code indexing with Weaviate collections**

## Planned Features

### Enhanced Health Command (v0.3.0)
Expand the health command to be the primary diagnostic tool with progressive depth levels.

#### `health --cluster` - Cluster Verification
**Purpose**: Automated validation of cluster integrity and replication
**Problem Solved**: Manual verification of node health and replication is error-prone
**Features**:
- Verify all nodes are visible and communicating
- Check system collection replication factors (CONFIG, FEEDBACK, METADATA)
- Validate derived collection inheritance (CHUNKED_* collections)
- Data distribution analysis across nodes
- Consensus verification for cluster operations
**Example Usage**:
```bash
elysiactl health --cluster                    # Full cluster verification
elysiactl health --cluster --collection NAME  # Verify specific collection
elysiactl health --cluster --quick            # Skip data consistency checks
```

#### `health --data` - Data Consistency Verification
**Purpose**: Deep validation of data integrity across nodes
**Problem Solved**: No easy way to verify data is properly replicated
**Features**:
- Sample data from each node and compare
- Verify read-after-write consistency
- Check replication lag between nodes
- Identify orphaned or missing data
- Generate consistency report
**Example Usage**:
```bash
elysiactl health --data                      # Check all collections
elysiactl health --data --sample-size 100    # Custom sample size
elysiactl health --data --fix                # Attempt to repair inconsistencies
```

#### `health --watch` - Continuous Monitoring Mode
**Purpose**: Real-time health monitoring dashboard
**Problem Solved**: Need to observe system behavior over time
**Features**:
- Live updating health metrics
- Resource usage graphs (CPU, memory, disk)
- Operation throughput monitoring
- Replication lag tracking
- Alert on anomalies
**Example Usage**:
```bash
elysiactl health --watch                     # Interactive dashboard
elysiactl health --watch --interval 5        # Update every 5 seconds
elysiactl health --watch --export metrics.json # Export metrics
```

### Chaos Engineering Command (v0.4.0)
#### `chaos` - Controlled Resilience Testing
**Purpose**: Automated testing of system resilience and failover
**Problem Solved**: Manual failover testing is complex and risky
**Features**:
- Controlled node failures with automatic recovery
- Network partition simulation
- Resource constraint testing (CPU/memory limits)
- Data integrity validation during failures
- Automated test scenarios from playbooks
**Safety Features**:
- Dry-run mode for planning
- Automatic rollback on critical failures
- Data backup before destructive tests
- Detailed audit logging
**Example Usage**:
```bash
# Node failure testing
elysiactl chaos node --kill 1 --duration 30s     # Kill node 1 for 30 seconds
elysiactl chaos node --stop-random --count 2     # Stop 2 random nodes
elysiactl chaos node --cycle                     # Rolling restart all nodes

# Network chaos
elysiactl chaos network --latency 500ms          # Add network latency
elysiactl chaos network --partition 1,2 from 3   # Partition nodes
elysiactl chaos network --packet-loss 10%        # Simulate packet loss

# Resource chaos
elysiactl chaos resource --cpu-limit 50%         # Limit CPU usage
elysiactl chaos resource --memory-pressure       # Simulate memory pressure

# Scenario playbooks
elysiactl chaos run failover-test.yaml          # Run test scenario
elysiactl chaos validate                        # Verify system recovered
```

### Performance Testing Command (v0.4.0)
#### `benchmark` - Performance Baseline and Testing
**Purpose**: Standardized performance testing and comparison
**Problem Solved**: No consistent way to measure performance impact of changes
**Features**:
- Automated benchmark suite execution
- Operation latency measurement (create, read, update, delete)
- Throughput testing under various loads
- Replication overhead measurement
- Resource usage profiling
- Historical performance tracking
- Regression detection
**Benchmark Types**:
- **Baseline**: Establish performance baseline
- **Stress**: Find breaking points
- **Endurance**: Long-running stability tests
- **Spike**: Sudden load increase handling
- **Comparison**: Before/after analysis
**Example Usage**:
```bash
# Create baselines
elysiactl benchmark baseline --save prod-baseline   # Save current performance
elysiactl benchmark baseline --operations 10000     # Specific operation count

# Run comparisons
elysiactl benchmark compare --baseline prod-baseline  # Compare to baseline
elysiactl benchmark compare --before v1 --after v2   # Compare two versions

# Stress testing
elysiactl benchmark stress --concurrent 100         # 100 concurrent clients
elysiactl benchmark stress --duration 1h           # Run for 1 hour
elysiactl benchmark stress --ramp-up 60s          # Gradual load increase

# Generate reports
elysiactl benchmark report --format html          # HTML performance report
elysiactl benchmark report --export metrics.csv   # Export raw metrics
```

### Test Data Management (v0.3.0)
#### `test-data` - Test Data Generation and Management
**Purpose**: Consistent test data creation for development and validation
**Problem Solved**: Manual test data creation is repetitive and inconsistent
**Features**:
- Generate realistic test data with various patterns
- Support for different data types and schemas
- Consistent seed-based generation
- Bulk data operations
- Test data lifecycle management
- Data anonymization capabilities
**Data Patterns**:
- **Synthetic**: Completely artificial data
- **Sampled**: Based on production patterns
- **Scenario**: Specific test scenarios
- **Load**: High-volume stress testing data
**Example Usage**:
```bash
# Generate test data
elysiactl test-data generate --records 1000        # Generate 1000 records
elysiactl test-data generate --pattern user-activity # Use specific pattern
elysiactl test-data generate --seed 42            # Reproducible generation

# Manage test data
elysiactl test-data list                          # Show all test datasets
elysiactl test-data clean                         # Remove all test data
elysiactl test-data clean --older-than 7d        # Clean old test data
elysiactl test-data export --format json         # Export test data

# Validation
elysiactl test-data validate                     # Verify data integrity
elysiactl test-data validate --collection NAME   # Validate specific collection
```

### Individual Service Control (v0.3.0)
**Purpose**: Fine-grained control over individual services
**Features**:
- `elysiactl weaviate start/stop/restart` - Control Weaviate cluster
- `elysiactl elysia start/stop/restart` - Control Elysia AI service
- `elysiactl weaviate scale --nodes 5` - Scale Weaviate cluster
- `elysiactl elysia workers --count 4` - Adjust Elysia workers
**Example Usage**:
```bash
elysiactl weaviate restart --rolling           # Rolling restart
elysiactl elysia stop --graceful --timeout 30  # Graceful shutdown
elysiactl weaviate scale --nodes 5 --wait      # Scale and wait for ready
```

### Enhanced Log Management (v0.3.0)
**Purpose**: Comprehensive log access and analysis
**Current Implementation**: Basic log viewing with --last-errors in health command
**Planned Enhancements**:
- `elysiactl logs [service]` - View service logs
- `elysiactl logs --follow` - Tail logs in real-time
- `elysiactl logs --since 1h` - Time-based filtering
- `elysiactl logs --level error` - Severity filtering
- `elysiactl logs --search "pattern"` - Search in logs
- `elysiactl logs --export` - Export logs for analysis
**Example Usage**:
```bash
elysiactl logs weaviate --follow --level error
elysiactl logs elysia --since 30m --search "timeout"
elysiactl logs --all --export logs.tar.gz
```

### Configuration Management (v0.4.0)
**Purpose**: Centralized configuration management
**Features**:
- `elysiactl config show` - Display current configuration
- `elysiactl config validate` - Validate configuration files
- `elysiactl config diff [env1] [env2]` - Compare configurations
- `elysiactl config apply` - Apply configuration changes
- `elysiactl config rollback` - Revert to previous configuration
- Environment-specific configs (dev/staging/prod)
- Secret management integration
**Example Usage**:
```bash
elysiactl config show --env production
elysiactl config validate --strict
elysiactl config apply --env staging --dry-run
```

### Backup and Restore (v0.5.0)
**Purpose**: Data protection and disaster recovery
**Features**:
- `elysiactl backup create` - Create data backups
- `elysiactl backup restore <backup-id>` - Restore from backup
- `elysiactl backup list` - Show available backups
- `elysiactl backup verify` - Verify backup integrity
- `elysiactl backup schedule` - Automated backup scheduling
- Incremental backup support
- Cross-cluster restore capability
**Example Usage**:
```bash
elysiactl backup create --full --compress
elysiactl backup schedule --daily --retain 7
elysiactl backup restore backup-20250831 --target cluster-2
```

### Multi-Environment Support (v0.5.0)
**Purpose**: Manage multiple Weaviate clusters and environments
**Features**:
- Environment switching and isolation
- Cluster registry management
- Cross-environment operations
- Environment cloning
- Configuration templating
**Example Usage**:
```bash
elysiactl env list                           # Show all environments
elysiactl env switch production              # Switch to production
elysiactl env clone staging to staging-test  # Clone environment
elysiactl env diff staging production        # Compare environments
```

### Migration Tools (v0.6.0)
**Purpose**: Schema and data migration management
**Features**:
- Schema version tracking
- Migration script execution
- Rollback capabilities
- Data transformation pipelines
- Zero-downtime migrations
**Example Usage**:
```bash
elysiactl migrate status                    # Show migration status
elysiactl migrate up --to version-5         # Migrate to specific version
elysiactl migrate rollback --steps 2        # Rollback 2 migrations
elysiactl migrate validate                  # Validate migration integrity
```

## Implementation Priority

### Phase 1: Core Diagnostics (v0.3.0)
1. Enhanced health command with --cluster and --data flags
2. Test data management
3. Individual service control
4. Enhanced log management

### Phase 2: Operational Excellence (v0.4.0)
1. Chaos engineering capabilities
2. Performance benchmarking
3. Configuration management

### Phase 3: Enterprise Features (v0.5.0+)
1. Backup and restore
2. Multi-environment support
3. Migration tools

## Technical Debt
- Add comprehensive error handling with actionable messages
- Implement structured logging with log levels
- Add configuration validation at startup
- Create integration test suite
- Improve cross-platform support (Windows, macOS)
- Add shell completion scripts
- Implement plugin architecture for extensions
- Add telemetry and usage analytics (opt-in)

## Design Principles
1. **Progressive Disclosure**: Simple commands for common tasks, flags for advanced features
2. **Fail-Safe Defaults**: Destructive operations require confirmation
3. **Observable Operations**: Clear feedback on what's happening
4. **Composable Commands**: Commands can be combined in scripts
5. **Consistent Interface**: Similar operations use similar syntax