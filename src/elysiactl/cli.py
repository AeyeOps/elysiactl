"""Main CLI application for elysiactl."""

from typing import Annotated

import typer
from rich.console import Console

from . import __version__
from .commands.collection import app as collection_app
from .commands.health import health_command
from .commands.index import app as index_app
from .commands.repair import app as repair_app
from .commands.repo import app as repo_app
from .commands.start import start_command
from .commands.status import status_command
from .commands.stop import stop_command

console = Console()


def version_callback(value: bool):
    """Handle --version flag."""
    if value:
        console.print(f"elysiactl version {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="elysiactl",
    help="Control utility for managing Elysia AI and Weaviate services",
    no_args_is_help=True,
)


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
):
    """elysiactl - Service management for Elysia AI and Weaviate."""


app.add_typer(repair_app, name="repair", help="Repair cluster issues")
app.add_typer(index_app, name="index", help="Index source code into Weaviate")
app.add_typer(collection_app, name="collection", help="Manage Weaviate collections")
app.add_typer(collection_app, name="col", help="Manage Weaviate collections (alias)")
@app.command()
def tui(
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
    from .tui.theme import theme_manager

    available_themes = theme_manager.get_available_themes()
    if theme not in available_themes:
        console.print(
            f"❌ Invalid theme '{theme}'. Available themes: {', '.join(available_themes)}"
        )
        raise typer.Exit(1)

    try:
        from .tui.app import RepoManagerApp

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


@app.command()
def start():
    """Start both Weaviate and Elysia services."""
    start_command()


@app.command()
def stop():
    """Stop both Elysia and Weaviate services."""
    stop_command()


@app.command()
def restart():
    """Restart both services (stop then start)."""
    stop_command()
    start_command()


@app.command()
def status():
    """Show the current status of both services."""
    status_command()


@app.command()
def health(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed diagnostics")
    ] = False,
    last_errors: Annotated[
        int | None,
        typer.Option(
            "--last-errors",
            help="Log lines per container to show (e.g., 3 lines × 3 nodes = 9 total logs, requires --verbose)",
        ),
    ] = None,
    cluster: Annotated[
        bool, typer.Option("--cluster", help="Perform cluster verification checks")
    ] = False,
    collection: Annotated[
        str | None, typer.Option("--collection", help="Verify specific collection only")
    ] = None,
    quick: Annotated[
        bool, typer.Option("--quick", help="Skip data consistency checks (faster)")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format for scripting")
    ] = False,
):
    """Perform health checks on both services."""
    health_command(
        verbose=verbose,
        last_errors=last_errors,
        cluster=cluster,
        collection=collection,
        quick=quick,
        json_output=json_output,
    )


if __name__ == "__main__":
    app()
