"""Health command implementation."""

import asyncio
import json
from typing import Optional
from ..services.weaviate import WeaviateService
from ..services.elysia import ElysiaService
from ..services.cluster_verification import ClusterVerifier
from ..utils.display import print_section_header, create_health_panel, console


def health_command(
    verbose: bool = False, 
    last_errors: Optional[int] = None,
    cluster: bool = False,
    collection: Optional[str] = None,
    quick: bool = False,
    fix: bool = False,
    json_output: bool = False
) -> None:
    """Perform health checks on both services."""
    # Validate flags
    if last_errors is not None and not verbose:
        last_errors = None  # Ignore --last-errors without --verbose
    elif verbose and last_errors is None:
        last_errors = 3  # Default to 3 logs per container (9 total with 3 nodes)
    
    weaviate = WeaviateService()
    elysia = ElysiaService()
    
    if cluster:
        # Perform cluster verification
        asyncio.run(_perform_cluster_verification(
            weaviate, collection, quick, fix, json_output
        ))
        return
    
    # Standard health checks
    print_section_header("Health Checks")
    
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


async def _perform_cluster_verification(
    weaviate_service: WeaviateService,
    collection: Optional[str],
    quick: bool,
    fix: bool,
    json_output: bool
) -> None:
    """Perform cluster verification checks."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from datetime import datetime
    
    verifier = ClusterVerifier(weaviate_service)
    
    if not json_output:
        print_section_header("Weaviate Cluster Verification")
        
        with console.status("[bold green]Running cluster verification..."):
            result = await verifier.verify_cluster(quick=quick, collection_filter=collection)
    else:
        result = await verifier.verify_cluster(quick=quick, collection_filter=collection)
    
    if json_output:
        # Output JSON format for scripting
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "cluster": {
                "healthy": result.healthy,
                "nodes": {
                    "expected": result.expected_nodes,
                    "actual": result.node_count
                }
            },
            "collections": {
                "system": {
                    name: {
                        "exists": status.exists,
                        "replication_factor": status.replication_factor,
                        "node_distribution": status.node_distribution,
                        "data_count": status.data_count,
                        "consistent": status.consistent,
                        "issues": status.issues
                    }
                    for name, status in result.system_collections.items()
                },
                "derived": {
                    name: {
                        "exists": status.exists,
                        "replication_factor": status.replication_factor,
                        "consistent": status.consistent
                    }
                    for name, status in result.derived_collections.items()
                }
            },
            "issues": [
                {
                    "severity": issue.severity,
                    "message": issue.message,
                    "collection": issue.collection,
                    "node": issue.node,
                    "fixable": issue.fixable
                }
                for issue in result.issues
            ],
            "warnings": [
                {
                    "message": warning.message,
                    "node": warning.node
                }
                for warning in result.warnings
            ],
            "replication_lag": result.replication_lag,
            "error": result.error
        }
        
        console.print(json.dumps(output_data, indent=2))
        return
    
    # Standard formatted output
    if result.error:
        error_panel = Panel(
            f"[bold red]Error: {result.error}",
            title="Cluster Verification Failed",
            border_style="red"
        )
        console.print(error_panel)
        return
    
    # Cluster topology section
    topology_table = Table(show_header=True, header_style="bold blue")
    topology_table.add_column("Check", style="cyan")
    topology_table.add_column("Status", justify="center")
    topology_table.add_column("Details")
    
    node_status = "✓" if result.node_count == result.expected_nodes else "✗"
    node_style = "green" if result.node_count == result.expected_nodes else "red"
    topology_table.add_row(
        "Node Count",
        Text(node_status, style=node_style),
        f"{result.node_count} of {result.expected_nodes} expected nodes"
    )
    
    topology_panel = Panel(topology_table, title="Cluster Topology", border_style="blue")
    console.print(topology_panel)
    
    # System collections section
    if result.system_collections:
        sys_table = Table(show_header=True, header_style="bold blue")
        sys_table.add_column("Collection", style="cyan")
        sys_table.add_column("Status", justify="center")
        sys_table.add_column("Replication", justify="center")
        sys_table.add_column("Distribution")
        
        for name, status in result.system_collections.items():
            if status.exists:
                status_icon = "✓" if status.consistent else "✗"
                status_style = "green" if status.consistent else "red"
                
                replication_text = f"factor={status.replication_factor}"
                if status.replication_factor == result.node_count:
                    replication_text += " ✓"
                    repl_style = "green"
                else:
                    replication_text += " ✗"
                    repl_style = "red"
                
                distribution = f"{len([n for n in status.node_distribution.values() if n > 0])}/{len(status.node_distribution)} nodes"
                
                sys_table.add_row(
                    name,
                    Text(status_icon, style=status_style),
                    Text(replication_text, style=repl_style),
                    distribution
                )
            else:
                sys_table.add_row(
                    name,
                    Text("✗", style="red"),
                    Text("N/A", style="dim"),
                    Text("Missing", style="red")
                )
        
        sys_panel = Panel(sys_table, title="System Collections", border_style="blue")
        console.print(sys_panel)
    
    # Derived collections section
    if result.derived_collections:
        derived_table = Table(show_header=True, header_style="bold blue")
        derived_table.add_column("Collection", style="cyan")
        derived_table.add_column("Status", justify="center")
        derived_table.add_column("Replication", justify="center")
        
        for name, status in result.derived_collections.items():
            status_icon = "✓" if status.consistent else "✗"
            status_style = "green" if status.consistent else "red"
            
            replication_text = f"factor={status.replication_factor}"
            
            derived_table.add_row(
                name,
                Text(status_icon, style=status_style),
                replication_text
            )
        
        derived_panel = Panel(derived_table, title="Derived Collections", border_style="blue")
        console.print(derived_panel)
    
    # Replication lag section
    if result.replication_lag:
        lag_table = Table(show_header=True, header_style="bold blue")
        lag_table.add_column("Node", justify="center")
        lag_table.add_column("Lag", justify="center")
        lag_table.add_column("Status", justify="center")
        
        for port, lag in result.replication_lag.items():
            lag_text = f"{lag:.3f}s"
            if lag < 0.5:
                lag_icon = "✓"
                lag_style = "green"
            elif lag < 1.0:
                lag_icon = "⚠"
                lag_style = "yellow"
            else:
                lag_icon = "✗"
                lag_style = "red"
            
            lag_table.add_row(
                f":{port}",
                lag_text,
                Text(lag_icon, style=lag_style)
            )
        
        lag_panel = Panel(lag_table, title="Replication Lag", border_style="blue")
        console.print(lag_panel)
    
    # Issues summary
    critical_issues = [i for i in result.issues if i.severity == "critical"]
    high_issues = [i for i in result.issues if i.severity == "high"]
    medium_issues = [i for i in result.issues if i.severity == "medium"]
    
    if result.issues or result.warnings:
        summary_text = []
        
        if critical_issues:
            summary_text.append(f"[bold red]CRITICAL: {len(critical_issues)} issues[/bold red]")
        if high_issues:
            summary_text.append(f"[red]HIGH: {len(high_issues)} issues[/red]")
        if medium_issues:
            summary_text.append(f"[yellow]MEDIUM: {len(medium_issues)} issues[/yellow]")
        if result.warnings:
            summary_text.append(f"[dim]WARNINGS: {len(result.warnings)}[/dim]")
        
        summary_panel = Panel(
            "\n".join([f"• {issue.message}" for issue in result.issues[:5]] + 
                     [f"• {warning.message}" for warning in result.warnings[:3]]),
            title=f"Issues Found: {' | '.join(summary_text)}",
            border_style="red" if critical_issues or high_issues else "yellow"
        )
        console.print(summary_panel)
        
        if not fix and any(i.fixable for i in result.issues):
            console.print("\n[bold yellow]Run with --fix to attempt repairs[/bold yellow]")
    else:
        success_panel = Panel(
            "[bold green]✓ All cluster verification checks passed[/bold green]",
            border_style="green"
        )
        console.print(success_panel)
    
    # Handle repair functionality
    if fix:
        fixable_issues = [i for i in result.issues if i.fixable]
        if fixable_issues:
            console.print(f"\n[yellow]Attempting to repair {len(fixable_issues)} fixable issues...[/yellow]")
            
            # This would require user confirmation in a real implementation
            repair_result = await verifier.attempt_repair(fixable_issues)
            
            console.print(f"Repair summary: {repair_result}")