from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Vertical, Horizontal

class StylingDemoApp(App):
    """Sample app for interactive styling and layout work."""
    
    CSS = """
    Screen {
        background: $surface;
        align: center middle;
    }
    
    .header {
        background: $primary;
        color: $text;
        text-align: center;
        padding: 1;
        border: solid $accent;
    }
    
    .content {
        height: 1fr;
        width: 100%;
        padding: 2;
    }
    
    .footer {
        background: $boost;
        color: $text-muted;
        text-align: center;
        padding: 1;
    }
    
    .demo-section {
        border: solid $primary;
        padding: 1;
        margin: 1 0;
        height: auto;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Vertical(classes="content"):
            yield Static("🎨 Interactive Styling Demo", classes="demo-section")
            
            with Horizontal(classes="demo-section"):
                yield Button("Primary", variant="primary", id="primary-btn")
                yield Button("Success", variant="success", id="success-btn")
                yield Button("Warning", variant="warning", id="warning-btn")
            
            yield Static("Try editing the CSS above and see changes instantly!", classes="demo-section")
        
        yield Footer()
    
    def on_button_pressed(self, event):
        self.notify(f"Clicked: {event.button.id}")

if __name__ == "__main__":
    app = StylingDemoApp()
    app.run()
