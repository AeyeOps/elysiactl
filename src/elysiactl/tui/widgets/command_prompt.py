"""Command prompt widget for natural language input."""

from textual import events
from textual.widgets import Input


class CommandPrompt(Input):
    """Natural language input widget for repository commands."""

    def __init__(self):
        super().__init__(
            id="command_prompt",
            placeholder="💬 Type 'help' or try 'list repos', 'show failed', 'status'...",
            type="text",
        )
        self.command_history = []
        self.history_index = -1
        self._multiline_buffer = ""  # Store multi-line content
        self._in_multiline_mode = False

    def _enter_multiline_mode(self):
        """Enter multi-line input mode."""
        self._in_multiline_mode = True
        self.placeholder = "📝 Multi-line mode - Shift+Enter/Ctrl+Enter/Alt+Enter for new line, Enter to submit, Esc to cancel"
        self.styles.background = "dark_blue"
        self.refresh()

    def _exit_multiline_mode(self):
        """Exit multi-line input mode."""
        self._in_multiline_mode = False
        self._multiline_buffer = ""
        self.placeholder = "💬 Type 'help' or try 'list repos', 'show failed', 'status'..."
        self.styles.background = None
        self.refresh()

    def get_multiline_preview(self) -> str:
        """Get a preview of the current multi-line content."""
        if not self._in_multiline_mode:
            return ""

        lines = self._multiline_buffer.split("\n") if self._multiline_buffer else []
        if self.value:
            lines.append(self.value)

        preview = "\n".join(f"{i + 1:2d}: {line}" for i, line in enumerate(lines))
        return f"Multi-line input ({len(lines)} lines):\n{preview}"

    def on_mount(self) -> None:
        """Set up the command prompt when mounted."""
        self.focus()

    def on_key(self, event) -> None:
        """Handle key events for command history navigation and multi-line input."""
        # Handle special cases for multi-line input
        if event.key == "enter" or event.key == "return":
            # For now, just handle regular enter - we'll implement multi-line later
            self._handle_regular_enter()
            event.prevent_default()
            return

        # Handle other keys...
        if event.key == "up":
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                self.value = self.command_history[self.history_index]
            event.prevent_default()

        elif event.key == "down":
            if self.command_history and self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.value = self.command_history[self.history_index]
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.value = ""
            event.prevent_default()

        elif event.key == "escape":
            # Cancel multi-line mode if active
            if self._in_multiline_mode:
                self._exit_multiline_mode()
                event.prevent_default()
            else:
                # Clear current input
                self.value = ""
                event.prevent_default()

    def _handle_multiline_enter(self):
        """Handle Shift+Enter, Ctrl+Enter, Alt+Enter for multi-line input."""
        # For now, treat as regular enter
        self._handle_regular_enter()

    def _enter_multiline_mode(self):
        """Enter multi-line input mode."""
        self._in_multiline_mode = True
        self.placeholder = "Multi-line mode (Esc to cancel, Enter to submit)"

    def _exit_multiline_mode(self):
        """Exit multi-line input mode."""
        self._in_multiline_mode = False
        self.placeholder = "Type a command..."
        self._multiline_buffer = ""

    def _handle_regular_enter(self):
        """Handle regular Enter key for command submission."""
        command = self.value.strip()
        if command:
            # Add to history
            self.command_history.append(command)
            self.history_index = len(self.command_history)

            # Clear the input
            self.value = ""

            # Notify parent app of the command
            self.post_message(self.CommandSubmitted(self, command))

    class CommandSubmitted(events.Message):
        """Message sent when a command is submitted."""

        def __init__(self, sender: "CommandPrompt", command: str):
            super().__init__()
            self.sender = sender
            self.command = command
