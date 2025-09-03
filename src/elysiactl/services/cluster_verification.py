"""Cluster verification service for Weaviate multi-node validation."""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..config import get_config
from .weaviate import WeaviateService


@dataclass
class Issue:
    """Represents a cluster verification issue."""

    severity: str  # "critical", "high", "medium", "low"
    message: str
    collection: str | None = None
    node: int | None = None
    fixable: bool = False
    issue_type: str | None = None


@dataclass
class Warning:
    """Represents a cluster verification warning."""

    message: str
    node: int | None = None


@dataclass
class CollectionStatus:
    """Status of a collection across the cluster."""

    name: str
    exists: bool
    replication_factor: int | None
    node_distribution: dict[int, int]  # port -> instance count
    data_count: int
    consistent: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class ConsistencyStatus:
    """Data consistency status for a collection."""

    consistent: bool
    total_records: int
    node_counts: dict[int, int]
    missing_records: dict[int, list[str]] = field(default_factory=dict)


@dataclass
class ClusterVerificationResult:
    """Result of cluster verification."""

    healthy: bool
    node_count: int
    expected_nodes: int
    system_collections: dict[str, CollectionStatus]
    derived_collections: dict[str, CollectionStatus]
    issues: list[Issue]
    warnings: list[Warning]
    error: str | None = None


class ClusterVerifier:
    """Weaviate cluster verification service."""

    def __init__(self, weaviate_service: WeaviateService):
        self.weaviate = weaviate_service
        config = get_config()
        self.nodes = config.services.weaviate_cluster_ports
        self.expected_node_count = len(self.nodes)
        # Expected system collections that should exist
        self.system_collections = [
            "ELYSIA_CONFIG__",
            "ELYSIA_TREES__",
            "ELYSIA_FEEDBACK__",
            "ELYSIA_METADATA__",
        ]

    async def verify_cluster(
        self, quick: bool = False, collection_filter: str | None = None
    ) -> ClusterVerificationResult:
        """Perform comprehensive cluster verification."""
        result = ClusterVerificationResult(
            healthy=True,
            node_count=0,
            expected_nodes=self.expected_node_count,
            system_collections={},
            derived_collections={},
            issues=[],
            warnings=[],
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
                await self._wait_for_replication_settling(result)

            # Determine overall health
            result.healthy = not any(
                issue.severity in ["critical", "high"] for issue in result.issues
            )

        except Exception as e:
            result.error = f"Verification failed: {e!s}"
            result.healthy = False

        return result

    async def _verify_topology(self, result: ClusterVerificationResult):
        """Verify cluster topology and node health."""
        healthy_nodes = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check each node
            config = get_config()
            hostname = config.services.weaviate_hostname
            for port in self.nodes:
                try:
                    response = await client.get(
                        f"{config.services.weaviate_scheme}://{hostname}:{port}/v1/nodes"
                    )
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
                                    node
                                    for node in cluster_nodes
                                    if node.get("status") != "HEALTHY"
                                ]

                                if unhealthy_nodes:
                                    for node in unhealthy_nodes:
                                        result.issues.append(
                                            Issue(
                                                severity="high",
                                                message=f"Node {node.get('name', 'unknown')} status: {node.get('status', 'unknown')}",
                                                node=port,
                                            )
                                        )

                            except json.JSONDecodeError:
                                result.warnings.append(
                                    Warning(f"Unable to parse cluster info from node {port}")
                                )

                except Exception as e:
                    result.issues.append(
                        Issue(
                            severity="critical" if port == self.nodes[0] else "high",
                            message=f"Node {port} unreachable: {e!s}",
                            node=port,
                        )
                    )

        # Validate node count
        if len(healthy_nodes) != self.expected_node_count:
            result.issues.append(
                Issue(
                    severity="critical",
                    message=f"Only {len(healthy_nodes)} of {self.expected_node_count} expected nodes are reachable",
                    fixable=False,
                )
            )

        # Update node count to reachable nodes if cluster info unavailable
        if not result.node_count:
            result.node_count = len(healthy_nodes)

    async def _verify_system_collections(
        self, result: ClusterVerificationResult, collection_filter: str | None
    ):
        """Verify system collections replication."""
        # Dynamically discover all ELYSIACTL_* collections
        async with httpx.AsyncClient(timeout=10.0) as client:
            existing_elysia_collections = []
            try:
                # Get all collections from schema
                response = await client.get(f"{get_config().services.weaviate_base_url}/schema")
                if response.status_code == 200:
                    schema = response.json()
                    all_collections = [c["class"] for c in schema.get("classes", [])]
                    # Filter for ELYSIACTL_* collections
                    existing_elysia_collections = [
                        c for c in all_collections if c.startswith("ELYSIACTL_")
                    ]
            except Exception:
                pass  # Will check expected collections below

            # Combine existing ELYSIACTL_* collections with expected ones
            all_system_collections = set(existing_elysia_collections) | set(self.system_collections)

            # Apply collection filter if provided
            collections_to_check = sorted(all_system_collections)
            if collection_filter:
                collections_to_check = [
                    c for c in collections_to_check if collection_filter.lower() in c.lower()
                ]

            for collection_name in collections_to_check:
                status = await self._check_collection_status(client, collection_name)
                result.system_collections[collection_name] = status

                # Validate replication
                if (
                    status.exists
                    and status.replication_factor
                    and status.replication_factor != result.node_count
                ):
                    result.issues.append(
                        Issue(
                            severity="high",
                            message=f"{collection_name} replication factor: {status.replication_factor} (expected: {result.node_count})",
                            collection=collection_name,
                            fixable=True,
                            issue_type="missing_replication",
                        )
                    )

                # Check distribution across nodes
                missing_nodes = []
                for port in self.nodes:
                    if port not in status.node_distribution or status.node_distribution[port] == 0:
                        missing_nodes.append(port)

                if missing_nodes and status.replication_factor and status.replication_factor > 1:
                    result.issues.append(
                        Issue(
                            severity="high",
                            message=f"{collection_name} not replicated to nodes: {missing_nodes}",
                            collection=collection_name,
                            fixable=True,
                            issue_type="missing_data",
                        )
                    )

    async def _verify_derived_collections(
        self, result: ClusterVerificationResult, collection_filter: str | None
    ):
        """Verify CHUNKED_* collections inherit parent replication."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Get all collections from primary node
                response = await client.get(f"{get_config().services.weaviate_base_url}/schema")
                if response.status_code != 200:
                    result.warnings.append(
                        Warning("Unable to fetch schema for derived collections check")
                    )
                    return

                schema_data = response.json()
                all_collections = [cls.get("class") for cls in schema_data.get("classes", [])]

                # Filter derived collections
                derived_collections = [c for c in all_collections if c and c.startswith("CHUNKED_")]

                if collection_filter:
                    derived_collections = [
                        c for c in derived_collections if collection_filter.lower() in c.lower()
                    ]

                for derived_name in derived_collections:
                    parent_name = derived_name.replace("CHUNKED_", "")

                    # Check both collections
                    derived_status = await self._check_collection_status(client, derived_name)
                    parent_status = await self._check_collection_status(client, parent_name)

                    result.derived_collections[derived_name] = derived_status

                    # Compare replication factors
                    if (
                        derived_status.exists
                        and parent_status.exists
                        and derived_status.replication_factor != parent_status.replication_factor
                    ):
                        result.issues.append(
                            Issue(
                                severity="medium",
                                message=f"{derived_name} replication factor ({derived_status.replication_factor}) doesn't match parent {parent_name} ({parent_status.replication_factor})",
                                collection=derived_name,
                            )
                        )

            except Exception as e:
                result.warnings.append(Warning(f"Error checking derived collections: {e!s}"))

    async def _check_collection_status(
        self, client: httpx.AsyncClient, collection_name: str
    ) -> CollectionStatus:
        """Check the status of a specific collection."""
        status = CollectionStatus(
            name=collection_name,
            exists=False,
            replication_factor=None,
            node_distribution={},
            data_count=0,
            consistent=True,
        )

        try:
            # Check collection schema on primary node
            response = await client.get(
                f"{get_config().services.weaviate_base_url}/schema/{collection_name}"
            )

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
                        node_response = await client.get(
                            f"{config.services.weaviate_scheme}://{hostname}:{port}/v1/schema"
                        )
                        if node_response.status_code == 200:
                            node_schema = node_response.json()
                            classes = node_schema.get("classes", [])
                            # Check if collection exists on this node (1 or 0, not count)
                            collection_exists = any(
                                c.get("class") == collection_name for c in classes
                            )
                            status.node_distribution[port] = 1 if collection_exists else 0
                        else:
                            status.node_distribution[port] = 0
                    except:
                        status.node_distribution[port] = 0

                # Get data count (from primary node)
                try:
                    count_response = await client.post(
                        f"{get_config().services.weaviate_base_url}/graphql",
                        json={
                            "query": f"{{ Aggregate {{ {collection_name} {{ meta {{ count }} }} }} }}"
                        },
                    )
                    if count_response.status_code == 200:
                        count_data = count_response.json()
                        count_path = (
                            count_data.get("data", {}).get("Aggregate", {}).get(collection_name, [])
                        )
                        if count_path:
                            status.data_count = count_path[0].get("meta", {}).get("count", 0)

                            # If collection is empty, force replication to address lazy replication
                            if status.data_count == 0 and status.exists:
                                await self.force_schema_replication(collection_name)
                                # Brief wait for schema to propagate
                                await asyncio.sleep(1.0)

                                # Re-check node distribution after forcing replication
                                for port in self.nodes:
                                    try:
                                        node_response = await client.get(
                                            f"{config.services.weaviate_scheme}://{hostname}:{port}/v1/schema"
                                        )
                                        if node_response.status_code == 200:
                                            node_schema = node_response.json()
                                            classes = node_schema.get("classes", [])
                                            collection_exists = any(
                                                c.get("class") == collection_name for c in classes
                                            )
                                            status.node_distribution[port] = (
                                                1 if collection_exists else 0
                                            )
                                        else:
                                            status.node_distribution[port] = 0
                                    except:
                                        status.node_distribution[port] = 0
                except:
                    pass  # Count not critical

        except Exception as e:
            status.issues.append(f"Error checking collection: {e!s}")

        return status

    async def _verify_data_consistency(
        self, result: ClusterVerificationResult, collection_filter: str | None
    ):
        """Verify data consistency across nodes."""
        collections_to_check = list(result.system_collections.keys())

        if collection_filter:
            collections_to_check = [
                c for c in collections_to_check if collection_filter.lower() in c.lower()
            ]

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
                                f"{config.services.weaviate_scheme}://{hostname}:{port}/v1/graphql",
                                json={
                                    "query": f"{{ Aggregate {{ {collection_name} {{ meta {{ count }} }} }} }}"
                                },
                            )
                            if count_response.status_code == 200:
                                count_data = count_response.json()
                                count_path = (
                                    count_data.get("data", {})
                                    .get("Aggregate", {})
                                    .get(collection_name, [])
                                )
                                if count_path:
                                    node_counts[port] = (
                                        count_path[0].get("meta", {}).get("count", 0)
                                    )
                        except:
                            node_counts[port] = -1  # Error marker

                # Check for count mismatches
                if len(set(v for v in node_counts.values() if v >= 0)) > 1:
                    result.issues.append(
                        Issue(
                            severity="high",
                            message=f"{collection_name} data count mismatch across nodes: {node_counts}",
                            collection=collection_name,
                            fixable=True,
                            issue_type="missing_data",
                        )
                    )
                    status.consistent = False

    async def _wait_for_replication_settling(self, result: ClusterVerificationResult):
        """Wait a brief moment for replication to settle across nodes.

        Weaviate uses RAFT consensus which typically settles quickly, but we add
        a small delay to ensure schema changes have propagated to all nodes.
        """
        # Only wait if we're checking multiple nodes
        if result.node_count > 1:
            await asyncio.sleep(2.0)  # 2 seconds is usually enough for RAFT to settle

    async def force_schema_replication(self, collection_name: str) -> bool:
        """Force schema replication by inserting and deleting a test record.

        Weaviate uses lazy replication - schemas only appear on replica nodes
        after first data write. This method triggers that replication.
        """
        test_id = str(uuid.uuid4())
        test_data = {
            "class": collection_name,
            "properties": {
                "config_key": f"__test_replication_{test_id}",
                "config_value": "Force schema replication to all nodes",
            },
        }

        try:
            # Insert test record to trigger replication using correct endpoint
            async with httpx.AsyncClient() as client:
                insert_response = await client.post(
                    f"{get_config().services.weaviate_base_url}/objects",
                    json=test_data,
                    timeout=5.0,
                )

                if insert_response.status_code not in [200, 201]:
                    return False

                result = insert_response.json()
                object_id = result.get("id")
                if not object_id:
                    return False

                # Wait briefly for replication to occur
                await asyncio.sleep(0.5)

                # Delete the test record
                delete_response = await client.delete(
                    f"{get_config().services.weaviate_base_url}/objects/{collection_name}/{object_id}",
                    timeout=5.0,
                )

                return delete_response.status_code in [200, 204]

        except (httpx.HTTPError, KeyError):
            return False

    async def attempt_repair(self, issues: list[Issue]) -> dict[str, Any]:
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
                "error": "Repair functionality not yet implemented",
            }
            repairs.append(repair_result)

        return {
            "total_issues": len(issues),
            "fixable_issues": len([i for i in issues if i.fixable]),
            "repairs_attempted": len(repairs),
            "repairs": repairs,
        }
