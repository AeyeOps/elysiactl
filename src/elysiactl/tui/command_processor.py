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
            # Load/discovery commands
            r"load.*repo": self.load_repositories,
            r"discover.*repo": self.load_repositories,
            r"scan.*repo": self.load_repositories,
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

    def load_repositories(self, command: str) -> dict[str, Any]:
        """Load/discover repositories."""
        return {
            "type": "action",
            "action": "load_repositories",
            "message": "Loading repositories from mgit discovery",
            "command": command,
        }

    def show_successful_repositories(self, command: str) -> dict[str, Any]:
        """Show only successful repositories."""
        return {
            "type": "action",
            "action": "filter_repositories",
            "filter": {"status": "success"},
            "message": "Showing successful repositories",
            "command": command,
        }

    def show_help(self, command: str = "") -> dict[str, Any]:
        """Show available commands."""
        help_text = """
Available commands:
• "show repos" or "list repos" - Display all repositories
• "load repos" or "discover repos" - Load repositories from mgit
• "show status" - Show repository status summary
• "show failed repos" - Show only failed repositories
• "show success repos" - Show only successful repositories
• "help" or "?" - Show this help message

You can also use natural language like:
• "what repositories do I have?"
• "show me the failed ones"
• "display repo status"
• "find failing repositories"
• "scan for new repos"
        """.strip()

        return {
            "type": "help",
            "message": "Here's what I can help you with:",
            "content": help_text,
            "command": command or "help",
        }
