# Cluster Verification Specification

## Overview
Implementation specification for `elysiactl health --cluster` command, providing automated validation of Weaviate cluster integrity and replication status.

## Command Structure
```bash
elysiactl health --cluster [OPTIONS]
```

### Options
- `--collection NAME` - Verify specific collection only
- `--quick` - Skip data consistency checks (faster)
- `--fix` - Attempt to repair detected issues (requires confirmation)
- `--json` - Output in JSON format for scripting

## Implementation Architecture

### Integration Point
Extends existing `health_command()` in `/src/elysiactl/commands/health.py` by adding cluster-specific checks when `--cluster` flag is present.

### Module Structure
```python
# src/elysiactl/services/cluster_verification.py
class ClusterVerifier:
    def __init__(self, weaviate_service: WeaviateService)
    async def verify_cluster(self) -> ClusterVerificationResult
    async def verify_collection(self, name: str) -> CollectionVerificationResult
    async def attempt_repair(self, issues: List[Issue]) -> RepairResult

# src/elysiactl/models/verification.py
@dataclass
class ClusterVerificationResult:
    healthy: bool
    node_count: int
    expected_nodes: int
    system_collections: Dict[str, CollectionStatus]
    derived_collections: Dict[str, CollectionStatus]
    issues: List[Issue]
    warnings: List[Warning]

@dataclass
class CollectionStatus:
    name: str
    exists: bool
    replication_factor: Optional[int]
    node_distribution: Dict[int, int]  # port -> instance count
    data_count: int
    consistency: ConsistencyStatus
```

## Verification Checks

### 1. Cluster Topology Verification
```python
async def verify_topology(self):
    """Verify all expected nodes are present and communicating."""
    # Check 1: Node count matches configuration
    nodes = await self.get_all_nodes()
    if len(nodes) != self.expected_node_count:
        self.add_issue("Node count mismatch", severity="critical")
    
    # Check 2: All nodes are healthy
    for node in nodes:
        if node.status != "healthy":
            self.add_issue(f"Node {node.name} unhealthy", severity="high")
    
    # Check 3: Gossip protocol functioning
    for node in nodes:
        peers = await self.get_node_peers(node)
        if len(peers) != len(nodes) - 1:
            self.add_issue(f"Node {node.name} missing peers", severity="high")
```

### 2. System Collection Verification
```python
async def verify_system_collections(self):
    """Verify ELYSIA_CONFIG__, ELYSIA_FEEDBACK__, ELYSIA_METADATA__ collections."""
    system_collections = ["ELYSIA_CONFIG__", "ELYSIA_FEEDBACK__", "ELYSIA_METADATA__"]
    
    for collection_name in system_collections:
        # Check 1: Collection exists on primary node
        exists = await self.collection_exists(collection_name, port=8080)
        if not exists:
            self.add_issue(f"{collection_name} missing", severity="critical")
            continue
        
        # Check 2: Replication factor equals node count
        schema = await self.get_collection_schema(collection_name)
        expected_factor = self.node_count if self.node_count > 1 else None
        actual_factor = schema.get("replicationConfig", {}).get("factor")
        
        if actual_factor != expected_factor:
            self.add_issue(
                f"{collection_name} replication factor: {actual_factor} (expected: {expected_factor})",
                severity="high"
            )
        
        # Check 3: Collection exists on all nodes
        for port in [8080, 8081, 8082]:
            node_has_collection = await self.collection_exists(collection_name, port)
            if not node_has_collection and expected_factor:
                self.add_issue(
                    f"{collection_name} not replicated to node {port}",
                    severity="high"
                )
```

### 3. Derived Collection Verification
```python
async def verify_derived_collections(self):
    """Verify CHUNKED_* collections inherit parent replication."""
    all_collections = await self.get_all_collections()
    
    for collection_name in all_collections:
        if collection_name.startswith("CHUNKED_"):
            parent_name = collection_name.replace("CHUNKED_", "")
            
            # Check: Derived collection has same replication as parent
            parent_factor = await self.get_replication_factor(parent_name)
            derived_factor = await self.get_replication_factor(collection_name)
            
            if parent_factor != derived_factor:
                self.add_issue(
                    f"{collection_name} replication mismatch with parent",
                    severity="medium"
                )
```

### 4. Data Consistency Verification (unless --quick)
```python
async def verify_data_consistency(self, collection_name: str):
    """Verify data is consistent across all nodes."""
    if self.quick_mode:
        return
    
    # Sample random records from primary node
    primary_samples = await self.sample_records(collection_name, port=8080, count=100)
    
    # Verify same records exist on other nodes
    for port in [8081, 8082]:
        for record_id in primary_samples:
            exists = await self.record_exists(collection_name, record_id, port)
            if not exists:
                self.add_issue(
                    f"Record {record_id} missing on node {port}",
                    severity="high"
                )
    
    # Check total counts match
    counts = {}
    for port in [8080, 8081, 8082]:
        counts[port] = await self.get_record_count(collection_name, port)
    
    if len(set(counts.values())) > 1:
        self.add_issue(
            f"Data count mismatch across nodes: {counts}",
            severity="high"
        )
```

### 5. Replication Lag Detection
```python
async def check_replication_lag(self):
    """Detect if replication is lagging between nodes."""
    # Write test record to primary
    test_id = f"test_{uuid.uuid4()}"
    await self.write_test_record(test_id, port=8080)
    
    # Check how long it takes to appear on other nodes
    start_time = time.time()
    max_wait = 5.0  # seconds
    
    for port in [8081, 8082]:
        while time.time() - start_time < max_wait:
            if await self.record_exists("ELYSIA_CONFIG__", test_id, port):
                lag = time.time() - start_time
                if lag > 1.0:
                    self.add_warning(f"Replication lag to node {port}: {lag:.2f}s")
                break
            await asyncio.sleep(0.1)
        else:
            self.add_issue(f"Replication timeout to node {port}", severity="high")
    
    # Clean up test record
    await self.delete_test_record(test_id)
```

## Output Format

### Standard Output
```
Weaviate Cluster Verification
=============================

Cluster Topology:
  ✓ 3 nodes detected (expected: 3)
  ✓ All nodes healthy
  ✓ Gossip protocol functioning

System Collections:
  ✓ ELYSIA_CONFIG__ [factor=3, distributed]
  ✓ ELYSIA_FEEDBACK__ [factor=3, distributed]
  ✗ ELYSIA_METADATA__ [factor=1, NOT REPLICATED]

Derived Collections:
  ✓ CHUNKED_documents [factor=2, matches parent]
  ⚠ CHUNKED_emails [factor=1, parent has factor=2]

Data Consistency:
  ✓ ELYSIA_CONFIG__: 1,234 records consistent
  ✗ ELYSIA_FEEDBACK__: 5 records missing on node 8082

Replication Status:
  ✓ Average lag: 0.3s
  ⚠ Peak lag: 1.2s to node 8082

ISSUES FOUND: 2 critical, 1 warning
Run 'elysiactl health --cluster --fix' to attempt repairs
```

### JSON Output (--json flag)
```json
{
  "timestamp": "2025-08-31T10:30:00Z",
  "cluster": {
    "healthy": false,
    "nodes": {
      "expected": 3,
      "actual": 3,
      "status": {
        "8080": "healthy",
        "8081": "healthy",
        "8082": "healthy"
      }
    }
  },
  "collections": {
    "system": {
      "ELYSIA_CONFIG__": {
        "exists": true,
        "replication_factor": 3,
        "node_distribution": {"8080": 1, "8081": 1, "8082": 1},
        "data_count": 1234,
        "consistent": true
      },
      "ELYSIA_METADATA__": {
        "exists": true,
        "replication_factor": 1,
        "node_distribution": {"8080": 1, "8081": 0, "8082": 0},
        "consistent": false,
        "issues": ["Not replicated to all nodes"]
      }
    },
    "derived": {
      "CHUNKED_documents": {
        "parent": "documents",
        "replication_matches_parent": true
      }
    }
  },
  "issues": [
    {
      "severity": "critical",
      "message": "ELYSIA_METADATA__ not replicated",
      "collection": "ELYSIA_METADATA__",
      "fixable": true
    }
  ],
  "warnings": [
    {
      "message": "Replication lag exceeds 1s to node 8082"
    }
  ]
}
```

## Repair Functionality (--fix flag)

### Automated Repairs
```python
async def attempt_repair(self, issues: List[Issue]) -> RepairResult:
    """Attempt to fix detected issues."""
    repairs = []
    
    for issue in issues:
        if issue.fixable:
            if issue.type == "missing_replication":
                # Recreate collection with proper replication
                success = await self.recreate_with_replication(issue.collection)
                repairs.append(RepairAttempt(issue, success))
            
            elif issue.type == "missing_data":
                # Trigger re-sync from primary node
                success = await self.resync_data(issue.collection, issue.node)
                repairs.append(RepairAttempt(issue, success))
    
    return RepairResult(repairs)
```

### Safety Measures
1. Always create backup before destructive operations
2. Require explicit confirmation for repairs
3. Dry-run mode to preview changes
4. Rollback capability if repairs fail

## Error Handling

### Connection Errors
```python
try:
    nodes = await self.get_all_nodes()
except httpx.ConnectError as e:
    return ClusterVerificationResult(
        healthy=False,
        error=f"Cannot connect to Weaviate: {e}",
        remediation="Ensure Weaviate is running: elysiactl start"
    )
```

### Partial Failures
- Continue verification even if some checks fail
- Aggregate all issues before reporting
- Provide actionable remediation steps

## Performance Considerations

### Optimization Strategies
1. **Parallel Checks**: Run node checks concurrently
2. **Sampling**: Use statistical sampling for large datasets
3. **Caching**: Cache cluster topology for duration of verification
4. **Progressive Loading**: Check critical items first

### Expected Timings
- Quick mode: < 2 seconds
- Standard mode: < 10 seconds for 1M records
- Deep verification: < 30 seconds for 10M records

## Testing Strategy

### Unit Tests
```python
def test_cluster_topology_verification():
    """Test node detection and health checks."""
    verifier = ClusterVerifier(mock_weaviate)
    result = await verifier.verify_topology()
    assert result.node_count == 3
    assert all(n.healthy for n in result.nodes)

def test_replication_factor_detection():
    """Test correct detection of replication factors."""
    # Test with replicated collection
    factor = await verifier.get_replication_factor("ELYSIA_CONFIG__")
    assert factor == 3
    
    # Test with non-replicated collection
    factor = await verifier.get_replication_factor("local_only")
    assert factor is None
```

### Integration Tests
1. Test with actual 3-node cluster
2. Test with single-node fallback
3. Test with degraded cluster (1 node down)
4. Test repair functionality in safe environment

## Success Criteria

### Minimum Viable Implementation
- Detect cluster size correctly
- Verify system collection replication
- Report issues clearly
- No false positives

### Production Ready
- All verification checks implemented
- JSON output for automation
- Repair functionality tested
- Performance within targets
- Comprehensive error handling

## Implementation Timeline

### Week 1: Core Infrastructure
- Create ClusterVerifier class
- Implement topology verification
- Basic output formatting

### Week 2: Collection Verification
- System collection checks
- Derived collection validation
- Replication factor verification

### Week 3: Data Consistency
- Sampling logic
- Cross-node verification
- Replication lag detection

### Week 4: Polish & Testing
- JSON output format
- Repair functionality
- Integration testing
- Documentation

## Dependencies

### Internal
- `WeaviateService` class for cluster interaction
- `display` module for output formatting
- Existing health check infrastructure

### External
- `httpx` for async HTTP calls
- `rich` for formatted output
- No new dependencies required

## Migration Path

### From Current Implementation
1. Extend existing `health_command()` with new flag
2. Reuse existing node check logic
3. Add new verification module
4. Maintain backward compatibility

### Future Enhancements
- Scheduled verification (cron-like)
- Historical tracking of cluster health
- Integration with monitoring systems
- Custom verification rules