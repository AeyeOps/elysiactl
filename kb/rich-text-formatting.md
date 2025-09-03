# Rich Text Formatting: Complete Guide

Rich is a Python library that transforms terminal output with beautiful formatting, colors, tables, progress bars, and interactive elements. This guide covers comprehensive usage patterns, integration techniques, and production deployment strategies.

## Core Rich Components

### Console Fundamentals

The Console object is Rich's primary interface for terminal output:

```python
from rich.console import Console

console = Console()
console.print("Hello", "World!")  # Basic printing with word wrapping
console.print("Styled text", style="bold red")  # Apply styles
console.print("[bold cyan]Markup[/bold cyan] text")  # BBCode-like markup
```

Console capabilities:
- Automatic text wrapping to terminal width
- Color and style support
- Unicode and emoji rendering
- Markup syntax processing
- File output redirection

### Text Formatting and Markup Syntax

Rich supports BBCode-style markup for inline formatting:

```python
console.print("Where there is a [bold cyan]Will[/bold cyan] there [u]is[/u] a [i]way[/i].")
console.print("[red]Error:[/red] Something went wrong")
console.print("Visit my [link=https://example.com]website[/link]!")
```

Common markup tags:
- `[bold]` / `[/bold]` - Bold text
- `[italic]` / `[/italic]` - Italic text
- `[underline]` / `[/underline]` - Underlined text
- `[red]`, `[blue]`, etc. - Colors
- `[link=URL]text[/link]` - Clickable hyperlinks

### Rich Inspect for Debugging

```python
from rich import inspect

def my_function():
    return {"data": [1, 2, 3]}

inspect(my_function, methods=True)  # Show object details
console.print(locals())  # Pretty-print local variables
```

## Advanced Formatting Features

### Tables with Styling

Rich tables support advanced formatting, alignment, and nested content:

```python
from rich.table import Table
from rich.console import Console

console = Console()
table = Table(title="Star Wars Movies", show_header=True, header_style="bold magenta")

# Add columns with specific styling
table.add_column("Date", style="dim", width=12)
table.add_column("Title")
table.add_column("Production Budget", justify="right")
table.add_column("Box Office", justify="right", style="green")

# Add rows with markup
table.add_row(
    "Dec 20, 2019", 
    "Star Wars: The Rise of Skywalker", 
    "$275,000,000", 
    "$375,126,118"
)
table.add_row(
    "May 25, 2018",
    "[red]Solo[/red]: A Star Wars Story",  # Markup in cells
    "$275,000,000",
    "$393,151,347",
)

console.print(table)
```

Table features:
- Automatic column width adjustment
- Text alignment (left, center, right)
- Cell styling and markup
- Nested Rich renderables
- Border customization
- Header styling

### Progress Bars and Spinners

Simple progress tracking:

```python
from rich.progress import track

for step in track(range(100), description="Processing..."):
    do_work(step)
```

Advanced progress bars with multiple columns:

```python
from rich.progress import Progress, BarColumn, TextColumn, TimeColumn
from rich.table import Column

progress = Progress(
    TextColumn("[bold blue]{task.description}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    TimeColumn(),
    expand=True,
)

with progress:
    task1 = progress.add_task("Download", total=1000)
    task2 = progress.add_task("Process", total=500)
    
    for i in range(1000):
        progress.update(task1, advance=1)
        if i % 2 == 0:
            progress.update(task2, advance=1)
```

Status indicators with spinners:

```python
from time import sleep
from rich.console import Console

console = Console()
with console.status("[bold green]Working on tasks...") as status:
    while tasks:
        task = tasks.pop(0)
        sleep(1)
        console.log(f"{task} complete")
```

### Live Displays and Updating Content

Create real-time updating displays:

```python
from rich.live import Live
from rich.table import Table
import time

def generate_table():
    table = Table()
    table.add_column("Time")
    table.add_column("Status")
    table.add_row(time.strftime("%H:%M:%S"), "Running")
    return table

with Live(generate_table(), refresh_per_second=4) as live:
    for i in range(40):
        time.sleep(0.4)
        live.update(generate_table())
```

### Panels, Columns, and Layout

Panels for grouping content:

```python
from rich.panel import Panel

console.print(Panel("Hello, World!", title="Greeting"))
console.print(Panel.fit("Fit to content", style="red"))
```

Column layouts:

```python
from rich.columns import Columns

renderables = [Panel(f"Panel {i}") for i in range(6)]
console.print(Columns(renderables))
```

Advanced layouts:

```python
from rich.layout import Layout

layout = Layout()
layout.split_column(
    Layout(name="header", size=3),
    Layout(name="body"),
    Layout(name="footer", size=3),
)
layout["body"].split_row(Layout(name="left"), Layout(name="right"))

layout["header"].update(Panel("Header"))
layout["footer"].update(Panel("Footer"))
layout["left"].update(Panel("Left"))
layout["right"].update(Panel("Right"))

console.print(layout)
```

### Syntax Highlighting

Code syntax highlighting with themes:

```python
from rich.syntax import Syntax

code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''

syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
console.print(syntax)

# Load from file
syntax = Syntax.from_path("script.py", line_numbers=True)
console.print(syntax)
```

Available themes: `monokai`, `github-dark`, `solarized-dark`, `dracula`, etc.

### Exception and Traceback Formatting

Enhanced traceback display:

```python
from rich.traceback import install

install()  # Install rich tracebacks globally

# Or use context manager for specific code blocks
from rich.console import Console
console = Console()

try:
    1/0
except:
    console.print_exception(show_locals=True)
```

### Logging with Rich Handlers

Integration with Python's logging system:

```python
import logging
from rich.logging import RichHandler

# Basic setup
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

log = logging.getLogger("rich")
log.info("Hello, World!")
log.error("Something went wrong")

# With markup enabled
handler = RichHandler(enable_markup=True)
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[handler]
)

logger = logging.getLogger("app")
logger.info("Processing [bold green]completed[/bold green]")
```

### Trees and Hierarchical Data

Display tree structures:

```python
from rich.tree import Tree

tree = Tree("🌳 Project")
tree.add("📁 src")
src = tree.children[-1]
src.add("📄 main.py")
src.add("📄 utils.py")

tree.add("📁 tests")
tests = tree.children[-1]
tests.add("📄 test_main.py")

console.print(tree)
```

### Markdown and Emoji Rendering

Render markdown content:

```python
from rich.markdown import Markdown

markdown_content = """
# Heading

This is **bold** and *italic* text.

- List item 1
- List item 2

```python
print("Hello, World!")
```
"""

md = Markdown(markdown_content)
console.print(md)
```

Emoji support:

```python
console.print(":smiley: :heart: :thumbs_up:")
console.print("😊 💖 👍")  # Direct Unicode
```

## Integration Patterns

### Rich + Textual: TUI Framework Integration

Using Rich renderables in Textual widgets:

```python
from rich.table import Table
from textual.app import App, ComposeResult
from textual.widgets import Static

class DataWidget(Static):
    def on_mount(self) -> None:
        table = Table("Name", "Value")
        table.add_row("Status", "Active")
        table.add_row("Count", "42")
        self.update(table)

class MyApp(App):
    def compose(self) -> ComposeResult:
        yield DataWidget()

if __name__ == "__main__":
    app = MyApp()
    app.run()
```

Custom Textual widgets with Rich renderables:

```python
from rich.syntax import Syntax
from textual.widget import Widget
from textual.reactive import reactive

class CodeView(Widget):
    code = reactive("")
    
    def render(self):
        return Syntax(self.code, "python", line_numbers=True)
```

### Rich + Typer: Beautiful CLI Output

Combining Rich with Typer for CLI applications:

```python
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

@app.command()
def show_data(name: str):
    """Display user data in a formatted table."""
    table = Table(title=f"Data for {name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Name", name)
    table.add_row("Status", "Active")
    
    console.print(table)

@app.command()
def process_files(files: list[str]):
    """Process multiple files with progress tracking."""
    from rich.progress import track
    
    for file in track(files, description="Processing..."):
        # Process file
        console.print(f"✅ Processed {file}")

if __name__ == "__main__":
    app()
```

## Custom Renderables

Create custom Rich renderables:

```python
from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style

class Rainbow:
    def __init__(self, text: str):
        self.text = text
    
    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        colors = ["red", "orange", "yellow", "green", "blue", "indigo", "violet"]
        for i, char in enumerate(self.text):
            color = colors[i % len(colors)]
            yield Segment(char, Style(color=color))

# Usage
console.print(Rainbow("Hello Rainbow!"))
```

Simple custom renderable:

```python
class StatusBadge:
    def __init__(self, status: str):
        self.status = status
    
    def __rich__(self) -> str:
        color = "green" if self.status == "active" else "red"
        return f"[{color}]●[/{color}] {self.status.upper()}"

console.print(StatusBadge("active"))
```

## Themes and Styling System

Custom themes:

```python
from rich.theme import Theme
from rich.console import Console

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "error": "bold red",
    "success": "bold green"
})

console = Console(theme=custom_theme)
console.print("Information message", style="info")
console.print("Warning message", style="warning")
console.print("Error message", style="error")
console.print("Success message", style="success")
```

Style composition:

```python
from rich.style import Style

style = Style(color="blue", bold=True, underline=True)
console.print("Styled text", style=style)

# Combining styles
base_style = Style(color="red")
emphasis = Style(bold=True)
combined = base_style + emphasis
```

## Performance Considerations

### Memory Usage Optimization

For large outputs, consider streaming approaches:

```python
# Instead of building large tables in memory
def stream_data():
    for row in large_dataset:
        yield format_row(row)

# Use generators with progress tracking
for item in track(stream_data(), total=estimated_count):
    console.print(item)
```

### Terminal Capability Detection

Rich automatically detects terminal capabilities:

```python
console = Console()

# Check capabilities
print(f"Color support: {console.color_system}")
print(f"Terminal width: {console.width}")
print(f"Height: {console.height}")

# Force specific settings
console = Console(color_system="256", width=80, force_terminal=True)
```

### Color Degradation Strategies

Rich handles color degradation automatically, but you can control it:

```python
# Force specific color systems
console = Console(color_system="truecolor")  # 16M colors
console = Console(color_system="256")       # 256 colors
console = Console(color_system="standard")  # 8 colors
console = Console(color_system=None)        # No colors
```

### Unicode Fallbacks

Rich handles Unicode fallbacks gracefully:

```python
# Rich automatically falls back to ASCII alternatives
console.print("▸ Progress: ████████░░ 80%")
# Falls back to: "> Progress: ########.. 80%"

# Force ASCII mode
console = Console(legacy_windows=True)
```

## Production Deployment Tips

### Environment Detection

```python
import os
from rich.console import Console

# Detect CI/production environments
is_ci = os.getenv('CI') == 'true'
is_production = os.getenv('ENVIRONMENT') == 'production'

# Configure console appropriately
console = Console(
    force_terminal=not is_ci,
    color_system=None if is_production else "auto",
    width=80 if is_ci else None
)
```

### File Output and Logging

```python
from rich.console import Console
from rich.text import Text
import sys

# Output to files
with open("output.html", "w") as f:
    file_console = Console(file=f, record=True)
    file_console.print("Rich content")
    # Export as HTML
    f.write(file_console.export_html())

# Capture output for testing
console = Console(file=sys.stdout, record=True)
console.print("Test output")
output = console.export_text()
```

### Error Handling

```python
from rich.console import Console
import sys

def safe_rich_print(content, fallback=""):
    """Safely print Rich content with fallback."""
    try:
        console.print(content)
    except Exception:
        # Fallback to plain print in case of Rich errors
        print(fallback or str(content), file=sys.stderr)

# Example usage
safe_rich_print(
    "[bold green]Success![/bold green]", 
    fallback="Success!"
)
```

## Common Pitfalls and Solutions

### Performance Issues

**Problem**: Slow rendering with large datasets
**Solution**: Use streaming and pagination

```python
# BAD: Building large table in memory
table = Table()
for row in million_rows:
    table.add_row(*row)

# GOOD: Paginate or stream
def paginate_data(data, page_size=100):
    for i in range(0, len(data), page_size):
        yield data[i:i + page_size]

for page in paginate_data(large_dataset):
    table = Table()
    for row in page:
        table.add_row(*row)
    console.print(table)
    input("Press Enter for next page...")
```

### Memory Leaks with Live Displays

**Problem**: Live displays not properly closed
**Solution**: Always use context managers

```python
# BAD
live = Live(content)
live.start()
# Forgot to call live.stop()

# GOOD
with Live(content) as live:
    # Updates happen here
    pass  # Automatically cleaned up
```

### Markup Injection

**Problem**: User input containing markup
**Solution**: Escape user content

```python
from rich.markup import escape

user_input = "[red]malicious[/red]"
console.print(f"User said: {escape(user_input)}")
# Output: User said: \[red]malicious\[/red]
```

## Real-World Examples

### Dashboard Layout

```python
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich.live import Live
import time

def create_dashboard():
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right", ratio=2)
    )
    
    # Header
    layout["header"].update(Panel("System Dashboard", style="bold blue"))
    
    # Left panel - Stats
    stats = Table()
    stats.add_column("Metric")
    stats.add_column("Value")
    stats.add_row("CPU Usage", "45%")
    stats.add_row("Memory", "2.1GB")
    stats.add_row("Disk", "67%")
    layout["left"].update(Panel(stats, title="System Stats"))
    
    # Right panel - Logs
    logs = "\n".join([
        "[dim]2024-01-01 12:00:01[/dim] INFO: Service started",
        "[dim]2024-01-01 12:00:02[/dim] INFO: Connected to database",
        "[dim]2024-01-01 12:00:03[/dim] [yellow]WARN[/yellow]: High memory usage",
        "[dim]2024-01-01 12:00:04[/dim] [red]ERROR[/red]: Connection timeout"
    ])
    layout["right"].update(Panel(logs, title="Recent Logs", border_style="blue"))
    
    # Footer
    layout["footer"].update(Panel("Press Ctrl+C to exit", style="dim"))
    
    return layout

# Run live dashboard
with Live(create_dashboard(), refresh_per_second=1) as live:
    try:
        while True:
            time.sleep(1)
            live.update(create_dashboard())
    except KeyboardInterrupt:
        pass
```

### Log Viewer with Syntax Highlighting

```python
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.columns import Columns

class LogViewer:
    def __init__(self):
        self.console = Console()
    
    def view_json_logs(self, log_entries):
        """Display JSON logs with syntax highlighting."""
        panels = []
        
        for entry in log_entries:
            # Syntax highlight JSON
            json_syntax = Syntax(
                entry['message'], 
                "json", 
                theme="monokai", 
                line_numbers=False
            )
            
            # Color code by log level
            level_colors = {
                "ERROR": "red",
                "WARN": "yellow", 
                "INFO": "blue",
                "DEBUG": "dim"
            }
            
            color = level_colors.get(entry['level'], "white")
            
            panel = Panel(
                json_syntax,
                title=f"[{color}]{entry['level']}[/{color}] - {entry['timestamp']}",
                border_style=color
            )
            panels.append(panel)
        
        self.console.print(Columns(panels, equal=True))

# Usage
viewer = LogViewer()
logs = [
    {
        "level": "INFO",
        "timestamp": "2024-01-01T12:00:00Z",
        "message": '{"user_id": 123, "action": "login", "success": true}'
    },
    {
        "level": "ERROR", 
        "timestamp": "2024-01-01T12:01:00Z",
        "message": '{"error": "database_timeout", "query": "SELECT * FROM users", "duration_ms": 5000}'
    }
]
viewer.view_json_logs(logs)
```

This comprehensive guide covers Rich's extensive capabilities for creating beautiful, functional terminal applications. Whether building simple CLI tools or complex TUI applications, Rich provides the building blocks for exceptional user experiences in the terminal.