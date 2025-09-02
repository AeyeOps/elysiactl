# Phase 3: Fix Weaviate RAFT Consensus and True Replication

## Objective
Fix the fundamental Weaviate cluster configuration to enable proper RAFT consensus and true data replication, resolving the root cause of false cluster verification failures.

## Problem Summary
The current Weaviate cluster appears healthy but lacks true replication due to missing RAFT consensus configuration. Collections show replication_factor=3 in their schema but actually have 3 shards on node1 with no replicas on other nodes. This creates a false sense of redundancy and causes cluster verification to correctly report issues that appear as false negatives.

## Root Cause Analysis

### What's Happening
1. **Gossip Cluster vs RAFT Cluster**: Nodes can see each other (gossip works) but can't replicate metadata (RAFT broken)
2. **Sharding Without Replication**: ELYSIA_CONFIG__ has 3 shards but replication_factor=1 in practice
3. **Missing Configuration**: docker-compose.yaml lacks CLUSTER_DATA_BIND_PORT and RAFT settings
4. **Misleading Schema**: Collections show replication_factor=3 but it's not honored without RAFT

### Evidence from Logs
- `"async replication disabled on shard"` - No replication despite schema settings
- `"local index \"ELYSIA_CONFIG__\" not found"` on nodes 2 and 3
- `"cannot achieve consistency level \"QUORUM\": read error"` - Can't read from replicas that don't exist
- All shards (W0komeZfLFXE, vVAA9Z7uzflt, USzx9SAQQLTg) only exist on node1

## Implementation Details

### File: `/opt/weaviate/docker-compose.yaml`

**Change 1: Add RAFT configuration to node1**
**Location:** Lines 22-32 (environment section)
**Current Code:**
```yaml
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_API_BASED_MODULES: 'true'
      ENABLE_MODULES: 'text2vec-openai,text2vec-google,generative-openai,generative-google,generative-anthropic,text2vec-ollama,generative-ollama'
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      GOOGLE_APIKEY: ${GOOGLE_API_KEY}
      ANTHROPIC_APIKEY: ${ANTHROPIC_API_KEY}
      CLUSTER_HOSTNAME: 'node1'
      CLUSTER_GOSSIP_BIND_PORT: 7100
```

**New Code:**
```yaml
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_API_BASED_MODULES: 'true'
      ENABLE_MODULES: 'text2vec-openai,text2vec-google,generative-openai,generative-google,generative-anthropic,text2vec-ollama,generative-ollama'
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      GOOGLE_APIKEY: ${GOOGLE_API_KEY}
      ANTHROPIC_APIKEY: ${ANTHROPIC_API_KEY}
      CLUSTER_HOSTNAME: 'node1'
      CLUSTER_GOSSIP_BIND_PORT: 7100
      CLUSTER_DATA_BIND_PORT: 7101
      RAFT_JOIN: 'node1,node2,node3'
      RAFT_BOOTSTRAP_EXPECT: 3
```

**Change 2: Fix node2 configuration**
**Location:** Lines 53-64
**Current Code:**
```yaml
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_API_BASED_MODULES: 'true'
      ENABLE_MODULES: 'text2vec-openai,text2vec-google,generative-openai,generative-google,generative-anthropic,text2vec-ollama,generative-ollama'
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      GOOGLE_APIKEY: ${GOOGLE_API_KEY}
      ANTHROPIC_APIKEY: ${ANTHROPIC_API_KEY}
      CLUSTER_HOSTNAME: 'node2'
      CLUSTER_GOSSIP_BIND_PORT: 7101
      CLUSTER_JOIN: 'node1:7100'
```

**New Code:**
```yaml
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_API_BASED_MODULES: 'true'
      ENABLE_MODULES: 'text2vec-openai,text2vec-google,generative-openai,generative-google,generative-anthropic,text2vec-ollama,generative-ollama'
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      GOOGLE_APIKEY: ${GOOGLE_API_KEY}
      ANTHROPIC_APIKEY: ${ANTHROPIC_API_KEY}
      CLUSTER_HOSTNAME: 'node2'
      CLUSTER_GOSSIP_BIND_PORT: 7100
      CLUSTER_DATA_BIND_PORT: 7101
      CLUSTER_JOIN: 'node1:7100'
      RAFT_JOIN: 'node1,node2,node3'
      RAFT_BOOTSTRAP_EXPECT: 3
```

**Change 3: Fix node3 configuration**
**Location:** Lines 85-96
**Current Code:**
```yaml
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_API_BASED_MODULES: 'true'
      ENABLE_MODULES: 'text2vec-openai,text2vec-google,generative-openai,generative-google,generative-anthropic,text2vec-ollama,generative-ollama'
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      GOOGLE_APIKEY: ${GOOGLE_API_KEY}
      ANTHROPIC_APIKEY: ${ANTHROPIC_API_KEY}
      CLUSTER_HOSTNAME: 'node3'
      CLUSTER_GOSSIP_BIND_PORT: 7102
      CLUSTER_JOIN: 'node1:7100'
```

**New Code:**
```yaml
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_API_BASED_MODULES: 'true'
      ENABLE_MODULES: 'text2vec-openai,text2vec-google,generative-openai,generative-google,generative-anthropic,text2vec-ollama,generative-ollama'
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      GOOGLE_APIKEY: ${GOOGLE_API_KEY}
      ANTHROPIC_APIKEY: ${ANTHROPIC_API_KEY}
      CLUSTER_HOSTNAME: 'node3'
      CLUSTER_GOSSIP_BIND_PORT: 7100
      CLUSTER_DATA_BIND_PORT: 7101
      CLUSTER_JOIN: 'node1:7100'
      RAFT_JOIN: 'node1,node2,node3'
      RAFT_BOOTSTRAP_EXPECT: 3
```

### File: `/opt/weaviate/fix-collections.sh` (New file)

**Purpose:** Script to recreate collections with proper replication after cluster fix
```bash
#!/bin/bash
set -e

echo "Fixing Weaviate Collections with Proper Replication"
echo "===================================================="

# Wait for RAFT consensus to form
echo "Waiting for RAFT consensus..."
for i in {1..30}; do
  SYNCED=$(curl -s http://localhost:8080/v1/cluster/statistics | jq -r '.synced // false')
  if [ "$SYNCED" = "true" ]; then
    echo "✓ RAFT consensus achieved"
    break
  fi
  echo "  Attempt $i/30: Waiting for consensus..."
  sleep 2
done

# Function to recreate a collection with proper replication
recreate_collection() {
  local COLLECTION=$1
  echo ""
  echo "Processing $COLLECTION..."
  
  # Check if collection exists
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/v1/schema/$COLLECTION)
  
  if [ "$STATUS" = "200" ]; then
    # Export current schema
    echo "  Exporting schema..."
    curl -s http://localhost:8080/v1/schema/$COLLECTION > /tmp/${COLLECTION}_backup.json
    
    # Check for data
    COUNT=$(curl -s -X POST http://localhost:8080/v1/graphql \
      -H "Content-Type: application/json" \
      -d "{\"query\": \"{ Aggregate { $COLLECTION { meta { count } } } }\"}" \
      | jq -r ".data.Aggregate.$COLLECTION[0].meta.count // 0")
    
    if [ "$COUNT" -gt "0" ]; then
      echo "  ⚠ Collection has $COUNT records. Skipping to prevent data loss."
      return
    fi
    
    # Delete collection
    echo "  Deleting old collection..."
    curl -s -X DELETE http://localhost:8080/v1/schema/$COLLECTION
    sleep 1
  fi
  
  # Create with proper replication
  echo "  Creating with replication factor=3..."
  
  if [ "$COLLECTION" = "ELYSIA_CONFIG__" ]; then
    curl -s -X POST http://localhost:8080/v1/schema \
      -H "Content-Type: application/json" \
      -d '{
        "class": "ELYSIA_CONFIG__",
        "properties": [
          {"name": "config_key", "dataType": ["text"]},
          {"name": "config_value", "dataType": ["text"]}
        ],
        "replicationConfig": {
          "factor": 3,
          "asyncEnabled": true
        },
        "shardingConfig": {
          "desiredCount": 3
        }
      }'
  elif [ "$COLLECTION" = "ELYSIA_FEEDBACK__" ]; then
    curl -s -X POST http://localhost:8080/v1/schema \
      -H "Content-Type: application/json" \
      -d '{
        "class": "ELYSIA_FEEDBACK__",
        "properties": [
          {"name": "feedback_id", "dataType": ["text"]},
          {"name": "content", "dataType": ["text"]},
          {"name": "timestamp", "dataType": ["date"]}
        ],
        "replicationConfig": {
          "factor": 3,
          "asyncEnabled": true
        },
        "shardingConfig": {
          "desiredCount": 3
        }
      }'
  elif [ "$COLLECTION" = "ELYSIA_METADATA__" ]; then
    curl -s -X POST http://localhost:8080/v1/schema \
      -H "Content-Type: application/json" \
      -d '{
        "class": "ELYSIA_METADATA__",
        "properties": [
          {"name": "meta_key", "dataType": ["text"]},
          {"name": "meta_value", "dataType": ["text"]},
          {"name": "meta_type", "dataType": ["text"]}
        ],
        "replicationConfig": {
          "factor": 3,
          "asyncEnabled": true
        },
        "shardingConfig": {
          "desiredCount": 3
        }
      }'
  fi
  
  echo "  ✓ Collection recreated with proper replication"
}

# Process system collections
recreate_collection "ELYSIA_CONFIG__"
recreate_collection "ELYSIA_FEEDBACK__"
recreate_collection "ELYSIA_METADATA__"

echo ""
echo "Verifying replication status..."
sleep 2

# Verify each collection
for COLLECTION in ELYSIA_CONFIG__ ELYSIA_FEEDBACK__ ELYSIA_METADATA__; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/v1/schema/$COLLECTION)
  if [ "$STATUS" = "200" ]; then
    FACTOR=$(curl -s http://localhost:8080/v1/schema/$COLLECTION | jq -r '.replicationConfig.factor // 1')
    SHARDS=$(curl -s http://localhost:8080/v1/schema/$COLLECTION/shards | jq length)
    echo "  $COLLECTION: replication_factor=$FACTOR, shards=$SHARDS"
  else
    echo "  $COLLECTION: NOT FOUND"
  fi
done

echo ""
echo "Collection fix complete. Run 'elysiactl health --cluster' to verify."
```

## Agent Workflow

### Step 1: Stop the Weaviate Cluster
1. Stop all services: `cd /opt/weaviate && docker-compose down`
2. Backup data volumes (optional but recommended):
   ```bash
   docker run --rm -v weaviate_weaviate_data_node1:/data -v $(pwd):/backup alpine tar czf /backup/node1_backup.tar.gz /data
   docker run --rm -v weaviate_weaviate_data_node2:/data -v $(pwd):/backup alpine tar czf /backup/node2_backup.tar.gz /data
   docker run --rm -v weaviate_weaviate_data_node3:/data -v $(pwd):/backup alpine tar czf /backup/node3_backup.tar.gz /data
   ```

### Step 2: Update Docker Compose Configuration
1. Edit `/opt/weaviate/docker-compose.yaml`
2. Apply all three changes listed above
3. Ensure CLUSTER_GOSSIP_BIND_PORT is 7100 for all nodes (internal port)
4. Add CLUSTER_DATA_BIND_PORT: 7101 for all nodes
5. Add RAFT_JOIN and RAFT_BOOTSTRAP_EXPECT for all nodes

### Step 3: Clear Existing Data (Clean Start)
Since collections are misconfigured and empty:
```bash
docker volume rm weaviate_weaviate_data_node1 weaviate_weaviate_data_node2 weaviate_weaviate_data_node3
```

### Step 4: Start the Fixed Cluster
```bash
cd /opt/weaviate
docker-compose up -d
```

### Step 5: Wait for RAFT Consensus
```bash
# Wait for cluster to form consensus
for i in {1..30}; do
  SYNCED=$(curl -s http://localhost:8080/v1/cluster/statistics 2>/dev/null | jq -r '.synced // false')
  if [ "$SYNCED" = "true" ]; then
    echo "Cluster synchronized"
    break
  fi
  echo "Waiting for consensus... ($i/30)"
  sleep 2
done
```

### Step 6: Create Collections with Proper Replication
```bash
chmod +x /opt/weaviate/fix-collections.sh
/opt/weaviate/fix-collections.sh
```

### Step 7: Verify with elysiactl
```bash
uv run elysiactl health --cluster
```

## Testing

### Pre-conditions
```bash
# Current broken state
uv run elysiactl health --cluster
# Shows ELYSIA_CONFIG__ as "1/3 nodes" (incorrect)

# Check logs for replication errors
docker logs weaviate-node1-1 2>&1 | grep -i "replication\|raft"
# Shows "async replication disabled"
```

### Post-fix Validation
```bash
# Check RAFT consensus
curl -s http://localhost:8080/v1/cluster/statistics | jq
# Should show: {"synced": true}

# Check nodes see each other
curl -s http://localhost:8080/v1/nodes | jq '.nodes | length'
# Should return: 3

# Check collection replication
curl -s http://localhost:8080/v1/schema/ELYSIA_CONFIG__ | jq '.replicationConfig'
# Should show: {"factor": 3, "asyncEnabled": true}

# Verify with elysiactl
uv run elysiactl health --cluster
# Should show ELYSIA_CONFIG__ properly replicated

# Test data insertion triggers replication
curl -X POST http://localhost:8080/v1/objects \
  -H "Content-Type: application/json" \
  -d '{"class": "ELYSIA_CONFIG__", "properties": {"config_key": "test", "config_value": "test"}}'

# Verify data exists on all nodes
for port in 8080 8081 8082; do
  echo "Node $port:"
  curl -s http://localhost:$port/v1/objects/ELYSIA_CONFIG__ | jq '.objects | length'
done
# All should show: 1
```

## Success Criteria
- [ ] RAFT consensus established (cluster/statistics shows synced=true)
- [ ] All 3 nodes visible in /v1/nodes endpoint
- [ ] Collections show replication_factor=3 in schema
- [ ] Collections have shards distributed across nodes
- [ ] No "async replication disabled" messages in logs
- [ ] elysiactl health --cluster shows correct replication
- [ ] Data inserted on node1 is readable from nodes 2 and 3
- [ ] Can achieve QUORUM consistency level for reads

## Rollback Plan
If the changes cause issues:
1. Stop the cluster: `docker-compose down`
2. Restore the original docker-compose.yaml
3. Restore data volumes from backups (if created)
4. Start with old configuration: `docker-compose up -d`

## Notes
- This fix addresses the root cause, not symptoms
- Without RAFT consensus, replication_factor in schema is meaningless
- CLUSTER_GOSSIP_BIND_PORT should be same internally (7100) for all nodes
- CLUSTER_DATA_BIND_PORT enables RAFT consensus for metadata replication
- After fix, collections will truly replicate across nodes
- This enables high availability and fault tolerance as intended

## Future Improvements for elysiactl
1. Add RAFT consensus check: `curl /v1/cluster/statistics`
2. Distinguish between sharding and replication in reports
3. Check for "async replication disabled" in logs
4. Verify actual shard distribution, not just schema presence
5. Add `elysiactl diagnose raft` command for RAFT status
6. Add `elysiactl diagnose shards <collection>` for shard details

## References
- [Weaviate Cluster Architecture](https://weaviate.io/developers/weaviate/concepts/cluster)
- [RAFT Consensus in Weaviate](https://weaviate.io/developers/weaviate/concepts/replication-architecture/cluster-architecture)
- [Replication vs Sharding](https://weaviate.io/developers/weaviate/concepts/replication-architecture/replication)
- [Docker Compose Multi-node Setup](https://weaviate.io/developers/weaviate/deploy/installation-guides/docker-installation#multi-node-setup)