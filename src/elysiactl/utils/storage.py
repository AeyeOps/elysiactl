"""Local storage utilities for persisting user preferences and app state."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class UserPreferences:
    """User preferences that persist between sessions."""

    current_theme: str = "default"
    sidebar_visible: bool = True
    sidebar_min_width: int = 120
    sidebar_min_height: int = 30
    command_history: list[str] = field(default_factory=list)
    max_history_size: int = 100
    startup_animation_enabled: bool = True
    startup_animation_speed: float = 0.025  # 2x faster than 0.05
    startup_animation_file: Optional[str] = None


class LocalStorage:
    """Simple JSON-based local storage for user preferences."""

    def __init__(self, app_name: str = "elysiactl", config_dir: Optional[Path] = None) -> None:
        """Initialize local storage.

        Args:
            app_name: Name of the application
            config_dir: Custom config directory (defaults to ~/.app_name)
        """
        self.app_name = app_name
        self.config_dir = config_dir or Path.home() / f".{app_name}"
        self.config_file = self.config_dir / "preferences.json"
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_preferences(self, preferences: UserPreferences) -> None:
        """Save user preferences to disk."""
        try:
            data = asdict(preferences)
            with open(self.config_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Failed to save preferences: {e}")

    def load_preferences(self) -> UserPreferences:
        """Load user preferences from disk."""
        if not self.config_file.exists():
            return UserPreferences()

        try:
            with open(self.config_file) as f:
                data = json.load(f)

            # Handle command_history being None in saved data
            if data.get("command_history") is None:
                data["command_history"] = []

            return UserPreferences(**data)
        except Exception as e:
            print(f"Warning: Failed to load preferences: {e}")
            return UserPreferences()

    def save_value(self, key: str, value: Any) -> None:
        """Save a single preference value."""
        preferences = self.load_preferences()

        # Update the preference
        if hasattr(preferences, key):
            setattr(preferences, key, value)
            self.save_preferences(preferences)

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a single preference value."""
        preferences = self.load_preferences()
        return getattr(preferences, key, default)

    def add_command_to_history(self, command: str) -> None:
        """Add a command to the history."""
        preferences = self.load_preferences()

        # Remove if already exists (to avoid duplicates)
        if command in preferences.command_history:
            preferences.command_history.remove(command)

        # Add to beginning
        preferences.command_history.insert(0, command)

        # Trim to max size
        if len(preferences.command_history) > preferences.max_history_size:
            preferences.command_history = preferences.command_history[
                : preferences.max_history_size
            ]

        self.save_preferences(preferences)

    def get_command_history(self) -> list[str]:
        """Get the command history."""
        preferences = self.load_preferences()
        return preferences.command_history.copy()

    def clear_command_history(self) -> None:
        """Clear the command history."""
        preferences = self.load_preferences()
        preferences.command_history = []
        self.save_preferences(preferences)


# Global storage instance
_storage = None


def get_storage() -> LocalStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = LocalStorage()
    return _storage


def save_user_preference(key: str, value: Any) -> None:
    """Save a user preference."""
    get_storage().save_value(key, value)


def get_user_preference(key: str, default: Any = None) -> Any:
    """Get a user preference."""
    return get_storage().get_value(key, default)


def add_to_command_history(command: str) -> None:
    """Add a command to the history."""
    get_storage().add_command_to_history(command)


def get_command_history() -> list[str]:
    """Get the command history."""
    return get_storage().get_command_history()
