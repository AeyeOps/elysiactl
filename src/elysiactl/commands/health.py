"""Health command implementation."""

from typing import Optional
from ..services.weaviate import WeaviateService
from ..services.elysia import ElysiaService
from ..utils.display import print_section_header, create_health_panel, console


def health_command(verbose: bool = False, last_errors: Optional[int] = None) -> None:
    """Perform health checks on both services."""
    # Validate flags
    if last_errors is not None and not verbose:
        last_errors = None  # Ignore --last-errors without --verbose
    elif verbose and last_errors is None:
        last_errors = 3  # Default to 3 logs per container (9 total with 3 nodes)
    
    print_section_header("Health Checks")
    
    weaviate = WeaviateService()
    elysia = ElysiaService()
    
    # Get health information
    weaviate_health = weaviate.get_health(verbose=verbose, last_errors=last_errors)
    elysia_health = elysia.get_health(verbose=verbose, last_errors=last_errors)
    
    # Display health panels - Elysia first, then Weaviate
    elysia_panel = create_health_panel("Elysia AI", elysia_health, verbose=verbose)
    console.print(elysia_panel)
    
    # For verbose mode, separate Weaviate health from logs
    if verbose:
        # Extract logs from weaviate_health to show separately
        weaviate_logs = weaviate_health.pop("recent_errors", None)
        
        # Show Weaviate health without logs
        weaviate_panel = create_health_panel("Weaviate Cluster", weaviate_health, verbose=verbose)
        console.print(weaviate_panel)
        
        # Show Weaviate logs in separate panel
        if weaviate_logs:
            from ..utils.display import create_logs_panel
            logs_panel = create_logs_panel("Weaviate Node Logs", weaviate_logs)
            console.print(logs_panel)
    else:
        # Basic mode - just show Weaviate health
        weaviate_panel = create_health_panel("Weaviate Cluster", weaviate_health, verbose=verbose)
        console.print(weaviate_panel)