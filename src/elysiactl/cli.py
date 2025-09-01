"""Main CLI application for elysiactl."""

import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console

from . import __version__
from .commands.start import start_command
from .commands.stop import stop_command
from .commands.status import status_command
from .commands.health import health_command
from .commands.repair import app as repair_app
from .commands.index import app as index_app

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
        Optional[bool], 
        typer.Option("--version", "-V", callback=version_callback, is_eager=True,
                    help="Show version and exit")
    ] = None,
):
    """elysiactl - Service management for Elysia AI and Weaviate."""
    pass

app.add_typer(repair_app, name="repair", help="Repair cluster issues")
app.add_typer(index_app, name="index", help="Index source code into Weaviate")


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
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed diagnostics")] = False,
    last_errors: Annotated[Optional[int], typer.Option("--last-errors", help="Log lines per container to show (e.g., 3 lines × 3 nodes = 9 total logs, requires --verbose)")] = None,
    cluster: Annotated[bool, typer.Option("--cluster", help="Perform cluster verification checks")] = False,
    collection: Annotated[Optional[str], typer.Option("--collection", help="Verify specific collection only")] = None,
    quick: Annotated[bool, typer.Option("--quick", help="Skip data consistency checks (faster)")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format for scripting")] = False
):
    """Perform health checks on both services."""
    health_command(
        verbose=verbose, 
        last_errors=last_errors,
        cluster=cluster,
        collection=collection,
        quick=quick,
        json_output=json_output
    )


if __name__ == "__main__":
    app()