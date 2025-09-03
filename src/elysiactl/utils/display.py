"""Rich display utilities for formatted terminal output."""

from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_success(message: str) -> None:
    """Print a success message in green."""
    console.print(f"✓ {message}", style="green")


def print_error(message: str) -> None:
    """Print an error message in red."""
    console.print(f"✗ {message}", style="red")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    console.print(f"⚠ {message}", style="yellow")


def print_info(message: str) -> None:
    """Print an info message in blue."""
    console.print(f"ℹ {message}", style="blue")


def create_status_table(services: dict[str, dict[str, Any]]) -> Table:
    """Create a rich table showing service status."""
    table = Table(title="Service Status", box=box.ROUNDED)

    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("PID", justify="center")
    table.add_column("Port", justify="center")
    table.add_column("Health", justify="center")

    for service_name, info in services.items():
        status = info.get("status", "unknown")
        pid = str(info.get("pid", "N/A"))
        port = str(info.get("port", "N/A"))
        health = info.get("health", "unknown")

        # Color code the status
        if status == "running":
            status_text = Text("Running", style="green")
        elif status == "stopped":
            status_text = Text("Stopped", style="red")
        else:
            status_text = Text("Unknown", style="yellow")

        # Color code the health
        if health == "healthy":
            health_text = Text("Healthy", style="green")
        elif health == "unhealthy":
            health_text = Text("Unhealthy", style="red")
        else:
            health_text = Text("Unknown", style="yellow")

        table.add_row(service_name, status_text, pid, port, health_text)

    return table


def create_health_panel(
    service_name: str, health_data: dict[str, Any], verbose: bool = False
) -> Panel:
    """Create a panel showing detailed health information."""
    if not verbose:
        # Existing basic panel
        return _create_basic_health_panel(service_name, health_data)
    else:
        # New verbose panel
        return _create_verbose_health_panel(service_name, health_data)


def _create_basic_health_panel(service_name: str, health_data: dict[str, Any]) -> Panel:
    """Create basic health panel for non-verbose mode."""
    health_text = []

    if health_data.get("reachable", False):
        health_text.append("✓ Service is reachable")
        response_time = health_data.get("response_time")
        if response_time:
            health_text.append(f"✓ Response time: {response_time:.2f}ms")
    else:
        health_text.append("✗ Service is not reachable")
        error = health_data.get("error")
        if error:
            health_text.append(f"✗ Error: {error}")

    additional_info = health_data.get("additional_info", {})
    for key, value in additional_info.items():
        health_text.append(f"• {key}: {value}")

    content = "\n".join(health_text)

    # Determine panel style based on health
    if health_data.get("reachable", False):
        style = "green"
        title = f"{service_name} Health - OK"
    else:
        style = "red"
        title = f"{service_name} Health - ERROR"

    return Panel(content, title=title, border_style=style)


def _create_verbose_health_panel(service_name: str, health_data: dict[str, Any]) -> Panel:
    """Create detailed health panel for verbose mode."""
    content = []

    # Basic health status
    if health_data.get("reachable"):
        content.append("✓ Service is reachable")
        if health_data.get("response_time"):
            content.append(f"✓ Response time: {health_data['response_time']:.2f}ms")
    else:
        content.append("✗ Service is not reachable")
        if health_data.get("error"):
            content.append(f"✗ Error: {health_data['error']}")

    # Node health (Weaviate only)
    if health_data.get("node_health"):
        content.append("\n[bold]Individual Node Health:[/bold]")
        for node in health_data["node_health"]:
            status = "✓" if node["status"] == "healthy" else "✗"
            status_text = node["status"]
            if node.get("response_time"):
                status_text += f" ({node['response_time']:.1f}ms)"
            content.append(f"  {status} Node {node['port']}: {status_text}")
            if node.get("error"):
                content.append(f"    Error: {node['error']}")

    # Collection status (Weaviate only)
    if "collection_status" in health_data:
        cs = health_data["collection_status"]
        content.append("\n[bold]ELYSIA_CONFIG__ Collection:[/bold]")
        exists_icon = "✓" if cs.get("exists") else "✗"
        content.append(f"  {exists_icon} Exists: {cs.get('exists', False)}")

        if cs.get("replication_factor") is not None:
            rf = cs["replication_factor"]
            rf_icon = "✓" if rf == 3 else "⚠"
            content.append(f"  {rf_icon} Replication Factor: {rf}")

        if cs.get("node_count"):
            content.append("  Node Distribution:")
            expected_count = 1 if cs.get("exists") else 0
            for port, count in cs["node_count"].items():
                count_icon = "✓" if count == expected_count else ("⚠" if count > 0 else "✗")
                content.append(f"    {count_icon} Node {port}: {count} instances")

        if cs.get("error"):
            content.append(f"  ✗ Collection check error: {cs['error']}")

    # Container/Process stats
    container_stats = health_data.get("container_stats") or health_data.get("process_stats")
    if container_stats and not container_stats.get("error"):
        stats_title = "Container Stats" if "container_stats" in health_data else "Process Stats"
        content.append(f"\n[bold]{stats_title}:[/bold]")

        if "container_count" in container_stats:
            # Docker container stats
            content.append(f"  • Containers: {container_stats.get('container_count', 'N/A')}")
            content.append(f"  • Running: {container_stats.get('running_containers', 'N/A')}")
            if "cpu_percent" in container_stats:
                content.append(f"  • CPU: {container_stats['cpu_percent']}")
            if "memory_usage" in container_stats:
                content.append(f"  • Memory: {container_stats['memory_usage']}")
        else:
            # Process stats
            if "pid" in container_stats:
                content.append(f"  • PID: {container_stats['pid']}")
            if "cpu_percent" in container_stats:
                content.append(f"  • CPU: {container_stats['cpu_percent']}")
            if "memory_mb" in container_stats:
                content.append(f"  • Memory: {container_stats['memory_mb']}")
            if "status" in container_stats:
                content.append(f"  • Status: {container_stats['status']}")
            if "create_time" in container_stats:
                content.append(f"  • Started: {container_stats['create_time']}")
            if "open_files" in container_stats:
                content.append(f"  • Open Files: {container_stats['open_files']}")
    elif container_stats and container_stats.get("error"):
        stats_title = "Container Stats" if "container_stats" in health_data else "Process Stats"
        content.append(f"\n[bold red]{stats_title} Error:[/bold red]")
        content.append(f"  {container_stats['error']}")

    # Connection count
    if health_data.get("connection_count") is not None:
        content.append(f"\n[bold]Active Connections:[/bold] {health_data['connection_count']}")

    # Recent logs - show full content without truncation
    if health_data.get("recent_errors"):
        content.append("\n[bold]Recent Logs:[/bold]")

        for i, log_line in enumerate(health_data["recent_errors"], 1):
            if log_line.strip():
                # Split container name from message if present
                parts = log_line.split("|", 1)
                if len(parts) == 2:
                    container = parts[0].strip()
                    message = parts[1].strip()

                    # For JSON logs, pretty-print them
                    if message.startswith("{"):
                        try:
                            import json

                            log_json = json.loads(message)
                            # Create a compact but readable format
                            formatted = json.dumps(log_json, indent=2)
                            # Indent each line for the panel
                            indented = "\n".join(f"      {line}" for line in formatted.split("\n"))
                            content.append(f"  {i}. [{container}]")
                            content.append(indented)
                        except:
                            # Not valid JSON, show as-is
                            content.append(f"  {i}. [{container}]")
                            content.append(f"      {message}")
                    else:
                        # Plain text log
                        content.append(f"  {i}. [{container}]")
                        # Wrap long lines for readability
                        if len(message) > 100:
                            # Break into chunks at word boundaries
                            import textwrap

                            wrapped = textwrap.fill(
                                message,
                                width=100,
                                initial_indent="      ",
                                subsequent_indent="      ",
                            )
                            content.append(wrapped)
                        else:
                            content.append(f"      {message}")
                else:
                    # No container prefix
                    content.append(f"  {i}. {log_line}")

    # Create panel with appropriate color
    status = "OK" if health_data.get("reachable") else "ERROR"
    color = "green" if health_data.get("reachable") else "red"

    # Check for warnings in verbose mode
    if health_data.get("reachable"):
        # Check for warning conditions
        if "collection_status" in health_data:
            cs = health_data["collection_status"]
            if cs.get("exists") and cs.get("replication_factor") != 3:
                color = "yellow"
                status = "WARNING"

        if "recent_errors" in health_data and any(
            error.strip() for error in health_data["recent_errors"]
        ):
            if color != "red":  # Don't override red with yellow
                color = "yellow"
                status = "WARNING"

    return Panel("\n".join(content), title=f"{service_name} Health - {status}", border_style=color)


def show_progress(message: str) -> None:
    """Show a progress message with spinner-like indicator."""
    console.print(f"⚙ {message}...", style="blue")


def print_section_header(title: str) -> None:
    """Print a section header with styling."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print("─" * len(title), style="cyan")


def create_logs_panel(title: str, logs: list) -> Panel:
    """Create a dedicated panel for displaying logs."""
    content = []

    if logs:
        for i, log_line in enumerate(logs, 1):
            if log_line.strip():
                # Split container name from message if present
                parts = log_line.split("|", 1)
                if len(parts) == 2:
                    container = parts[0].strip()
                    message = parts[1].strip()

                    # For JSON logs, pretty-print them
                    if message.startswith("{"):
                        try:
                            import json

                            log_json = json.loads(message)
                            # Create a compact format with key fields
                            node = log_json.get("node", "?")
                            level = log_json.get("level", "info")
                            msg = log_json.get("msg", "")
                            action = log_json.get("action", "")

                            # Color-code by level
                            level_color = {
                                "error": "red",
                                "warn": "yellow",
                                "info": "cyan",
                                "debug": "dim",
                            }.get(level, "white")

                            content.append(
                                f"  {i}. [{container}] [bold {level_color}]{level.upper()}[/bold {level_color}] {msg}"
                            )
                            if action:
                                content.append(f"      Action: {action}")
                        except:
                            # Not valid JSON, show first part
                            if len(message) > 100:
                                content.append(f"  {i}. [{container}] {message[:100]}...")
                            else:
                                content.append(f"  {i}. [{container}] {message}")
                    else:
                        # Plain text log
                        if len(message) > 100:
                            content.append(f"  {i}. [{container}] {message[:100]}...")
                        else:
                            content.append(f"  {i}. [{container}] {message}")
                else:
                    # No container prefix
                    if len(log_line) > 120:
                        content.append(f"  {i}. {log_line[:120]}...")
                    else:
                        content.append(f"  {i}. {log_line}")
    else:
        content.append("  No recent logs available")

    return Panel("\n".join(content), title=title, border_style="blue")
