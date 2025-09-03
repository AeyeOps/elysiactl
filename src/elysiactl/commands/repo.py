"""Repository management commands for elysiactl."""

import typer
from typing import Optional
from typing_extensions import Annotated
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from ..services.repository import repo_service, Repository

console = Console()

app = typer.Typer(
    name="repo",
    help="Manage repository connections and monitoring",
    no_args_is_help=True,
)

@app.command("add")
def add_repo(
    repo_pattern: Annotated[str, typer.Argument(help="Repository pattern (org/repo or org/project/repo)")],
    watch: Annotated[bool, typer.Option("--watch", "-w", help="Monitor for changes")] = False,
    provider: Annotated[Optional[str], typer.Option("--provider", "-p", help="Specific git provider")] = None,
):
    """Add repositories to monitoring."""
    console.print(f"🔍 Discovering repositories: {repo_pattern}")
    if watch:
        console.print("👀 Watch mode enabled - will monitor for changes")

    try:
        # Discover repositories using mgit integration
        repositories = repo_service.discover_repositories(repo_pattern, provider)

        if repositories:
            console.print(f"✅ Found {len(repositories)} repositories")

            # Display discovered repositories
            table = Table(title="Discovered Repositories")
            table.add_column("Repository", style="cyan")
            table.add_column("Project", style="magenta")
            table.add_column("Private", style="yellow")
            table.add_column("Branch", style="green")

            for repo in repositories[:10]:  # Show first 10
                table.add_row(
                    repo.repository,
                    repo.project,
                    "🔒" if repo.is_private else "🌐",
                    repo.default_branch
                )

            console.print(table)

            if len(repositories) > 10:
                console.print(f"... and {len(repositories) - 10} more repositories")

            # Save repository configuration
            repo_service.save_repository_config()
            console.print("💾 Repository configuration saved")

        else:
            console.print("❌ No repositories found matching pattern")
            console.print("💡 Try: 'pdidev/*/*' or 'myorg/project/*'")

    except Exception as e:
        console.print(f"❌ Error discovering repositories: {e}")

@app.command("status")
def repo_status():
    """Show status of monitored repositories."""
    # TODO: Implement status display
    console.print("📊 Repository Status:")
    console.print("No repositories currently monitored")

@app.command("list")
def list_repos():
    """List all monitored repositories."""
    # Load repository configuration
    repo_service.load_repository_config()

    if not repo_service.repositories:
        console.print("📋 Monitored Repositories:")
        console.print("No repositories currently configured")
        console.print("\n💡 To add repositories, use:")
        console.print("   elysiactl repo add 'pdidev/*/*' --watch")
        return

    console.print(f"📋 Monitored Repositories ({len(repo_service.repositories)})")

    table = Table()
    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("Project", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Last Sync", style="yellow")

    for repo in repo_service.repositories.values():
        status_icon = {
            "success": "✅",
            "failed": "❌",
            "pending": "⏳",
            "unknown": "❓"
        }.get(repo.sync_status, "❓")

        last_sync = repo.last_sync.strftime("%Y-%m-%d %H:%M") if repo.last_sync else "Never"

        table.add_row(
            repo.display_name,
            repo.project,
            f"{status_icon} {repo.sync_status}",
            last_sync
        )

    console.print(table)

@app.command("remove")
def remove_repo(
    repo_pattern: Annotated[str, typer.Argument(help="Repository pattern to remove")],
):
    """Remove repositories from monitoring."""
    console.print(f"🗑️  Removing repositories: {repo_pattern}")
    # TODO: Implement removal logic
    console.print("✅ Repository removal completed")

@app.command("sync")
def sync_repos():
    """Manually sync all monitored repositories."""
    console.print("🔄 Syncing repositories...")
    # TODO: Implement sync logic
    console.print("✅ Sync completed")

@app.command("tui")
def launch_tui(
    theme: Annotated[str, typer.Option("--theme", "-t", help="UI theme (default, light, minimal, professional)")] = "default",
    dev: Annotated[bool, typer.Option("--dev", help="Enable Textual developer console")] = False,
):
    """Launch the interactive repository management TUI."""
    import os
    import warnings

    # Suppress the specific libmagic warning
    warnings.filterwarnings("ignore", message="libmagic not available")

    if dev:
        console.print("DEV MODE: Enabling Textual Console...")
        os.environ["TEXTUAL"] = "dev"
    
    console.print(f"🚀 Launching Repository Management TUI with {theme} theme...")

    # Validate theme
    from ..tui.theme import theme_manager
    available_themes = theme_manager.get_available_themes()
    if theme not in available_themes:
        console.print(f"❌ Invalid theme '{theme}'. Available themes: {', '.join(available_themes)}")
        raise typer.Exit(1)

    try:
        from ..tui.app import RepoManagerApp
        app = RepoManagerApp(theme_name=theme)
        console.print("✅ TUI starting...")
        app.run()
    except ImportError as e:
        console.print(f"❌ TUI dependencies not available: {e}")
        console.print("💡 Install with: pip install textual textual-dev")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error launching TUI: {e}")
        raise typer.Exit(1)