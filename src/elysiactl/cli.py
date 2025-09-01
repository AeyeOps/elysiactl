"""Main CLI application for ElysiaCtl."""

import typer
from typing import Optional
from typing_extensions import Annotated

from .commands.start import start_command
from .commands.stop import stop_command
from .commands.status import status_command
from .commands.health import health_command

app = typer.Typer(
    name="elysiactl",
    help="Control utility for managing Elysia AI and Weaviate services",
    no_args_is_help=True,
)


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
    last_errors: Annotated[Optional[int], typer.Option("--last-errors", help="Log lines per container to show (e.g., 3 lines × 3 nodes = 9 total logs, requires --verbose)")] = None
):
    """Perform health checks on both services."""
    health_command(verbose=verbose, last_errors=last_errors)


if __name__ == "__main__":
    app()