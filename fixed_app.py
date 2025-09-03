from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.scroll_view import ScrollView
from textual.widgets import Button, Static, Label, Input

class VisibleRowsApp(App):
    """An app to demonstrate how to get the visible rows of a ScrollView."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #my_scroll_view {
        width: 100%;
        height: 1fr;
        border: round green;
        background: $surface;
    }

    #info_label {
        margin-top: 1;
        content-align: center;
        width: 100%;
    }

    Input {
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Vertical():
            # A ScrollView with initial content
            yield ScrollView(
                Static("Welcome to the chat!\n"),
                id="my_scroll_view"
            )
            yield Label("Enter your message:", id="info_label")
            yield Input(placeholder="Type here...", id="message_input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the input submission event."""
        input_widget = self.query_one("#message_input", Input)
        scroll_view = self.query_one(ScrollView)
        static_content = self.query_one(Static)

        # Get the entered message
        message = event.value.strip()
        if message:
            # Append the new message to the existing content
            current_content = static_content.renderable.plain
            new_content = current_content + f"{message}\n"
            static_content.update(new_content)

            # Scroll to the bottom to show the new message
            scroll_view.scroll_end()

        # Clear the input for next message
        input_widget.value = ""


if __name__ == "__main__":
    app = VisibleRowsApp()
    app.run()