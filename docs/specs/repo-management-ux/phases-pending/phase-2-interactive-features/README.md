# Phase 2: Interactive Features & Filtering
**Status**: Planned
**Estimated Duration**: 2-3 days
**Prerequisites**: Phase 1 Complete
**Deliverable**: Conversational interface with natural language input

## 🎯 Objectives

Transform the basic TUI into an interactive, conversational experience:
- Open prompt area with natural language processing
- Smart pattern matching for repository commands
- Real-time filtering and search capabilities
- Integration with repository service for live data

## 📋 Implementation Steps

### 1. Enhance Command Processor
```python
# src/elysiactl/tui/command_processor.py
class AdvancedCommandProcessor:
    """Advanced command processing with pattern matching."""

    PATTERNS = {
        r"show.*repo": "show_repositories",
        r"list.*repo": "list_repositories",
        r"find.*fail": "show_failed_repositories",
        r"search.*python": "filter_python_repositories",
        r"show.*status": "show_repository_status",
    }

    def process_command(self, command: str):
        """Process natural language commands with regex matching."""
        import re

        command_lower = command.lower()
        for pattern, action in self.PATTERNS.items():
            if re.search(pattern, command_lower):
                params = self.extract_parameters(command)
                return getattr(self, action)(**params)

        return self.show_help()
```

### 2. Implement Parameter Extraction
```python
# src/elysiactl/tui/parameter_extraction.py
class ParameterExtractor:
    """Extract parameters from natural language commands."""

    def extract_status_filter(self, command: str) -> str:
        """Extract status filter from command (failed, success, etc.)."""
        if "fail" in command.lower():
            return "failed"
        elif "success" in command.lower():
            return "success"
        return None

    def extract_language_filter(self, command: str) -> str:
        """Extract programming language from command."""
        languages = ["python", "javascript", "java", "go", "rust"]
        for lang in languages:
            if lang in command.lower():
                return lang
        return None
```

### 3. Add Filtering Capabilities
```python
# src/elysiactl/tui/widgets/filtered_table.py
from textual.widgets import DataTable
from ...services.repository import repo_service

class FilteredRepositoryTable(DataTable):
    """Repository table with filtering capabilities."""

    def __init__(self):
        super().__init__()
        self.current_filter = {}

    def apply_filter(self, filter_type: str, value: str):
        """Apply a filter to the displayed repositories."""
        self.current_filter[filter_type] = value
        self.refresh_data()

    def refresh_data(self):
        """Refresh table data based on current filters."""
        repositories = repo_service.get_repositories_by_pattern("")

        # Apply filters
        if self.current_filter.get("status"):
            repositories = [r for r in repositories
                          if r.sync_status == self.current_filter["status"]]

        if self.current_filter.get("language"):
            repositories = [r for r in repositories
                          if self.current_filter["language"] in r.description.lower()]

        self.display_repositories(repositories)
```

### 4. Connect to Repository Service
- Replace mock data with real repository service calls
- Handle loading states and async operations
- Add error handling for service failures
- Implement data refresh capabilities

### 5. Add Real-time Feedback
```python
# src/elysiactl/tui/widgets/status_indicator.py
from textual.widgets import Static
from textual import reactive

class StatusIndicator(Static):
    """Real-time status indicator widget."""

    status_message = reactive("Ready")

    def watch_status_message(self, old_message: str, new_message: str):
        """Update display when status changes."""
        self.update(f"Status: {new_message}")
```

### 6. Implement Command History
```python
# src/elysiactl/tui/command_history.py
class CommandHistory:
    """Maintain command history for better UX."""

    def __init__(self, max_history=50):
        self.history = []
        self.max_history = max_history
        self.current_index = -1

    def add_command(self, command: str):
        """Add command to history."""
        self.history.append(command)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.current_index = len(self.history)

    def get_previous_command(self) -> str:
        """Get previous command in history."""
        if self.history and self.current_index > 0:
            self.current_index -= 1
            return self.history[self.current_index]
        return ""

    def get_next_command(self) -> str:
        """Get next command in history."""
        if self.history and self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        return ""
```

## 🎨 Enhanced UI Features

### Dynamic Filtering Interface
```
┌─ Filtered: Failed Repositories ──────────────────────────┐
│ 🔴 auth-service        │ Status: Failed │ Last: 3h ago   │
│ 🔴 legacy-api          │ Status: Failed │ Last: 6h ago   │
│ 🔴 deprecated-svc      │ Status: Failed │ Last: 12h ago  │
└──────────────────────────────────────────────────────────┘

💬 What would you like to do with your repositories? ────────┐
│ > show me python repositories                              │
│                                                           │
│ Previous commands:                                        │
│ > show failed repos                                       │
│ > list all repos                                           │
└────────────────────────────────────────────────────────────┘
```

## ✅ Success Criteria

- [ ] Natural language commands work ("show failed repos")
- [ ] Real-time filtering updates table display
- [ ] Command history navigation (up/down arrows)
- [ ] Integration with repository service
- [ ] Error handling for invalid commands
- [ ] Loading states during data operations
- [ ] Context-aware command suggestions

## 🔄 Integration Points

- Connects to `src/elysiactl/services/repository.py`
- Uses existing command infrastructure from Phase 1
- Prepares foundation for Phase 3 background sync
- Sets up patterns for Phase 4 MGit integration

## 📁 Files to Create/Modify

```
src/elysiactl/
├── tui/
│   ├── command_processor.py     # Enhanced with regex patterns
│   ├── parameter_extraction.py  # New: parameter parsing
│   └── widgets/
│       ├── filtered_table.py    # New: filtering capabilities
│       └── status_indicator.py  # New: real-time status
└── services/
    └── repository.py            # Enhance with filtering methods
```

## 🧪 Testing Plan

- Command parsing accuracy tests
- Filter application verification
- Real-time update testing
- Error condition handling
- Performance with large datasets