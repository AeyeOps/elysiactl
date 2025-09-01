"""Weaviate service management."""

import os
import time
from typing import Dict, Any, Optional, List
import httpx
import subprocess
import json

from ..utils.process import run_command, find_process_by_port, get_docker_container_pid
from ..utils.display import show_progress, print_success, print_error

WEAVIATE_DIR = "/opt/weaviate"
WEAVIATE_PORT = 8080
HEALTH_ENDPOINT = f"http://localhost:{WEAVIATE_PORT}/v1/nodes"


class WeaviateService:
    """Manages Weaviate cluster via docker-compose."""
    
    def __init__(self):
        self.work_dir = WEAVIATE_DIR
        self.port = WEAVIATE_PORT
    
    def start(self) -> bool:
        """Start the Weaviate cluster."""
        show_progress("Starting Weaviate cluster")
        
        if not os.path.exists(self.work_dir):
            print_error(f"Weaviate directory not found: {self.work_dir}")
            return False
        
        if not os.path.exists(os.path.join(self.work_dir, "docker-compose.yaml")):
            print_error("docker-compose.yaml not found in Weaviate directory")
            return False
        
        # Start docker-compose
        result = run_command(
            ["docker-compose", "up", "-d"],
            cwd=self.work_dir
        )
        
        if result.returncode != 0:
            print_error(f"Failed to start Weaviate: {result.stderr}")
            return False
        
        # Wait for Weaviate to be healthy
        show_progress("Waiting for Weaviate to be ready")
        if self._wait_for_health():
            print_success("Weaviate cluster started successfully")
            return True
        else:
            print_error("Weaviate failed to become healthy within timeout")
            return False
    
    def stop(self) -> bool:
        """Stop the Weaviate cluster."""
        show_progress("Stopping Weaviate cluster")
        
        if not os.path.exists(self.work_dir):
            print_error(f"Weaviate directory not found: {self.work_dir}")
            return False
        
        result = run_command(
            ["docker-compose", "down"],
            cwd=self.work_dir
        )
        
        if result.returncode != 0:
            print_error(f"Failed to stop Weaviate: {result.stderr}")
            return False
        
        print_success("Weaviate cluster stopped successfully")
        return True
    
    def is_running(self) -> bool:
        """Check if Weaviate cluster is running (check all 3 nodes)."""
        # Check all three ports to see if cluster is running
        for port in [8080, 8081, 8082]:
            if find_process_by_port(port) is not None:
                return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Weaviate service status - returns cluster summary."""
        # This is for backward compatibility - returns overall cluster status
        nodes = self.get_nodes_status()
        
        # Determine overall cluster status
        running_nodes = [n for n in nodes if n["status"] == "running"]
        is_cluster_running = len(running_nodes) > 0
        
        # Use first running node's PID for display
        running_pid = running_nodes[0]["pid"] if running_nodes else None
        
        return {
            "status": "running" if is_cluster_running else "stopped",
            "pid": running_pid or "N/A",
            "port": f"{self.port} (+8081,+8082)" if is_cluster_running else self.port,
            "health": "healthy" if self._check_health() else "unhealthy" if is_cluster_running else "unknown"
        }
    
    def get_nodes_status(self) -> list[Dict[str, Any]]:
        """Get status for each individual Weaviate node."""
        nodes = []
        node_configs = [
            {"name": "Weaviate-1", "port": 8080, "container": "weaviate-node1-1"},
            {"name": "Weaviate-2", "port": 8081, "container": "weaviate-node2-1"},
            {"name": "Weaviate-3", "port": 8082, "container": "weaviate-node3-1"},
        ]
        
        for config in node_configs:
            # Check if port is listening
            pid = find_process_by_port(config["port"])
            
            # Get actual Docker PID if detected
            if pid == -1:
                docker_pid = get_docker_container_pid(config["container"])
                pid = docker_pid if docker_pid else "Docker"
            
            # Check node health
            node_healthy = self._check_node(config["port"])
            
            nodes.append({
                "name": config["name"],
                "status": "running" if pid else "stopped",
                "pid": pid or "N/A",
                "port": config["port"],
                "health": "healthy" if node_healthy["status"] == "healthy" else "unhealthy" if pid else "unknown"
            })
        
        return nodes
    
    def get_health(self, verbose: bool = False, last_errors: Optional[int] = None) -> Dict[str, Any]:
        """Get health information with optional verbose diagnostics."""
        # Basic health check (existing functionality)
        health_data = self._get_basic_health()
        
        if verbose:
            # Check individual nodes
            health_data["node_health"] = self._check_all_nodes()
            
            # Check ELYSIA_CONFIG__ collection
            health_data["collection_status"] = self._check_collection_status()
            
            # Get container stats
            health_data["container_stats"] = self._get_container_stats()
            
            # Parse recent errors
            if last_errors:
                health_data["recent_errors"] = self._get_recent_errors(last_errors)
            
            # Count active connections
            health_data["connection_count"] = self._get_connection_count()
        
        return health_data
    
    def _get_basic_health(self) -> Dict[str, Any]:
        """Get basic health information."""
        health_data = {
            "reachable": False,
            "response_time": None,
            "error": None,
            "additional_info": {}
        }
        
        try:
            start_time = time.time()
            with httpx.Client(timeout=5.0) as client:
                response = client.get(HEALTH_ENDPOINT)
                response_time = (time.time() - start_time) * 1000
                
                health_data["response_time"] = response_time
                
                if response.status_code == 200:
                    health_data["reachable"] = True
                    try:
                        data = response.json()
                        health_data["additional_info"]["nodes"] = len(data.get("nodes", []))
                    except:
                        pass
                else:
                    health_data["error"] = f"HTTP {response.status_code}"
                    
        except Exception as e:
            health_data["error"] = str(e)
        
        return health_data
    
    def _check_health(self) -> bool:
        """Simple health check."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(HEALTH_ENDPOINT)
                return response.status_code == 200
        except:
            return False
    
    def _wait_for_health(self, timeout: int = 60) -> bool:
        """Wait for Weaviate to become healthy."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_health():
                return True
            time.sleep(2)
        return False
    
    def _check_all_nodes(self) -> List[Dict[str, Any]]:
        """Check health of all three Weaviate nodes."""
        nodes = []
        for port in [8080, 8081, 8082]:
            node_health = self._check_node(port)
            nodes.append(node_health)
        return nodes
    
    def _check_node(self, port: int) -> Dict[str, Any]:
        """Check health of a single Weaviate node."""
        node_health = {
            "port": port,
            "status": "unknown",
            "response_time": None,
            "error": None
        }
        
        try:
            start_time = time.time()
            with httpx.Client(timeout=3.0) as client:
                response = client.get(f"http://localhost:{port}/v1/nodes")
                response_time = (time.time() - start_time) * 1000
                
                node_health["response_time"] = response_time
                
                if response.status_code == 200:
                    node_health["status"] = "healthy"
                else:
                    node_health["status"] = "unhealthy"
                    node_health["error"] = f"HTTP {response.status_code}"
                    
        except Exception as e:
            node_health["status"] = "unreachable"
            node_health["error"] = str(e)
        
        return node_health
    
    def _check_collection_status(self) -> Dict[str, Any]:
        """Check ELYSIA_CONFIG__ collection status across nodes."""
        collection_status = {
            "name": "ELYSIA_CONFIG__",
            "exists": False,
            "replication_factor": None,
            "node_count": {}
        }
        
        try:
            # Check collection existence and replication on main node
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"http://localhost:{WEAVIATE_PORT}/v1/schema/ELYSIA_CONFIG__")
                
                if response.status_code == 200:
                    collection_status["exists"] = True
                    try:
                        schema = response.json()
                        collection_status["replication_factor"] = schema.get("replicationConfig", {}).get("factor", 1)
                    except:
                        pass
                
                # Count collections per node
                for port in [8080, 8081, 8082]:
                    try:
                        node_response = client.get(f"http://localhost:{port}/v1/schema")
                        if node_response.status_code == 200:
                            schema_data = node_response.json()
                            classes = schema_data.get("classes", [])
                            elysia_collections = [c for c in classes if c.get("class") == "ELYSIA_CONFIG__"]
                            collection_status["node_count"][port] = len(elysia_collections)
                    except:
                        collection_status["node_count"][port] = 0
                        
        except Exception as e:
            collection_status["error"] = str(e)
        
        return collection_status
    
    def _get_container_stats(self) -> Dict[str, Any]:
        """Get Docker container statistics."""
        stats = {}
        
        try:
            # Get container stats using docker-compose ps and docker stats
            result = run_command(
                ["docker-compose", "ps", "--format", "json"],
                cwd=self.work_dir
            )
            
            if result.returncode == 0:
                try:
                    containers = []
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            containers.append(json.loads(line))
                    
                    stats["container_count"] = len(containers)
                    stats["running_containers"] = len([c for c in containers if c.get("State") == "running"])
                    
                    # Get basic stats from first running container
                    running_containers = [c for c in containers if c.get("State") == "running"]
                    if running_containers:
                        container_name = running_containers[0].get("Name", "")
                        if container_name:
                            stats_result = run_command(
                                ["docker", "stats", "--no-stream", "--format", "table {{.CPUPerc}}\t{{.MemUsage}}", container_name],
                                timeout=5
                            )
                            if stats_result.returncode == 0:
                                lines = stats_result.stdout.strip().split('\n')
                                if len(lines) > 1:  # Skip header
                                    parts = lines[1].split('\t')
                                    if len(parts) >= 2:
                                        stats["cpu_percent"] = parts[0].strip()
                                        stats["memory_usage"] = parts[1].strip()
                                        
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            stats["error"] = str(e)
        
        return stats
    
    def _get_recent_errors(self, count: int) -> List[str]:
        """Get recent log lines from Docker containers."""
        logs = []
        
        try:
            # Just get the recent logs - no filtering, let user see what's actually happening
            result = run_command(
                ["docker-compose", "logs", "--tail", str(count), "--no-color"],
                cwd=self.work_dir,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip():  # Skip empty lines
                        logs.append(line.strip())
            
            if not logs:
                logs.append("No recent logs available")
                            
        except Exception as e:
            logs.append(f"Error retrieving logs: {str(e)}")
        
        return logs
    
    def _get_connection_count(self) -> Optional[int]:
        """Count active HTTP connections to Weaviate ports."""
        try:
            result = run_command(
                ["netstat", "-an"],
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                connection_count = 0
                for line in lines:
                    if any(f":808{i}" in line for i in [0, 1, 2]) and "ESTABLISHED" in line:
                        connection_count += 1
                return connection_count
                
        except Exception:
            pass
        
        return None