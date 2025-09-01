# Phase 2: Force Schema Replication with Test Record [SUPERSEDED BY PHASE 3]

## Status: SUPERSEDED
**Reason:** Discovery of missing RAFT consensus configuration makes this approach ineffective. Without RAFT consensus (CLUSTER_DATA_BIND_PORT, RAFT_JOIN, RAFT_BOOTSTRAP_EXPECT), Weaviate cannot replicate metadata/schemas between nodes, regardless of data writes. Phase 3 addresses the root cause.

## Original Objective
Modify cluster verification to trigger Weaviate's lazy replication by inserting and deleting a test record, forcing schemas to appear on all nodes.

## Problem Summary (Now Understood Differently)
Originally thought: Weaviate uses lazy replication for collections - schemas only replicate to other nodes after the first data write.
Actually discovered: The real issue is missing RAFT consensus configuration. Without RAFT, Weaviate operates in gossip-only mode where metadata/schemas cannot replicate at all, even with replication_factor=3.

## Background Research
According to Weaviate documentation:
- Collection definitions are part of cluster metadata that should replicate via Raft consensus
- However, in practice, schema replication to non-primary nodes occurs lazily on first data write
- Inserting any record forces the schema to propagate to all configured replica nodes
- This behavior is by design for efficiency but creates confusion in verification

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/services/cluster_verification.py`

**Change 1: Add test record insertion method**
**Location:** Line 380 (after check_replication_lag method)
**Current Code:**
```python
    async def check_replication_lag(self) -> dict:
        """Check replication lag by writing and reading test record."""
        lag_results = {}
        
        # Try to write a test record
        test_id = f"test_{int(time.time())}"
        test_data = {
            "test_id": test_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Write test record to primary node
            write_response = httpx.post(
                f"http://localhost:8080/v1/objects/ELYSIA_CONFIG__",
                json=test_data,
                timeout=5.0
            )
            
            if write_response.status_code == 200:
                # [rest of method...]
```

**New Code:**
```python
    async def force_schema_replication(self, collection_name: str) -> bool:
        """Force schema replication by inserting and deleting a test record.
        
        Weaviate uses lazy replication - schemas only appear on replica nodes
        after first data write. This method triggers that replication.
        """
        test_id = f"replication_trigger_{uuid.uuid4()}"
        test_data = {
            "config_key": f"__test_replication_{test_id}",
            "config_value": "Force schema replication to all nodes"
        }
        
        try:
            # Insert test record to trigger replication
            insert_response = httpx.post(
                f"http://localhost:8080/v1/objects/{collection_name}",
                json=test_data,
                timeout=5.0
            )
            
            if insert_response.status_code not in [200, 201]:
                return False
            
            object_id = insert_response.json().get("id")
            if not object_id:
                return False
            
            # Wait briefly for replication to occur
            await asyncio.sleep(0.5)
            
            # Delete the test record
            delete_response = httpx.delete(
                f"http://localhost:8080/v1/objects/{collection_name}/{object_id}",
                timeout=5.0
            )
            
            return delete_response.status_code in [200, 204]
            
        except (httpx.HTTPError, KeyError):
            return False
    
    async def check_replication_lag(self) -> dict:
        """Check replication lag by writing and reading test record."""
        lag_results = {}
        
        # Try to write a test record
        test_id = f"test_{int(time.time())}"
        test_data = {
            "test_id": test_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Write test record to primary node
            write_response = httpx.post(
                f"http://localhost:8080/v1/objects/ELYSIA_CONFIG__",
                json=test_data,
                timeout=5.0
            )
            
            if write_response.status_code == 200:
                # [rest of method...]
```

**Change 2: Use force_schema_replication in verify_collection**
**Location:** Line 155 (in verify_collection method, after checking collection existence)
**Current Code:**
```python
    async def verify_collection(self, collection_name: str) -> CollectionStatus:
        """Verify a specific collection's replication status."""
        # Check if collection exists on primary node
        try:
            response = httpx.get(f"http://localhost:8080/v1/schema/{collection_name}")
            exists = response.status_code == 200
        except httpx.ConnectError:
            exists = False
        
        if not exists:
            return CollectionStatus(
                name=collection_name,
                exists=False,
                replication_factor=None,
                node_distribution={},
                data_count=0,
                consistent=True,
                issues=[]
            )
```

**New Code:**
```python
    async def verify_collection(self, collection_name: str) -> CollectionStatus:
        """Verify a specific collection's replication status."""
        # Check if collection exists on primary node
        try:
            response = httpx.get(f"http://localhost:8080/v1/schema/{collection_name}")
            exists = response.status_code == 200
        except httpx.ConnectError:
            exists = False
        
        if not exists:
            return CollectionStatus(
                name=collection_name,
                exists=False,
                replication_factor=None,
                node_distribution={},
                data_count=0,
                consistent=True,
                issues=[]
            )
        
        # Force schema replication if collection is empty
        # This addresses Weaviate's lazy replication behavior
        try:
            count_response = httpx.post(
                "http://localhost:8080/v1/graphql",
                json={
                    "query": f"""
                    {{
                        Aggregate {{
                            {collection_name} {{
                                meta {{
                                    count
                                }}
                            }}
                        }}
                    }}
                    """
                },
                timeout=5.0
            )
            
            if count_response.status_code == 200:
                result = count_response.json()
                count_data = result.get("data", {}).get("Aggregate", {}).get(collection_name, [])
                if count_data and len(count_data) > 0:
                    current_count = count_data[0].get("meta", {}).get("count", 0)
                    
                    # If collection is empty, force replication
                    if current_count == 0:
                        await self.force_schema_replication(collection_name)
                        # Brief wait for schema to propagate
                        await asyncio.sleep(1.0)
        except (httpx.HTTPError, KeyError):
            # Continue with verification even if forcing replication fails
            pass
```

**Change 3: Add import for uuid**
**Location:** Line 5 (in imports section)
**Current Code:**
```python
import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
```

**New Code:**
```python
import time
import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
```

### File: `/opt/elysiactl/src/elysiactl/commands/repair.py`

**Change 4: Add force replication after recreation**
**Location:** Line 92 (after recreating collection)
**Current Code:**
```python
        create_response.raise_for_status()
        console.print("[green]✓[/green] Recreated ELYSIA_CONFIG__ with replication factor=3")
    except httpx.HTTPError as e:
        console.print(f"[red]Failed to recreate collection: {e}[/red]")
```

**New Code:**
```python
        create_response.raise_for_status()
        console.print("[green]✓[/green] Recreated ELYSIA_CONFIG__ with replication factor=3")
        
        # Force schema replication by inserting and deleting a test record
        console.print("[dim]Triggering schema replication...[/dim]")
        test_data = {
            "config_key": "__replication_trigger",
            "config_value": "Forcing schema to replicate to all nodes"
        }
        
        try:
            # Insert test record
            trigger_response = httpx.post(
                "http://localhost:8080/v1/objects/ELYSIA_CONFIG__",
                json=test_data,
                timeout=5.0
            )
            
            if trigger_response.status_code in [200, 201]:
                object_id = trigger_response.json().get("id")
                
                # Wait for replication
                import time
                time.sleep(1.0)
                
                # Delete test record
                if object_id:
                    httpx.delete(f"http://localhost:8080/v1/objects/ELYSIA_CONFIG__/{object_id}")
                
                console.print("[green]✓[/green] Schema replication triggered")
        except httpx.HTTPError:
            console.print("[yellow]⚠[/yellow] Could not trigger replication (collection may be read-only)")
            
    except httpx.HTTPError as e:
        console.print(f"[red]Failed to recreate collection: {e}[/red]")
```

## Agent Workflow

### Step 1: Update cluster_verification.py
1. Open `/opt/elysiactl/src/elysiactl/services/cluster_verification.py`
2. Add `import uuid` to imports
3. Add `force_schema_replication` method after line 380
4. Modify `verify_collection` method to call `force_schema_replication` for empty collections
5. Save the file

### Step 2: Update repair.py
1. Open `/opt/elysiactl/src/elysiactl/commands/repair.py`
2. Add replication trigger logic after successful collection recreation
3. Save the file

### Step 3: Test the implementation
1. Run cluster verification: `uv run elysiactl health --cluster`
2. Verify ELYSIA_CONFIG__ now shows as replicated to all nodes
3. Run repair command: `uv run elysiactl repair config-replication`
4. Verify immediate replication occurs (no false "PARTIAL" message)

## Testing

### Pre-conditions
```bash
# Ensure cluster is running
uv run elysiactl status

# Check current false negative
uv run elysiactl health --cluster
# Should show ELYSIA_CONFIG__ as "1/3 nodes" (false negative)
```

### Execution
```bash
# Test cluster verification with new logic
uv run elysiactl health --cluster
# Should now show ELYSIA_CONFIG__ properly replicated

# Test repair command with trigger
uv run elysiactl repair config-replication
# Should show immediate success without "PARTIAL" message
```

### Post-conditions
```bash
# Verify accurate reporting
uv run elysiactl health --cluster | grep "ELYSIA_CONFIG__"
# Should show "3/3 nodes" or correct distribution

# Verify no test records remain
curl -X POST http://localhost:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ Get { ELYSIA_CONFIG__ { config_key config_value } } }"}'
# Should return empty results
```

## Success Criteria
- [ ] Cluster verification accurately reports replication status for empty collections
- [ ] No false negatives for properly configured collections
- [ ] Test records are inserted and deleted successfully
- [ ] Schema appears on all configured replica nodes after trigger
- [ ] No test data remains in collections after verification
- [ ] Repair command shows immediate success without misleading "PARTIAL" messages

## Rollback Plan
If the changes cause issues:
1. Remove the `force_schema_replication` method
2. Remove calls to `force_schema_replication` from `verify_collection`
3. Remove trigger logic from repair command
4. The original behavior returns (with false negatives but no side effects)

## Discovery During Implementation

### What We Found
1. **API Endpoint Issue**: Initial implementation used wrong endpoint `/v1/objects/COLLECTION_NAME` instead of `/v1/objects` with class in payload
2. **Docker Logs Revealed Root Cause**: 
   - "async replication disabled on shard"
   - ELYSIA_CONFIG__ shards exist only on node1
   - No actual replication occurring despite replication_factor=3
3. **Missing RAFT Configuration**: The docker-compose.yaml lacks critical RAFT settings:
   - No CLUSTER_DATA_BIND_PORT for any nodes
   - No RAFT_JOIN configuration
   - No RAFT_BOOTSTRAP_EXPECT setting

### Why This Phase Won't Work
Without RAFT consensus:
- Metadata/schemas cannot replicate between nodes
- Only gossip cluster exists (for node discovery)
- No consensus mechanism for schema synchronization
- Writing data won't trigger schema replication because the underlying infrastructure isn't configured

## Next Steps
Implement Phase 3 to fix the root cause by adding RAFT consensus configuration to docker-compose.yaml. Only after RAFT is properly configured will schema replication (lazy or otherwise) function correctly.

## Original Notes (For Historical Context)
- This leverages Weaviate's documented lazy replication behavior
- The test record insertion is safe as it's immediately deleted
- This approach is deterministic - it forces eventual consistency to complete
- Based on research showing cluster metadata should replicate via Raft but doesn't until first write
- Fixes user experience issue where correct configurations appear broken