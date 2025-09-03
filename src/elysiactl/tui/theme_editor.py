"""Interactive theme editor for elysiactl TUI."""

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label, Static


class ColorSwatch(Widget):
    """A clickable color swatch widget."""

    def __init__(self, color: str, name: str = "", **kwargs):
        super().__init__(**kwargs)
        self.color = color
        self.name = name or color

    def render(self) -> str:
        """Render the color swatch."""
        return f"[{self.color} on {self.color}]█[/{self.color} on {self.color}] {self.name}"

    def on_click(self, event: events.Click) -> None:
        """Handle color swatch clicks."""
        self.post_message(self.ColorSelected(self, self.color, self.name))

    class ColorSelected(events.Message):
        """Message sent when a color is selected."""

        def __init__(self, sender: "ColorSwatch", color: str, name: str):
            super().__init__()
            self.sender = sender
            self.color = color
            self.name = name


class ColorPalette(Widget):
    """Color palette widget with predefined colors."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_color = None

    def compose(self) -> ComposeResult:
        """Create the color palette."""
        # Basic color palette
        colors = [
            ("#ff4757", "Red"),
            ("#ffa502", "Orange"),
            ("#ffd93d", "Yellow"),
            ("#00ff88", "Green"),
            ("#00d4ff", "Cyan"),
            ("#8b5cf6", "Purple"),
            ("#ff6b6b", "Coral"),
            ("#4ecdc4", "Teal"),
            ("#ffe66d", "Gold"),
            ("#a3be8c", "Sage"),
            ("#88c0d0", "Frost"),
            ("#ebcb8b", "Sand"),
            ("#bf616a", "Rose"),
            ("#2e3440", "Polar Night"),
            ("#3b4252", "Dark Gray"),
            ("#eceff4", "Snow"),
        ]

        with Vertical():
            yield Label("🎨 Color Palette", classes="palette-title")

            # Create rows of color swatches
            for i in range(0, len(colors), 4):
                with Horizontal():
                    for j in range(4):
                        if i + j < len(colors):
                            color, name = colors[i + j]
                            yield ColorSwatch(color, name, classes="color-swatch")

    def on_color_swatch_color_selected(self, event: ColorSwatch.ColorSelected) -> None:
        """Handle color selection from swatches."""
        self.selected_color = event.color
        self.post_message(self.ColorChosen(event.color, event.name))

    class ColorChosen(events.Message):
        """Message sent when a color is chosen from the palette."""

        def __init__(self, color: str, name: str):
            super().__init__()
            self.color = color
            self.name = name


class ThemeElementInspector(Widget):
    """Widget for inspecting current theme element colors."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_element = None
        self.current_color = None

    def compose(self) -> ComposeResult:
        """Create the inspector interface."""
        with Vertical():
            yield Label("🔍 Element Inspector", classes="inspector-title")
            yield Static("Click on a UI element to inspect its colors", id="inspector-help")
            yield Static("", id="element-info")
            yield Static("", id="color-info")
            yield Button("🎨 Edit Color", id="edit-color-btn", disabled=True)

    def inspect_element(self, element_name: str, element_type: str = "unknown") -> None:
        """Inspect a UI element and show its color information."""
        self.current_element = element_name

        # Get current theme colors (simplified for now)
        # In a full implementation, this would query the actual CSS/computed styles
        mock_colors = {
            "header": {"background": "#00d4ff", "color": "#ffffff"},
            "button": {"background": "#8b5cf6", "color": "#ffffff"},
            "input": {"background": "#2a2a4e", "border": "#00d4ff"},
            "panel": {"background": "#1a1a2e", "border": "#475569"},
        }

        colors = mock_colors.get(element_type, {"background": "#666666", "color": "#ffffff"})

        element_info = self.query_one("#element-info", Static)
        color_info = self.query_one("#color-info", Static)
        edit_btn = self.query_one("#edit-color-btn", Button)

        element_info.update(f"📦 Element: {element_name} ({element_type})")
        color_info.update(f"🎨 Colors: {', '.join([f'{k}: {v}' for k, v in colors.items()])}")
        edit_btn.disabled = False

        self.current_color = list(colors.values())[0] if colors else None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "edit-color-btn" and self.current_element and self.current_color:
            self.post_message(self.EditColorRequested(self.current_element, self.current_color))

    class EditColorRequested(events.Message):
        """Message sent when color editing is requested."""

        def __init__(self, element: str, current_color: str):
            super().__init__()
            self.element = element
            self.current_color = current_color


class ThemeEditor(Widget):
    """Main theme editor widget combining inspector and palette."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inspector = ThemeElementInspector()
        self.palette = ColorPalette()
        self.editing_element = None

    def compose(self) -> ComposeResult:
        """Create the theme editor interface."""
        with Horizontal():
            with Vertical(classes="editor-panel"):
                yield self.inspector
                yield Button("💾 Save Theme", id="save-theme-btn")
                yield Button("🔄 Reset", id="reset-theme-btn")

            with Vertical(classes="palette-panel"):
                yield self.palette
                yield Static("Click a color to apply to selected element", classes="palette-help")

    def on_theme_element_inspector_edit_color_requested(self, event) -> None:
        """Handle color edit requests."""
        self.editing_element = event.element
        # Highlight the palette for color selection
        self.notify(f"🎨 Select a color for {event.element}")

    def on_color_palette_color_chosen(self, event: ColorPalette.ColorChosen) -> None:
        """Handle color selection from palette."""
        if self.editing_element:
            self.apply_color_to_element(self.editing_element, event.color, event.name)
            self.notify(f"✅ Applied {event.name} to {self.editing_element}")

    def apply_color_to_element(self, element: str, color: str, color_name: str) -> None:
        """Apply selected color to a theme element."""
        # This would update the actual theme in a full implementation
        # For now, just log the change
        self.log(f"Applied {color} ({color_name}) to {element}")

        # Update the inspector to reflect the change
        self.inspector.inspect_element(element, "updated")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-theme-btn":
            self.save_current_theme()
        elif event.button.id == "reset-theme-btn":
            self.reset_theme()

    def save_current_theme(self) -> None:
        """Save the current theme modifications."""
        # This would save the modified theme to a file
        self.notify("💾 Theme saved successfully!")

    def reset_theme(self) -> None:
        """Reset theme to original state."""
        self.notify("🔄 Theme reset to original state")
