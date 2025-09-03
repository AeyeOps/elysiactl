"""Main Textual application for repository management."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button
from textual.containers import Container, Vertical
from textual import events
from textual.theme import Theme
from typing import Dict, Any
from .widgets.repository_table import RepositoryTable
from .widgets.command_prompt import CommandPrompt
from .command_processor import CommandProcessor

class RepoManagerApp(App):
    """Main repository management TUI application."""

    def __init__(self, theme_name: str = "default"):
        # Register custom themes with Textual
        self._register_themes()
        super().__init__()

    def _register_themes(self):
        """Register custom themes with Textual's theme system."""
        # Default theme - Professional dark with gold/coral accents
        default_theme = Theme(
            name="default",
            primary="#00d4ff",      # Bright cyan
            secondary="#8b5cf6",    # Purple accent
            accent="#ff6b6b",       # Coral red
            foreground="#ffffff",   # Pure white text
            background="#1a1a2e",   # Dark blue-gray (lighter than before)
            surface="#2a2a4e",      # Medium blue-gray surface
            success="#00ff88",      # Bright green
            warning="#ffa500",      # Orange
            error="#ff4757",        # Red
            panel="#475569",        # Dark slate
        )

        # Light theme - Professional light theme
        light_theme = Theme(
            name="light",
            primary="#0366d6",      # Professional blue
            secondary="#586069",    # Muted gray
            accent="#28a745",       # Success green
            foreground="#24292e",   # Dark gray text
            background="#ffffff",   # Pure white background
            surface="#f8f9fa",      # Light gray surface
            success="#28a745",      # Consistent green
            warning="#ffd33d",      # Warm yellow
            error="#d73a49",        # Muted red
            panel="#e1e4e8",        # Subtle borders
        )

        # Professional theme - Corporate colors
        professional_theme = Theme(
            name="professional",
            primary="#3b82f6",      # Professional blue
            secondary="#64748b",    # Muted blue-gray
            accent="#10b981",       # Professional teal
            foreground="#f1f5f9",   # Off-white text
            background="#0f172a",   # Dark slate background
            surface="#1e293b",      # Darker slate surface
            success="#10b981",      # Consistent success
            warning="#f59e0b",      # Professional warning
            error="#ef4444",        # Clean error red
            panel="#334155",        # Subtle border gray
        )

        # Minimal theme - Clean monochrome
        minimal_theme = Theme(
            name="minimal",
            primary="#ffffff",      # Pure white
            secondary="#666666",    # Medium gray
            accent="#ffffff",       # White accent
            foreground="#ffffff",   # White text
            background="#000000",   # Pure black
            surface="#111111",      # Very dark gray
            success="#00ff00",      # Bright green
            warning="#ffff00",      # Yellow
            error="#ff0000",        # Red
            panel="#333333",        # Dark gray
        )

        # Register all themes
        self.register_theme(default_theme)
        self.register_theme(light_theme)
        self.register_theme(professional_theme)
        self.register_theme(minimal_theme)

    @property
    def CSS(self):
        """CSS that uses Textual's built-in theme variables."""

        return """
        Screen {
            background: $background;
            color: $foreground;
        }

        Header {
            background: $primary;
            color: $foreground;
            text-align: center;
            height: 3;
        }

        Footer {
            height: 4;
            width: 1fr;
            background: $primary;
            color: $foreground;
            padding: 0 2;
        }

        CommandPrompt {
            height: 2;
            padding: 0 1 0 2;
            background: $surface;
            color: $foreground;
        }

        #bottom_section {
            dock: bottom;
            height: 7;
            width: 100%;
        }

        #main-container {
            height: 1fr;
        }

        #repository_table {
            height: 1fr;
            border: solid $panel;
            background: $surface;
            color: $foreground;
        }

        #results_scroll {
            height: 30%;
            border: solid $accent;
            background: $surface;
            color: $foreground;
            scrollbar-size: 1 1;
        }

        /* Status-specific styling */
        .status-success {
            color: $success;
        }

        .status-failed {
            color: $error;
        }

        .status-syncing {
            color: $warning;
        }
        """

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()

        # Main content area with two scrollable panes
        with Vertical(id="main-container"):
            self.repo_table = RepositoryTable(id="repository_table")
            yield self.repo_table

            from textual.containers import ScrollableContainer
            self.results_scroll = ScrollableContainer(id="results_scroll")
            yield self.results_scroll

        # Bottom section for input and footer
        with Vertical(id="bottom_section"):
            self.command_prompt = CommandPrompt()
            yield self.command_prompt
            yield Footer()

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("Q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("?", "show_help", "Help"),
        ("t", "cycle_theme", "Theme"),
        ("l", "list_repos", "List"),
        ("s", "show_status", "Status"),
        ("f", "show_failed", "Failed"),
        ("ctrl+g", "show_more", "More"),
    ]

    def __init__(self, theme_name: str = "default"):
        super().__init__()
        # Register custom themes with Textual after super().__init__()
        self._register_themes()
        self.command_processor = CommandProcessor()
        self.repo_table = None
        self._available_themes = ["default", "light", "professional", "minimal"]
        self.current_theme_index = self._available_themes.index(theme_name) if theme_name in self._available_themes else 0

        # Set initial theme
        self.theme = theme_name

    def on_mount(self) -> None:
        """Initialize the application when mounted."""
        # Ensure theme is applied properly
        if hasattr(self, 'theme') and self.theme:
            pass  # Theme should already be set
        else:
            self.theme = "default"  # Fallback

        # Focus the command prompt after a short delay to ensure it's ready
        self.set_timer(0.1, lambda: self.command_prompt.focus() if self.command_prompt else None)

    # def update_footer(self) -> None:
    #     """Update footer with current status information."""
    #     repo_count = self.repo_table.get_repository_count() if self.repo_table else 0
    #     status_counts = self.repo_table.get_status_counts() if self.repo_table else {}

    #     footer_content = (
    #         f"📊 {repo_count} repos | "
    #         f"✅ {status_counts.get('success', 0)} | "
    #         f"❌ {status_counts.get('failed', 0)} | "
    #         f"🔄 {status_counts.get('syncing', 0)} | "
    #         f"[?] Help | [Q] Quit | [T] Theme"
    #     )

    #     # Update footer using the proper Textual API
    #     self.set_footer(footer_content)

    async def on_command_prompt_command_submitted(self, event) -> None:
        """Handle command submission from the prompt."""
        command = event.command

        # Display the command in the repository table for testing scrolling
        if self.repo_table:
            self.repo_table.add_command_output(command)

        # Process the command using our command processor
        result = self.command_processor.process_command(command)

        if result["type"] == "action":
            await self.handle_action(result)
        elif result["type"] == "help":
            self.show_help_content(result)
        elif result["type"] == "unknown":
            self.show_unknown_command(result)
        elif result["type"] == "error":
            self.show_error(result)

    async def handle_action(self, result: Dict[str, Any]) -> None:
        """Handle action-type commands."""
        action = result.get("action")

        if action == "show_repositories":
            # Repositories are already displayed, just refresh if needed
            if self.repo_table:
                self.repo_table.load_mock_data()
                self.repo_table.add_command_output("list repos", "✅ Refreshed repository list")

        elif action == "show_status":
            status_counts = self.repo_table.get_status_counts() if self.repo_table else {}
            status_msg = f"📊 Status: {status_counts.get('success', 0)} ✓, {status_counts.get('failed', 0)} ✗, {status_counts.get('syncing', 0)} ⟳"
            if self.repo_table:
                self.repo_table.add_command_output("status", status_msg)

        elif action == "filter_repositories":
            filter_criteria = result.get("filter", {})
            if filter_criteria.get("status") == "failed":
                failed_count = self.repo_table.get_status_counts().get("failed", 0) if self.repo_table else 0
                if self.repo_table:
                    self.repo_table.add_command_output("show failed", f"🔍 Found {failed_count} failed repositories")

    def show_help_content(self, result: Dict[str, Any]) -> None:
        """Show help content."""
        help_content = result.get("content", "Help content not available")
        if self.repo_table:
            self.repo_table.add_command_output("help", "💡 Help displayed (see toast for details)")
        self.notify("💡 Help", title="Available Commands")
        # In a full implementation, we'd show this in a modal or dedicated area

    def show_unknown_command(self, result: Dict[str, Any]) -> None:
        """Handle unknown commands."""
        message = result.get("message", "Unknown command")
        suggestion = result.get("suggestion", "")
        if self.repo_table:
            self.repo_table.add_command_output(message, f"💡 {suggestion}")
        self.notify(f"❓ {message}\n💡 {suggestion}", title="Command Not Recognized", severity="warning")

    def show_error(self, result: Dict[str, Any]) -> None:
        """Handle command errors."""
        message = result.get("message", "An error occurred")
        if self.repo_table:
            self.repo_table.add_command_output("error", f"❌ {message}")
        self.notify(f"❌ {message}", title="Error", severity="error")

    def action_show_help(self) -> None:
        """Show help when ? is pressed."""
        help_text = """
[b]Available Commands:[/b]
• [cyan]list[/cyan] - Show all repositories
• [cyan]status[/cyan] - Show repository status summary
• [cyan]show failed[/cyan] - Show only failed repositories
• [cyan]sync all[/cyan] - Sync all repositories
• [cyan]add <url>[/cyan] - Add a new repository
• [cyan]help[/cyan] - Show this help

[b]Key Bindings:[/b]
• [yellow]?[/yellow] - Show help
• [yellow]T[/yellow] - Cycle themes
• [yellow]Q[/yellow] - Quit application
• [yellow]↑↓[/yellow] - Navigate command history
        """.strip()
        self.notify(help_text, title="Repository Manager Help")

    def action_cycle_theme(self) -> None:
        """Cycle through available themes using Textual's built-in system."""
        self.current_theme_index = (self.current_theme_index + 1) % len(self._available_themes)
        new_theme_name = self._available_themes[self.current_theme_index]

        # Use Textual's built-in theme switching
        self.theme = new_theme_name
        self.notify(f"🎨 Switched to {new_theme_name} theme")

    def action_list_repos(self) -> None:
        """List all repositories."""
        if self.repo_table:
            self.repo_table.load_mock_data()
            self.repo_table.add_command_output("list (shortcut)", "✅ Repository list refreshed")

    def action_show_status(self) -> None:
        """Show repository status summary."""
        status_counts = self.repo_table.get_status_counts() if self.repo_table else {}
        status_msg = f"📊 Status: {status_counts.get('success', 0)} ✓, {status_counts.get('failed', 0)} ✗, {status_counts.get('syncing', 0)} ⟳"
        if self.repo_table:
            self.repo_table.add_command_output("status (shortcut)", status_msg)

    def action_show_failed(self) -> None:
        """Show only failed repositories."""
        failed_count = self.repo_table.get_status_counts().get("failed", 0) if self.repo_table else 0
        if self.repo_table:
            self.repo_table.add_command_output("show failed (shortcut)", f"🔍 Found {failed_count} failed repositories")

    def action_show_more(self) -> None:
        """Show extended commands (future expansion)."""
        if self.repo_table:
            self.repo_table.add_command_output("more (shortcut)", "🔮 Extended commands panel - Coming in Phase 3!")

if __name__ == "__main__":
    import sys
    theme_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    app = RepoManagerApp(theme_name=theme_name)
    app.run()