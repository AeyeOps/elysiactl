"""Command processor for handling natural language repository commands."""

import re
from typing import Any


class CommandProcessor:
    """Process natural language commands into repository actions."""

    def __init__(self):
        self.commands = {
            # Basic viewing commands
            r"show.*repo": self.show_repositories,
            r"list.*repo": self.show_repositories,
            r"display.*repo": self.show_repositories,
            # Status commands
            r"status": self.show_status,
            r"show.*status": self.show_status,
            r"repo.*status": self.show_status,
            # Filtering commands
            r"show.*fail": self.show_failed_repositories,
            r"find.*fail": self.show_failed_repositories,
            r"list.*fail": self.show_failed_repositories,
            r"show.*success": self.show_successful_repositories,
            r"list.*success": self.show_successful_repositories,
            # Discovery commands
            r"find.*repo": self.find_repositories,
            r"discover.*repo": self.find_repositories,
            r"search.*repo": self.find_repositories,
            # Add/Monitor commands
            r"add.*repo": self.add_repositories,
            r"monitor.*repo": self.add_repositories,
            # Load/discovery commands
            r"load.*repo": self.find_repositories,
            r"scan.*repo": self.find_repositories,
            # Help commands
            r"help": self.show_help,
            r"\?": self.show_help,
            r"what.*do": self.show_help,
        }

    def process_command(self, command: str) -> dict[str, Any]:
        """Process a natural language command and return the result."""
        command_lower = command.lower().strip()

        # Debug output
        print(f"Processing command: '{command}' -> '{command_lower}'")

        # Check for exact matches first
        if command_lower in ["help", "?"]:
            print("Exact match found for help")
            return self.show_help()

        # Check pattern matches
        for pattern, handler in self.commands.items():
            print(f"Checking pattern: '{pattern}'")
            if re.search(pattern, command_lower):
                print(f"Pattern matched: '{pattern}' for command '{command_lower}'")
                try:
                    return handler(command)
                except Exception as e:
                    print(f"Error in handler: {e}")
                    return {
                        "type": "error",
                        "message": f"Error processing command: {e}",
                        "command": command,
                    }

        # No match found
        print(f"No pattern matched for command: '{command_lower}'")
        return {
            "type": "unknown",
            "message": f"I don't understand: '{command}'",
            "suggestion": "Try 'show repos', 'show status', or 'help'",
            "command": command,
        }

    def show_repositories(self, command: str) -> dict[str, Any]:
        """Show all repositories."""
        return {
            "type": "action",
            "action": "show_repositories",
            "message": "Displaying all repositories",
            "command": command,
        }

    def show_status(self, command: str) -> dict[str, Any]:
        """Show repository status summary."""
        return {
            "type": "action",
            "action": "show_status",
            "message": "Showing repository status summary",
            "command": command,
        }

    def find_repositories(self, command: str) -> dict[str, Any]:
        """Find/discover repositories using mgit."""
        # Extract pattern from command
        pattern = self._extract_pattern(command)
        if not pattern:
            # For backward compatibility with "load repos" commands
            return {
                "type": "action",
                "action": "load_repositories",
                "message": "Loading repositories from mgit discovery",
                "command": command,
            }

        return {
            "type": "repo_find",
            "pattern": pattern,
            "message": f"Finding repositories with pattern: {pattern}",
            "command": command,
        }

    def add_repositories(self, command: str) -> dict[str, Any]:
        """Add repositories to monitoring."""
        # Extract pattern if specified
        pattern = self._extract_pattern(command)

        return {
            "type": "repo_add",
            "pattern": pattern,
            "message": f"Adding repositories{' with pattern: ' + pattern if pattern else ' from selection'} to monitoring",
            "command": command,
        }

    def load_repositories(self, command: str) -> dict[str, Any]:
        """Load/discover repositories (backward compatibility)."""
        return {
            "type": "action",
            "action": "load_repositories",
            "message": "Loading repositories from mgit discovery",
            "command": command,
        }

    def _extract_pattern(self, command: str) -> str | None:
        """Extract repository pattern from command."""
        # Look for quoted strings or word after "repos"
        import re

        # Find quoted strings
        quoted = re.findall(r'["\']([^"\']+)["\']', command)
        if quoted:
            return quoted[0]

        # Find pattern after "repos" or "repo"
        match = re.search(r"repo(?:s)?\s+(\S+)", command.lower())
        if match:
            pattern = match.group(1)
            # Skip if it's a common word
            if pattern not in ["to", "from", "with", "and", "the", "for"]:
                return pattern

        return None

    def show_successful_repositories(self, command: str) -> dict[str, Any]:
        """Show only successful repositories."""
        return {
            "type": "action",
            "action": "filter_repositories",
            "filter": {"status": "success"},
            "message": "Showing successful repositories",
            "command": command,
        }

    def show_failed_repositories(self, command: str) -> dict[str, Any]:
        """Show only failed repositories."""
        return {
            "type": "action",
            "action": "filter_repositories",
            "filter": {"status": "failed"},
            "message": "Showing failed repositories",
            "command": command,
        }

    def show_help(self, command: str = "") -> dict[str, Any]:
        """Show available commands."""
        help_text = """
Repository Management TUI

Commands:
• "find repos <pattern>" - Discover repositories using mgit
• "add repos [pattern]" - Add discovered repos to monitoring
• "show repos" - Display all monitored repositories
• "status" - Show repository status summary
• "show failed" - Show only failed repositories
• "show success" - Show only successful repositories
• "help" - Show this help

Examples:
• find repos "pdidev/*/*"
• find repos "p97networks/Loyalty-Platform/*"
• add repos
• show repos

Pattern Examples:
• "org/*/*" - All repos in organization
• "org/project/*" - All repos in specific project
• "org/*/*payment*" - Payment-related repos
        """.strip()

        return {
            "type": "help",
            "message": "Repository Management Commands:",
            "content": help_text,
            "command": command or "help",
        }
