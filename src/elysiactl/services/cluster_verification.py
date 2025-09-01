"""Cluster verification service for Weaviate multi-node validation."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
import httpx
import json

from .weaviate import WeaviateService


@dataclass
class Issue:
    """Represents a cluster verification issue."""
    severity: str  # "critical", "high", "medium", "low"
    message: str
    collection: Optional[str] = None
    node: Optional[int] = None
    fixable: bool = False
    issue_type: Optional[str] = None


@dataclass
class Warning:
    """Represents a cluster verification warning."""
    message: str
    node: Optional[int] = None


@dataclass
class CollectionStatus:
    """Status of a collection across the cluster."""
    name: str
    exists: bool
    replication_factor: Optional[int]
    node_distribution: Dict[int, int]  # port -> instance count
    data_count: int
    consistent: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class ConsistencyStatus:
    """Data consistency status for a collection."""
    consistent: bool
    total_records: int
    node_counts: Dict[int, int]
    missing_records: Dict[int, List[str]] = field(default_factory=dict)


@dataclass
class ClusterVerificationResult:
    """Result of cluster verification."""
    healthy: bool
    node_count: int
    expected_nodes: int
    system_collections: Dict[str, CollectionStatus]
    derived_collections: Dict[str, CollectionStatus]
    issues: List[Issue]
    warnings: List[Warning]
    replication_lag: Dict[int, float] = field(default_factory=dict)
    error: Optional[str] = None


class ClusterVerifier:
    """Weaviate cluster verification service."""
    
    def __init__(self, weaviate_service: WeaviateService):
        self.weaviate = weaviate_service
        self.nodes = [8080, 8081, 8082]
        self.expected_node_count = 3
        self.system_collections = ["ELYSIA_CONFIG__", "ELYSIA_FEEDBACK__", "ELYSIA_METADATA__"]
        
    async def verify_cluster(self, quick: bool = False, collection_filter: Optional[str] = None) -> ClusterVerificationResult:
        """Perform comprehensive cluster verification."""
        result = ClusterVerificationResult(
            healthy=True,
            node_count=0,
            expected_nodes=self.expected_node_count,
            system_collections={},
            derived_collections={},
            issues=[],
            warnings=[]
        )
        
        try:
            # Check topology first
            await self._verify_topology(result)
            
            if result.node_count == 0:
                result.error = "No Weaviate nodes reachable"
                result.healthy = False
                return result
            
            # Check system collections
            await self._verify_system_collections(result, collection_filter)
            
            # Check derived collections
            await self._verify_derived_collections(result, collection_filter)
            
            # Data consistency checks (unless quick mode)
            if not quick:
                await self._verify_data_consistency(result, collection_filter)
                await self._check_replication_lag(result)
            
            # Determine overall health
            result.healthy = not any(issue.severity in ["critical", "high"] for issue in result.issues)
            
        except Exception as e:
            result.error = f"Verification failed: {str(e)}"
            result.healthy = False
        
        return result
    
    async def _verify_topology(self, result: ClusterVerificationResult):
        """Verify cluster topology and node health."""
        healthy_nodes = []
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check each node
            for port in self.nodes:
                try:
                    response = await client.get(f"http://localhost:{port}/v1/nodes")
                    if response.status_code == 200:
                        healthy_nodes.append(port)
                        # Get cluster info from first healthy node
                        if not result.node_count:
                            try:
                                data = response.json()
                                cluster_nodes = data.get("nodes", [])
                                result.node_count = len(cluster_nodes)
                                
                                # Check if all cluster nodes are healthy
                                unhealthy_nodes = [
                                    node for node in cluster_nodes 
                                    if node.get("status") != "HEALTHY"
                                ]
                                
                                if unhealthy_nodes:
                                    for node in unhealthy_nodes:
                                        result.issues.append(Issue(
                                            severity="high",
                                            message=f"Node {node.get('name', 'unknown')} status: {node.get('status', 'unknown')}",
                                            node=port
                                        ))
                                        
                            except json.JSONDecodeError:
                                result.warnings.append(Warning(f"Unable to parse cluster info from node {port}"))
                                
                except Exception as e:
                    result.issues.append(Issue(
                        severity="critical" if port == 8080 else "high",
                        message=f"Node {port} unreachable: {str(e)}",
                        node=port
                    ))
        
        # Validate node count
        if len(healthy_nodes) != self.expected_node_count:
            result.issues.append(Issue(
                severity="critical",
                message=f"Only {len(healthy_nodes)} of {self.expected_node_count} expected nodes are reachable",
                fixable=False
            ))
        
        # Update node count to reachable nodes if cluster info unavailable
        if not result.node_count:
            result.node_count = len(healthy_nodes)
    
    async def _verify_system_collections(self, result: ClusterVerificationResult, collection_filter: Optional[str]):
        """Verify system collections replication."""
        collections_to_check = self.system_collections
        if collection_filter:
            collections_to_check = [c for c in self.system_collections if collection_filter.lower() in c.lower()]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for collection_name in collections_to_check:
                status = await self._check_collection_status(client, collection_name)
                result.system_collections[collection_name] = status
                
                # Validate replication
                if status.exists and status.replication_factor and status.replication_factor != result.node_count:
                    result.issues.append(Issue(
                        severity="high",
                        message=f"{collection_name} replication factor: {status.replication_factor} (expected: {result.node_count})",
                        collection=collection_name,
                        fixable=True,
                        issue_type="missing_replication"
                    ))
                
                # Check distribution across nodes
                missing_nodes = []
                for port in self.nodes:
                    if port not in status.node_distribution or status.node_distribution[port] == 0:
                        missing_nodes.append(port)
                
                if missing_nodes and status.replication_factor and status.replication_factor > 1:
                    result.issues.append(Issue(
                        severity="high",
                        message=f"{collection_name} not replicated to nodes: {missing_nodes}",
                        collection=collection_name,
                        fixable=True,
                        issue_type="missing_data"
                    ))
    
    async def _verify_derived_collections(self, result: ClusterVerificationResult, collection_filter: Optional[str]):
        """Verify CHUNKED_* collections inherit parent replication."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Get all collections from primary node
                response = await client.get("http://localhost:8080/v1/schema")
                if response.status_code != 200:
                    result.warnings.append(Warning("Unable to fetch schema for derived collections check"))
                    return
                
                schema_data = response.json()
                all_collections = [cls.get("class") for cls in schema_data.get("classes", [])]
                
                # Filter derived collections
                derived_collections = [c for c in all_collections if c and c.startswith("CHUNKED_")]
                
                if collection_filter:
                    derived_collections = [c for c in derived_collections if collection_filter.lower() in c.lower()]
                
                for derived_name in derived_collections:
                    parent_name = derived_name.replace("CHUNKED_", "")
                    
                    # Check both collections
                    derived_status = await self._check_collection_status(client, derived_name)
                    parent_status = await self._check_collection_status(client, parent_name)
                    
                    result.derived_collections[derived_name] = derived_status
                    
                    # Compare replication factors
                    if (derived_status.exists and parent_status.exists and 
                        derived_status.replication_factor != parent_status.replication_factor):
                        result.issues.append(Issue(
                            severity="medium",
                            message=f"{derived_name} replication factor ({derived_status.replication_factor}) doesn't match parent {parent_name} ({parent_status.replication_factor})",
                            collection=derived_name
                        ))
                        
            except Exception as e:
                result.warnings.append(Warning(f"Error checking derived collections: {str(e)}"))
    
    async def _check_collection_status(self, client: httpx.AsyncClient, collection_name: str) -> CollectionStatus:
        """Check the status of a specific collection."""
        status = CollectionStatus(
            name=collection_name,
            exists=False,
            replication_factor=None,
            node_distribution={},
            data_count=0,
            consistent=True
        )
        
        try:
            # Check collection schema on primary node
            response = await client.get(f"http://localhost:8080/v1/schema/{collection_name}")
            
            if response.status_code == 200:
                status.exists = True
                try:
                    schema = response.json()
                    replication_config = schema.get("replicationConfig", {})
                    status.replication_factor = replication_config.get("factor", 1)
                except:
                    status.replication_factor = 1
                
                # Check distribution across nodes
                for port in self.nodes:
                    try:
                        node_response = await client.get(f"http://localhost:{port}/v1/schema")
                        if node_response.status_code == 200:
                            node_schema = node_response.json()
                            classes = node_schema.get("classes", [])
                            # Check if collection exists on this node (1 or 0, not count)
                            collection_exists = any(c.get("class") == collection_name for c in classes)
                            status.node_distribution[port] = 1 if collection_exists else 0
                        else:
                            status.node_distribution[port] = 0
                    except:
                        status.node_distribution[port] = 0
                
                # Get data count (from primary node)
                try:
                    count_response = await client.post(
                        "http://localhost:8080/v1/graphql",
                        json={
                            "query": f"{{ Aggregate {{ {collection_name} {{ meta {{ count }} }} }} }}"
                        }
                    )
                    if count_response.status_code == 200:
                        count_data = count_response.json()
                        count_path = count_data.get("data", {}).get("Aggregate", {}).get(collection_name, [])
                        if count_path:
                            status.data_count = count_path[0].get("meta", {}).get("count", 0)
                except:
                    pass  # Count not critical
                    
        except Exception as e:
            status.issues.append(f"Error checking collection: {str(e)}")
        
        return status
    
    async def _verify_data_consistency(self, result: ClusterVerificationResult, collection_filter: Optional[str]):
        """Verify data consistency across nodes."""
        collections_to_check = list(result.system_collections.keys())
        
        if collection_filter:
            collections_to_check = [c for c in collections_to_check if collection_filter.lower() in c.lower()]
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for collection_name in collections_to_check:
                status = result.system_collections[collection_name]
                
                if not status.exists or status.replication_factor <= 1:
                    continue
                
                # Check data counts across nodes
                node_counts = {}
                for port in self.nodes:
                    if port in status.node_distribution and status.node_distribution[port] > 0:
                        try:
                            count_response = await client.post(
                                f"http://localhost:{port}/v1/graphql",
                                json={
                                    "query": f"{{ Aggregate {{ {collection_name} {{ meta {{ count }} }} }} }}"
                                }
                            )
                            if count_response.status_code == 200:
                                count_data = count_response.json()
                                count_path = count_data.get("data", {}).get("Aggregate", {}).get(collection_name, [])
                                if count_path:
                                    node_counts[port] = count_path[0].get("meta", {}).get("count", 0)
                        except:
                            node_counts[port] = -1  # Error marker
                
                # Check for count mismatches
                if len(set(v for v in node_counts.values() if v >= 0)) > 1:
                    result.issues.append(Issue(
                        severity="high",
                        message=f"{collection_name} data count mismatch across nodes: {node_counts}",
                        collection=collection_name,
                        fixable=True,
                        issue_type="missing_data"
                    ))
                    status.consistent = False
    
    async def _check_replication_lag(self, result: ClusterVerificationResult):
        """Check replication lag by writing a test record."""
        if not result.system_collections.get("ELYSIA_CONFIG__", {}).exists:
            return
        
        test_id = f"test_{uuid.uuid4()}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Write test record to primary node
                write_response = await client.post(
                    "http://localhost:8080/v1/objects",
                    json={
                        "class": "ELYSIA_CONFIG__",
                        "id": test_id,
                        "properties": {
                            "test_field": "cluster_verification_test"
                        }
                    }
                )
                
                if write_response.status_code not in [200, 201]:
                    result.warnings.append(Warning("Unable to write test record for lag detection"))
                    return
                
                start_time = time.time()
                max_wait = 5.0
                
                # Check replication to other nodes
                for port in [8081, 8082]:
                    node_start = time.time()
                    while time.time() - start_time < max_wait:
                        try:
                            check_response = await client.get(f"http://localhost:{port}/v1/objects/ELYSIA_CONFIG__/{test_id}")
                            if check_response.status_code == 200:
                                lag = time.time() - node_start
                                result.replication_lag[port] = lag
                                
                                if lag > 1.0:
                                    result.warnings.append(Warning(
                                        f"Replication lag to node {port}: {lag:.2f}s",
                                        node=port
                                    ))
                                break
                        except:
                            pass
                        
                        await asyncio.sleep(0.1)
                    else:
                        result.issues.append(Issue(
                            severity="high",
                            message=f"Replication timeout to node {port}",
                            node=port,
                            fixable=False
                        ))
                
                # Clean up test record
                await client.delete(f"http://localhost:8080/v1/objects/ELYSIA_CONFIG__/{test_id}")
                
            except Exception as e:
                result.warnings.append(Warning(f"Replication lag check failed: {str(e)}"))
    
    async def attempt_repair(self, issues: List[Issue]) -> Dict[str, Any]:
        """Attempt to repair detected issues."""
        repairs = []
        
        # This is a placeholder for repair functionality
        # In a real implementation, this would:
        # 1. Create backups before making changes
        # 2. Fix replication factors
        # 3. Re-sync missing data
        # 4. Validate repairs
        
        for issue in issues:
            if not issue.fixable:
                continue
            
            repair_result = {
                "issue": issue.message,
                "attempted": True,
                "success": False,
                "error": "Repair functionality not yet implemented"
            }
            repairs.append(repair_result)
        
        return {
            "total_issues": len(issues),
            "fixable_issues": len([i for i in issues if i.fixable]),
            "repairs_attempted": len(repairs),
            "repairs": repairs
        }