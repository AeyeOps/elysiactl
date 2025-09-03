# Latest Features & Best Practices: Textual, Rich, and Typer
*Generated from comprehensive research via context7 - Updated as of Sept 2025*

## 🎨 Rich v13+ Advanced Features

### Core Capabilities
- **Rich Tables**: Styled headers, custom columns (align/width), live updates, emoji support
- **Progress Bars**: Multiple concurrent progress bars with spinners
- **Syntax Highlighting**: Pygments integration with 300+ languages/themes
- **Markdown Rendering**: Full markdown support in terminal
- **Live Updates**: `Live()` context for streaming updates
- **Pretty Printing**: Enhanced object inspection with `rich.inspect()`

### Key Features for Repo Management
```python
from rich.table import Table
from rich.console import Console
from rich.progress import track

def display_repo_status(repos):
    table = Table(title="Repository Status")
    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("Docs", justify="right")
    table.add_column("Last Sync", style="yellow")
    table.add_column("Status", style="green")

    for repo in repos[:50]:  # Handle large lists efficiently
        table.add_row(
            repo['name'],
            str(repo['docs']),
            repo['last_sync'],
            repo['status_emoji']
        )
    Console().print(table)

# Progress tracking for sync operations
for repo in track(repos_to_sync, description="Syncing repos..."):
    sync_repository(repo)
```

### Performance Best Practices
- Use `Console.record=True` for capturing output
- Implement pagination for large datasets (>1000 items)
- Leverage `rich.live.Live` for real-time updates
- Use `rich.columns.Columns` for directory-like listings

## 🚀 Textual v0.70+ Modern TUI Features

### Core Architecture
- **Reactive Data Model**: Auto-update UI with `@reactive` properties
- **Widget System**: 20+ built-in widgets (DataTable, Tree, Markdown, etc.)
- **CSS Styling**: Web-like CSS with terminal-specific properties
- **Virtual Scrolling**: Efficiently handle 100K+ items
- **Async Support**: Full asyncio integration with `@work` decorator

### Essential Widgets for Repo Management
```python
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Input
from textual.containers import VerticalScroll
from textual import reactive

class RepoManagerApp(App):
    """Repository management TUI with persistent UI elements."""

    CSS = """
    Screen { background: $surface; }
    Footer { dock: bottom; background: $primary; }
    Input#prompt { dock: bottom; margin-bottom: 1; }
    DataTable#repo_table {
        dock: top;
        height: 75%;
        border: solid $accent;
    }
    """

    show_failed_only = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="repo_table")
        yield Input(placeholder="💬 What would you like to do?", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the repository table."""
        table = self.query_one("#repo_table", DataTable)
        table.add_columns("Repository", "Docs", "Last Sync", "Status")
        self.load_repositories()

    def load_repositories(self) -> None:
        """Load and display repositories with virtual scrolling."""
        table = self.query_one("#repo_table", DataTable)
        repos = self.get_repositories()

        for repo in repos:
            if not self.show_failed_only or repo['status'] == 'failed':
                table.add_row(
                    repo['name'], repo['docs'], repo['last_sync'], repo['status']
                )

    def watch_show_failed_only(self, value: bool) -> None:
        """Reactively update display when filter changes."""
        self.load_repositories()  # Re-render filtered results

    @work(thread=True)
    def sync_repositories(self) -> None:
        """Background sync with progress updates."""
        # Implementation for async repository syncing
        pass
```

### Performance Optimizations
- **Virtual Scrolling**: Only render visible rows in DataTable
- **Background Workers**: Use `@work` for non-blocking operations
- **Reactive Updates**: Automatic UI updates via reactive properties
- **Efficient Layouts**: CSS-based layouts with `grid-auto-flow`

### Advanced Features
- **Command Palette**: Bind keys to complex actions
- **Fuzzy Matching**: Built-in fuzzy search capabilities
- **Themes**: Dynamic theme switching
- **Accessibility**: Full keyboard navigation and screen reader support

## ⚡ Typer v0.12+ Modern CLI Patterns

### Core Features
- **Type-Driven CLI**: Full Python type hint integration
- **Rich Integration**: Beautiful output with colors/progress bars
- **Shell Completion**: Auto-generated completions for bash/zsh/fish
- **Command Groups**: Hierarchical command organization
- **Callback System**: Pre/post command hooks

### Repository Management CLI Structure
```python
from typing import Annotated, Optional
import typer
from pathlib import Path
from rich.console import Console

console = Console()
app = typer.Typer(
    name="elysiactl",
    help="Control utility for managing Elysia AI and Weaviate services",
    no_args_is_help=True
)

repo_app = typer.Typer(
    name="repo",
    help="Manage repository connections and monitoring"
)
app.add_typer(repo_app)

@repo_app.command("add")
def add_repo(
    pattern: Annotated[str, typer.Argument(help="Repository pattern (org/project/repo)")],
    watch: Annotated[bool, typer.Option("--watch", "-w", help="Monitor for changes")] = False,
    provider: Annotated[Optional[str], typer.Option("--provider", "-p", help="Git provider")] = None,
    limit: Annotated[Optional[int], typer.Option("--limit", "-l", help="Max repositories")] = 100
):
    """Add repositories to monitoring."""
    console.print(f"🔍 Discovering repositories: {pattern}")

    try:
        repos = discover_repositories(pattern, provider, limit)

        if repos:
            # Display with Rich table
            table = Table(title=f"Found {len(repos)} repositories")
            table.add_column("Repository", style="cyan")
            table.add_column("Project", style="magenta")
            table.add_column("Status", style="green")

            for repo in repos[:10]:  # Show preview
                table.add_row(repo.name, repo.project, "✅ Ready")
            console.print(table)

            if len(repos) > 10:
                console.print(f"... and {len(repos) - 10} more")

            # Persist configuration
            save_repo_config(repos)
            console.print("💾 Repository configuration saved")

        else:
            console.print("❌ No repositories found")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"❌ Error: {e}")
        raise typer.Exit(1)

@repo_app.command("status")
def repo_status(
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    filter_status: Annotated[Optional[str], typer.Option("--filter", "-f", help="Filter by status")] = None
):
    """Show repository status with filtering."""
    repos = load_repo_config()

    if filter_status:
        repos = [r for r in repos if r.status == filter_status]

    if json_output:
        import json
        console.print_json(data=[r.__dict__ for r in repos])
    else:
        # Rich table display
        display_repo_table(repos)

@repo_app.command("sync")
def sync_repos(
    parallel: Annotated[int, typer.Option("--parallel", "-p", help="Parallel sync jobs")] = 4,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes")] = False
):
    """Sync all monitored repositories."""
    from concurrent.futures import ThreadPoolExecutor
    from rich.progress import Progress

    repos = load_repo_config()
    console.print(f"🔄 Syncing {len(repos)} repositories...")

    with Progress() as progress:
        task = progress.add_task("Syncing...", total=len(repos))

        def sync_repo(repo):
            if not dry_run:
                # Actual sync logic
                pass
            progress.update(task, advance=1)
            return repo

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            results = list(executor.map(sync_repo, repos))

    console.print("✅ Sync completed")

@app.callback()
def main_callback(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output")] = False,
    config_file: Annotated[Optional[Path], typer.Option("--config", help="Config file")] = None
):
    """Global options for elysiactl."""
    if verbose:
        console.print("🐛 Verbose mode enabled")
    if config_file:
        console.print(f"⚙️ Using config: {config_file}")
```

### Best Practices
- **Type Annotations**: Use `Annotated` for complex parameter types
- **Rich Integration**: Combine with Rich for beautiful output
- **Error Handling**: Use `try/except` with `typer.Exit()` for clean exits
- **Command Groups**: Organize related commands with sub-apps
- **Shell Completion**: Enable with `--install-completion`

## 🔗 Integration Patterns

### Textual + Rich (Seamless Integration)
```python
from textual.widgets import Static
from rich.table import Table

class RepoTableWidget(Static):
    """Widget that displays repository data using Rich tables."""

    def render(self):
        table = Table(title="Repository Status")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")

        for repo in self.repos:
            table.add_row(repo.name, repo.status)

        return table  # Textual automatically renders Rich objects
```

### Typer + Textual (CLI to TUI)
```python
@app.command("tui")
def launch_tui():
    """Launch the interactive TUI."""
    from .tui import RepoManagerApp

    app = RepoManagerApp()
    app.run()

# Or embed TUI components in CLI
@app.command("status")
def status(interactive: bool = False):
    """Show status - use --interactive for TUI."""
    if interactive:
        # Launch mini TUI for this command
        from textual.widgets import DataTable
        # ... TUI implementation
    else:
        # Standard CLI output
        display_status_table()
```

### Performance Considerations
- **Large Datasets**: Use pagination/virtual scrolling (Textual DataTable)
- **Background Tasks**: Leverage `@work` decorator for non-blocking operations
- **Memory Management**: Stream processing for 100K+ repositories
- **Caching**: Cache repository metadata to reduce API calls

This knowledge base provides a solid foundation for implementing the repository management UX with modern, performant TUI/CLI patterns.