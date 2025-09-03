"""Start command implementation."""

import sys

from ..services.elysia import ElysiaService
from ..services.weaviate import WeaviateService
from ..utils.display import print_error, print_section_header


def start_command() -> None:
    """Start both Weaviate and Elysia services."""
    print_section_header("Starting Services")

    weaviate = WeaviateService()
    elysia = ElysiaService()

    success = True

    # Start Weaviate first
    if not weaviate.start():
        success = False

    # Only start Elysia if Weaviate started successfully
    if success:
        if not elysia.start():
            success = False

    if not success:
        print_error("Failed to start all services")
        sys.exit(1)
