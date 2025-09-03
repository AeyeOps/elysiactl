"""Command processor for handling natural language repository commands."""

import re
from typing import Dict, Any, Optional

class CommandProcessor:
    """Process natural language commands into repository actions."""

    def __init__(self):
        self.commands = {
            # Basic viewing commands
            r"show.*repo": self.show_repositories,
            r"list.*repo": self.show_repositories,
            r"display.*repo": self.show_repositories,

            # Status commands
            r"show.*status": self.show_status,
            r"repo.*status": self.show_status,

            # Filtering commands
            r"show.*fail": self.show_failed_repositories,
            r"find.*fail": self.show_failed_repositories,
            r"list.*fail": self.show_failed_repositories,

            # Help commands
            r"help": self.show_help,
            r"\?": self.show_help,
            r"what.*do": self.show_help,
        }

    def process_command(self, command: str) -> Dict[str, Any]:
        """Process a natural language command and return the result."""
        command_lower = command.lower().strip()

        # Check for exact matches first
        if command_lower in ["help", "?"]:
            return self.show_help()

        # Check pattern matches
        for pattern, handler in self.commands.items():
            if re.search(pattern, command_lower):
                try:
                    return handler(command)
                except Exception as e:
                    return {
                        "type": "error",
                        "message": f"Error processing command: {e}",
                        "command": command
                    }

        # No match found
        return {
            "type": "unknown",
            "message": f"I don't understand: '{command}'",
            "suggestion": "Try 'show repos', 'show status', or 'help'",
            "command": command
        }

    def show_repositories(self, command: str) -> Dict[str, Any]:
        """Show all repositories."""
        return {
            "type": "action",
            "action": "show_repositories",
            "message": "Displaying all repositories",
            "command": command
        }

    def show_status(self, command: str) -> Dict[str, Any]:
        """Show repository status summary."""
        return {
            "type": "action",
            "action": "show_status",
            "message": "Showing repository status summary",
            "command": command
        }

    def show_failed_repositories(self, command: str) -> Dict[str, Any]:
        """Show only failed repositories."""
        return {
            "type": "action",
            "action": "filter_repositories",
            "filter": {"status": "failed"},
            "message": "Showing failed repositories",
            "command": command
        }

    def show_help(self, command: str = "") -> Dict[str, Any]:
        """Show available commands."""
        help_text = """
Available commands:
• "show repos" or "list repos" - Display all repositories
• "show status" - Show repository status summary
• "show failed repos" - Show only failed repositories
• "help" or "?" - Show this help message

You can also use natural language like:
• "what repositories do I have?"
• "show me the failed ones"
• "display repo status"
• "find failing repositories"
        """.strip()

        return {
            "type": "help",
            "message": "Here's what I can help you with:",
            "content": help_text,
            "command": command or "help"
        }