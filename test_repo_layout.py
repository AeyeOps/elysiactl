#!/usr/bin/env python3

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, DataTable, Input, Static
from textual import reactive

class RepositoryManagerApp(App):
    """Repository management TUI with visual layout for browser testing."""

    CSS = """
    Screen { background: $surface; color: $text; }

    #main_layout {
        layout: grid;
        grid-size: 1 3;
        grid-rows: auto 1fr auto;
        height: 100%;
    }

    Header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        border-bottom: solid $accent;
    }

    #repo_table {
        height: 60%;
        border: solid $accent;
        margin: 1;
    }

    #command_input {
        dock: bottom;
        height: 3;
        margin: 1;
        border: solid $accent;
    }

    Footer {
        dock: bottom;
        height: 2;
        background: $primary;
        color: $text;
        border-top: solid $accent;
    }

    #status_panel {
        height: 10%;
        background: $secondary;
        color: $text;
        border: solid $accent;
        margin: 1;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="repo_table")
        yield Static("Status: Ready | Repositories: 0 | Queue: 0", id="status_panel")
        yield Input(placeholder="💬 What would you like to do?", id="command_input")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the repository table."""
        table = self.query_one("#repo_table", DataTable)
        table.add_columns("Repository", "Docs", "Last Sync", "Status")
        table.add_row("textualize/textual", "1,234", "2 min ago", "✅ Synced")
        table.add_row("textualize/rich", "5,678", "5 min ago", "🔄 Syncing")
        table.add_row("tiangolo/typer", "9,012", "1 hour ago", "❌ Failed")

if __name__ == "__main__":
    app = RepositoryManagerApp()
    app.run()