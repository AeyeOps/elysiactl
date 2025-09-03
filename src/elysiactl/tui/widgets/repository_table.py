"""Repository table widget for displaying repository information."""

from textual.widgets import DataTable
from rich.text import Text
from ...services.repository import Repository
from datetime import datetime

class RepositoryTable(DataTable):
    """Widget for displaying repository information in a table format."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repositories = []

    def on_mount(self) -> None:
        """Initialize table when mounted."""
        # Add columns with responsive widths
        self.add_columns(
            Text("Repository", overflow="ellipsis"),
            Text("Status", justify="center"),
            Text("Last Sync", overflow="ellipsis"),
            Text("Project", overflow="ellipsis")
        )

        # Load initial data
        self.load_mock_data()

    def load_mock_data(self) -> None:
        """Load mock repository data for demonstration."""
        mock_repos = [
            Repository(
                organization="pdidev",
                project="Blue Cow",
                repository="api-gateway",
                clone_url="https://dev.azure.com/pdidev/Blue%20Cow/_git/api-gateway",
                ssh_url="pdidev@vs-ssh.visualstudio.com:v3/pdidev/Blue%20Cow/api-gateway",
                default_branch="main",
                is_private=True,
                description="API Gateway service",
                sync_status="success"
            ),
            Repository(
                organization="pdidev",
                project="Blue Cow",
                repository="user-service",
                clone_url="https://dev.azure.com/pdidev/Blue%20Cow/_git/user-service",
                ssh_url="pdidev@vs-ssh.visualstudio.com:v3/pdidev/Blue%20Cow/user-service",
                default_branch="develop",
                is_private=True,
                description="User management service",
                sync_status="success"
            ),
            Repository(
                organization="pdidev",
                project="Blue Cow",
                repository="auth-service",
                clone_url="https://dev.azure.com/pdidev/Blue%20Cow/_git/auth-service",
                ssh_url="pdidev@vs-ssh.visualstudio.com:v3/pdidev/Blue%20Cow/auth-service",
                default_branch="develop",
                is_private=True,
                description="Authentication service",
                sync_status="failed"
            ),
            Repository(
                organization="pdidev",
                project="Envoy",
                repository="envoy-config",
                clone_url="https://dev.azure.com/pdidev/Envoy/_git/envoy-config",
                ssh_url="pdidev@vs-ssh.visualstudio.com:v3/pdidev/Envoy/envoy-config",
                default_branch="main",
                is_private=True,
                description="Envoy proxy configuration",
                sync_status="success"
            ),
            Repository(
                organization="pdidev",
                project="LogisticsCloud",
                repository="plc-automation",
                clone_url="https://dev.azure.com/pdidev/LogisticsCloud/_git/plc-automation",
                ssh_url="pdidev@vs-ssh.visualstudio.com:v3/pdidev/LogisticsCloud/plc-automation",
                default_branch="develop",
                is_private=True,
                description="Logistics cloud automation",
                sync_status="syncing"
            )
        ]

        self.repositories = mock_repos
        self.display_repositories(mock_repos)

    def display_repositories(self, repositories: list[Repository]) -> None:
        """Display repositories in the table."""
        self.clear()

        for repo in repositories:
            # Format status with emoji
            status_emoji = {
                "success": "✅",
                "failed": "❌",
                "syncing": "🔄",
                "unknown": "❓"
            }.get(repo.sync_status, "❓")

            # Format last sync
            last_sync = "Never"
            if repo.last_sync:
                last_sync = repo.last_sync.strftime("%Y-%m-%d %H:%M")

            # Truncate long names to fit terminal width
            repo_name = repo.repository[:20] + "..." if len(repo.repository) > 20 else repo.repository
            project_name = repo.project[:15] + "..." if len(repo.project) > 15 else repo.project

            # Add row to table
            self.add_row(
                repo_name,
                f"{status_emoji} {repo.sync_status}",
                last_sync,
                project_name
            )

    def add_command_output(self, command: str, output: str = None):
        """Add command output to the table with infinite scroll behavior."""
        if output is None:
            output = f"Executed: {command}"

        # Create a new "command result" row
        command_row = [
            f"💬 {command}",
            "✅ executed",
            f"{datetime.now().strftime('%H:%M:%S')}",
            "Command"
        ]

        # Add to the END of the table (receipt printer style - newest at bottom)
        self.add_row(*command_row)

        # For infinite scroll: let table grow naturally, don't limit entries
        # User can scroll up to see older content
        # Table height stays fixed, content flows through it

        # Optional: If we want to prevent memory issues with truly infinite content,
        # we could implement a "virtual scrolling" approach later
        pass

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