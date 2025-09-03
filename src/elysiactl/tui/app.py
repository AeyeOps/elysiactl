"""Main Textual application for repository management."""

from typing import Any, ClassVar

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from ..services.repository import Repository
from .command_processor import CommandProcessor
from .theme_editor import ThemeEditor
from .theme_manager import ThemeManager
from .widgets.command_prompt import CommandPrompt
from .widgets.virtual_scrollable import (
    TableActionSelected,
    TableRowSelected,
    VirtualScrollableWidget,
)


class RepoManagerApp(App):
    """Main repository management TUI application."""

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
            height: 4;
            width: 1fr;
            padding: 1;
            background: $surface;
            color: $foreground;
            border: none;
        }

        #bottom_section {
            dock: bottom;
            height: 8;
            width: 100%;
        }

        #main-container {
            height: 1fr;
        }

        #virtual_scroller {
            height: 1fr;
            background: $surface;
            color: $foreground;
            overflow-y: auto;
        }

        /* Padding rows for bumper effects */
        .padding-row {
            height: 1;
            background: $surface;
            color: $surface;
            border: none;
        }

        #above_scroll_padding {
            /* 4th row from top - padding above scroll view */
        }

        #below_scroll_padding {
            /* 5th row from bottom - padding below scroll view */
        }

        /* Sleek vertical line prefixes for messages */
        .user-prefix {
            color: $accent;
            background: transparent;
        }

        .system-prefix {
            color: $warning;
            background: transparent;
        }

        .ai-prefix {
            color: $success;
            background: transparent;
        }

        .message-timestamp {
            color: $text-muted;
            background: transparent;
        }
        """

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        # Top padding row (invisible, used for bumper effect)
        yield Static("", id="top_padding", classes="padding-row")

        yield Header()

        # Padding row above scroll view (4th row from top)
        yield Static("", id="above_scroll_padding", classes="padding-row")

        # Main content area with virtual scrolling for mixed content types
        with Vertical(id="main-container"):
            self.virtual_scroller = VirtualScrollableWidget(id="virtual_scroller")
            yield self.virtual_scroller

        # Padding row below scroll view (5th row from bottom)
        yield Static("", id="below_scroll_padding", classes="padding-row")

        # Bottom section for input and footer
        with Vertical(id="bottom_section"):
            self.command_prompt = CommandPrompt()
            yield self.command_prompt
            yield Footer()

    BINDINGS: ClassVar = [
        ("q", "quit", "Quit"),
        ("Q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("?", "show_help", "Help"),
        ("t", "cycle_theme", "Theme"),
        ("l", "list_repos", "List"),
        ("s", "show_status", "Status"),
        ("f", "show_failed", "Failed"),
        ("ctrl+g", "show_more", "More"),
        ("ctrl+e", "open_theme_editor", "Theme Editor"),
    ]

    def __init__(self, theme_name: str = "default"):
        super().__init__()
        # Register custom themes with Textual after super().__init__()
        self._register_themes()
        self.command_processor = CommandProcessor()
        self.virtual_scroller = None
        # Available themes will be set in _register_themes (don't overwrite!)
        # self._available_themes = []  # <-- This was overwriting the registered themes!
        self.current_theme_index = 0

        # Sidebar configuration
        self.sidebar_visible = True
        self.sidebar_min_width = 120  # Minimum width to show sidebar
        self.sidebar_min_height = 30  # Minimum height to show sidebar

        # Set initial theme
        self.theme = theme_name

    def _register_themes(self):
        """Register themes using the ThemeManager for external configuration support."""
        theme_manager = ThemeManager()
        available_themes = theme_manager.get_available_themes()

        # Register all available themes
        for theme in available_themes.values():
            self.register_theme(theme)

        # Update available themes list
        self._available_themes = list(available_themes.keys())

    def on_mount(self) -> None:
        """Initialize the application when mounted."""
        # Ensure theme is applied properly
        if hasattr(self, "theme") and self.theme:
            pass  # Theme should already be set
        else:
            self.theme = "default"  # Fallback

        # Start the startup animation instead of showing welcome immediately
        if self.virtual_scroller:
            self.virtual_scroller.start_startup_animation()

        # Focus the command prompt after a short delay to ensure it's ready
        self.set_timer(0.1, lambda: self.command_prompt.focus() if self.command_prompt else None)

    async def on_command_prompt_command_submitted(self, event) -> None:
        """Handle command submission from the prompt."""
        command = event.command

        # Display the command in the virtual scroller
        if self.virtual_scroller:
            self.virtual_scroller.add_text_message(command, "user")

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

    async def handle_action(self, result: dict[str, Any]) -> None:
        """Handle action-type commands."""
        action = result.get("action")

        if action == "show_repositories":
            # Load and display repositories
            if self.virtual_scroller:
                mock_repos = [
                    Repository(
                        organization="pdidev",
                        project="Blue Cow",
                        repository="api-gateway",
                        clone_url="",
                        ssh_url="",
                        default_branch="main",
                        is_private=True,
                        description="API Gateway",
                        last_sync=None,
                        sync_status="success",
                    ),
                    Repository(
                        organization="pdidev",
                        project="Blue Cow",
                        repository="user-service",
                        clone_url="",
                        ssh_url="",
                        default_branch="develop",
                        is_private=True,
                        description="User service",
                        last_sync=None,
                        sync_status="success",
                    ),
                    Repository(
                        organization="pdidev",
                        project="Blue Cow",
                        repository="auth-service",
                        clone_url="",
                        ssh_url="",
                        default_branch="develop",
                        is_private=True,
                        description="Auth service",
                        last_sync=None,
                        sync_status="failed",
                    ),
                ]
                self.virtual_scroller.add_repository_table(mock_repos)
                self.virtual_scroller.add_ai_response(
                    "Here are your repositories! You can click on any row to interact with them."
                )

        elif action == "show_status":
            # Show status summary
            if self.virtual_scroller:
                self.virtual_scroller.add_ai_response(
                    "📊 Repository Status Summary\n✅ Success: 2 repositories\n❌ Failed: 1 repository\n🔄 Syncing: 0 repositories\n\nAll systems operational!"
                )

        elif action == "filter_repositories":
            filter_criteria = result.get("filter", {})
            if filter_criteria.get("status") == "failed":
                if self.virtual_scroller:
                    failed_repos = [
                        Repository(
                            "pdidev",
                            "Blue Cow",
                            "auth-service",
                            "",
                            "",
                            "develop",
                            True,
                            "Auth service",
                            "failed",
                        )
                    ]
                    self.virtual_scroller.add_repository_table(failed_repos)
                    self.virtual_scroller.add_ai_response(
                        "🔍 Found 1 failed repository. You can click on it to troubleshoot or retry."
                    )

    def show_help_content(self, result: dict[str, Any]) -> None:
        """Show help content."""
        if self.virtual_scroller:
            self.virtual_scroller.add_ai_response(
                "💡 Help System Available\n\nCommands:\n- list - Show all repositories\n- status - Show repository status\n- show failed - Show only failed repos\n- help - Show this help\n\nKey Bindings:\n- ? - Show help\n- T - Cycle themes\n- Q - Quit application"
            )
        self.notify("💡 Help", title="Available Commands", timeout=2.0)
        # In a full implementation, we'd show this in a modal or dedicated area

    def show_unknown_command(self, result: dict[str, Any]) -> None:
        """Handle unknown commands."""
        message = result.get("message", "Unknown command")
        suggestion = result.get("suggestion", "")
        if self.virtual_scroller:
            self.virtual_scroller.add_ai_response(
                f"❓ I didn't understand '{message}'\n💡 Try: {suggestion}"
            )
        self.notify(
            f"❓ {message}\n💡 {suggestion}",
            title="Command Not Recognized",
            severity="warning",
            timeout=2.0,
        )

    def show_error(self, result: dict[str, Any]) -> None:
        """Handle command errors."""
        message = result.get("message", "An error occurred")
        if self.virtual_scroller:
            self.virtual_scroller.add_ai_response(
                f"❌ Error: {message}\n\nPlease check your command and try again."
            )
        self.notify(f"❌ {message}", title="Error", severity="error", timeout=2.0)

    def on_table_row_selected(self, event: TableRowSelected) -> None:
        """Handle table row selection."""
        row_data = event.row_data
        repo_name = row_data.get("repository", "Unknown")
        status = row_data.get("sync_status", "unknown")
        self.notify(
            f"📁 Selected: {repo_name} ({status})", title="Repository Selected", timeout=2.0
        )

        # Add AI response about the selected repository
        if self.virtual_scroller:
            self.virtual_scroller.add_ai_response(
                f"You selected '{repo_name}' with status '{status}'. What would you like to do with this repository?\n\nOptions:\n- View details\n- Retry sync\n- Open in browser\n- View logs"
            )

    def on_table_action_selected(self, event: TableActionSelected) -> None:
        """Handle table action selection."""
        actions = event.actions
        self.notify(
            f"🎯 Available actions: {', '.join(actions)}", title="Actions Available", timeout=3.0
        )

        # Add AI response with action options
        if self.virtual_scroller:
            action_list = "\n".join(f"- {action}" for action in actions)
            self.virtual_scroller.add_ai_response(
                f"Available actions:\n{action_list}\n\nClick an action or type a command to proceed."
            )

    def action_show_help(self) -> None:
        """Show help when ? is pressed."""
        help_text = """
[b]Available Commands:[/b]
- [cyan]list[/cyan] - Show all repositories
- [cyan]status[/cyan] - Show repository status summary
- [cyan]show failed[/cyan] - Show only failed repositories
- [cyan]sync all[/cyan] - Sync all repositories
- [cyan]add <url>[/cyan] - Add a new repository
- [cyan]help[/cyan] - Show this help

[b]Key Bindings:[/b]
- [yellow]?[/yellow] - Show help
- [yellow]T[/yellow] - Cycle themes
- [yellow]Q[/yellow] - Quit application
- [yellow]up/down arrows[/yellow] - Navigate command history
        """.strip()
        # Add help content to the virtual scroller instead of using a notification
        if self.virtual_scroller:
            self.virtual_scroller.add_ai_response(f"🆘 Help System\n\n{help_text}")
            self.virtual_scroller.add_text_message("? (help)", "system")

    def action_cycle_theme(self) -> None:
        """Cycle through available themes."""
        if not self._available_themes:
            self.notify("No themes available", title="Theme Error", severity="error")
            return

        self.current_theme_index = (self.current_theme_index + 1) % len(self._available_themes)
        new_theme_name = self._available_themes[self.current_theme_index]

        # Use Textual's built-in theme switching
        self.theme = new_theme_name
        self.notify(f"Switched to {new_theme_name} theme", timeout=2.0)

        # Also add to virtual scroller
        if self.virtual_scroller:
            self.virtual_scroller.add_text_message(f"Theme changed to {new_theme_name}", "system")

    def action_open_theme_editor(self) -> None:
        """Open the interactive theme editor."""
        from textual.screen import ModalScreen

        class ThemeEditorScreen(ModalScreen):
            """Modal screen for the theme editor."""

            def compose(self) -> ComposeResult:
                yield ThemeEditor()

            def on_theme_editor_edit_color_requested(self, event) -> None:
                """Handle color edit requests from the editor."""
                # Forward to main app if needed

            def on_color_palette_color_chosen(self, event) -> None:
                """Handle color selection from palette."""
                # Forward to main app if needed

        self.push_screen(ThemeEditorScreen())


if __name__ == "__main__":
    import sys

    theme_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    app = RepoManagerApp(theme_name=theme_name)
    app.run()
