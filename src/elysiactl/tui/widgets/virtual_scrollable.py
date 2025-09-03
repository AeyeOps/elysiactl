"""Simplified scrolling widget using Textual's native ScrollView."""

from datetime import datetime
from typing import Any, List, Dict, Optional
from textual.containers import ScrollableContainer
from textual.widgets import Static
from textual import events
from textual.strip import Segment, Strip

from ...services.repository import Repository


class ConversationItem:
    """Represents a single item in the conversation."""

    def __init__(self, item_type: str, content: Any, metadata: Optional[Dict[str, Any]] = None):
        self.item_type = item_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.id = f"{item_type}_{self.timestamp.timestamp()}"

    def render(self) -> str:
        """Render the item as a string for display."""
        if self.item_type == "text":
            sender = self.metadata.get("sender", "user")
            prefix = "│ " if sender == "user" else "│ "
            timestamp = f"[{self.timestamp.strftime('%H:%M:%S')}] "
            return f"{prefix}{timestamp}{self.content}"

        elif self.item_type == "ai_response":
            prefix = "│ "
            timestamp = f"[{self.timestamp.strftime('%H:%M:%S')}] "
            return f"{prefix}{timestamp}{self.content}"

        elif self.item_type == "system_message":
            prefix = "│ "
            timestamp = f"[{self.timestamp.strftime('%H:%M:%S')}] "
            return f"{prefix}{timestamp}{self.content}"

        elif self.item_type == "table":
            lines = []
            lines.append(f"📊 {self.content.get('title', 'Table')}")
            lines.append("─" * 70)
            for row in self.content.get("data", []):
                row_text = " | ".join(f"{k}: {v}" for k, v in row.items())
                lines.append(f"  {row_text}")
            if self.content.get("actions"):
                actions_text = " | ".join(f"[{action}]" for action in self.content["actions"])
                lines.append(f"  Actions: {actions_text}")
            return "\n".join(lines)

        elif self.item_type == "repo_table":
            lines = []
            lines.append("📂 Repositories")
            lines.append("  Repository       | Status  | Last Sync    | Project")
            for repo in self.content:
                status_emoji = {"success": "✅", "failed": "❌", "syncing": "🔄"}.get(
                    repo.sync_status, "❓"
                )
                last_sync = repo.last_sync.strftime("%m-%d %H:%M") if repo.last_sync else "Never"
                repo_name = (repo.repository[:15] + "..." if len(repo.repository) > 15 else repo.repository)
                project_name = repo.project[:12] + "..." if len(repo.project) > 12 else repo.project
                row = f"  {repo_name:<17} | {status_emoji:<7} | {last_sync:<12} | {project_name}"
                lines.append(row)
            return "\n".join(lines)

        elif self.item_type == "startup_line":
            # Startup lines don't have prefix or timestamp for clean graphic
            return self.content

        elif self.item_type == "intro_line":
            # Intro lines have minimal formatting
            return f"│ {self.content}"

        elif self.item_type == "spacer":
            # Return a blank line that will be visible
            return " "
class ConversationView(ScrollableContainer):
    """A scrollable conversation view using Textual's native scrolling."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.items: List[ConversationItem] = []
        self.auto_scroll = True
        self.content_container = None

    def compose(self):
        """Compose the conversation view."""
        self.content_container = Static("", id="conversation-content")
        yield self.content_container

    def start_startup_animation(self) -> None:
        """Start the animated startup sequence filling from bottom upward."""
        # Clear any existing content
        self.items = []

        # Pre-fill with empty lines to create scrollable content
        # This ensures the container can scroll and new lines appear at bottom
        empty_lines = 80  # Fixed number of lines for consistent animation
        for _ in range(empty_lines):
            self.items.append(ConversationItem("spacer", ""))

        # Startup graphic lines
        self.startup_lines = [
            "┌─────────────────────────────────────────────────────────────────┐",
            "│                                                                 │",
            "│                    Welcome to elysiactl                         │",
            "│                                                                 │",
            "│                                                                 │",
            "│                Control Center for Elysia AI                     │",
            "│                                                                 │",
            "│                                                                 │",
            "│                                                                 │",
            "│  ┌─ Commands ──────────────────────────────────────────────┐    │",
            "│  │  • start    - Launch Elysia and Weaviate services       │    │",
            "│  │  • stop     - Gracefully stop all services              │    │",
            "│  │  • status   - Show service health and status            │    │",
            "│  │  • health   - Detailed health checks                    │    │",
            "│  │  • restart  - Stop and restart services                 │    │",
            "│  └─────────────────────────────────────────────────────────┘    │",
            "│                                                                 │",
            "│                                                                 │",
            "│                                                                 │",
            "│                Type 'help' for all commands                     │",
            "│                                                                 │",
            "└─────────────────────────────────────────────────────────────────┘",
        ]

        # Additional intro lines
        self.intro_lines = [
            "",
            "",
            "Tip: Use arrow keys to scroll through history",
            "",
            "",
            "Auto-scroll is enabled - content will follow new messages",
            "",
            "",
            "",
            "",
            "",
            "",
            "Ready to manage your Elysia AI services!",
            "",
            ""
        ]

        # Start the animation
        self.startup_index = 0
        # Initial setup with spacers to establish scroll position
        self._update_display()
        self.scroll_to_bottom()  # Position at bottom before animation
        self.set_timer(0.1, self._animate_next_line)  # Faster initial delay

    def _animate_next_line(self) -> None:
        """Animate the next line in the startup sequence."""
        if self.startup_index < len(self.startup_lines):
            # Add the next startup line
            line = self.startup_lines[self.startup_index]
            # Create a temporary item for animation
            temp_item = ConversationItem("startup_line", line)
            self.items.append(temp_item)
            self._update_display()

            # Scroll to show the new line (it will appear at bottom)
            self.scroll_to_bottom()

            self.startup_index += 1

            # Schedule next line after a delay
            self.set_timer(0.025, self._animate_next_line)  # Faster delay between lines

        elif hasattr(self, 'intro_lines') and self.intro_lines:
            # Startup graphic complete, add intro lines
            self._add_intro_lines()

    def scroll_to_bottom_smooth(self) -> None:
        """Enhanced scroll to bottom with animation."""
        self.scroll_end(animate=True)

    def _add_intro_lines(self) -> None:
        """Add the final intro lines after startup graphic."""
        for line in self.intro_lines:
            # Include empty lines as actual blank lines in the display
            temp_item = ConversationItem("intro_line", line)
            self.items.append(temp_item)

        # Clear the temporary attributes
        if hasattr(self, 'startup_lines'):
            delattr(self, 'startup_lines')
        if hasattr(self, 'intro_lines'):
            delattr(self, 'intro_lines')
        if hasattr(self, 'startup_index'):
            delattr(self, 'startup_index')

        self._update_display()
        self.scroll_to_bottom()

    def _show_welcome_message(self) -> None:
        """Legacy method - now handled by startup animation."""
        pass

    def add_user_message(self, message: str) -> None:
        """Add a user message to the conversation."""
        item = ConversationItem("text", message, {"sender": "user"})
        self.items.append(item)
        self._update_display()
        if self.auto_scroll:
            self.scroll_to_bottom()

    def add_assistant_response(self, response: str) -> None:
        """Add an assistant response to the conversation."""
        item = ConversationItem("ai_response", response)
        self.items.append(item)
        self._update_display()
        if self.auto_scroll:
            self.scroll_to_bottom()

    def add_blank_line(self) -> None:
        """Add a visible blank line to the conversation."""
        item = ConversationItem("spacer", " ")
        self.items.append(item)
        self._update_display()
        if self.auto_scroll:
            self.scroll_to_bottom()

    def add_system_message(self, message: str) -> None:
        """Add a system message to the conversation."""
        item = ConversationItem("system_message", message)
        self.items.append(item)
        self._update_display()
        if self.auto_scroll:
            self.scroll_to_bottom()

    def add_interactive_table(self, title: str, data: List[Dict], actions: Optional[List[str]] = None) -> None:
        """Add an interactive table to the conversation."""
        content = {"title": title, "data": data, "actions": actions}
        item = ConversationItem("table", content)
        self.items.append(item)
        self._update_display()
        if self.auto_scroll:
            self.scroll_to_bottom()

    def add_repository_table(self, repositories: List[Repository]) -> None:
        """Add a repository table to the conversation."""
        item = ConversationItem("repo_table", repositories)
        self.items.append(item)
        self._update_display()
        if self.auto_scroll:
            self.scroll_to_bottom()

    def _update_display(self) -> None:
        """Update the displayed content."""
        if not self.items:
            # Don't show anything when empty during startup animation
            content = ""
        else:
            rendered_items = []
            for item in self.items:
                rendered_items.append(item.render())
            content = "\n".join(rendered_items)

        self.content_container.update(content)

    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the conversation."""
        self.scroll_end(animate=True)

    def scroll_to_top(self) -> None:
        """Scroll to the top of the conversation."""
        self.scroll_home(animate=True)

    def toggle_auto_scroll(self) -> None:
        """Toggle auto-scroll behavior."""
        self.auto_scroll = not self.auto_scroll
        self.notify(f"Auto-scroll {'enabled' if self.auto_scroll else 'disabled'}")

    # Legacy API compatibility
    def add_text_message(self, text: str, sender: str = "user", timestamp: datetime = None) -> None:
        """Legacy method for backward compatibility."""
        if sender == "user":
            self.add_user_message(text)
        else:
            self.add_system_message(text)

    def add_ai_response(self, response: str, widget_data: dict = None) -> None:
        """Legacy method for backward compatibility."""
        self.add_assistant_response(response)

    # Event handlers for custom behavior
    def on_key(self, event: events.Key) -> None:
        """Handle keyboard events."""
        if event.key == "a":
            self.toggle_auto_scroll()
            event.prevent_default()
        elif event.key == "ctrl+end":
            self.scroll_to_bottom()
            event.prevent_default()
        elif event.key == "home":
            self.scroll_to_top()
            event.prevent_default()
        # Let ScrollableContainer handle other scrolling keys (up, down, pageup, pagedown, etc.)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        """Handle mouse scroll down."""
        # Disable auto-scroll when user manually scrolls
        self.auto_scroll = False
        # Let parent handle the scroll

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        """Handle mouse scroll up."""
        # Disable auto-scroll when user manually scrolls
        self.auto_scroll = False
        # Let parent handle the scroll


# For backwards compatibility, keep the old class name
VirtualScrollableWidget = ConversationView

# Legacy message classes for compatibility
class TableRowSelected(events.Message):
    """Message sent when a table row is selected."""

    def __init__(self, table_index: int, row_index: int, row_data: dict):
        super().__init__()
        self.table_index = table_index
        self.row_index = row_index
        self.row_data = row_data


class TableActionSelected(events.Message):
    """Message sent when a table action is selected."""

    def __init__(self, table_index: int, actions: list[str]):
        super().__init__()
        self.table_index = table_index
        self.actions = actions