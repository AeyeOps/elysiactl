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

    def on_mount(self) -> None:
        """Set up the command prompt when mounted."""
        self.focus()
        # Set placeholder text after mounting
        if hasattr(self, 'placeholder'):
            self.placeholder = "💬 Type 'help' or try 'list repos', 'show failed', 'status'..."

    async def on_key(self, event) -> None:
        """Handle key events for command history navigation."""
        if event.key == "up":
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                self.text = self.command_history[self.history_index]
            event.prevent_default()

        elif event.key == "down":
            if self.command_history and self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.text = self.command_history[self.history_index]
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.text = ""
            event.prevent_default()

        elif event.key == "enter":
            # Handle Enter key for command submission
            command = self.text.strip()
            if command:
                # Add to history
                self.command_history.append(command)
                self.history_index = len(self.command_history)

                # Clear the input
                self.text = ""

                # Notify parent app of the command
                self.post_message(self.CommandSubmitted(self, command))
            event.prevent_default()

    class CommandSubmitted(events.Message):
        """Message sent when a command is submitted."""

        def __init__(self, sender: "CommandPrompt", command: str):
            super().__init__()
            self.sender = sender
            self.command = command