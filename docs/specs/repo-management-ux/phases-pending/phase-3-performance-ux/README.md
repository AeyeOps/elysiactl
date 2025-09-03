# Phase 3: Performance & Advanced UX
**Status**: Planned
**Estimated Duration**: 3-4 days
**Prerequisites**: Phase 1 & 2 Complete
**Deliverable**: High-performance TUI with virtual scrolling and background sync

## 🎯 Objectives

Scale the TUI to production levels with:
- Virtual scrolling for hundreds of repositories
- Background sync capabilities with progress tracking
- Real-time status updates and reactive UI
- Performance optimizations for large datasets
- Advanced footer with health metrics

## 📋 Implementation Steps

### 1. Implement Virtual Scrolling
```python
# src/elysiactl/tui/widgets/virtual_table.py
from textual.widgets import DataTable
from textual.containers import ScrollView

class VirtualRepositoryTable(DataTable):
    """High-performance table with virtual scrolling."""

    def __init__(self, total_repos: int = 0):
        super().__init__()
        self.total_repositories = total_repos
        self.loaded_repositories = []
        self.page_size = 50
        self.current_page = 0

    def load_page(self, page: int):
        """Load a specific page of repositories."""
        start_idx = page * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_repositories)

        # Load repositories for this page
        page_repos = self.fetch_repositories(start_idx, end_idx)

        # Update display
        self.clear()
        for repo in page_repos:
            self.add_row(repo.name, repo.status, repo.last_sync)

    def on_scroll(self, event):
        """Handle scroll events to load more data."""
        if self.needs_more_data(event):
            self.load_next_page()

    def fetch_repositories(self, start: int, end: int):
        """Fetch repositories for the given range."""
        # Implementation to fetch data efficiently
        pass
```

### 2. Add Background Sync with Progress
```python
# src/elysiactl/tui/sync_manager.py
from textual import work
from textual.widgets import ProgressBar
import asyncio

class SyncManager:
    """Manage background repository synchronization."""

    def __init__(self, app):
        self.app = app
        self.sync_queue = asyncio.Queue()
        self.active_syncs = {}

    @work(thread=True)
    def start_sync(self, repositories: list):
        """Start background sync for repositories."""
        for repo in repositories:
            self.sync_queue.put_nowait(repo)

        # Start worker tasks
        for i in range(min(4, len(repositories))):  # Max 4 concurrent
            asyncio.create_task(self.sync_worker())

    async def sync_worker(self):
        """Worker to process sync queue."""
        while not self.sync_queue.empty():
            repo = await self.sync_queue.get()
            await self.sync_repository(repo)
            self.sync_queue.task_done()

    async def sync_repository(self, repo):
        """Sync individual repository with progress updates."""
        self.active_syncs[repo.name] = "syncing"

        # Update UI
        self.app.update_repo_status(repo.name, "syncing")

        try:
            # Actual sync logic here
            await self.perform_sync(repo)
            self.app.update_repo_status(repo.name, "success")
        except Exception as e:
            self.app.update_repo_status(repo.name, "failed")

        del self.active_syncs[repo.name]
```

### 3. Implement Reactive Status Updates
```python
# src/elysiactl/tui/widgets/live_status.py
from textual.widget import Widget
from textual import reactive
from textual.containers import Container
from textual.widgets import Label

class LiveStatusWidget(Container):
    """Live status dashboard with reactive updates."""

    total_repos = reactive(0)
    healthy_count = reactive(0)
    syncing_count = reactive(0)
    failed_count = reactive(0)

    def compose(self):
        yield Label(id="status_summary")
        yield Label(id="sync_progress")

    def watch_total_repos(self):
        """Update when total repo count changes."""
        self.update_summary()

    def watch_healthy_count(self):
        """Update when healthy count changes."""
        self.update_summary()

    def update_summary(self):
        """Update the status summary display."""
        summary = f"📊 Status: {self.healthy_count}/{self.total_repos} Healthy"
        self.query_one("#status_summary", Label).update(summary)

    def update_sync_progress(self):
        """Update sync progress display."""
        if self.syncing_count > 0:
            progress = f"🔄 Active syncs: {self.syncing_count}"
        else:
            progress = "✅ All repositories synced"
        self.query_one("#sync_progress", Label).update(progress)
```

### 4. Add Footer with Health Metrics
```python
# src/elysiactl/tui/widgets/enhanced_footer.py
from textual.widgets import Footer

class EnhancedFooter(Footer):
    """Enhanced footer with health metrics and command hints."""

    def __init__(self):
        super().__init__()
        self.health_status = "checking"
        self.queue_size = 0
        self.next_sync = None

    def update_health_status(self, status: str):
        """Update health status display."""
        self.health_status = status
        self.refresh()

    def update_queue_info(self, queue_size: int, next_sync: str = None):
        """Update queue information."""
        self.queue_size = queue_size
        self.next_sync = next_sync or "-"
        self.refresh()

    def render(self):
        """Render enhanced footer with metrics."""
        health_icon = {
            "healthy": "✅",
            "warning": "⚠️",
            "error": "❌",
            "checking": "🔄"
        }.get(self.health_status, "❓")

        return f"{health_icon} Health: {self.health_status} | Queue: {self.queue_size} pending | Next: {self.next_sync}"
```

### 5. Performance Optimizations
```python
# src/elysiactl/tui/performance_optimizer.py
class PerformanceOptimizer:
    """Optimize TUI performance for large datasets."""

    def __init__(self, app):
        self.app = app
        self.cache = {}
        self.debounce_timer = None

    def debounce_update(self, func, delay=0.3):
        """Debounce rapid updates to prevent UI thrashing."""
        if self.debounce_timer:
            self.debounce_timer.cancel()

        async def delayed_update():
            await asyncio.sleep(delay)
            await func()

        self.debounce_timer = asyncio.create_task(delayed_update())

    def cache_repository_data(self, key: str, data):
        """Cache repository data to reduce API calls."""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': 300  # 5 minutes
        }

    def get_cached_data(self, key: str):
        """Get cached data if still valid."""
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached['timestamp'] < cached['ttl']:
                return cached['data']
            else:
                del self.cache[key]
        return None
```

### 6. Add Keyboard Shortcuts
```python
# src/elysiactl/tui/app.py (enhanced)
class RepoManagerApp(App):
    """Enhanced repository management app with keyboard shortcuts."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh data"),
        ("f", "focus_prompt", "Focus command prompt"),
        ("?", "show_help", "Show help"),
        ("ctrl+r", "force_refresh", "Force refresh all data"),
    ]

    def action_refresh(self):
        """Refresh repository data."""
        self.load_repositories()

    def action_focus_prompt(self):
        """Focus the command prompt."""
        prompt = self.query_one(CommandPrompt)
        prompt.focus()

    def action_show_help(self):
        """Show help overlay."""
        self.show_help_overlay()
```

## 🎨 Advanced UI Features

### Virtual Scrolling with Progress Indicators
```
┌─ Repository Status (1,247 repos) ────────────────────────┤
│ Repository          │ Status    │ Last Sync │ Progress   │
├─────────────────────┼───────────┼───────────┼────────────┤
│ api-gateway         │ ✓         │ 5m ago   │ 100%       │
│ user-service        │ 🔄        │ syncing  │ ▓▓▓▓▓▓░░░ │
│ auth-service        │ ✓         │ 3h ago   │ 100%       │
│ data-pipeline       │ ⚠️        │ failed   │ 0%         │
│ [Showing 1-50 of 1,247 - Scroll for more]             │
└─────────────────────────────────────────────────────────┘
```

### Enhanced Footer with Metrics
```
Command: [add-repo] [status] [list] [sync] [help] [quit] ──┐
Health: ✅ 1,243/1,247 repos | Queue: 2 pending | Next: 2m │
Active: 🔄 2 syncing | Failed: ⚠️ 2 | Updated: 5m ago   │
────────────────────────────────────────────────────────────
```

## ✅ Success Criteria

- [ ] Handles 1,000+ repositories without performance issues
- [ ] Virtual scrolling loads data on demand
- [ ] Background sync with real-time progress updates
- [ ] Reactive UI updates without blocking
- [ ] Keyboard shortcuts for power users
- [ ] Comprehensive health metrics in footer
- [ ] Debounced updates prevent UI thrashing
- [ ] Efficient caching reduces API calls

## 🔄 Integration Points

- Extends Phase 2 filtering with performance optimizations
- Prepares for Phase 4 MGit real-time data integration
- Uses existing repository service architecture
- Maintains compatibility with Phase 1 UI structure

## 📁 Files to Create/Modify

```
src/elysiactl/
├── tui/
│   ├── sync_manager.py          # New: background sync management
│   ├── performance_optimizer.py # New: performance optimizations
│   └── widgets/
│       ├── virtual_table.py     # New: virtual scrolling table
│       ├── live_status.py       # New: reactive status widget
│       └── enhanced_footer.py   # New: metrics-rich footer
└── services/
    └── repository.py            # Add performance optimizations
```

## 🧪 Testing Plan

- Performance testing with 10,000+ repositories
- Memory usage monitoring during virtual scrolling
- Background sync reliability testing
- Keyboard shortcut functionality verification
- Real-time update accuracy testing
- Error recovery and edge case handling