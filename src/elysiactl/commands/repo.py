"""Repository management commands for elysiactl."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ..services.repository import repo_service

console = Console()

app = typer.Typer(
    name="repo",
    help="Manage repository connections and monitoring",
    no_args_is_help=True,
)


@app.command("find")
def find_repos(
    pattern: Annotated[
        str, typer.Argument(help="Repository pattern (org/project/*, */project/*, etc.)")
    ],
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Limit number of results (default: no limit)"),
    ] = None,
    timeout: Annotated[
        int, typer.Option("--timeout", "-t", help="Timeout in seconds (default: 300)")
    ] = 300,
):
    """Find repositories matching a pattern across configured providers."""
    console.print(f"🔍 Finding repositories: {pattern}")

    try:
        # Discover repositories using our comprehensive mgit integration
        repositories = repo_service.discover_repositories(
            pattern=pattern, limit=limit, timeout=timeout
        )

        if repositories:
            console.print(f"✅ Found {len(repositories)} repositories matching '{pattern}'")

            # Display discovered repositories
            table = Table(title=f"Repositories matching '{pattern}'")
            table.add_column("Organization", style="cyan", no_wrap=True)
            table.add_column("Project", style="magenta", no_wrap=True)
            table.add_column("Repository", style="green", no_wrap=True)
            table.add_column("Private", style="yellow")
            table.add_column("Branch", style="blue")

            for repo in repositories:
                table.add_row(
                    repo.organization,
                    repo.project,
                    repo.repository,
                    "🔒" if repo.is_private else "🌐",
                    repo.default_branch,
                )

            console.print(table)

            if limit and len(repositories) >= limit:
                console.print(f"💡 Showing first {limit} results. Use --limit to see more.")

            console.print("\n💡 Next steps:")
            console.print("   • Use 'elysiactl repo tui' for interactive selection")
            console.print("   • Use 'elysiactl repo add <pattern>' to add to monitoring")
        else:
            console.print("❌ No repositories found matching pattern")
            console.print("💡 Pattern examples:")
            console.print("   • 'pdidev/*/*' - All repos in pdidev organization")
            console.print("   • 'pdidev/LogisticsCloud/*' - All repos in specific project")
            console.print("   • 'pdidev/*/*payment*' - Payment-related repos across projects")

    except Exception as e:
        console.print(f"❌ Error finding repositories: {e}")


@app.command("add")
def add_repo(
    pattern: Annotated[str, typer.Argument(help="Repository pattern to add to monitoring")],
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Limit number of repos to add (default: no limit)"),
    ] = None,
    confirm: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
):
    """Add repositories matching pattern to monitoring."""
    console.print(f"🔍 Discovering repositories: {pattern}")

    try:
        # Discover repositories using our comprehensive mgit integration
        repositories = repo_service.discover_repositories(pattern=pattern, limit=limit)

        if repositories:
            console.print(f"✅ Found {len(repositories)} repositories matching '{pattern}'")

            # Show what will be added
            table = Table(title="Repositories to be added to monitoring")
            table.add_column("Organization", style="cyan", no_wrap=True)
            table.add_column("Project", style="magenta", no_wrap=True)
            table.add_column("Repository", style="green", no_wrap=True)

            for repo in repositories:
                table.add_row(repo.organization, repo.project, repo.repository)

            console.print(table)

            # Confirmation prompt (unless --yes is used)
            if not confirm:
                if len(repositories) > 10:
                    console.print(
                        f"⚠️  This will add {len(repositories)} repositories to monitoring."
                    )
                    console.print(
                        "   You can manage them later with 'elysiactl repo list' and 'elysiactl repo remove'"
                    )

                response = typer.confirm("Add these repositories to monitoring?", default=True)
                if not response:
                    console.print("❌ Operation cancelled")
                    return

            # Add repositories to monitoring
            added_count = 0
            for repo in repositories:
                if repo.full_name not in repo_service.repositories:
                    repo_service.repositories[repo.full_name] = repo
                    added_count += 1
                else:
                    console.print(f"⚠️  Repository {repo.display_name} already being monitored")

            # Save the updated configuration
            repo_service.save_repository_config()

            if added_count > 0:
                console.print(f"✅ Successfully added {added_count} repositories to monitoring")
                console.print("💡 Next steps:")
                console.print("   • Use 'elysiactl repo list' to see monitored repositories")
                console.print("   • Use 'elysiactl repo sync' to sync all monitored repos")
                console.print("   • Use 'elysiactl repo status' to check sync status")
            else:
                console.print("ℹ️  All discovered repositories were already being monitored")

        else:
            console.print("❌ No repositories found matching pattern")
            console.print(
                "💡 Try: 'elysiactl repo find <pattern>' to discover available repositories"
            )

    except Exception as e:
        console.print(f"❌ Error adding repositories: {e}")


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
        status_icon = {"success": "✅", "failed": "❌", "pending": "⏳", "unknown": "❓"}.get(
            repo.sync_status, "❓"
        )

        last_sync = repo.last_sync.strftime("%Y-%m-%d %H:%M") if repo.last_sync else "Never"

        table.add_row(
            repo.display_name, repo.project, f"{status_icon} {repo.sync_status}", last_sync
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
    theme: Annotated[
        str, typer.Option("--theme", "-t", help="UI theme (default, light, minimal, professional)")
    ] = "default",
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
    from ..tui.theme_manager import ThemeManager

    available_themes = ThemeManager().get_available_themes()
    if theme not in available_themes:
        console.print(
            f"❌ Invalid theme '{theme}'. Available themes: {', '.join(available_themes)}"
        )
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
