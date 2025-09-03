# Textual Core Concepts: Complete Framework Guide

**A comprehensive guide to building text-based user interfaces with Textual, Rich, and Typer in Python.**

*Optimized for LLM parsing with practical examples and implementation patterns.*

---

## Table of Contents

1. [Framework Overview](#framework-overview)
2. [Core Architecture](#core-architecture)
3. [Application Lifecycle](#application-lifecycle)
4. [Widget System](#widget-system)
5. [Layout Systems](#layout-systems)
6. [CSS Styling (TCSS)](#css-styling-tcss)
7. [Event System](#event-system)
8. [Reactive Properties](#reactive-properties)
9. [Message Passing](#message-passing)
10. [Screen Management](#screen-management)
11. [Rich Integration](#rich-integration)
12. [Typer CLI Integration](#typer-cli-integration)
13. [Performance Considerations](#performance-considerations)
14. [Common Patterns](#common-patterns)
15. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

---

## Framework Overview

### What is Textual?

Textual is a Python framework for building sophisticated terminal user interfaces (TUIs) and web applications using the same codebase. It provides:

- **Declarative UI composition** using Python context managers
- **CSS-like styling** with Textual CSS (TCSS)
- **Rich text rendering** through integration with the Rich library
- **Async-first architecture** with full asyncio support
- **Cross-platform compatibility** (Linux, macOS, Windows)
- **Web deployment** capability through Textual Web

### Core Philosophy

```python
# Textual follows these design principles:
# 1. Declarative composition over imperative construction
# 2. CSS-style separation of concerns
# 3. Event-driven architecture
# 4. Rich text as a first-class citizen
# 5. Performance through efficient rendering
```

---

## Core Architecture

### The Component Hierarchy

```
App
├── Screen(s)
│   ├── Container(s)
│   │   ├── Widget(s)
│   │   └── Widget(s)
│   └── Widget(s)
└── Modal Screen(s)
```

### Essential Classes

#### App Class
The root container and entry point for all Textual applications.

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button

class MyApp(App):
    """Main application class"""
    
    # CSS styling (optional)
    CSS = """
    Screen {
        background: $surface;
        align: center middle;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Define the UI structure"""
        yield Header()
        yield Button("Click me!", id="main-button")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        self.notify("Button was pressed!")

if __name__ == "__main__":
    MyApp().run()
```

#### Widget Class
Base class for all UI components.

```python
from textual.widget import Widget
from textual.reactive import var

class CustomCounter(Widget):
    """A custom widget with reactive state"""
    
    count = var(0)  # Reactive variable
    
    DEFAULT_CSS = """
    CustomCounter {
        background: $boost;
        border: solid $primary;
        padding: 1;
        text-align: center;
    }
    """
    
    def render(self) -> str:
        """Define what the widget displays"""
        return f"Count: {self.count}"
    
    def on_click(self) -> None:
        """Handle clicks"""
        self.count += 1
```

---

## Application Lifecycle

### Lifecycle Events

```python
class MyApp(App):
    async def on_mount(self) -> None:
        """Called when app is mounted (after compose)"""
        self.title = "My Application"
        # Initialize resources, start timers, etc.
    
    async def on_ready(self) -> None:
        """Called when app is ready for interaction"""
        # Focus specific widgets, show welcome messages
        self.query_one("#main-input").focus()
    
    async def on_unmount(self) -> None:
        """Called when app is about to close"""
        # Cleanup resources, save state, etc.
        await self.save_user_data()
```

### Startup Sequence

1. `App.__init__()` - App initialization
2. `compose()` - UI structure definition
3. Widget tree construction
4. `on_mount()` - App and widget mounting
5. Layout calculation
6. First render
7. `on_ready()` - Ready for user interaction

---

## Widget System

### Built-in Widgets

#### Input Widgets
```python
from textual.widgets import Input, Button, Checkbox, RadioSet, Select

# Text input with validation
input_widget = Input(placeholder="Enter your name...", 
                    validators=[Length(minimum=1)])

# Button with styling
button = Button("Submit", variant="primary", id="submit-btn")

# Checkbox with initial state
checkbox = Checkbox("Enable notifications", value=True)

# Radio button set
radio_set = RadioSet("Option 1", "Option 2", "Option 3")

# Dropdown select
select = Select([("value1", "Display 1"), ("value2", "Display 2")])
```

#### Display Widgets
```python
from textual.widgets import Static, Label, Pretty, Rule, ProgressBar

# Static text with markup
static = Static("[bold]Hello[/bold] [red]World[/red]!")

# Simple label
label = Label("Status: Ready")

# Pretty-printed Python objects
pretty = Pretty({"name": "Alice", "age": 30})

# Horizontal rule
rule = Rule("Section Divider")

# Progress indicator
progress = ProgressBar(total=100, progress=42)
```

#### Layout Containers
```python
from textual.containers import Container, Horizontal, Vertical, Grid, ScrollableContainer

# Basic container
container = Container(Widget1(), Widget2())

# Horizontal layout
horizontal = Horizontal(Button("Left"), Button("Right"))

# Vertical layout
vertical = Vertical(Header(), Content(), Footer())

# Grid layout
grid = Grid(
    Widget(), Widget(),
    Widget(), Widget(),
    id="main-grid"
)

# Scrollable content
scrollable = ScrollableContainer(VeryLongContent())
```

### Custom Widget Development

#### Basic Custom Widget
```python
from textual.widget import Widget
from rich.console import RenderableType

class StatusIndicator(Widget):
    """A simple status indicator widget"""
    
    DEFAULT_CSS = """
    StatusIndicator {
        height: 3;
        width: 20;
        border: round $primary;
        text-align: center;
        background: $surface;
    }
    
    StatusIndicator.online {
        background: green;
        color: white;
    }
    
    StatusIndicator.offline {
        background: red;
        color: white;
    }
    """
    
    def __init__(self, status: str = "offline") -> None:
        super().__init__()
        self.status = status
        self.add_class(status)
    
    def render(self) -> RenderableType:
        return f"● {self.status.upper()}"
    
    def set_status(self, status: str) -> None:
        """Update the status"""
        self.remove_class(self.status)
        self.status = status
        self.add_class(status)
        self.refresh()
```

#### Advanced Custom Widget with Composition
```python
from textual.widgets import Button, Label
from textual.containers import Horizontal

class CounterWidget(Widget):
    """A counter with increment/decrement buttons"""
    
    def __init__(self, initial_value: int = 0):
        super().__init__()
        self.value = initial_value
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button("-", id="decrement")
            yield Label(str(self.value), id="counter-value")
            yield Button("+", id="increment")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "increment":
            self.value += 1
        elif event.button.id == "decrement":
            self.value -= 1
        
        # Update the label
        self.query_one("#counter-value", Label).update(str(self.value))
```

---

## Layout Systems

### Layout Types

#### Vertical Layout (Default)
```python
# Widgets stack vertically (top to bottom)
class VerticalApp(App):
    def compose(self) -> ComposeResult:
        yield Static("Widget 1")
        yield Static("Widget 2")
        yield Static("Widget 3")

# CSS equivalent
"""
Screen {
    layout: vertical;
}
"""
```

#### Horizontal Layout
```python
# Widgets arrange horizontally (left to right)
from textual.containers import Horizontal

class HorizontalApp(App):
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static("Left")
            yield Static("Center")
            yield Static("Right")

# CSS equivalent
"""
Horizontal {
    layout: horizontal;
}
"""
```

#### Grid Layout
```python
# Grid-based layout with specified dimensions
from textual.containers import Grid

class GridApp(App):
    CSS = """
    Grid {
        grid-size: 2 3;  /* 2 columns, 3 rows */
        grid-columns: 1fr 2fr;  /* Column widths */
        grid-rows: auto 1fr auto;  /* Row heights */
        grid-gutter: 1;  /* Spacing between cells */
    }
    """
    
    def compose(self) -> ComposeResult:
        with Grid():
            yield Static("Cell 1")
            yield Static("Cell 2")
            yield Static("Cell 3") 
            yield Static("Cell 4")
            yield Static("Cell 5")
            yield Static("Cell 6")
```

#### Docking Layout
```python
# Dock widgets to screen edges
class DockedApp(App):
    CSS = """
    .header {
        dock: top;
        height: 3;
    }
    
    .sidebar {
        dock: left;
        width: 20;
    }
    
    .footer {
        dock: bottom;
        height: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("Header", classes="header")
        yield Static("Sidebar", classes="sidebar")
        yield Static("Main Content")  # Fills remaining space
        yield Static("Footer", classes="footer")
```

### Responsive Design

```python
# Use fr units for flexible sizing
"""
/* Flexible columns that adapt to screen size */
Grid {
    grid-columns: 1fr 2fr 1fr;  /* 25%, 50%, 25% */
}

/* Responsive breakpoints */
@media (max-width: 80) {
    Sidebar {
        display: none;  /* Hide sidebar on small screens */
    }
}

/* Auto-sizing */
Widget {
    width: auto;  /* Size to content */
    height: auto;
}
"""
```

---

## CSS Styling (TCSS)

### Textual CSS Overview

Textual uses CSS-like syntax for styling with some terminal-specific adaptations.

#### Basic Syntax
```css
/* Type selector - styles all widgets of this type */
Button {
    background: blue;
    color: white;
    border: solid green;
}

/* ID selector - styles widget with specific ID */
#main-button {
    background: red;
    margin: 1;
}

/* Class selector - styles widgets with specific class */
.primary-button {
    background: $primary;
    text-style: bold;
}

/* Descendant selector - styles buttons inside containers */
Container Button {
    width: 100%;
}
```

#### Color System
```css
/* Named colors */
background: red;
color: blue;

/* Hex colors */
background: #ff0000;
color: #0066cc;

/* RGB colors */
background: rgb(255, 0, 0);
color: rgba(0, 102, 204, 0.8);

/* HSL colors */
background: hsl(0, 100%, 50%);

/* Design system variables */
background: $primary;
color: $text;
border: solid $accent;
```

#### Layout Properties
```css
/* Dimensions */
width: 50;        /* Fixed width in characters */
height: 10;       /* Fixed height in lines */
width: 50%;       /* Percentage of parent */
width: 1fr;       /* Fractional unit (flexible) */
width: auto;      /* Size to content */

/* Spacing */
margin: 1;              /* All sides */
margin: 1 2;            /* Vertical, horizontal */
margin: 1 2 1 2;        /* Top, right, bottom, left */
padding: 1;             /* Internal spacing */

/* Positioning */
dock: top;              /* Dock to edge */
offset: 2 1;            /* Position offset */
```

#### Border and Outline
```css
/* Border styles */
border: solid red;
border: thick blue;
border: round green;
border: heavy white;
border-top: solid $primary;

/* Outlines (don't affect layout) */
outline: solid yellow;
outline: thick $accent;
```

#### Text Styling
```css
/* Text appearance */
text-style: bold;
text-style: italic;
text-style: underline;
text-style: strike;
text-style: bold italic;

/* Text alignment */
text-align: left;
text-align: center;
text-align: right;
text-align: justify;

/* Content alignment within widget */
content-align: center middle;
content-align: left top;
content-align: right bottom;
```

### Advanced Styling

#### Pseudo-classes
```css
/* State-based styling */
Button:hover {
    background: $accent;
}

Button:focus {
    border: thick $primary;
}

Button:disabled {
    background: $surface;
    color: $text-muted;
}

/* Position-based */
Widget:first-child {
    margin-top: 0;
}

Widget:last-child {
    margin-bottom: 0;
}
```

#### Component Classes
```python
# Define component classes for granular styling
class DataTable(Widget):
    COMPONENT_CLASSES = {
        "data-table--header",
        "data-table--row", 
        "data-table--cell",
        "data-table--cursor"
    }
    
    # Usage in CSS
    """
    .data-table--header {
        background: $boost;
        text-style: bold;
    }
    
    .data-table--row:hover {
        background: $primary 10%;
    }
    
    .data-table--cell {
        padding: 0 1;
    }
    """
```

### CSS Organization

#### Inline Styles
```python
# Quick styling for individual widgets
widget = Button("Click me", styles="background: red; color: white;")
```

#### App-level CSS
```python
class MyApp(App):
    CSS = """
    Screen {
        background: $surface;
    }
    
    Button {
        margin: 1;
    }
    """
```

#### External CSS Files
```python
class MyApp(App):
    CSS_PATH = "styles.tcss"  # Load from external file
```

---

## Event System

### Event-Driven Architecture

Textual uses an event-driven model where widgets communicate through messages and events.

#### Built-in Events

```python
from textual.events import Key, Click, Mount, Resize

class EventHandlingApp(App):
    def on_mount(self) -> None:
        """Widget is mounted and ready"""
        self.title = "Event Demo"
    
    def on_resize(self, event: Resize) -> None:
        """Terminal was resized"""
        self.notify(f"New size: {event.size}")
    
    def on_key(self, event: Key) -> None:
        """Key was pressed"""
        if event.key == "q":
            self.exit()
        elif event.key == "ctrl+c":
            self.exit()
    
    def on_click(self, event: Click) -> None:
        """Mouse click occurred"""
        self.notify(f"Clicked at {event.x}, {event.y}")
```

#### Widget-Specific Events

```python
class FormApp(App):
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter name", id="name-input")
        yield Button("Submit", id="submit-btn")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Input value changed"""
        if len(event.value) >= 3:
            self.query_one("#submit-btn").disabled = False
        else:
            self.query_one("#submit-btn").disabled = True
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter pressed in input"""
        self.process_form()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Button was clicked"""
        if event.button.id == "submit-btn":
            self.process_form()
    
    def process_form(self) -> None:
        name = self.query_one("#name-input", Input).value
        self.notify(f"Hello, {name}!")
```

### Custom Events

#### Defining Custom Events
```python
from textual.message import Message

class UserLoggedIn(Message):
    """Custom event for user login"""
    
    def __init__(self, username: str, user_id: int) -> None:
        super().__init__()
        self.username = username
        self.user_id = user_id

class LoginWidget(Widget):
    def authenticate(self, username: str, password: str) -> None:
        # Perform authentication...
        if success:
            # Post custom event
            self.post_message(UserLoggedIn(username, user_id))
```

#### Handling Custom Events
```python
class MainApp(App):
    def on_user_logged_in(self, event: UserLoggedIn) -> None:
        """Handle custom user login event"""
        self.title = f"Welcome, {event.username}!"
        self.push_screen("dashboard")
```

### Event Bubbling and Capture

```python
class EventBubblingDemo(App):
    def compose(self) -> ComposeResult:
        with Container(id="outer"):
            with Container(id="inner"):
                yield Button("Click me", id="button")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles at app level (bubbled up)"""
        self.notify("App level handler")
        # event.stop()  # Uncomment to stop bubbling
    
    def on_click(self, event: Click) -> None:
        """Handle clicks at various levels"""
        widget = event.widget
        self.notify(f"Clicked on {widget.id or widget.__class__.__name__}")
```

---

## Reactive Properties

### What are Reactive Properties?

Reactive properties automatically update the UI when their values change.

#### Basic Reactive Variables

```python
from textual.reactive import var, reactive
from textual.widget import Widget

class CounterWidget(Widget):
    """Widget with reactive counter"""
    
    # Reactive variable with default value
    count = var(0)
    
    # Alternative syntax
    # count = reactive(0)
    
    def render(self) -> str:
        return f"Count: {self.count}"
    
    def on_click(self) -> None:
        self.count += 1  # Automatically triggers re-render
```

#### Reactive Validation

```python
class ValidationWidget(Widget):
    """Widget with validated reactive properties"""
    
    name = var("")
    age = var(0)
    
    def validate_name(self, name: str) -> str:
        """Validate and transform name"""
        if not name:
            raise ValueError("Name cannot be empty")
        return name.strip().title()
    
    def validate_age(self, age: int) -> int:
        """Validate age"""
        if age < 0:
            raise ValueError("Age cannot be negative")
        if age > 150:
            raise ValueError("Age seems unrealistic")
        return age
    
    def render(self) -> str:
        return f"Name: {self.name}, Age: {self.age}"
```

#### Watch Methods

```python
class WatcherWidget(Widget):
    """Widget that watches reactive changes"""
    
    status = var("idle")
    progress = var(0.0)
    
    def watch_status(self, old_value: str, new_value: str) -> None:
        """Called when status changes"""
        self.notify(f"Status changed from {old_value} to {new_value}")
        
        # Update appearance based on status
        self.remove_class(old_value)
        self.add_class(new_value)
    
    def watch_progress(self, progress: float) -> None:
        """Called when progress changes"""
        if progress >= 1.0:
            self.status = "complete"
        elif progress > 0:
            self.status = "working"
        else:
            self.status = "idle"
```

#### Computed Properties

```python
from textual.reactive import Reactive

class UserProfileWidget(Widget):
    """Widget with computed reactive properties"""
    
    first_name = var("")
    last_name = var("")
    birth_year = var(2000)
    
    @property
    def full_name(self) -> str:
        """Computed property that updates when dependencies change"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def age(self) -> int:
        """Computed age"""
        from datetime import datetime
        return datetime.now().year - self.birth_year
    
    def render(self) -> str:
        return f"{self.full_name} ({self.age} years old)"
```

### Reactive Data Binding

```python
class DataBoundForm(Widget):
    """Form with two-way data binding"""
    
    # Model data
    user_data = var({
        "name": "",
        "email": "",
        "age": 0
    })
    
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Name", id="name")
        yield Input(placeholder="Email", id="email") 
        yield Input(placeholder="Age", id="age")
        yield Button("Save", id="save")
    
    def on_mount(self) -> None:
        """Bind form fields to data"""
        self.bind_data()
    
    def bind_data(self) -> None:
        """Set up two-way binding"""
        name_input = self.query_one("#name", Input)
        email_input = self.query_one("#email", Input)
        age_input = self.query_one("#age", Input)
        
        # Set initial values
        name_input.value = self.user_data["name"]
        email_input.value = self.user_data["email"]
        age_input.value = str(self.user_data["age"])
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Update model when form changes"""
        if event.input.id == "name":
            new_data = self.user_data.copy()
            new_data["name"] = event.value
            self.user_data = new_data
        # ... handle other fields
    
    def watch_user_data(self, data: dict) -> None:
        """Update UI when model changes"""
        self.notify(f"User data updated: {data}")
```

---

## Message Passing

### Message System Overview

Textual uses a message passing system for widget communication and decoupled architecture.

#### Basic Message Passing

```python
from textual.message import Message

# Define custom messages
class DataUpdated(Message):
    """Sent when data is updated"""
    
    def __init__(self, data: dict) -> None:
        super().__init__()
        self.data = data

class StatusChanged(Message):
    """Sent when status changes"""
    
    def __init__(self, status: str, details: str = "") -> None:
        super().__init__()
        self.status = status
        self.details = details

# Widget that sends messages
class DataProvider(Widget):
    """Widget that provides data to other components"""
    
    def load_data(self) -> None:
        """Load and broadcast data"""
        data = {"users": 100, "posts": 500}  # Example data
        self.post_message(DataUpdated(data))
        self.post_message(StatusChanged("loaded", "Data loaded successfully"))

# Widget that receives messages
class StatusDisplay(Widget):
    """Widget that displays status information"""
    
    status = var("ready")
    
    def on_status_changed(self, event: StatusChanged) -> None:
        """Handle status change messages"""
        self.status = event.status
        if event.details:
            self.notify(event.details)
    
    def render(self) -> str:
        return f"Status: {self.status}"
```

#### Parent-Child Communication

```python
class ParentWidget(Widget):
    """Parent widget that manages child state"""
    
    def compose(self) -> ComposeResult:
        yield ChildWidget("child1")
        yield ChildWidget("child2")
    
    def on_child_widget_value_changed(self, event: ChildWidget.ValueChanged) -> None:
        """Handle messages from child widgets"""
        child = event.sender
        self.notify(f"Child {child.name} changed to {event.value}")
        
        # Update other children if needed
        for other_child in self.query(ChildWidget):
            if other_child != child:
                other_child.sync_value(event.value)

class ChildWidget(Widget):
    """Child widget that communicates with parent"""
    
    class ValueChanged(Message):
        """Sent when child value changes"""
        
        def __init__(self, sender: ChildWidget, value: str) -> None:
            super().__init__()
            self.sender = sender
            self.value = value
    
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.value = ""
    
    def on_click(self) -> None:
        """Emit message when clicked"""
        self.value = f"clicked at {time.time()}"
        self.post_message(self.ValueChanged(self, self.value))
```

#### Message Targeting

```python
class MessageTargetingDemo(App):
    """Demonstrate targeted message sending"""
    
    def compose(self) -> ComposeResult:
        with Container(id="container1"):
            yield Button("Button 1", id="btn1")
        with Container(id="container2"):
            yield Button("Button 2", id="btn2")
        yield Button("Broadcast", id="broadcast")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "broadcast":
            # Send to all buttons
            message = CustomMessage("broadcast")
            for button in self.query(Button):
                button.post_message(message)
            
            # Send to specific widget
            specific_widget = self.query_one("#btn1")
            specific_widget.post_message(CustomMessage("targeted"))
```

#### Async Message Handling

```python
class AsyncMessageHandler(Widget):
    """Widget that handles messages asynchronously"""
    
    async def on_data_updated(self, event: DataUpdated) -> None:
        """Async message handler"""
        # Process data asynchronously
        processed_data = await self.process_data_async(event.data)
        
        # Update UI on main thread
        self.call_from_thread(self.update_ui, processed_data)
    
    async def process_data_async(self, data: dict) -> dict:
        """Simulate async data processing"""
        await asyncio.sleep(1)  # Simulate network/disk I/O
        return {key: value * 2 for key, value in data.items()}
    
    def update_ui(self, data: dict) -> None:
        """Update UI with processed data"""
        self.notify(f"Processed: {data}")
```

---

## Screen Management

### Screen System

Screens in Textual are like pages or views in a traditional application.

#### Basic Screen Management

```python
from textual.screen import Screen

class MainScreen(Screen):
    """Main application screen"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Button("Go to Settings", id="settings-btn")
        yield Button("Go to Profile", id="profile-btn")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "settings-btn":
            self.app.push_screen("settings")
        elif event.button.id == "profile-btn":
            self.app.push_screen("profile")

class SettingsScreen(Screen):
    """Settings screen"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Settings Screen")
        yield Button("Back", id="back-btn")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()

class MultiScreenApp(App):
    """App with multiple screens"""
    
    # Define screens
    SCREENS = {
        "main": MainScreen(),
        "settings": SettingsScreen(),
        "profile": ProfileScreen(),
    }
    
    def on_mount(self) -> None:
        """Start with main screen"""
        self.push_screen("main")
```

#### Modal Screens

```python
class ConfirmDialog(Screen):
    """Modal confirmation dialog"""
    
    CSS = """
    ConfirmDialog {
        align: center middle;
    }
    
    #dialog {
        width: 50;
        height: 10;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    """
    
    def __init__(self, message: str, callback: Callable = None) -> None:
        super().__init__()
        self.message = message
        self.callback = callback
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Static(self.message)
            with Horizontal():
                yield Button("Yes", id="yes", variant="primary")
                yield Button("No", id="no", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        result = event.button.id == "yes"
        
        if self.callback:
            self.callback(result)
        
        self.app.pop_screen()  # Close modal

# Usage
class AppWithModal(App):
    def show_confirm_dialog(self) -> None:
        """Show confirmation dialog"""
        dialog = ConfirmDialog(
            "Are you sure you want to delete this item?",
            callback=self.on_confirm_result
        )
        self.push_screen(dialog)
    
    def on_confirm_result(self, confirmed: bool) -> None:
        """Handle dialog result"""
        if confirmed:
            self.notify("Item deleted!")
        else:
            self.notify("Cancelled")
```

#### Screen Navigation

```python
class NavigationApp(App):
    """App demonstrating screen navigation patterns"""
    
    def __init__(self) -> None:
        super().__init__()
        self.screen_stack = []  # Track navigation history
    
    def push_screen_with_history(self, screen_name: str) -> None:
        """Push screen and track in history"""
        current = self.screen.title if hasattr(self.screen, 'title') else 'unknown'
        self.screen_stack.append(current)
        self.push_screen(screen_name)
    
    def pop_screen_with_history(self) -> None:
        """Pop screen and navigate to previous"""
        if self.screen_stack:
            previous = self.screen_stack.pop()
            self.pop_screen()
        else:
            self.exit()  # No more screens to go back to
    
    def on_key(self, event: Key) -> None:
        """Global navigation keys"""
        if event.key == "escape":
            self.pop_screen_with_history()
        elif event.key == "ctrl+h":  # Home
            self.screen_stack.clear()
            self.switch_screen("main")
```

#### Screen Data Passing

```python
class DataPassingScreen(Screen):
    """Screen that receives and displays data"""
    
    def __init__(self, user_data: dict) -> None:
        super().__init__()
        self.user_data = user_data
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Welcome, {self.user_data['name']}!")
        yield Static(f"Email: {self.user_data['email']}")
        yield Button("Edit", id="edit")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "edit":
            # Pass data to edit screen
            edit_screen = EditUserScreen(self.user_data)
            self.app.push_screen(edit_screen)

class EditUserScreen(Screen):
    """Screen for editing user data"""
    
    def __init__(self, user_data: dict) -> None:
        super().__init__()
        self.user_data = user_data.copy()
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(value=self.user_data["name"], id="name")
        yield Input(value=self.user_data["email"], id="email")
        yield Button("Save", id="save")
        yield Button("Cancel", id="cancel")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            # Update data and return
            self.user_data["name"] = self.query_one("#name", Input).value
            self.user_data["email"] = self.query_one("#email", Input).value
            
            # Send data back to calling screen
            self.app.post_message(UserDataUpdated(self.user_data))
            self.app.pop_screen()
        elif event.button.id == "cancel":
            self.app.pop_screen()
```

---

## Rich Integration

### Rich Components in Textual

Textual seamlessly integrates with Rich for advanced text rendering and formatting.

#### Rich Text Rendering

```python
from rich.text import Text
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from textual.widgets import Static

# Rich Text objects
def create_rich_text() -> Text:
    """Create styled Rich Text object"""
    text = Text()
    text.append("Hello ", style="bold cyan")
    text.append("World", style="red on yellow")
    text.append("!", style="bold")
    return text

class RichTextWidget(Static):
    """Widget displaying Rich Text"""
    
    def on_mount(self) -> None:
        rich_text = create_rich_text()
        self.update(rich_text)
```

#### Rich Tables

```python
from rich.table import Table

class DataTableWidget(Static):
    """Widget displaying Rich Table"""
    
    def __init__(self, data: List[dict]) -> None:
        super().__init__()
        self.data = data
    
    def on_mount(self) -> None:
        table = self.create_table()
        self.update(table)
    
    def create_table(self) -> Table:
        """Create Rich Table from data"""
        table = Table(title="User Data", show_header=True)
        
        # Add columns
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Email", style="blue")
        table.add_column("Status", justify="center")
        
        # Add rows
        for user in self.data:
            status_style = "green" if user["active"] else "red"
            status_text = "Active" if user["active"] else "Inactive"
            
            table.add_row(
                str(user["id"]),
                user["name"],
                user["email"],
                f"[{status_style}]{status_text}[/]"
            )
        
        return table
```

#### Syntax Highlighting

```python
from rich.syntax import Syntax

class CodeDisplayWidget(Static):
    """Widget for displaying syntax-highlighted code"""
    
    def __init__(self, code: str, language: str = "python") -> None:
        super().__init__()
        self.code = code
        self.language = language
    
    def on_mount(self) -> None:
        syntax = Syntax(
            self.code,
            self.language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )
        self.update(syntax)

# Usage
python_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Generate first 10 Fibonacci numbers
fib_sequence = [fibonacci(i) for i in range(10)]
print(fib_sequence)
"""

code_widget = CodeDisplayWidget(python_code, "python")
```

#### Progress Bars and Panels

```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

class ProgressWidget(Widget):
    """Widget with Rich progress bar"""
    
    def compose(self) -> ComposeResult:
        yield Static(id="progress-display")
        yield Button("Start Task", id="start")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            self.run_task()
    
    async def run_task(self) -> None:
        """Run task with progress display"""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        
        progress_display = self.query_one("#progress-display", Static)
        
        with progress:
            task = progress.add_task("Processing...", total=100)
            
            for i in range(100):
                await asyncio.sleep(0.05)  # Simulate work
                progress.update(task, advance=1)
                
                # Update display
                panel = Panel(progress, title="Task Progress")
                progress_display.update(panel)
        
        progress_display.update("[bold green]Task completed! ✓[/]")
```

#### Rich Console for Logging

```python
from rich.console import Console
from rich.logging import RichHandler
import logging

class LoggingWidget(Widget):
    """Widget with Rich-enhanced logging"""
    
    def __init__(self) -> None:
        super().__init__()
        self.console = Console()
        self.setup_logging()
    
    def setup_logging(self) -> None:
        """Configure Rich logging handler"""
        logging.basicConfig(
            level="DEBUG",
            format="%(message)s",
            handlers=[RichHandler(console=self.console, markup=True)]
        )
        self.logger = logging.getLogger("app")
    
    def compose(self) -> ComposeResult:
        yield Button("Debug", id="debug")
        yield Button("Info", id="info")
        yield Button("Warning", id="warning")
        yield Button("Error", id="error")
        yield Static(id="log-display")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        
        if button_id == "debug":
            self.logger.debug("This is a [cyan]debug[/] message")
        elif button_id == "info":
            self.logger.info("This is an [green]info[/] message")
        elif button_id == "warning":
            self.logger.warning("This is a [yellow]warning[/] message")
        elif button_id == "error":
            self.logger.error("This is an [red]error[/] message")
```

---

## Typer CLI Integration

### Building CLIs with Textual and Typer

Combine Textual's rich UI capabilities with Typer's CLI framework for powerful command-line applications.

#### Basic CLI with TUI Mode

```python
import typer
from typing import Optional
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

# Textual TUI App
class DataViewerApp(App):
    """TUI for viewing data"""
    
    def __init__(self, data_file: str) -> None:
        super().__init__()
        self.data_file = data_file
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Viewing: {self.data_file}", id="title")
        yield Static("Data content here...", id="content")
        yield Footer()
    
    def on_mount(self) -> None:
        self.title = f"Data Viewer - {self.data_file}"
        # Load and display data
        self.load_data()
    
    def load_data(self) -> None:
        """Load data from file"""
        try:
            with open(self.data_file, 'r') as f:
                content = f.read()
            self.query_one("#content", Static).update(content)
        except FileNotFoundError:
            self.query_one("#content", Static).update(
                f"[red]Error: File '{self.data_file}' not found[/]"
            )

# Typer CLI App
app = typer.Typer()

@app.command()
def view(
    file: str = typer.Argument(..., help="File to view"),
    tui: bool = typer.Option(False, "--tui", help="Launch TUI mode"),
    format_output: bool = typer.Option(True, "--format/--no-format", help="Format output")
):
    """View file contents"""
    if tui:
        # Launch TUI
        tui_app = DataViewerApp(file)
        tui_app.run()
    else:
        # CLI mode
        try:
            with open(file, 'r') as f:
                content = f.read()
            
            if format_output:
                typer.echo(f"📁 File: {file}")
                typer.echo("─" * 40)
            
            typer.echo(content)
            
        except FileNotFoundError:
            typer.echo(f"Error: File '{file}' not found", err=True)
            raise typer.Exit(1)

@app.command()
def config():
    """Open configuration TUI"""
    config_app = ConfigApp()
    config_app.run()

if __name__ == "__main__":
    app()
```

#### CLI with Multiple TUI Modes

```python
import typer
from enum import Enum
from pathlib import Path

class UIMode(str, Enum):
    cli = "cli"
    tui = "tui"
    web = "web"

class LogViewerApp(App):
    """TUI for log viewing"""
    
    CSS = """
    .log-entry {
        margin: 0 1;
        padding: 0 1;
    }
    
    .log-entry.error {
        background: red 20%;
        color: white;
    }
    
    .log-entry.warning {
        background: yellow 20%;
        color: black;
    }
    
    .log-entry.info {
        background: blue 20%;
        color: white;
    }
    """
    
    def __init__(self, log_files: List[Path], filter_level: str = "info") -> None:
        super().__init__()
        self.log_files = log_files
        self.filter_level = filter_level
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Input(placeholder="Filter logs...", id="filter")
            with ScrollableContainer():
                yield Static(id="log-content")
        yield Footer()
    
    def on_mount(self) -> None:
        self.load_logs()
    
    def load_logs(self) -> None:
        """Load and display logs"""
        log_entries = []
        for log_file in self.log_files:
            # Parse log files and create entries
            entries = self.parse_log_file(log_file)
            log_entries.extend(entries)
        
        # Filter by level
        filtered = [
            entry for entry in log_entries 
            if entry["level"] >= self.filter_level
        ]
        
        # Display
        content = self.format_log_entries(filtered)
        self.query_one("#log-content", Static).update(content)

# CLI Application
app = typer.Typer()

@app.command()
def logs(
    files: List[Path] = typer.Argument(..., help="Log files to view"),
    mode: UIMode = typer.Option(UIMode.cli, help="Interface mode"),
    level: str = typer.Option("info", help="Minimum log level"),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log updates"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Save filtered logs")
):
    """View and analyze log files"""
    
    # Validate files exist
    for file in files:
        if not file.exists():
            typer.echo(f"Error: File {file} does not exist", err=True)
            raise typer.Exit(1)
    
    if mode == UIMode.tui:
        # Launch TUI
        log_app = LogViewerApp(files, level)
        log_app.run()
        
    elif mode == UIMode.cli:
        # CLI mode with Rich output
        from rich.console import Console
        console = Console()
        
        for file in files:
            console.print(f"📄 {file}", style="bold blue")
            # Process and display logs
            
    elif mode == UIMode.web:
        # Launch web interface (using Textual Web)
        typer.echo("Launching web interface...")
        # Implementation for web mode

@app.command()
def analyze(
    files: List[Path] = typer.Argument(..., help="Log files to analyze"),
    output_format: str = typer.Option("table", help="Output format (table, json, csv)")
):
    """Analyze log files and generate reports"""
    
    if output_format == "table":
        # Use Rich tables for CLI output
        from rich.table import Table
        from rich.console import Console
        
        console = Console()
        table = Table(title="Log Analysis")
        table.add_column("File", style="cyan")
        table.add_column("Total Entries", justify="right")
        table.add_column("Errors", justify="right", style="red")
        table.add_column("Warnings", justify="right", style="yellow")
        
        for file in files:
            stats = analyze_log_file(file)
            table.add_row(
                str(file),
                str(stats["total"]),
                str(stats["errors"]),
                str(stats["warnings"])
            )
        
        console.print(table)
    
    # Other output formats...

if __name__ == "__main__":
    app()
```

#### Configuration Management

```python
import typer
from pathlib import Path
import json
from typing import Dict, Any

# Configuration TUI
class ConfigApp(App):
    """TUI for managing application configuration"""
    
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.config_data = {}
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("Configuration", id="title")
            yield Input(id="key-input", placeholder="Setting key")
            yield Input(id="value-input", placeholder="Setting value")
            with Horizontal():
                yield Button("Set", id="set", variant="primary")
                yield Button("Delete", id="delete", variant="error")
                yield Button("Save", id="save", variant="success")
            yield Static(id="config-display")
        yield Footer()
    
    def on_mount(self) -> None:
        self.load_config()
        self.update_display()
    
    def load_config(self) -> None:
        """Load configuration from file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config_data = json.load(f)
    
    def save_config(self) -> None:
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config_data, f, indent=2)
    
    def update_display(self) -> None:
        """Update configuration display"""
        display = "\n".join([
            f"{key}: {value}" 
            for key, value in self.config_data.items()
        ])
        self.query_one("#config-display", Static).update(display or "[dim]No settings[/]")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        key_input = self.query_one("#key-input", Input)
        value_input = self.query_one("#value-input", Input)
        
        if event.button.id == "set":
            if key_input.value and value_input.value:
                self.config_data[key_input.value] = value_input.value
                key_input.value = ""
                value_input.value = ""
                self.update_display()
                self.notify("Setting added")
        
        elif event.button.id == "delete":
            if key_input.value in self.config_data:
                del self.config_data[key_input.value]
                key_input.value = ""
                self.update_display()
                self.notify("Setting deleted")
        
        elif event.button.id == "save":
            self.save_config()
            self.notify("Configuration saved")

# CLI with config management
config_app = typer.Typer()

@config_app.command("edit")
def edit_config(
    config_file: Path = typer.Option(
        Path.home() / ".myapp" / "config.json",
        help="Configuration file path"
    )
):
    """Edit configuration using TUI"""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    tui_app = ConfigApp(config_file)
    tui_app.run()

@config_app.command("get")
def get_setting(
    key: str = typer.Argument(..., help="Setting key"),
    config_file: Path = typer.Option(
        Path.home() / ".myapp" / "config.json",
        help="Configuration file path"
    )
):
    """Get a configuration setting"""
    if not config_file.exists():
        typer.echo("Configuration file not found", err=True)
        raise typer.Exit(1)
    
    with open(config_file) as f:
        config = json.load(f)
    
    if key in config:
        typer.echo(config[key])
    else:
        typer.echo(f"Setting '{key}' not found", err=True)
        raise typer.Exit(1)

@config_app.command("set")
def set_setting(
    key: str = typer.Argument(..., help="Setting key"),
    value: str = typer.Argument(..., help="Setting value"),
    config_file: Path = typer.Option(
        Path.home() / ".myapp" / "config.json",
        help="Configuration file path"
    )
):
    """Set a configuration setting"""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    config = {}
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
    
    config[key] = value
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    typer.echo(f"Set {key} = {value}")

# Main CLI app
main_app = typer.Typer()
main_app.add_typer(config_app, name="config")

if __name__ == "__main__":
    main_app()
```

---

## Performance Considerations

### Rendering Performance

#### Efficient Widget Updates
```python
class EfficientWidget(Widget):
    """Widget optimized for performance"""
    
    def __init__(self) -> None:
        super().__init__()
        self._cached_content = None
        self._content_dirty = True
    
    def render(self) -> str:
        """Use cached rendering when possible"""
        if self._content_dirty or self._cached_content is None:
            self._cached_content = self._generate_content()
            self._content_dirty = False
        
        return self._cached_content
    
    def _generate_content(self) -> str:
        """Generate content (expensive operation)"""
        # Expensive rendering logic here
        return "Generated content"
    
    def mark_dirty(self) -> None:
        """Mark content as needing re-render"""
        self._content_dirty = True
        self.refresh()
```

#### Batch Updates
```python
class BatchUpdateWidget(Widget):
    """Widget that batches multiple updates"""
    
    def __init__(self) -> None:
        super().__init__()
        self._pending_updates = []
        self._update_timer = None
    
    def queue_update(self, data: Any) -> None:
        """Queue an update for batching"""
        self._pending_updates.append(data)
        
        # Cancel existing timer
        if self._update_timer:
            self._update_timer.cancel()
        
        # Schedule batch update
        self._update_timer = self.set_timer(0.1, self._apply_batch_updates)
    
    def _apply_batch_updates(self) -> None:
        """Apply all queued updates at once"""
        if self._pending_updates:
            # Process all updates together
            processed_data = self._process_batch(self._pending_updates)
            self._pending_updates.clear()
            
            # Single UI update
            self._update_display(processed_data)
    
    def _process_batch(self, updates: List[Any]) -> Any:
        """Process multiple updates efficiently"""
        # Combine/deduplicate/optimize updates
        return updates
    
    def _update_display(self, data: Any) -> None:
        """Update display once for all batched changes"""
        self.refresh()
```

### Memory Management

#### Large Dataset Handling
```python
class VirtualizedListWidget(Widget):
    """List widget that virtualizes large datasets"""
    
    def __init__(self, data_source: Callable, total_items: int) -> None:
        super().__init__()
        self.data_source = data_source
        self.total_items = total_items
        self.visible_range = (0, 50)  # Only keep visible items in memory
        self.item_cache = {}
    
    def render(self) -> str:
        """Render only visible items"""
        start, end = self.visible_range
        lines = []
        
        for i in range(start, min(end, self.total_items)):
            item = self._get_item(i)
            lines.append(str(item))
        
        return "\n".join(lines)
    
    def _get_item(self, index: int) -> Any:
        """Get item with caching"""
        if index not in self.item_cache:
            # Only cache visible items
            if len(self.item_cache) > 100:  # Limit cache size
                # Remove oldest items
                oldest = min(self.item_cache.keys())
                del self.item_cache[oldest]
            
            self.item_cache[index] = self.data_source(index)
        
        return self.item_cache[index]
    
    def scroll_to(self, index: int) -> None:
        """Scroll to specific index"""
        visible_count = 50
        self.visible_range = (index, index + visible_count)
        self.refresh()
```

#### Resource Cleanup
```python
class ResourceAwareWidget(Widget):
    """Widget that properly manages resources"""
    
    def __init__(self) -> None:
        super().__init__()
        self._timers = []
        self._background_tasks = set()
    
    def set_interval_tracked(self, interval: float, callback: Callable) -> None:
        """Set interval timer and track for cleanup"""
        timer = self.set_interval(interval, callback)
        self._timers.append(timer)
    
    async def start_background_task(self, coro: Coroutine) -> None:
        """Start background task and track for cleanup"""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def on_unmount(self) -> None:
        """Clean up resources when widget unmounts"""
        # Cancel all timers
        for timer in self._timers:
            timer.cancel()
        self._timers.clear()
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to finish cancellation
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        await super().on_unmount()
```

### Layout Optimization

#### Minimize Layout Thrashing
```python
class LayoutOptimizedWidget(Widget):
    """Widget that minimizes layout calculations"""
    
    def __init__(self) -> None:
        super().__init__()
        self._layout_dirty = True
        self._last_size = None
    
    def on_resize(self, event) -> None:
        """Only recalculate layout when size actually changes"""
        new_size = (event.size.width, event.size.height)
        
        if self._last_size != new_size:
            self._layout_dirty = True
            self._last_size = new_size
    
    def render(self) -> str:
        """Use cached layout when possible"""
        if self._layout_dirty:
            self._recalculate_layout()
            self._layout_dirty = False
        
        return self._render_with_layout()
    
    def _recalculate_layout(self) -> None:
        """Expensive layout calculation"""
        # Only called when actually needed
        pass
```

---

## Common Patterns

### Form Handling Pattern

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional
from textual.validation import Validator, ValidationResult

@dataclass
class UserData:
    name: str = ""
    email: str = ""
    age: int = 0

class EmailValidator(Validator):
    """Validate email addresses"""
    
    def validate(self, value: str) -> ValidationResult:
        if "@" not in value:
            return self.failure("Must contain @ symbol")
        if "." not in value.split("@")[1]:
            return self.failure("Invalid email format")
        return self.success()

class FormApp(App):
    """Complete form handling pattern"""
    
    CSS = """
    .form-group {
        margin: 1 0;
    }
    
    .form-label {
        color: $text-muted;
    }
    
    .form-input {
        margin: 0 0 1 0;
    }
    
    .form-actions {
        margin: 2 0 0 0;
    }
    
    .error {
        background: red 20%;
        color: white;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            with Container(classes="form-group"):
                yield Label("Name:", classes="form-label")
                yield Input(
                    placeholder="Enter your name",
                    id="name",
                    classes="form-input"
                )
            
            with Container(classes="form-group"):
                yield Label("Email:", classes="form-label")
                yield Input(
                    placeholder="Enter your email",
                    id="email",
                    classes="form-input",
                    validators=[EmailValidator()]
                )
            
            with Container(classes="form-group"):
                yield Label("Age:", classes="form-label")
                yield Input(
                    placeholder="Enter your age",
                    id="age",
                    classes="form-input"
                )
            
            with Horizontal(classes="form-actions"):
                yield Button("Submit", id="submit", variant="primary")
                yield Button("Clear", id="clear", variant="default")
        
        yield Static(id="messages")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.submit_form()
        elif event.button.id == "clear":
            self.clear_form()
    
    def submit_form(self) -> None:
        """Validate and submit form"""
        # Collect form data
        form_data = self.get_form_data()
        
        # Validate
        errors = self.validate_form(form_data)
        if errors:
            self.show_errors(errors)
            return
        
        # Process form
        try:
            self.process_form_data(form_data)
            self.show_success("Form submitted successfully!")
            self.clear_form()
        except Exception as e:
            self.show_errors([f"Submission failed: {e}"])
    
    def get_form_data(self) -> Dict[str, Any]:
        """Extract data from form fields"""
        return {
            "name": self.query_one("#name", Input).value,
            "email": self.query_one("#email", Input).value,
            "age": self.query_one("#age", Input).value
        }
    
    def validate_form(self, data: Dict[str, Any]) -> List[str]:
        """Validate form data"""
        errors = []
        
        if not data["name"].strip():
            errors.append("Name is required")
        
        if not data["email"].strip():
            errors.append("Email is required")
        
        try:
            age = int(data["age"])
            if age < 0 or age > 120:
                errors.append("Age must be between 0 and 120")
        except ValueError:
            errors.append("Age must be a number")
        
        return errors
    
    def process_form_data(self, data: Dict[str, Any]) -> None:
        """Process validated form data"""
        user_data = UserData(
            name=data["name"],
            email=data["email"],
            age=int(data["age"])
        )
        # Save to database, send to API, etc.
    
    def show_errors(self, errors: List[str]) -> None:
        """Display validation errors"""
        error_text = "\n".join([f"❌ {error}" for error in errors])
        messages = self.query_one("#messages", Static)
        messages.update(error_text)
        messages.add_class("error")
    
    def show_success(self, message: str) -> None:
        """Display success message"""
        messages = self.query_one("#messages", Static)
        messages.update(f"✅ {message}")
        messages.remove_class("error")
    
    def clear_form(self) -> None:
        """Clear all form fields"""
        self.query_one("#name", Input).value = ""
        self.query_one("#email", Input).value = ""
        self.query_one("#age", Input).value = ""
        self.query_one("#messages", Static).update("")
```

### Data Loading Pattern

```python
import asyncio
from typing import Optional, List, Dict, Any
from enum import Enum

class LoadingState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"

class DataLoader(Widget):
    """Reusable data loading pattern"""
    
    state = var(LoadingState.IDLE)
    data = var(None)
    error_message = var("")
    
    CSS = """
    DataLoader {
        align: center middle;
        height: 100%;
    }
    
    .loading {
        color: $accent;
        text-style: bold;
    }
    
    .error {
        background: red 20%;
        color: white;
        padding: 1;
        border: thick red;
    }
    
    .success {
        background: green 20%;
        color: white;
    }
    """
    
    def __init__(self, loader_func: Callable, auto_load: bool = True) -> None:
        super().__init__()
        self.loader_func = loader_func
        if auto_load:
            self.call_after_refresh(self.load_data)
    
    def compose(self) -> ComposeResult:
        yield Static(id="content")
        yield Button("Retry", id="retry", variant="primary")
    
    def on_mount(self) -> None:
        self.query_one("#retry").display = False
    
    async def load_data(self) -> None:
        """Load data with state management"""
        self.state = LoadingState.LOADING
        self.error_message = ""
        
        try:
            # Call the loader function
            if asyncio.iscoroutinefunction(self.loader_func):
                result = await self.loader_func()
            else:
                result = self.loader_func()
            
            self.data = result
            self.state = LoadingState.SUCCESS
            
        except Exception as e:
            self.error_message = str(e)
            self.state = LoadingState.ERROR
    
    def watch_state(self, state: LoadingState) -> None:
        """Update UI based on loading state"""
        content = self.query_one("#content", Static)
        retry_btn = self.query_one("#retry", Button)
        
        if state == LoadingState.LOADING:
            content.update("[.loading]⏳ Loading...[/]")
            retry_btn.display = False
        
        elif state == LoadingState.SUCCESS:
            content.update(self.render_data())
            retry_btn.display = False
        
        elif state == LoadingState.ERROR:
            content.update(f"[.error]❌ Error: {self.error_message}[/]")
            retry_btn.display = True
        
        else:  # IDLE
            content.update("")
            retry_btn.display = False
    
    def render_data(self) -> str:
        """Override to customize data rendering"""
        if isinstance(self.data, (list, tuple)):
            return f"[.success]✅ Loaded {len(self.data)} items[/]"
        elif isinstance(self.data, dict):
            return f"[.success]✅ Loaded {len(self.data)} keys[/]"
        else:
            return f"[.success]✅ Data loaded: {self.data}[/]"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "retry":
            self.load_data()

# Usage example
async def fetch_users() -> List[Dict[str, Any]]:
    """Simulate API call"""
    await asyncio.sleep(2)  # Simulate network delay
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
    ]

class UserDataLoader(DataLoader):
    """Specialized loader for user data"""
    
    def render_data(self) -> str:
        """Custom rendering for user data"""
        if not self.data:
            return "[dim]No users found[/]"
        
        users = self.data
        lines = ["[bold]Users:[/]"]
        for user in users:
            lines.append(f"• {user['name']} ({user['email']})")
        
        return "\n".join(lines)

class DataApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield UserDataLoader(fetch_users)
        yield Footer()
```

### Modular Component Pattern

```python
from abc import ABC, abstractmethod
from typing import Protocol

class Configurable(Protocol):
    """Protocol for configurable components"""
    
    def configure(self, **kwargs) -> None:
        """Configure the component"""
        ...

class Component(Widget, ABC):
    """Base class for reusable components"""
    
    def __init__(self, **config) -> None:
        super().__init__()
        self.config = config
        self.configure(**config)
    
    @abstractmethod
    def configure(self, **kwargs) -> None:
        """Configure component with parameters"""
        pass

class SearchBox(Component):
    """Reusable search component"""
    
    class SearchSubmitted(Message):
        """Sent when search is submitted"""
        
        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query
    
    def configure(
        self,
        placeholder: str = "Search...",
        show_button: bool = True,
        auto_search: bool = False,
        **kwargs
    ) -> None:
        """Configure search box"""
        self.placeholder = placeholder
        self.show_button = show_button
        self.auto_search = auto_search
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder=self.placeholder, id="search-input")
            if self.show_button:
                yield Button("Search", id="search-btn", variant="primary")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        if self.auto_search and len(event.value) >= 3:
            self.post_message(self.SearchSubmitted(event.value))
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.post_message(self.SearchSubmitted(event.value))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-btn":
            query = self.query_one("#search-input", Input).value
            self.post_message(self.SearchSubmitted(query))

class StatusBar(Component):
    """Reusable status bar component"""
    
    CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $boost;
        color: $text;
        padding: 0 1;
    }
    
    .status-item {
        margin: 0 2;
    }
    """
    
    status_items = var({})
    
    def configure(
        self,
        items: Dict[str, str] = None,
        show_time: bool = True,
        **kwargs
    ) -> None:
        """Configure status bar"""
        self.status_items = items or {}
        self.show_time = show_time
        
        if self.show_time:
            self.set_interval(1, self.update_time)
    
    def compose(self) -> ComposeResult:
        yield Static(id="status-content")
    
    def update_time(self) -> None:
        """Update current time"""
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        items = self.status_items.copy()
        items["time"] = current_time
        self.status_items = items
    
    def watch_status_items(self, items: Dict[str, str]) -> None:
        """Update status display when items change"""
        content_parts = []
        for key, value in items.items():
            content_parts.append(f"[.status-item]{key}: {value}[/]")
        
        content = " | ".join(content_parts)
        self.query_one("#status-content", Static).update(content)
    
    def set_status(self, key: str, value: str) -> None:
        """Set individual status item"""
        new_items = self.status_items.copy()
        new_items[key] = value
        self.status_items = new_items

# Usage - composing components
class ComposedApp(App):
    """App built from reusable components"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        # Search component
        yield SearchBox(
            placeholder="Search products...",
            auto_search=True,
            show_button=True
        )
        
        # Main content
        yield Container(Static("Main content here"), id="main")
        
        # Status bar component
        yield StatusBar(
            items={"users": "0", "products": "0"},
            show_time=True
        )
    
    def on_search_box_search_submitted(self, event: SearchBox.SearchSubmitted) -> None:
        """Handle search from component"""
        self.notify(f"Searching for: {event.query}")
        # Perform search...
    
    def on_mount(self) -> None:
        """Update status with real data"""
        status_bar = self.query_one(StatusBar)
        status_bar.set_status("users", "150")
        status_bar.set_status("products", "1,234")
```

---

## Anti-Patterns to Avoid

### Common Mistakes

#### 1. Direct DOM Manipulation
```python
# ❌ BAD: Direct manipulation without framework knowledge
class BadWidget(Widget):
    def on_click(self) -> None:
        # Directly accessing private attributes
        self._content = "Changed!"
        # Manual refresh calls everywhere
        self.refresh()

# ✅ GOOD: Use reactive properties
class GoodWidget(Widget):
    content = var("Initial")
    
    def on_click(self) -> None:
        self.content = "Changed!"  # Automatically triggers refresh
```

#### 2. Blocking Operations in Event Handlers
```python
# ❌ BAD: Blocking the UI thread
class BadAsyncWidget(Widget):
    def on_button_pressed(self, event: Button.Pressed) -> None:
        import time
        time.sleep(5)  # Blocks entire UI
        self.notify("Done!")

# ✅ GOOD: Use async methods
class GoodAsyncWidget(Widget):
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        await asyncio.sleep(5)  # Non-blocking
        self.notify("Done!")
    
    # Or run in background
    def on_button_pressed_alt(self, event: Button.Pressed) -> None:
        self.run_worker(self.background_task(), exclusive=True)
    
    async def background_task(self) -> None:
        await asyncio.sleep(5)
        self.notify("Done!")
```

#### 3. Memory Leaks with Timers and Tasks
```python
# ❌ BAD: Unmanaged resources
class LeakyWidget(Widget):
    def on_mount(self) -> None:
        # Timer never gets cleaned up
        self.set_interval(1, self.update_data)
        
        # Task reference not tracked
        asyncio.create_task(self.background_work())

# ✅ GOOD: Proper resource management
class CleanWidget(Widget):
    def __init__(self) -> None:
        super().__init__()
        self._timers = []
        self._tasks = set()
    
    def on_mount(self) -> None:
        timer = self.set_interval(1, self.update_data)
        self._timers.append(timer)
        
        task = asyncio.create_task(self.background_work())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
    
    async def on_unmount(self) -> None:
        # Clean up resources
        for timer in self._timers:
            timer.cancel()
        
        for task in self._tasks:
            if not task.done():
                task.cancel()
```

#### 4. Inefficient Re-rendering
```python
# ❌ BAD: Excessive re-renders
class InefficientWidget(Widget):
    def __init__(self) -> None:
        super().__init__()
        self.data = []
    
    def render(self) -> str:
        # Complex calculation on every render
        processed = []
        for item in self.data:
            processed.append(expensive_transform(item))
        return "\n".join(processed)

# ✅ GOOD: Cached rendering
class EfficientWidget(Widget):
    def __init__(self) -> None:
        super().__init__()
        self._data = []
        self._cached_render = None
        self._data_dirty = True
    
    @property
    def data(self) -> list:
        return self._data
    
    @data.setter
    def data(self, value: list) -> None:
        self._data = value
        self._data_dirty = True
        self.refresh()
    
    def render(self) -> str:
        if self._data_dirty or self._cached_render is None:
            processed = [expensive_transform(item) for item in self._data]
            self._cached_render = "\n".join(processed)
            self._data_dirty = False
        
        return self._cached_render
```

#### 5. Poor Error Handling
```python
# ❌ BAD: Silent failures
class BadErrorHandling(Widget):
    def load_data(self) -> None:
        try:
            data = risky_operation()
            self.display_data(data)
        except:
            pass  # Silent failure

# ✅ GOOD: Proper error handling
class GoodErrorHandling(Widget):
    def load_data(self) -> None:
        try:
            data = risky_operation()
            self.display_data(data)
        except ConnectionError as e:
            self.show_error("Connection failed. Please check your internet.")
            self.log.error(f"Connection error: {e}")
        except ValueError as e:
            self.show_error("Invalid data received.")
            self.log.error(f"Data validation error: {e}")
        except Exception as e:
            self.show_error("An unexpected error occurred.")
            self.log.exception(f"Unexpected error in load_data: {e}")
    
    def show_error(self, message: str) -> None:
        self.notify(message, severity="error")
        # Also update UI to show error state
```

#### 6. Tight Coupling Between Components
```python
# ❌ BAD: Tight coupling
class TightlyCoupledParent(Widget):
    def compose(self) -> ComposeResult:
        self.search_widget = SpecificSearchWidget()
        self.results_widget = SpecificResultsWidget()
        
        # Direct method calls create tight coupling
        self.search_widget.set_results_widget(self.results_widget)
        
        yield self.search_widget
        yield self.results_widget

# ✅ GOOD: Loose coupling through messages
class LooselyCoupledParent(Widget):
    def compose(self) -> ComposeResult:
        yield SearchWidget()  # Generic, reusable
        yield ResultsWidget()  # Generic, reusable
    
    def on_search_widget_search_submitted(self, event: SearchWidget.SearchSubmitted) -> None:
        # Parent coordinates between widgets
        results_widget = self.query_one(ResultsWidget)
        results_widget.search(event.query)
```

---

## Conclusion

This comprehensive guide covers the core concepts and patterns needed to build sophisticated terminal user interfaces with Textual. The framework's combination of declarative composition, CSS-like styling, reactive properties, and rich text rendering makes it a powerful choice for Python TUI development.

**Key Takeaways:**

1. **Structure applications** using the Widget/Container hierarchy
2. **Separate concerns** with TCSS styling and reactive properties
3. **Handle events asynchronously** to maintain responsive UIs
4. **Leverage Rich integration** for advanced text rendering
5. **Integrate with Typer** for powerful CLI applications
6. **Follow performance best practices** for smooth user experiences
7. **Use proven patterns** for common UI scenarios
8. **Avoid anti-patterns** that lead to maintenance issues

For additional resources and up-to-date information, refer to the official Textual documentation and the growing ecosystem of Textual applications and extensions.

---

*This documentation is optimized for LLM parsing and practical implementation. Each code example is self-contained and follows current best practices as of 2024-2025.*