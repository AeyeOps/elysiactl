# Phase 1: TUI Foundation & Basic Display
**Status**: Ready to Implement
**Estimated Duration**: 1-2 days
**Deliverable**: Functional TUI with repository table display

## 🎯 Objectives

Create the foundational Textual User Interface with:
- Footer + Open Prompt Area layout (as designed)
- Basic repository table widget
- Simple command mapping for core functionality
- Responsive design that works on any terminal size

## 📋 Implementation Steps

### 1. Create TUI App Structure
```python
# src/elysiactl/tui/app.py
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from .widgets import RepositoryTable, CommandPrompt

class RepoManagerApp(App):
    """Main repository management TUI application."""

    CSS = """
    Screen { background: $surface; }
    Footer { dock: bottom; background: $primary; }
    CommandPrompt { dock: bottom; margin-bottom: 1; }
    RepositoryTable { dock: top; height: 75%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield RepositoryTable()
        yield CommandPrompt()
        yield Footer()
```

### 2. Build Repository Table Widget
```python
# src/elysiactl/tui/widgets/repository_table.py
from textual.widgets import DataTable
from ...services.repository import repo_service

class RepositoryTable(DataTable):
    """Widget for displaying repository information in a table."""

    def on_mount(self):
        """Initialize table with columns and load initial data."""
        self.add_columns("Repository", "Status", "Last Sync", "Size")
        self.load_repositories()

    def load_repositories(self):
        """Load and display repository data."""
        # Implementation to populate table with repository data
        pass
```

### 3. Implement Command Prompt Widget
```python
# src/elysiactl/tui/widgets/command_prompt.py
from textual.widgets import Input

class CommandPrompt(Input):
    """Natural language input widget for repository commands."""

    def __init__(self):
        super().__init__(placeholder="💬 What would you like to do with repositories?")

    def on_submit(self, event):
        """Handle natural language commands."""
        self.process_command(event.value)
        self.clear()
```

### 4. Add Command Processing Logic
```python
# src/elysiactl/tui/command_processor.py
class CommandProcessor:
    """Process natural language commands into actions."""

    COMMANDS = {
        "show repos": "show_repository_table",
        "list repositories": "show_repository_table",
        "repo status": "show_repository_status",
    }

    def process_command(self, command: str):
        """Process a natural language command."""
        command_lower = command.lower()
        for pattern, action in self.COMMANDS.items():
            if pattern in command_lower:
                return getattr(self, action)()
        return self.show_help()
```

### 5. Connect to Existing Repository Service
- Integrate with `src/elysiactl/services/repository.py`
- Load mock data initially, prepare for real data
- Handle loading states and error conditions

### 6. Add TUI Command to CLI
```python
# Update src/elysiactl/commands/repo.py
@app.command("tui")
def launch_tui():
    """Launch the interactive repository management TUI."""
    from ..tui.app import RepoManagerApp
    app = RepoManagerApp()
    app.run()
```

## 🎨 UI Design

### Layout Structure
```
┌─ Repository Health Dashboard ──────────────────────────────┐
│ 📊 Overall Status: ✓ 5/5 Healthy (100.0% success rate)     │
│ 🔄 Active Syncs: 0 (No active syncs)                      │
│ 📈 Total Repositories: 5                                   │
└─────────────────────────────────────────────────────────────┘

┌─ Repository Status ──────────────────────────────────────┤
│ Repository    │ Status    │ Last Sync │ Size             │
├───────────────┼───────────┼───────────┼──────────────────┤
│ api-gateway   │ ✓         │ Never     │ -                │
│ user-service  │ ✓         │ Never     │ -                │
│ auth-service  │ ✓         │ Never     │ -                │
└───────────────┴───────────┴───────────┴──────────────────┘

───────────────────────────────────────────────────────────────
💬 What would you like to do with your repositories? ──────────┐
│                                                              │
│ > show repos                                                 │
└───────────────────────────────────────────────────────────────
Command: [add-repo] [status] [list] [sync] [help] [quit] ──┐
Health: ✓ 5/5 repos | Queue: 0 pending | Next: -      │
───────────────────────────────────────────────────────────────
```

## ✅ Success Criteria

- [ ] TUI launches without errors
- [ ] Repository table displays mock data correctly
- [ ] Command prompt accepts input
- [ ] Basic commands ("show repos", "list") work
- [ ] Responsive layout adapts to terminal size
- [ ] Clean exit functionality works
- [ ] No crashes or hangs during normal operation

## 🔄 Next Steps

**After Phase 1 Completion:**
- Move this directory to `phases-done/`
- Begin Phase 2: Interactive Features & Filtering
- Connect to real repository data
- Implement natural language processing

## 📁 Files to Create/Modify

```
src/elysiactl/
├── tui/
│   ├── __init__.py
│   ├── app.py                 # Main TUI application
│   ├── command_processor.py   # Command processing logic
│   └── widgets/
│       ├── __init__.py
│       ├── repository_table.py
│       └── command_prompt.py
└── commands/
    └── repo.py                # Add TUI command
```

## 🧪 Testing Plan

- Unit tests for individual widgets
- Integration tests for command processing
- Manual testing of TUI interactions
- Cross-platform testing (Linux terminal, different sizes)