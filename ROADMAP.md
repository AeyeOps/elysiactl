# ElysiaCtl Roadmap

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