"""Simplified scrolling widget using Textual's VerticalScroll container."""

from datetime import datetime

from textual.containers import VerticalScroll
from textual.widgets import Static

from ...services.repository import Repository
from .repository_table import RepositoryTable


class ConversationView(VerticalScroll):
    """A scrollable conversation view using Textual's VerticalScroll container."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository_table: RepositoryTable | None = None

    def on_mount(self) -> None:
        """Initialize the scrollable view."""
        self.call_later(self._initialize_view)

    def _initialize_view(self) -> None:
        """Initialize the view with top spacers for receipt printer effect."""
        try:
            # Get terminal size to determine how many spacer lines to add
            import shutil
            terminal_size = shutil.get_terminal_size()

            # Calculate available height (subtract header, footer, and command prompt area)
            # Header is 3 lines, footer is 4 lines, command prompt area is about 2 lines
            available_height = max(10, terminal_size.lines - 9)  # Minimum 10 lines

            # Add spacer lines at the top to push initial content to the bottom
            # This creates the receipt printer effect
            for _ in range(available_height):
                self.mount(Static("", classes="receipt-spacer"))

            # Now add the welcome message - it will appear at the bottom
            self.add_ai_response("Welcome to elysiactl TUI\nType 'help' for available commands")

            # Scroll to bottom to show the welcome message
            self.scroll_end(animate=False)
        except (AttributeError, ValueError):
            self.add_ai_response("Welcome to elysiactl TUI")

    def add_text_message(self, text: str, sender: str) -> None:
        """Add a text message to the conversation with receipt printer effect."""
        prefix_map = {"user": "user-prefix", "system": "system-prefix", "ai": "ai-prefix"}
        prefix_class = prefix_map.get(sender, "system-prefix")
        timestamp = datetime.now().strftime("%H:%M:%S")

        message = Static(
            f"[{prefix_class}]│[/] [message-timestamp]{timestamp}[/] {text}",
            classes="conversation-item",
        )

        # Insert new message BEFORE existing content (receipt printer effect)
        # This makes new content appear at the bottom and push older content up
        if self.children:
            self.mount(message, before=self.children[0])
        else:
            self.mount(message)

        # Scroll to show the new message at the bottom
        self.scroll_end(animate=True, duration=0.1)

    def add_ai_response(self, response: str) -> None:
        """Add an AI response to the conversation."""
        self.add_text_message(response, "ai")

    def add_repository_table(
        self, repositories: list[Repository], selectable: bool = False
    ) -> None:
        """Add a repository table to the conversation with receipt printer effect."""
        if self.repository_table:
            self.repository_table.remove()

        self.repository_table = RepositoryTable()

        # Insert table BEFORE existing content (receipt printer effect)
        if self.children:
            self.mount(self.repository_table, before=self.children[0])
        else:
            self.mount(self.repository_table)

        self.repository_table.display_repositories(repositories)
        # Scroll to show the new table at the bottom
        self.scroll_end(animate=True, duration=0.1)

    def add_separator(self) -> None:
        """Add a separator line with receipt printer effect."""
        separator = Static("─" * self.size.width, classes="separator-line")

        # Insert separator BEFORE existing content (receipt printer effect)
        if self.children:
            self.mount(separator, before=self.children[0])
        else:
            self.mount(separator)

        # Scroll to show the separator at the bottom
        self.scroll_end(animate=True, duration=0.1)
