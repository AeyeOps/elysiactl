"""Repository table widget for displaying repository information."""

from datetime import datetime

from rich.text import Text
from textual.widgets import DataTable
from textual.widgets.data_table import RowKey

from ...services.repository import Repository


class RepositoryTable(DataTable):
    """Widget for displaying repository information in a table format."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repositories: list[Repository] = []
        self.selection: set[RowKey] = set()
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """Initialize table when mounted."""
        # Add columns with responsive widths
        self.add_columns(
            Text(" ", justify="center", no_wrap=True),
            Text("Repository", overflow="ellipsis"),
            Text("Status", justify="center"),
            Text("Last Sync", overflow="ellipsis"),
            Text("Project", overflow="ellipsis"),
        )

    def display_repositories(self, repositories: list[Repository]) -> None:
        """Display repositories in the table."""
        self.clear()
        self.repositories = repositories

        for repo in repositories:
            repo_key = RowKey(str(repo.ssh_url))
            is_selected = repo_key in self.selection
            checkbox = "[x]" if is_selected else "[ ]"

            # Format status with emoji
            status_emoji = {"success": "✅", "failed": "❌", "syncing": "🔄", "unknown": "❓"}.get(
                repo.sync_status, "❓"
            )

            # Format last sync
            last_sync = "Never"
            if repo.last_sync:
                last_sync = repo.last_sync.strftime("%Y-%m-%d %H:%M")

            # Truncate long names to fit terminal width
            repo_name = (
                repo.repository[:20] + "..." if len(repo.repository) > 20 else repo.repository
            )
            project_name = repo.project[:15] + "..." if len(repo.project) > 15 else repo.project

            # Add row to table
            self.add_row(
                checkbox,
                repo_name,
                f"{status_emoji} {repo.sync_status}",
                last_sync,
                project_name,
                key=repo_key,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if event.row_key in self.selection:
            self.selection.remove(event.row_key)
        else:
            self.selection.add(event.row_key)

        # Find the specific repository associated with the row_key
        repo_to_update = next(
            (repo for repo in self.repositories if str(repo.ssh_url) == event.row_key.value), None
        )

        if repo_to_update:
            self.display_repositories(self.repositories)  # Redraw to update checkbox

    def get_selected_repositories(self) -> list[Repository]:
        """Return the selected repositories."""
        selected_repos = []
        for repo in self.repositories:
            if RowKey(str(repo.ssh_url)) in self.selection:
                selected_repos.append(repo)
        return selected_repos

    def add_command_output(self, command: str, output: str = None):
        """Add command output to the table with infinite scroll behavior."""
        if output is None:
            output = f"Executed: {command}"

        # Create a new "command result" row
        command_row = [
            " ",  # No checkbox for command output
            f"💬 {command}",
            "✅ executed",
            f"{datetime.now().strftime('%H:%M:%S')}",
            "Command",
        ]

        # Add to the END of the table (receipt printer style - newest at bottom)
        self.add_row(*command_row)

    def get_repository_count(self) -> int:
        """Get the total number of repositories."""
        return len(self.repositories)

    def get_status_counts(self) -> dict:
        """Get counts of repositories by status."""
        counts = {"success": 0, "failed": 0, "syncing": 0, "unknown": 0}
        for repo in self.repositories:
            status = repo.sync_status
            if status in counts:
                counts[status] += 1
        return counts
