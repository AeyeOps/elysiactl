"""Command prompt widget for natural language input."""

from textual.widgets import TextArea
from textual import events

class CommandPrompt(TextArea):
    """Natural language input widget for repository commands."""

    def __init__(self):
        super().__init__(
            id="command_prompt",
            language="text"
        )
        self.command_history = []
        self.history_index = -1
        self.placeholder_text = "💬 Type 'help' or try 'list repos', 'show failed', 'status'..."
        self.showing_placeholder = False

    def on_mount(self) -> None:
        """Set up the command prompt when mounted."""
        self.focus()
        self._show_placeholder()

    def _show_placeholder(self):
        """Show the placeholder text in subtle gray."""
        if not self.text:
            self.text = self.placeholder_text
            self.showing_placeholder = True
            # Add CSS class for placeholder styling
            self.add_class("placeholder")

    def _hide_placeholder(self):
        """Hide the placeholder when user starts typing."""
        if self.showing_placeholder:
            self.text = ""
            self.showing_placeholder = False
            # Remove CSS class
            self.remove_class("placeholder")

    async def on_key(self, event) -> None:
        """Handle key events for command history navigation."""
        
        # Handle typing (any printable character that would add to text)
        # Check if it's a single character (printable) and not a special key combo
        if (len(event.key) == 1 and 
            event.key not in ["\t", "\n", "\r"] and 
            not event.key.startswith("ctrl+") and
            not event.key.startswith("alt+") and
            not event.key.startswith("shift+") and
            not event.key.startswith("meta+")):
            if self.showing_placeholder:
                self._hide_placeholder()
        
        # Handle special keys
        if event.key == "up":
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                self._hide_placeholder()
                self.text = self.command_history[self.history_index]
            event.prevent_default()

        elif event.key == "down":
            if self.command_history and self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self._hide_placeholder()
                self.text = self.command_history[self.history_index]
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self._show_placeholder()
            event.prevent_default()

        elif event.key == "enter":
            # Handle Enter key for command submission
            if self.showing_placeholder:
                # Don't submit placeholder
                event.prevent_default()
                return
                
            command = self.text.strip()
            if command:
                # Add to history
                self.command_history.append(command)
                self.history_index = len(self.command_history)

                # Clear the input and show placeholder
                self._show_placeholder()

                # Notify parent app of the command
                self.post_message(self.CommandSubmitted(self, command))
            event.prevent_default()

        elif event.key == "escape":
            # Clear input and show placeholder
            self._show_placeholder()
            event.prevent_default()

    class CommandSubmitted(events.Message):
        """Message sent when a command is submitted."""

        def __init__(self, sender: "CommandPrompt", command: str):
            super().__init__()
            self.sender = sender
            self.command = command
