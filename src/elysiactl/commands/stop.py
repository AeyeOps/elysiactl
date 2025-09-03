"""Stop command implementation."""

import sys

from ..services.elysia import ElysiaService
from ..services.weaviate import WeaviateService
from ..utils.display import print_error, print_section_header


def stop_command() -> None:
    """Stop both Elysia and Weaviate services."""
    print_section_header("Stopping Services")

    weaviate = WeaviateService()
    elysia = ElysiaService()

    success = True

    # Stop Elysia first (graceful shutdown)
    if not elysia.stop():
        success = False

    # Then stop Weaviate
    if not weaviate.stop():
        success = False

    if not success:
        print_error("Failed to stop all services cleanly")
        sys.exit(1)
