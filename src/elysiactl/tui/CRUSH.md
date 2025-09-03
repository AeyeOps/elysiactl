# elysiactl TUI Development Guide

## Overview
This guide documents patterns, practices, and architecture for developing the elysiactl Terminal User Interface (TUI). The TUI follows Textual framework conventions while incorporating project-specific patterns.

## 🎨 Theme Management

### External Theme Configuration
Themes are managed through external JSON files in `~/.elysiactl/themes/`:

```json
{
  "primary": "#00d4ff",
  "secondary": "#8b5cf6",
  "accent": "#ff6b6b",
  "foreground": "#ffffff",
  "background": "#1a1a2e",
  "surface": "#2a2a4e",
  "success": "#00ff88",
  "warning": "#ffa500",
  "error": "#ff4757",
  "panel": "#475569"
}
```

### Theme Loading Priority
1. Built-in themes (default, light, professional, minimal)
2. External JSON files (`~/.elysiactl/themes/*.json`)
3. Environment variables (`ELYSIACTL_THEME_*`)
4. Runtime theme switching

### CSS Theme Variables
Always use theme variables in CSS instead of hardcoded colors:

```python
# ✅ Good - Uses theme variables
def CSS(self):
    return """
    .my-widget {
        color: $primary;
        background: $surface;
        border: solid $panel;
    }
    """

# ❌ Bad - Hardcoded colors
def CSS(self):
    return """
    .my-widget {
        color: #00d4ff;
        background: #2a2a4e;
        border: solid #475569;
    }
    """
```

## 🏗️ Widget Architecture

### Virtual Scrolling Pattern
For content that may exceed screen height, use VirtualScrollableWidget:

```python
class VirtualScrollableWidget(Widget):
    def render_line(self, y: int) -> Strip:
        # Only render visible lines for performance
        return self._render_item_line(item, line_index, item_index)

    def add_content(self, content: Dict):
        # Add to content_items list
        self.content_items.append(content)
        self.refresh()
```

### Widget Composition
Follow composition over inheritance:

```python
# ✅ Good - Composable widgets
class RepoManagerApp(App):
    def compose(self):
        yield Header()
        with Vertical():
            yield VirtualScrollableWidget()
            yield CommandPrompt()

# ❌ Bad - Monolithic widgets
class RepoManagerApp(App):
    def compose(self):
        yield RepoManagerWidget()  # Does everything
```

### Event Handling
Use Textual's message system for widget communication:

```python
class TableRowSelected(Message):
    def __init__(self, table_index: int, row_data: Dict):
        super().__init__()
        self.table_index = table_index
        self.row_data = row_data

# In widget
self.post_message(TableRowSelected(index, data))

# In parent app
def on_table_row_selected(self, event: TableRowSelected):
    # Handle selection
    pass
```

## 🎯 Interaction Patterns

### Command Processing
Use natural language command processing:

```python
class CommandProcessor:
    def __init__(self):
        self.commands = {
            r"show.*repo": self.show_repositories,
            r"list.*repo": self.show_repositories,
            r"show.*status": self.show_status,
        }

    def process_command(self, command: str) -> Dict:
        for pattern, handler in self.commands.items():
            if re.search(pattern, command.lower()):
                return handler(command)
        return {"type": "unknown", "message": "Command not understood"}
```

### Keyboard Shortcuts
Standard shortcuts for power users:

```python
BINDINGS = [
    ("q", "quit", "Quit application"),
    ("?", "show_help", "Show help"),
    ("t", "cycle_theme", "Cycle themes"),
    ("l", "list_repos", "List repositories"),
    ("s", "show_status", "Show status"),
]
```

### Responsive Design
Handle different terminal sizes:

```python
def on_resize(self, event):
    """Handle terminal resize events."""
    width, height = event.size
    if width < 80:
        # Compact layout
        pass
    elif width < 120:
        # Standard layout
        pass
    else:
        # Wide layout with sidebar
        pass
```

## 🎨 Styling Conventions

### TCSS Best Practices
Use semantic class names and theme variables:

```python
DEFAULT_CSS = """
MyWidget {
    layout: vertical;
    height: 1fr;
    border: solid $panel;
    background: $surface;
}

.my-header {
    color: $primary;
    text-style: bold;
}

.status-success {
    color: $success;
}

.status-error {
    color: $error;
}
"""
```

### Color Usage Guidelines
- Use theme variables, never hardcoded colors
- Maintain sufficient contrast ratios
- Consider color blindness accessibility
- Use colors semantically (success=green, error=red, etc.)

## 📊 Data Management

### Repository Data Structure
Consistent data models for repositories:

```python
@dataclass
class Repository:
    organization: str
    project: str
    repository: str
    sync_status: str  # "success", "failed", "syncing"
    last_sync: Optional[datetime]
    description: Optional[str]
```

### State Management
Use reactive properties for dynamic updates:

```python
class MyWidget(Widget):
    repo_count = var(0)
    selected_repo = var(None)

    def watch_repo_count(self, old_count, new_count):
        # React to changes
        self.refresh()

    def watch_selected_repo(self, old_repo, new_repo):
        # Handle selection changes
        if new_repo:
            self.show_repo_details(new_repo)
```

## 🧪 Testing Patterns

### Widget Testing
Use Textual's testing framework:

```python
import pytest
from textual.testing import AppTester

@pytest.mark.asyncio
async def test_command_processing():
    app = RepoManagerApp()
    async with app.run_test() as pilot:
        await pilot.type("show repos")
        await pilot.press("enter")

        # Verify response appears in virtual scroller
        assert "repositories" in pilot.app.virtual_scroller.content_items
```

### Integration Testing
Test complete user workflows:

```python
async def test_full_workflow():
    app = RepoManagerApp()
    async with app.run_test() as pilot:
        # Type command
        await pilot.type("list repos")
        await pilot.press("enter")

        # Wait for response
        await pilot.pause(0.1)

        # Verify UI updates
        assert pilot.app.virtual_scroller.get_total_lines() > 0
```

## ⚡ Performance Optimization

### Virtual Scrolling
Always use virtual scrolling for large datasets:

```python
def render_line(self, y: int) -> Strip:
    """Only render visible lines."""
    if not self._is_line_visible(y):
        return Strip.blank()

    return self._render_actual_line(y)
```

### Lazy Loading
Load data on demand:

```python
async def load_more_repos(self):
    """Load additional repositories when scrolling near end."""
    if self.near_end_of_content():
        new_repos = await self.fetch_repos(self.current_page + 1)
        self.add_repositories(new_repos)
```

### Memory Management
Clean up resources:

```python
async def on_unmount(self):
    """Clean up resources when widget is removed."""
    self.content_items.clear()
    if hasattr(self, 'background_task'):
        self.background_task.cancel()
```

## 🔧 Development Workflow

### Local Development
Use Textual's dev server for rapid iteration:

```bash
# Development mode with live CSS editing
textual run --dev src/elysiactl/tui/app.py

# Or serve via web
textual serve --dev elysiactl repo tui --port 9150
```

### Debugging
Enable debug logging and use browser dev tools:

```python
# In app initialization
import logging
logging.basicConfig(level=logging.DEBUG)

# Use browser dev tools when serving via web
# Open http://localhost:9150 for debugging
```

### Code Organization
Maintain clean separation:

```
src/elysiactl/tui/
├── app.py              # Main application
├── widgets/            # Custom widgets
│   ├── virtual_scrollable.py
│   ├── command_prompt.py
│   └── repository_table.py
├── theme_manager.py    # Theme management
├── command_processor.py # Command processing
└── CRUSH.md           # This guide
```

## 📋 Best Practices

### ✅ Do's
- Use theme variables in CSS, never hardcoded colors
- Implement virtual scrolling for large datasets
- Handle terminal resize events
- Use Textual's message system for widget communication
- Write comprehensive tests for user interactions
- Follow semantic naming conventions
- Document widget behavior and props

### ❌ Don'ts
- Hardcode colors or styles
- Create monolithic widgets
- Ignore performance with large datasets
- Use synchronous operations in event handlers
- Mix data fetching with UI rendering
- Ignore accessibility considerations
- Skip error handling in user interactions

## 🚀 Future Enhancements

### Planned Features
- Responsive sidebar with repository statistics
- Advanced filtering and search capabilities
- Keyboard shortcut customization
- Plugin system for extending functionality
- Export/import of repository configurations
- Real-time collaboration features

### Architecture Improvements
- State management with reactive stores
- Component library for consistent UI
- Advanced theming with custom color schemes
- Performance monitoring and optimization
- Accessibility compliance (WCAG guidelines)

This guide should be updated as new patterns emerge and best practices evolve. Always prioritize user experience, performance, and maintainability in TUI development.</content>
<parameter name="file_path">src/elysiactl/tui/CRUSH.md