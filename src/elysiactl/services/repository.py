"""Repository data management and JSONL file handling."""

import json
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonlines


class SubprocessManager:
    """Manages long-running subprocess operations with proper tracking and cleanup."""

    def __init__(self):
        self.active_processes: dict[str, subprocess.Popen] = {}
        self.process_lock = threading.Lock()
        self._shutdown_event = threading.Event()

    def start_process(self, operation_id: str, cmd: list[str], **kwargs) -> subprocess.Popen:
        """Start a tracked subprocess."""
        with self.process_lock:
            if operation_id in self.active_processes:
                raise RuntimeError(f"Operation {operation_id} already running")

            # Set up signal handling for clean shutdown
            def cleanup_handler(signum, frame):
                self.cancel_operation(operation_id)

            old_handler = signal.signal(signal.SIGINT, cleanup_handler)
            old_term_handler = signal.signal(signal.SIGTERM, cleanup_handler)

            try:
                # Start process with proper setup
                process = subprocess.Popen(
                    cmd,
                    stdout=kwargs.get("stdout", subprocess.PIPE),
                    stderr=kwargs.get("stderr", subprocess.PIPE),
                    text=kwargs.get("text", True),
                    **{k: v for k, v in kwargs.items() if k not in ["stdout", "stderr", "text"]},
                )

                self.active_processes[operation_id] = process
                return process

            finally:
                # Restore original signal handlers
                signal.signal(signal.SIGINT, old_handler)
                signal.signal(signal.SIGTERM, old_term_handler)

    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a running operation."""
        with self.process_lock:
            if operation_id in self.active_processes:
                process = self.active_processes[operation_id]
                try:
                    process.terminate()
                    # Give it time to terminate gracefully
                    try:
                        process.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        process.kill()  # Force kill if it doesn't respond
                    return True
                except Exception:
                    # Process might already be dead
                    pass
                finally:
                    del self.active_processes[operation_id]
        return False

    def wait_for_completion(self, operation_id: str, timeout: float | None = None) -> int | None:
        """Wait for operation to complete with optional timeout."""
        with self.process_lock:
            if operation_id not in self.active_processes:
                return None

            process = self.active_processes[operation_id]

        try:
            if timeout:
                return process.wait(timeout=timeout)
            else:
                return process.wait()
        except subprocess.TimeoutExpired:
            return None
        finally:
            with self.process_lock:
                self.active_processes.pop(operation_id, None)

    def get_active_operations(self) -> list[str]:
        """Get list of currently active operation IDs."""
        with self.process_lock:
            return list(self.active_processes.keys())

    def cleanup_all(self):
        """Clean up all active processes."""
        with self.process_lock:
            for operation_id in list(self.active_processes.keys()):
                self.cancel_operation(operation_id)

    def is_operation_active(self, operation_id: str) -> bool:
        """Check if an operation is currently active."""
        with self.process_lock:
            return operation_id in self.active_processes


# Global subprocess manager instance
subprocess_manager = SubprocessManager()


@dataclass
class Repository:
    """Represents a repository from mgit discovery."""

    organization: str
    project: str
    repository: str
    clone_url: str
    ssh_url: str
    default_branch: str
    is_private: bool
    description: str | None
    last_sync: datetime | None = None
    sync_status: str = "unknown"  # unknown, success, failed, pending

    @property
    def full_name(self) -> str:
        """Get the full repository name (org/project/repo)."""
        return f"{self.organization}/{self.project}/{self.repository}"

    @property
    def display_name(self) -> str:
        """Get a display-friendly name."""
        return f"{self.organization}/{self.repository}"


class RepositoryService:
    """Service for managing repository data and mgit integration."""

    def __init__(self, data_dir: Path = None):
        """Initialize repository service."""
        self.data_dir = data_dir or Path.home() / ".elysiactl" / "repos"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.repositories: dict[str, Repository] = {}

    def load_from_jsonl(self, jsonl_path: Path) -> list[Repository]:
        """Load repositories from mgit JSONL output file."""
        repositories = []

        try:
            # Read the entire file content first for debugging
            with open(jsonl_path) as f:
                content = f.read().strip()
                print(f"DEBUG: JSONL file content length: {len(content)}")
                print(f"DEBUG: First 200 chars: {content[:200]}")

            # Parse as JSONL (one JSON object per line)
            with jsonlines.open(jsonl_path) as reader:
                for line_num, line in enumerate(reader, 1):
                    try:
                        # Handle both mgit list format and diff-remote format
                        if "organization" in line:
                            # mgit list format
                            repo = Repository(
                                organization=line["organization"],
                                project=line["project"],
                                repository=line["repository"],
                                clone_url=line["clone_url"],
                                ssh_url=line["ssh_url"],
                                default_branch=line["default_branch"],
                                is_private=line["is_private"],
                                description=line.get("description"),
                            )
                            repositories.append(repo)
                            self.repositories[repo.full_name] = repo
                    except Exception as e:
                        print(f"Error parsing line {line_num}: {e}")
                        print(f"Line content: {line}")
                        continue

        except Exception as e:
            print(f"Error loading JSONL file {jsonl_path}: {e}")
            # Try to parse as regular JSON if JSONL fails
            try:
                with open(jsonl_path) as f:
                    content = f.read().strip()
                    if content:
                        # Parse as JSON array
                        data = json.loads(content)
                        if isinstance(data, list):
                            for item in data:
                                if "organization" in item:
                                    repo = Repository(
                                        organization=item["organization"],
                                        project=item["project"],
                                        repository=item["repository"],
                                        clone_url=item["clone_url"],
                                        ssh_url=item["ssh_url"],
                                        default_branch=item["default_branch"],
                                        is_private=item["is_private"],
                                        description=item.get("description"),
                                    )
                                    repositories.append(repo)
                                    self.repositories[repo.full_name] = repo
            except Exception as json_e:
                print(f"Failed to parse as JSON either: {json_e}")

        return repositories

    def discover_repositories(
        self, pattern: str = "*", limit: int | None = None, timeout: int = 300
    ) -> list[Repository]:
        """Discover repositories using mgit with proper subprocess management."""
        import tempfile

        from ..config.settings import config

        # Get comprehensive mgit information
        mgit_info = config.get_mgit_info()

        # Fail fast if mgit is not available
        if not mgit_info["effective_path"]:
            if mgit_info["configured_path"]:
                error_msg = f"Configured mgit path not found: {mgit_info['configured_path']}"
            else:
                error_msg = "mgit not found. Please configure 'tools.mgit_path' in ~/.elysiactl/settings.yaml or ensure mgit is in PATH"

            print(f"Error: {error_msg}")
            print("\nTo fix this:")
            print("1. Install mgit and add to PATH, OR")
            print("2. Set path in ~/.elysiactl/settings.yaml:")
            print("   tools:")
            print('     mgit_path: "/path/to/mgit"')
            return []

        mgit_path = mgit_info["effective_path"]

        # Display mgit information
        self._display_mgit_info(mgit_info)

        operation_id = f"discover_{pattern}_{int(time.time())}"

        # Create temporary file for mgit output
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Build mgit command with optional limit
            cmd = [mgit_path, "list", pattern, "--format", "json"]
            if limit is not None and limit > 0:
                cmd.extend(["--limit", str(limit)])

            print(f"Starting repository discovery: {' '.join(cmd)}")

            # Start tracked subprocess
            process = subprocess_manager.start_process(
                operation_id, cmd, stdout=open(tmp_path, "w"), stderr=subprocess.PIPE
            )

            # Wait for completion with timeout
            print(f"Discovery operation '{operation_id}' started...")

            try:
                # Wait for the process to complete with timeout
                return_code = subprocess_manager.wait_for_completion(operation_id, timeout=timeout)
                if return_code is None:
                    # Process timed out
                    raise subprocess.TimeoutExpired(cmd, timeout)

                if return_code == 0:
                    print(f"Discovery completed successfully for pattern: {pattern}")
                    return self.load_from_jsonl(tmp_path)
                else:
                    stderr_output = process.stderr.read() if process.stderr else "No error output"
                    print(f"Error running mgit (return code {return_code}): {stderr_output}")
                    return []

            except subprocess.TimeoutExpired:
                print(f"Repository discovery timed out after {timeout} seconds")
                subprocess_manager.cancel_operation(operation_id)
                return []
        except Exception as e:
            print(f"Error during repository discovery: {e}")
            subprocess_manager.cancel_operation(operation_id)
            return []
        finally:
            # Clean up temporary file
            tmp_path.unlink(missing_ok=True)

    def get_repository_status(self, repo: Repository) -> str:
        """Get the sync status for a repository."""
        # Check if repository exists locally

        # Try to find local repository path
        # This is a simple check - in production this would be more sophisticated
        from ..config.settings import config

        sync_dest = Path(config.get_sync_destination())
        local_path = sync_dest / repo.organization / repo.project / repo.repository

        if local_path and local_path.exists():
            # Repository exists locally, check if it's up to date
            try:
                # Simple check: see if .git directory exists
                git_dir = local_path / ".git"
                if git_dir.exists():
                    return "success"  # Repository is cloned and has git
                else:
                    return "unknown"  # Directory exists but not a git repo
            except Exception:
                return "unknown"
        else:
            return "unknown"  # Repository not found locally

    def update_repository_status(self, repo_name: str, status: str):
        """Update the sync status for a repository."""
        if repo_name in self.repositories:
            self.repositories[repo_name].sync_status = status
            self.repositories[repo_name].last_sync = datetime.now()

    def get_repositories_by_status(self, status: str) -> list[Repository]:
        """Get repositories filtered by sync status."""
        return [repo for repo in self.repositories.values() if repo.sync_status == status]

    def get_repositories_by_pattern(self, pattern: str) -> list[Repository]:
        """Get repositories matching a pattern."""
        # Simple pattern matching for now
        pattern_lower = pattern.lower()
        return [
            repo
            for repo in self.repositories.values()
            if pattern_lower in repo.organization.lower()
            or pattern_lower in repo.repository.lower()
            or pattern_lower in repo.project.lower()
        ]

    def save_repository_config(self):
        """Save current repository configuration."""
        config_file = self.data_dir / "repositories.json"

        config = {
            "repositories": [
                {
                    "full_name": repo.full_name,
                    "organization": repo.organization,
                    "project": repo.project,
                    "repository": repo.repository,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "default_branch": repo.default_branch,
                    "is_private": repo.is_private,
                    "description": repo.description,
                    "last_sync": repo.last_sync.isoformat() if repo.last_sync else None,
                    "sync_status": repo.sync_status,
                }
                for repo in self.repositories.values()
            ],
            "last_updated": datetime.now().isoformat(),
        }

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

    def cleanup(self):
        """Clean up resources and active subprocesses."""
        subprocess_manager.cleanup_all()

    def cancel_discovery(self, pattern: str) -> bool:
        """Cancel an active discovery operation for a pattern."""
        operation_id = f"discover_{pattern}"
        return subprocess_manager.cancel_operation(operation_id)

    def get_active_discoveries(self) -> list[str]:
        """Get list of active discovery operations."""
        return [
            op for op in subprocess_manager.get_active_operations() if op.startswith("discover_")
        ]

    def _display_mgit_info(self, mgit_info: dict[str, Any]):
        """Display comprehensive mgit information."""
        print("\n--- mgit Information ---")
        print(f"Path: {mgit_info['effective_path']}")

        if mgit_info["version"]:
            print(f"Version: {mgit_info['version']}")
        else:
            print("Version: Unknown")

        print(f"Source: {mgit_info['source']}")

        if mgit_info["configured_path"] and mgit_info["source"] == "configured":
            print("Configured path is being used")
        elif mgit_info["path_found"] and mgit_info["source"] == "PATH":
            print("Found in PATH")

        print("---\n")


# Global service instance
repo_service = RepositoryService()
