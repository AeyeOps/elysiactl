"""Theme configuration management for elysiactl TUI."""

import json
import os
from pathlib import Path
from typing import Any

from textual.theme import Theme


class ThemeManager:
    """Manages loading and registering themes for the TUI."""

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".elysiactl" / "themes"
        self.themes: dict[str, Theme] = {}
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure the theme configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_builtin_themes(self) -> dict[str, Theme]:
        """Load the built-in themes that ship with elysiactl."""
        return {
            "default": self._create_default_theme(),
            "light": self._create_light_theme(),
            "professional": self._create_professional_theme(),
            "minimal": self._create_minimal_theme(),
            "dark": self._create_dark_theme(),
            "monokai": self._create_monokai_theme(),
            "github": self._create_github_theme(),
            "dracula": self._create_dracula_theme(),
            "solarized": self._create_solarized_theme(),
            "nord": self._create_nord_theme(),
        }

    def load_external_themes(self) -> dict[str, Theme]:
        """Load themes from external JSON/YAML files."""
        external_themes = {}

        # Look for theme files in the config directory
        for theme_file in self.config_dir.glob("*.json"):
            try:
                theme_name = theme_file.stem
                with open(theme_file) as f:
                    theme_data = json.load(f)
                external_themes[theme_name] = self._create_theme_from_data(theme_data, theme_name)
            except Exception as e:
                print(f"Warning: Failed to load theme {theme_file}: {e}")

        return external_themes

    def load_theme_from_env(self, theme_name: str) -> Theme | None:
        """Load a theme configuration from environment variables.

        Environment variables should be prefixed with ELYSIACTL_THEME_{THEME_NAME}_
        For example: ELYSIACTL_THEME_CUSTOM_PRIMARY="#ff0000"
        """
        env_prefix = f"ELYSIACTL_THEME_{theme_name.upper()}_"
        theme_data = {}

        # Map environment variables to theme properties
        env_mappings = {
            f"{env_prefix}PRIMARY": "primary",
            f"{env_prefix}SECONDARY": "secondary",
            f"{env_prefix}ACCENT": "accent",
            f"{env_prefix}FOREGROUND": "foreground",
            f"{env_prefix}BACKGROUND": "background",
            f"{env_prefix}SURFACE": "surface",
            f"{env_prefix}SUCCESS": "success",
            f"{env_prefix}WARNING": "warning",
            f"{env_prefix}ERROR": "error",
            f"{env_prefix}PANEL": "panel",
        }

        for env_var, theme_key in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                theme_data[theme_key] = value

        if theme_data:
            return self._create_theme_from_data(theme_data, theme_name)

        return None

    def _create_theme_from_data(self, data: dict[str, Any], name: str) -> Theme:
        """Create a Textual Theme object from theme data."""
        return Theme(
            name=name,
            primary=data.get("primary", "#00d4ff"),
            secondary=data.get("secondary", "#8b5cf6"),
            accent=data.get("accent", "#ff6b6b"),
            foreground=data.get("foreground", "#ffffff"),
            background=data.get("background", "#1a1a2e"),
            surface=data.get("surface", "#2a2a4e"),
            success=data.get("success", "#00ff88"),
            warning=data.get("warning", "#ffa500"),
            error=data.get("error", "#ff4757"),
            panel=data.get("panel", "#475569"),
        )

    def _create_default_theme(self) -> Theme:
        """Create the default dark theme."""
        return Theme(
            name="default",
            primary="#00d4ff",  # Bright cyan
            secondary="#8b5cf6",  # Purple accent
            accent="#ff6b6b",  # Coral red
            foreground="#ffffff",  # Pure white text
            background="#1a1a2e",  # Dark blue-gray (lighter than before)
            surface="#2a2a4e",  # Medium blue-gray surface
            success="#00ff88",  # Bright green
            warning="#ffa500",  # Orange
            error="#ff4757",  # Red
            panel="#475569",  # Dark slate
        )

    def _create_light_theme(self) -> Theme:
        """Create the light theme."""
        return Theme(
            name="light",
            primary="#0366d6",  # Professional blue
            secondary="#586069",  # Muted gray
            accent="#28a745",  # Success green
            foreground="#24292e",  # Dark gray text
            background="#ffffff",  # Pure white background
            surface="#f8f9fa",  # Light gray surface
            success="#28a745",  # Consistent green
            warning="#ffd33d",  # Warm yellow
            error="#d73a49",  # Muted red
            panel="#e1e4e8",  # Subtle borders
        )

    def _create_professional_theme(self) -> Theme:
        """Create the professional theme."""
        return Theme(
            name="professional",
            primary="#3b82f6",  # Professional blue
            secondary="#64748b",  # Muted blue-gray
            accent="#10b981",  # Professional teal
            foreground="#f1f5f9",  # Off-white text
            background="#0f172a",  # Dark slate background
            surface="#1e293b",  # Darker slate surface
            success="#10b981",  # Consistent success
            warning="#f59e0b",  # Professional warning
            error="#ef4444",  # Clean error red
            panel="#334155",  # Subtle border gray
            text_muted="#64748b",  # Muted blue-gray
        )

    def _create_minimal_theme(self) -> Theme:
        """Create the minimal theme."""
        return Theme(
            name="minimal",
            primary="#ffffff",  # Pure white
            secondary="#666666",  # Medium gray
            accent="#ffffff",  # White accent
            foreground="#ffffff",  # White text
            background="#000000",  # Pure black
            surface="#111111",  # Very dark gray
            success="#00ff00",  # Bright green
            warning="#ffff00",  # Yellow
            error="#ff0000",  # Red
            panel="#333333",  # Dark gray
            text_muted="#555555",  # Dark gray for minimal theme
        )

    def _create_dark_theme(self) -> Theme:
        """Create the dark theme."""
        return Theme(
            name="dark",
            primary="#61dafb",  # React blue
            secondary="#21ba45",  # Green accent
            accent="#f39c12",  # Orange
            foreground="#ffffff",  # White text
            background="#1e1e1e",  # VS Code dark background
            surface="#252526",  # VS Code dark surface
            success="#4ade80",  # Light green
            warning="#fbbf24",  # Yellow
            error="#f87171",  # Light red
            panel="#3e3e42",  # Dark panel
            text_muted="#858585",  # Medium gray for dark theme
        )

    def _create_monokai_theme(self) -> Theme:
        """Create the monokai theme."""
        return Theme(
            name="monokai",
            primary="#f92672",  # Monokai pink
            secondary="#66d9ef",  # Monokai blue
            accent="#a6e22e",  # Monokai green
            foreground="#f8f8f2",  # Monokai foreground
            background="#272822",  # Monokai background
            surface="#3e3d32",  # Monokai surface
            success="#a6e22e",  # Green
            warning="#fd971f",  # Orange
            error="#f92672",  # Red
            panel="#49483e",  # Monokai panel
            text_muted="#75715e",  # Monokai comment color
        )

    def _create_github_theme(self) -> Theme:
        """Create the GitHub theme."""
        return Theme(
            name="github",
            primary="#0366d6",  # GitHub blue
            secondary="#586069",  # GitHub gray
            accent="#28a745",  # GitHub green
            foreground="#24292e",  # GitHub dark text
            background="#ffffff",  # White background
            surface="#f6f8fa",  # GitHub light gray
            success="#28a745",  # Green
            warning="#ffd33d",  # Yellow
            error="#d73a49",  # Red
            panel="#e1e4e8",  # GitHub border gray
            text_muted="#586069",  # GitHub secondary text
        )

    def _create_dracula_theme(self) -> Theme:
        """Create the Dracula theme."""
        return Theme(
            name="dracula",
            primary="#bd93f9",  # Dracula purple
            secondary="#50fa7b",  # Dracula green
            accent="#ffb86c",  # Dracula orange
            foreground="#f8f8f2",  # Dracula foreground
            background="#282a36",  # Dracula background
            surface="#44475a",  # Dracula surface
            success="#50fa7b",  # Green
            warning="#ffb86c",  # Orange
            error="#ff5555",  # Red
            panel="#6272a4",  # Dracula panel
            text_muted="#6272a4",  # Dracula comment color
        )

    def _create_solarized_theme(self) -> Theme:
        """Create the Solarized theme."""
        return Theme(
            name="solarized",
            primary="#268bd2",  # Solarized blue
            secondary="#859900",  # Solarized green
            accent="#b58900",  # Solarized yellow
            foreground="#586e75",  # Solarized base01
            background="#fdf6e3",  # Solarized base3
            surface="#eee8d5",  # Solarized base2
            success="#859900",  # Green
            warning="#b58900",  # Yellow
            error="#dc322f",  # Red
            panel="#93a1a1",  # Solarized base1
            text_muted="#93a1a1",  # Solarized base1 for muted text
        )

    def _create_nord_theme(self) -> Theme:
        """Create the Nord theme."""
        return Theme(
            name="nord",
            primary="#88c0d0",  # Nord blue
            secondary="#a3be8c",  # Nord green
            accent="#ebcb8b",  # Nord yellow
            foreground="#eceff4",  # Nord snow storm 3
            background="#2e3440",  # Nord polar night 0
            surface="#3b4252",  # Nord polar night 1
            success="#a3be8c",  # Green
            warning="#ebcb8b",  # Yellow
            error="#bf616a",  # Red
            panel="#4c566a",  # Nord polar night 2
            text_muted="#4c566a",  # Nord polar night 2
        )

    def get_available_themes(self) -> dict[str, Theme]:
        """Get all available themes (built-in + external + env-based)."""
        themes = self.load_builtin_themes()
        themes.update(self.load_external_themes())

        # Check for environment-based themes
        env_themes = ["custom", "user", "company"]
        for theme_name in env_themes:
            env_theme = self.load_theme_from_env(theme_name)
            if env_theme:
                themes[theme_name] = env_theme

        return themes

    def create_sample_theme_file(self, theme_name: str = "custom"):
        """Create a sample theme configuration file."""
        sample_theme = {
            "primary": "#00d4ff",
            "secondary": "#8b5cf6",
            "accent": "#ff6b6b",
            "foreground": "#ffffff",
            "background": "#1a1a2e",
            "surface": "#2a2a4e",
            "success": "#00ff88",
            "warning": "#ffa500",
            "error": "#ff4757",
            "panel": "#475569",
        }

        theme_file = self.config_dir / f"{theme_name}.json"
        with open(theme_file, "w") as f:
            json.dump(sample_theme, f, indent=2)

        return theme_file

    def list_theme_files(self):
        """List all available theme configuration files."""
        return list(self.config_dir.glob("*.json"))
