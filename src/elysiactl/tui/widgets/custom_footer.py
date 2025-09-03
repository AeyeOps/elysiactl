"""Custom footer widget that displays key bindings in two rows."""

from typing import ClassVar

from textual.containers import Horizontal, Vertical
from textual.widgets import Static


class CustomFooter(Vertical):
    """Custom footer displaying key bindings in two rows."""

    @property
    def CSS(self):
        return """
        CustomFooter {
            height: 4;
            background: $primary;
            color: $foreground;
            padding: 0 2;
        }
        
        .footer_binding {
            color: $text-muted;
            text-align: left;
        }
        """

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

    def __init__(self):
        super().__init__(id="custom_footer")

    def compose(self):
        """Compose the footer with two rows of bindings."""
        # Split bindings into two rows
        row1_bindings = self.BINDINGS[:5]  # First 5 bindings
        row2_bindings = self.BINDINGS[5:]  # Next 5 bindings

        # First row
        with Horizontal(id="footer_row1"):
            for key, action, description in row1_bindings:
                yield Static(f"[{key}] {description}", classes="footer_binding")

        # Second row
        with Horizontal(id="footer_row2"):
            for key, action, description in row2_bindings:
                yield Static(f"[{key}] {description}", classes="footer_binding")

    def on_mount(self) -> None:
        """Set up the footer when mounted."""
        # Ensure equal spacing
        for child in self.walk_children():
            if hasattr(child, "styles"):
                child.styles.width = "1fr"
                child.styles.text_align = "left"