"""Elysia service management."""

import os
import time
from typing import Any

import httpx
import psutil

from ..config import get_config
from ..utils.display import print_error, print_success, show_progress
from ..utils.process import (
    find_process_by_port,
    get_conda_env_path,
    is_process_running,
    kill_process,
    load_pid,
    remove_pid_file,
    run_command,
    run_command_async,
    save_pid,
)

ELYSIACTL_DIR = "/opt/elysia"
CONDA_ENV = "elysia"


class ElysiaService:
    """Manages Elysia AI service."""

    def __init__(self):
        self.work_dir = ELYSIACTL_DIR
        self.port = get_config().services.elysia_port
        self.conda_env = CONDA_ENV

    @property
    def health_endpoint(self) -> str:
        """Get the health check endpoint URL."""
        from urllib.parse import urlparse

        config = get_config()
        parsed = urlparse(config.services.elysia_url)
        if not parsed.hostname:
            raise ValueError(
                f"Cannot extract hostname from Elysia URL: {config.services.elysia_url}"
            )
        return f"{config.services.elysia_scheme}://{parsed.hostname}:{self.port}/api/health"

    def start(self) -> bool:
        """Start the Elysia service."""
        show_progress("Starting Elysia AI service")

        if not os.path.exists(self.work_dir):
            print_error(f"Elysia directory not found: {self.work_dir}")
            return False

        # Check if already running
        existing_pid = load_pid()
        port_pid = find_process_by_port(self.port)

        if (existing_pid and is_process_running(existing_pid)) or port_pid:
            print_success("Elysia is already running")
            # Update PID file if we found a process on the port but don't have a stored PID
            if not existing_pid and port_pid:
                save_pid(port_pid)
            return True

        # Get conda environment path
        conda_env_path = get_conda_env_path(self.conda_env)
        if not conda_env_path:
            print_error(f"Conda environment '{self.conda_env}' not found")
            return False

        # Prepare environment with conda activation
        env = os.environ.copy()
        env["PATH"] = f"{conda_env_path}/bin:{env['PATH']}"
        env["CONDA_DEFAULT_ENV"] = self.conda_env
        env["CONDA_PREFIX"] = conda_env_path

        # Start Elysia
        try:
            process = run_command_async(["elysia", "start"], cwd=self.work_dir, env=env)

            # Save PID
            save_pid(process.pid)

            # Wait a moment to check if process started successfully
            time.sleep(2)
            if not is_process_running(process.pid):
                print_error("Elysia process failed to start")
                remove_pid_file()
                return False

            # Wait for service to be ready
            show_progress("Waiting for Elysia to be ready")
            if self._wait_for_health():
                print_success("Elysia AI service started successfully")
                return True
            else:
                print_error("Elysia failed to become healthy within timeout")
                self.stop()
                return False

        except Exception as e:
            print_error(f"Failed to start Elysia: {e}")
            remove_pid_file()
            return False

    def stop(self) -> bool:
        """Stop the Elysia service."""
        show_progress("Stopping Elysia AI service")

        pid = load_pid()
        if not pid:
            print_success("Elysia is not running (no PID file)")
            return True

        if not is_process_running(pid):
            print_success("Elysia process is not running")
            remove_pid_file()
            return True

        # Try to kill the process gracefully
        if kill_process(pid):
            print_success("Elysia AI service stopped successfully")
            remove_pid_file()
            return True
        else:
            print_error("Failed to stop Elysia process")
            return False

    def is_running(self) -> bool:
        """Check if Elysia is running."""
        pid = load_pid()
        if pid is not None and is_process_running(pid):
            return True
        # Also check if something is running on the port
        return find_process_by_port(self.port) is not None

    def get_status(self) -> dict[str, Any]:
        """Get Elysia service status."""
        pid = load_pid()
        port_pid = find_process_by_port(self.port)
        is_running = (pid is not None and is_process_running(pid)) or port_pid is not None

        # Use the port PID if we don't have a stored PID
        display_pid = pid if pid and is_process_running(pid) else port_pid

        return {
            "status": "running" if is_running else "stopped",
            "pid": display_pid or "N/A",
            "port": self.port,
            "health": "healthy"
            if self._check_health()
            else "unhealthy"
            if is_running
            else "unknown",
        }

    def get_health(self, verbose: bool = False, last_errors: int | None = None) -> dict[str, Any]:
        """Get health information with optional verbose diagnostics."""
        # Basic health check (existing functionality)
        health_data = self._get_basic_health()

        if verbose:
            # Get process stats
            health_data["process_stats"] = self._get_process_stats()

            # Parse recent errors from logs
            if last_errors:
                health_data["recent_errors"] = self._get_recent_errors(last_errors)

            # Check active connections
            health_data["connection_count"] = self._get_connection_count()

        return health_data

    def _get_basic_health(self) -> dict[str, Any]:
        """Get basic health information."""
        health_data = {
            "reachable": False,
            "response_time": None,
            "error": None,
            "additional_info": {},
        }

        try:
            start_time = time.time()
            with httpx.Client(timeout=5.0) as client:
                response = client.get(self.health_endpoint)
                response_time = (time.time() - start_time) * 1000

                health_data["response_time"] = response_time

                if response.status_code == 200:
                    health_data["reachable"] = True
                    health_data["additional_info"]["endpoint"] = "Health API available"
                else:
                    health_data["error"] = f"HTTP {response.status_code}"

        except Exception as e:
            health_data["error"] = str(e)

        return health_data

    def _check_health(self) -> bool:
        """Simple health check."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(self.health_endpoint)
                return response.status_code == 200
        except:
            return False

    def _wait_for_health(self, timeout: int = 30) -> bool:
        """Wait for Elysia to become healthy."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_health():
                return True
            time.sleep(1)
        return False

    def _get_process_stats(self) -> dict[str, Any]:
        """Get process statistics."""
        stats = {}

        pid = load_pid()
        if pid and is_process_running(pid):
            try:
                process = psutil.Process(pid)
                stats["pid"] = pid
                stats["cpu_percent"] = f"{process.cpu_percent():.1f}%"

                memory_info = process.memory_info()
                stats["memory_mb"] = f"{memory_info.rss / (1024 * 1024):.1f} MB"

                stats["status"] = process.status()
                stats["create_time"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(process.create_time())
                )

                # Get file descriptors count
                try:
                    stats["open_files"] = len(process.open_files())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    stats["open_files"] = "N/A"

                # Get connections
                try:
                    connections = process.connections()
                    stats["connections"] = len(connections)
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    stats["connections"] = "N/A"

            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                stats["error"] = f"Cannot access process info: {e!s}"
        else:
            stats["error"] = "Process not running or PID not found"

        return stats

    def _get_recent_errors(self, count: int) -> list[str]:
        """Extract recent error lines from application logs."""
        errors = []

        try:
            # Look for Elysia log files in various locations
            log_locations = [
                os.path.join(self.work_dir, "logs"),
                os.path.join(self.work_dir, "elysia.log"),
                "/var/log/elysia",
                "/tmp/elysia.log",
            ]

            # Also check systemd journal if available
            try:
                result = run_command(
                    [
                        "journalctl",
                        "-u",
                        "elysia*",
                        "--no-pager",
                        "-n",
                        str(count * 2),
                        "--since",
                        "1 hour ago",
                    ],
                    timeout=5,
                )
                if result.returncode == 0:
                    lines = result.stdout.split("\n")
                    for line in lines:
                        line_lower = line.lower()
                        if any(
                            keyword in line_lower
                            for keyword in ["error", "exception", "fail", "traceback", "critical"]
                        ):
                            errors.append(line.strip())
                            if len(errors) >= count:
                                break
            except Exception:
                pass

            # If no systemd logs found, try to find log files
            if not errors:
                for log_path in log_locations:
                    if os.path.exists(log_path):
                        try:
                            if os.path.isdir(log_path):
                                # Look for .log files in directory
                                for file in os.listdir(log_path):
                                    if file.endswith(".log"):
                                        file_path = os.path.join(log_path, file)
                                        self._extract_errors_from_file(file_path, errors, count)
                                        if len(errors) >= count:
                                            break
                            else:
                                # It's a file
                                self._extract_errors_from_file(log_path, errors, count)

                            if len(errors) >= count:
                                break

                        except Exception as e:
                            errors.append(f"Error reading {log_path}: {e!s}")

            # If still no errors found, check if process is outputting to stdout/stderr
            if not errors:
                pid = load_pid()
                if pid and is_process_running(pid):
                    errors.append("No error logs found - process may be logging to stdout/stderr")
                else:
                    errors.append("No error logs found - process not running")

        except Exception as e:
            errors.append(f"Error retrieving logs: {e!s}")

        return errors[:count]  # Ensure we don't exceed requested count

    def _extract_errors_from_file(self, file_path: str, errors: list[str], max_count: int) -> None:
        """Extract errors from a specific log file."""
        try:
            result = run_command(["tail", "-n", str(max_count * 3), file_path], timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split("\n")
                for line in lines:
                    line_lower = line.lower()
                    if any(
                        keyword in line_lower
                        for keyword in ["error", "exception", "fail", "traceback", "critical"]
                    ):
                        errors.append(f"[{os.path.basename(file_path)}] {line.strip()}")
                        if len(errors) >= max_count:
                            break
        except Exception:
            pass

    def _get_connection_count(self) -> int | None:
        """Count active HTTP connections to Elysia port."""
        try:
            result = run_command(["netstat", "-an"], timeout=5)

            if result.returncode == 0:
                lines = result.stdout.split("\n")
                connection_count = 0
                for line in lines:
                    if f":{self.port}" in line and "ESTABLISHED" in line:
                        connection_count += 1
                return connection_count

        except Exception:
            pass

        return None
