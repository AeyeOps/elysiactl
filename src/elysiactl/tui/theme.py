"""Theme system for the repository management TUI."""

from dataclasses import dataclass


@dataclass
class Theme:
    """Represents a TUI theme with colors and styles."""

    name: str
    background: str
    surface: str
    primary: str
    secondary: str
    accent: str
    text: str
    text_muted: str
    success: str
    warning: str
    error: str
    border: str

    @classmethod
    def from_dict(cls, name: str, data: dict[str, str]) -> "Theme":
        """Create a theme from a dictionary."""
        return cls(
            name=name,
            background=data.get("background", "#000000"),
            surface=data.get("surface", "#1a1a1a"),
            primary=data.get("primary", "#3b82f6"),
            secondary=data.get("secondary", "#6b7280"),
            accent=data.get("accent", "#10b981"),
            text=data.get("text", "#ffffff"),
            text_muted=data.get("text_muted", "#9ca3af"),
            success=data.get("success", "#10b981"),
            warning=data.get("warning", "#f59e0b"),
            error=data.get("error", "#ef4444"),
            border=data.get("border", "#374151"),
        )


class ThemeManager:
    """Manages themes for the TUI application."""

    def __init__(self) -> None:
        self.themes: dict[str, Theme] = {}
        self.current_theme: Theme = self._create_default_theme()
        self._load_builtin_themes()

    def _create_default_theme(self) -> Theme:
        """Create the default dark theme."""
        return Theme(
            name="default",
            background="#000000",
            surface="#1a1a1a",
            primary="#3b82f6",
            secondary="#6b7280",
            accent="#10b981",
            text="#ffffff",
            text_muted="#9ca3af",
            success="#10b981",
            warning="#f59e0b",
            error="#ef4444",
            border="#374151",
        )

    def _load_builtin_themes(self) -> None:
        """Load built-in themes with professional color palettes."""
        # Default (Dark) - Professional dark theme with modern colors
        self.themes["default"] = Theme(
            name="default",
            background="#0f0f23",  # Deep dark blue-black
            surface="#1a1a2e",  # Dark blue-gray
            primary="#00d4ff",  # Bright cyan
            secondary="#8b5cf6",  # Purple accent
            accent="#ff6b6b",  # Coral red
            text="#ffffff",  # Pure white
            text_muted="#94a3b8",  # Muted blue-gray
            success="#00ff88",  # Bright green
            warning="#ffa500",  # Orange
            error="#ff4757",  # Red
            border="#334155",  # Dark slate
        )

        # Light theme - Professional light theme inspired by modern design systems
        self.themes["light"] = Theme(
            name="light",
            background="#fafbfc",  # GitHub-style light gray background
            surface="#ffffff",  # Pure white surface
            primary="#0366d6",  # Professional blue (GitHub blue)
            secondary="#586069",  # Muted gray for secondary elements
            accent="#28a745",  # Success green for accents
            text="#24292e",  # Dark gray for primary text
            text_muted="#586069",  # Medium gray for muted text
            success="#28a745",  # Consistent green for success states
            warning="#ffd33d",  # Warm yellow for warnings
            error="#d73a49",  # Muted red for errors
            border="#e1e4e8",  # Subtle light gray borders
        )

        # Minimal theme - Clean monochrome with subtle accents
        self.themes["minimal"] = Theme(
            name="minimal",
            background="#000000",  # Pure black background
            surface="#0a0a0a",  # Very dark gray surface
            primary="#ffffff",  # Pure white for primary elements
            secondary="#666666",  # Medium gray for secondary elements
            accent="#ffffff",  # White accent to maintain consistency
            text="#ffffff",  # White text
            text_muted="#999999",  # Light gray for muted text
            success="#00ff00",  # Bright green for success
            warning="#ffff00",  # Yellow for warnings
            error="#ff0000",  # Red for errors
            border="#333333",  # Dark gray borders
        )

        # Professional theme - Corporate color palette
        self.themes["professional"] = Theme(
            name="professional",
            background="#1e293b",  # Professional slate background
            surface="#334155",  # Darker slate surface
            primary="#3b82f6",  # Professional blue
            secondary="#64748b",  # Muted blue-gray
            accent="#10b981",  # Professional teal green
            text="#f1f5f9",  # Off-white text for readability
            text_muted="#94a3b8",  # Muted text color
            success="#10b981",  # Consistent success green
            warning="#f59e0b",  # Professional warning orange
            error="#ef4444",  # Clean error red
            border="#475569",  # Subtle border gray
        )

    def get_theme(self, name: str | None = None) -> Theme:
        """Get a theme by name."""
        if name is None:
            return self.current_theme
        return self.themes.get(name, self.current_theme)

    def set_theme(self, name: str) -> bool:
        """Set the current theme."""
        if name in self.themes:
            self.current_theme = self.themes[name]
            return True
        return False

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names."""
        return list(self.themes.keys())

    def to_css_variables(self, theme: Theme | None = None) -> str:
        """Convert theme to CSS variables."""
        if theme is None:
            theme = self.current_theme

        return f"""
        :root {{
            --background: {theme.background};
            --surface: {theme.surface};
            --primary: {theme.primary};
            --secondary: {theme.secondary};
            --accent: {theme.accent};
            --text: {theme.text};
            --text-muted: {theme.text_muted};
            --success: {theme.success};
            --warning: {theme.warning};
            --error: {theme.error};
            --border: {theme.border};
        }}
        """


# Global theme manager instance
theme_manager = ThemeManager()
