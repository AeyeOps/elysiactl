"""Main Textual application for repository management."""

from typing import Any, ClassVar

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header

from ..services.repository import Repository
from .command_processor import CommandProcessor
from .theme_manager import ThemeManager
from .widgets.command_prompt import CommandPrompt
from .widgets.custom_footer import CustomFooter
from .widgets.virtual_scrollable import ConversationView


class RepoManagerApp(App):
    """Main repository management TUI application."""

    @property
    def CSS(self) -> str:
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

        Header:hover {
            background: $primary-lighten-1;
        }

        Footer {
            height: 4;
            width: 1fr;
            background: $primary;
            color: $foreground;
            padding: 0 2;
        }

        CustomFooter {
            height: 4;
            width: 1fr;
            background: $primary;
            color: $foreground;
            padding: 0 2;
        }

        .footer_binding {
            color: $text-muted;
            text-align: left;
        }

        CommandPrompt {
            height: auto;  /* Dynamic height 1-5 rows */
            width: 1fr;
            padding: 1;
            background: $surface;  /* Match scroll view background */
            color: $foreground;
            border: none;
            min-height: 1;  /* Start at 1 row */
            max-height: 5;  /* Grow up to 5 rows maximum */
        }

        /* Placeholder text styling */
        CommandPrompt.placeholder {
            color: $panel;  /* Use panel theme color for subtle placeholders */
        }

        /* Subtle separator line */
        .separator-line {
            color: $panel;  /* Same subtle color as placeholder text */
            text-style: dim;  /* Make it even more subtle */
            align: center middle;
        }

        #bottom_section {
            dock: bottom;
            height: auto;  /* Adjust based on CommandPrompt height + 4 for footer */
            width: 100%;
            min-height: 5;  /* 1 + 4 */
            max-height: 9;  /* 5 + 4 */
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

        /* Enhanced startup animation styles */
        #virtual_scroller {
            /* Basic styling for smooth appearance */
            background: $surface;
            color: $foreground;
        }

        /* Startup line styling for better visual appeal */
        .startup-line {
            text-style: bold;
            text-align: center;
        }

        .startup-line.highlight {
            color: $accent;
        }

        /* Intro line styling */
        .intro-line {
            text-align: center;
            color: $text-muted;
            text-style: italic;
        }

        .intro-line.ready {
            color: $success;
            text-style: bold;
        }

        /* Clickable table rows */
        .clickable-row {
            background: $surface;
        }

        .clickable-row:hover {
            background: $surface-lighten-1;
        }

        .clickable-row.selected {
            background: $primary-darken-2;
            color: $primary-lighten-3;
        }
        """

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()

        # Main content area with virtual scrolling for mixed content types
        with Vertical(id="main-container"):
            self.virtual_scroller = ConversationView(id="virtual_scroller")
            yield self.virtual_scroller

        # Bottom section for input and footer
        with Vertical(id="bottom_section"):
            self.command_prompt = CommandPrompt()
            yield self.command_prompt
            yield CustomFooter()

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
        self.virtual_scroller: ConversationView | None = None
        # Available themes will be set in _register_themes (don't overwrite!)
        # self._available_themes = []  # <-- This was overwriting the registered themes!
        self.current_theme_index = 0

        # Sidebar configuration
        self.sidebar_visible = True
        self.sidebar_min_width = 120  # Minimum width to show sidebar
        self.sidebar_min_height = 30  # Minimum height to show sidebar

        # Set initial theme
        self.theme = theme_name

        # Enable mouse support
        self.enable_mouse()

        # Track selected repositories
        self.selected_repositories: set[Repository] = set()

    def _register_themes(self) -> None:
        """Register themes using the ThemeManager for external configuration support."""
        theme_manager = ThemeManager()
        available_themes = theme_manager.get_available_themes()

        # Register all available themes
        for theme in available_themes.values():
            self.register_theme(theme)

        # Update available themes list
        self._available_themes = list(available_themes.keys())

    async def on_header_click(self, event) -> None:
        """Handle header click for app information."""
        if self.virtual_scroller:
            self.virtual_scroller.add_separator()
            self.virtual_scroller.add_ai_response(
                "🖱️ **Repository Management TUI**\n\n"
                "• **Version**: elysiactl with mgit integration\n"
                "• **Purpose**: Interactive repository discovery and management\n"
                "• **Features**: Pattern-based discovery, visual selection, sync monitoring\n\n"
                "💡 **Quick Start**:\n"
                "1. Try 'find repos \"org/project/*\"' to discover repositories\n"
                "2. Use 'add repos' to add them to monitoring\n"
                "3. Check 'status' for sync progress\n\n"
                "🎯 **Pro Tip**: Use wildcards (*) for flexible pattern matching!"
            )

    def enable_mouse(self) -> None:
        """Enable mouse support for the application."""
        # Mouse support is enabled by default in Textual, but we can configure it

    def on_mount(self) -> None:
        """Initialize the application when mounted."""
        # Focus the command prompt - completely passive, no automatic actions
        self.set_timer(0.1, lambda: self.command_prompt.focus() if self.command_prompt else None)

    def load_real_repositories(self) -> list[Repository]:
        """Load real repositories from mgit discovery."""
        try:
            from ..services.repository import repo_service

            # Try to load from monitored repositories first
            if repo_service.repositories:
                repos = list(repo_service.repositories.values())
                return repos

            # If no monitored repos, return empty list
            # User will see empty table and can use commands to discover repos
            return []

        except Exception:
            # Don't print console messages in TUI - let the UI handle errors gracefully
            return []

    def handle_repo_find_command(self, pattern: str, limit: int = 50) -> None:
        """Handle repository discovery command in TUI."""
        if self.virtual_scroller:
            self.virtual_scroller.add_ai_response(
                f"🔍 Discovering repositories with pattern: {pattern}"
            )

        # Run discovery in background to avoid blocking UI
        def discover_task():
            try:
                from ..services.repository import repo_service

                repos = repo_service.discover_repositories(pattern=pattern, limit=limit)

                if repos:
                    # Add to TUI
                    self.call_from_thread(self._show_discovered_repos, repos, pattern)
                else:
                    self.call_from_thread(
                        lambda: self.virtual_scroller.add_ai_response(
                            "No repositories found matching pattern"
                        )
                        if self.virtual_scroller
                        else None
                    )
            except Exception:
                self.call_from_thread(
                    lambda: self.virtual_scroller.add_ai_response(f"❌ Discovery error: {e}")
                    if self.virtual_scroller
                    else None
                )

        # Start background task
        import threading

        thread = threading.Thread(target=discover_task, daemon=True)
        thread.start()

    def _show_discovered_repos(self, repos: list[Repository], pattern: str) -> None:
        """Show discovered repositories in TUI."""
        if self.virtual_scroller:
            # Add table with selection capability
            self.virtual_scroller.add_repository_table(repos, selectable=True)
            self.virtual_scroller.add_ai_response(
                f"✅ Found {len(repos)} repositories matching '{pattern}'\n"
                "💡 Use your mouse or arrow keys to select repositories. "
                "Press Enter to toggle selection. "
                "Then, use 'add repos' to add them to monitoring."
            )

    def handle_repo_add_command(self, pattern: str | None) -> None:
        """Handle adding repositories to monitoring in TUI."""
        # Get selected repos from the table
        selected_repos = []
        if self.virtual_scroller and self.virtual_scroller.repository_table:
            selected_repos = self.virtual_scroller.repository_table.get_selected_repositories()

        if not selected_repos:
            if self.virtual_scroller:
                self.virtual_scroller.add_ai_response(
                    "❌ No repositories selected. Use 'find repos <pattern>' first, "
                    "then select repositories from the table."
                )
            return

        # Run add task in background
        def add_task():
            try:
                from ..services.repository import repo_service

                # Add repositories to the service
                for repo in selected_repos:
                    repo_service.repositories[repo.full_name] = repo
                repo_service.save_repository_config()
                self.call_from_thread(self._show_added_repos, selected_repos)
            except Exception:
                self.call_from_thread(
                    lambda: self.virtual_scroller.add_ai_response(f"❌ Add error: {e}")
                    if self.virtual_scroller
                    else None
                )

        import threading

        thread = threading.Thread(target=add_task, daemon=True)
        thread.start()

    def _show_added_repos(self, repos: list[Repository]) -> None:
        """Show confirmation after adding repositories."""
        if self.virtual_scroller:
            repo_names = ", ".join([r.repository for r in repos])
            self.virtual_scroller.add_ai_response(
                f"✅ Successfully added {len(repos)} repositories to monitoring:\n{repo_names}"
            )

    def on_command_prompt_command_submitted(self, message) -> None:
        """Handle CommandSubmitted message from CommandPrompt widget."""
        command = message.command
        print(f"DEBUG: Received command via message: '{command}'")

        # Display the command in the virtual scroller
        if self.virtual_scroller:
            self.virtual_scroller.add_text_message(command, "user")

        # Process the command using our command processor
        result = self.command_processor.process_command(command)
        print(f"DEBUG: Command processor result: {result}")

        if result["type"] == "action":
            self.handle_action(result)
        elif result["type"] == "help":
            self.show_help_content(result)
        elif result["type"] == "unknown":
            self.show_unknown_command(result)
        elif result["type"] == "error":
            self.show_error(result)

    def show_help_content(self, result: dict[str, Any]) -> None:
        """Show help content."""
        help_content = result.get("content", "Help content not available")
        if self.virtual_scroller:
            self.virtual_scroller.add_ai_response(
                "💡 Help System Available\n\nCommands:\n- list - Show all repositories\n- status - Show repository status\n- show failed - Show only failed repos\n- help - Show this help\n\nKey Bindings:\n- ? - Show help\n- T - Cycle themes\n- Q - Quit application"
            )
        self.notify("💡 Help", title="Available Commands", timeout=2.0)

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

    def handle_action(self, result: dict[str, Any]) -> None:
        """Handle action-type commands."""
        action = result.get("action")

        if action == "show_repositories":
            # Load and display repositories using real service
            if self.virtual_scroller:
                from ..services.repository import repo_service

                # Get real repositories
                repos = list(repo_service.repositories.values())
                if not repos:
                    # No repositories loaded, try to discover
                    repos = repo_service.discover_repositories()

                if repos:
                    self.virtual_scroller.add_repository_table(repos)
                    self.virtual_scroller.add_ai_response(
                        f"Here are your {len(repos)} repositories. Click any row to interact with them."
                    )
                else:
                    self.virtual_scroller.add_ai_response(
                        "No repositories found. Use 'load repos' to discover repositories or check your mgit configuration."
                    )

        elif action == "show_status":
            # Show status summary using real data
            if self.virtual_scroller:
                from ..services.repository import repo_service

                # Get real status counts
                all_repos = list(repo_service.repositories.values())

                if all_repos:
                    success_count = sum(1 for repo in all_repos if repo.sync_status == "success")
                    failed_count = sum(1 for repo in all_repos if repo.sync_status == "failed")
                    syncing_count = sum(1 for repo in all_repos if repo.sync_status == "syncing")
                    unknown_count = len(all_repos) - success_count - failed_count - syncing_count

                    status_msg = "Repository Status Summary\n"
                    status_msg += f"Success: {success_count}\n"
                    status_msg += f"Failed: {failed_count}\n"
                    status_msg += f"Syncing: {syncing_count}\n"
                    status_msg += f"Unknown: {unknown_count}\n"

                    self.virtual_scroller.add_ai_response(status_msg)
                else:
                    self.virtual_scroller.add_ai_response(
                        "No repositories loaded. Use 'load repos' first."
                    )

        elif action == "load_repositories":
            # Load repositories from mgit discovery
            if self.virtual_scroller:
                try:
                    real_repos = self.load_real_repositories()
                    if real_repos:
                        self.virtual_scroller.add_repository_table(real_repos)
                        self.virtual_scroller.add_ai_response(
                            f"Loaded {len(real_repos)} repositories from mgit discovery"
                        )
                    else:
                        self.virtual_scroller.add_ai_response(
                            "mgit discovery found no repositories in the configured sync directory"
                        )
                except Exception as e:
                    self.virtual_scroller.add_ai_response(f"Filesystem scan failed: {e!s}")

        elif action == "filter_repositories":
            filter_criteria = result.get("filter", {})
            status_filter = filter_criteria.get("status")

            if self.virtual_scroller:
                from ..services.repository import repo_service

                if status_filter == "failed":
                    # Get repositories filtered by status
                    failed_repos = repo_service.get_repositories_by_status("failed")

                    if failed_repos:
                        self.virtual_scroller.add_repository_table(failed_repos)
                        self.virtual_scroller.add_ai_response(
                            f"Found {len(failed_repos)} failed repositories"
                        )
                    else:
                        # Also check for unknown status repos (not cloned)
                        unknown_repos = repo_service.get_repositories_by_status("unknown")
                        if unknown_repos:
                            self.virtual_scroller.add_repository_table(unknown_repos)
                            self.virtual_scroller.add_ai_response(
                                f"Found {len(unknown_repos)} uncloned repositories"
                            )
                        else:
                            self.virtual_scroller.add_ai_response(
                                "No failed or uncloned repositories found"
                            )

                elif status_filter == "success":
                    # Get successful repositories
                    success_repos = repo_service.get_repositories_by_status("success")

                    if success_repos:
                        self.virtual_scroller.add_repository_table(success_repos)
                        self.virtual_scroller.add_ai_response(
                            f"Found {len(success_repos)} successful repositories"
                        )
                    else:
                        self.virtual_scroller.add_ai_response("No successful repositories found")

        elif action == "repo_find":
            # Handle repository discovery
            pattern = result.get("pattern")
            limit = result.get("limit", 50)
            self.handle_repo_find_command(pattern, limit)

        elif action == "repo_add":
            # Handle adding repositories to monitoring
            pattern = result.get("pattern")
            self.handle_repo_add_command(pattern)
