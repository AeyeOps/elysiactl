"""Status command implementation."""

from ..services.elysia import ElysiaService
from ..services.weaviate import WeaviateService
from ..utils.display import console, create_status_table, print_section_header


def status_command() -> None:
    """Show the current status of both services."""
    print_section_header("Service Status")

    weaviate = WeaviateService()
    elysia = ElysiaService()

    # Collect status information
    # Get individual Weaviate nodes
    services = {}
    for node in weaviate.get_nodes_status():
        services[node["name"]] = node

    # Add Elysia service
    services["Elysia AI"] = elysia.get_status()

    # Display status table
    table = create_status_table(services)
    console.print(table)
