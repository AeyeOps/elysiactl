"""Process management utilities."""

import os
import psutil
import subprocess
from typing import Optional, List, Dict, Any
import time

PID_FILE = "/tmp/elysia.pid"


def run_command(cmd: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, timeout: Optional[float] = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout
    )


def run_command_async(cmd: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> subprocess.Popen:
    """Run a command asynchronously and return the process."""
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_process_info(pid: int) -> Optional[Dict[str, Any]]:
    """Get information about a process."""
    try:
        process = psutil.Process(pid)
        return {
            "pid": pid,
            "name": process.name(),
            "status": process.status(),
            "cpu_percent": process.cpu_percent(),
            "memory_info": process.memory_info()._asdict(),
            "create_time": process.create_time(),
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def save_pid(pid: int) -> None:
    """Save a PID to the PID file."""
    with open(PID_FILE, "w") as f:
        f.write(str(pid))


def load_pid() -> Optional[int]:
    """Load PID from the PID file."""
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def remove_pid_file() -> None:
    """Remove the PID file."""
    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass


def kill_process(pid: int, timeout: int = 10) -> bool:
    """Kill a process gracefully, with fallback to force kill."""
    try:
        process = psutil.Process(pid)
        
        # Try graceful termination first
        process.terminate()
        
        # Wait for the process to terminate
        try:
            process.wait(timeout=timeout)
            return True
        except psutil.TimeoutExpired:
            # Force kill if graceful termination fails
            process.kill()
            process.wait(timeout=5)
            return True
            
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def find_process_by_port(port: int) -> Optional[int]:
    """Find a process listening on a specific port."""
    # Try psutil first, but only if it returns a valid PID
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN and conn.pid:
                return conn.pid
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        # Fallback for cases where psutil can't access network connections
        pass
    
    # Alternative method: check if port is listening using ss/netstat output
    try:
        result = subprocess.run(
            ["ss", "-tlnp"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if (f":{port}" in line or f"*:{port}" in line) and "LISTEN" in line:
                    # For Docker containers, we'll return a special value
                    # -1 indicates it's running in Docker (we can't get the real PID)
                    return -1  # Docker container indicator
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return None


def get_docker_container_pid(container_name_pattern: str) -> Optional[str]:
    """Get the PID of a Docker container by name pattern."""
    try:
        # Find container matching pattern
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            for name in result.stdout.split('\n'):
                if container_name_pattern in name:
                    # Get the PID of this container
                    pid_result = subprocess.run(
                        ["docker", "inspect", name, "--format", "{{.State.Pid}}"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if pid_result.returncode == 0:
                        pid = pid_result.stdout.strip()
                        if pid and pid != "0":
                            return pid
                    break
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def find_processes_by_name(name: str) -> List[int]:
    """Find all processes with a specific name."""
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] == name:
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids


def wait_for_process_to_stop(pid: int, timeout: int = 30) -> bool:
    """Wait for a process to stop."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_process_running(pid):
            return True
        time.sleep(0.5)
    return False


def get_conda_env_path(env_name: str) -> Optional[str]:
    """Get the path to a conda environment."""
    try:
        result = run_command(["conda", "env", "list", "--json"])
        if result.returncode == 0:
            import json
            env_data = json.loads(result.stdout)
            for env_path in env_data.get("envs", []):
                if env_path.endswith(f"/{env_name}") or env_path.endswith(f"\\{env_name}"):
                    return env_path
    except Exception:
        pass
    return None