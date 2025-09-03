# Textual Widget Patterns - Production-Ready Components

This comprehensive guide covers advanced widget patterns, compound widgets, modal dialogs, and reusable components for building sophisticated TUI applications with Textual.

## Table of Contents

- [Built-in Widget Catalog](#built-in-widget-catalog)
- [Custom Widget Development Lifecycle](#custom-widget-development-lifecycle)
- [Compound Widgets](#compound-widgets)
- [Form Components and Validation](#form-components-and-validation)
- [Data Display Widgets](#data-display-widgets)
- [Modal and Dialog Patterns](#modal-and-dialog-patterns)
- [Tab and Accordion Interfaces](#tab-and-accordion-interfaces)
- [Progress Indicators and Loading States](#progress-indicators-and-loading-states)
- [Charts and Data Visualization](#charts-and-data-visualization)
- [Responsive Widget Design](#responsive-widget-design)
- [Widget Styling with TCSS](#widget-styling-with-tcss)
- [Animation and Transitions](#animation-and-transitions)
- [Keyboard Navigation Patterns](#keyboard-navigation-patterns)
- [Focus Management](#focus-management)
- [Accessibility Considerations](#accessibility-considerations)
- [Advanced Patterns](#advanced-patterns)

---

## Built-in Widget Catalog

### Core Input Widgets

#### Input Widget
**Purpose**: Single-line text input with validation and restrictions
**Use Cases**: Forms, search fields, data entry

```python
from textual.app import App, ComposeResult
from textual.widgets import Input, Header, Footer

class InputApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Enter your name")
        yield Input(placeholder="Enter binary digits", restrict=r"[01]*")
        yield Input(placeholder="Password", password=True)
        yield Footer()

app = InputApp()
```

**CSS Styling**:
```css
Input {
    border: solid $primary;
    background: $surface;
    color: $text;
}

Input:focus {
    border: solid $accent;
}

Input.-invalid {
    border: solid $error;
}
```

#### MaskedInput Widget
**Purpose**: Formatted input with predefined patterns
**Use Cases**: Credit cards, phone numbers, dates

```python
from textual.widgets import MaskedInput

class MaskedInputApp(App):
    def compose(self) -> ComposeResult:
        yield MaskedInput("9999-9999-9999-9999", id="credit-card")
        yield MaskedInput("(999) 999-9999", id="phone")
        yield MaskedInput("99/99/9999", id="date")
```

#### TextArea Widget
**Purpose**: Multi-line text editing with syntax highlighting
**Use Cases**: Code editors, documentation, long-form text

```python
from textual.widgets import TextArea

class CodeEditor(App):
    def compose(self) -> ComposeResult:
        yield TextArea(
            language="python",
            theme="monokai",
            show_line_numbers=True,
            soft_wrap=True,
            read_only=False
        )
```

### Selection Widgets

#### Button Widget with Variants
**Purpose**: Trigger actions with semantic styling
**Use Cases**: Forms, toolbars, confirmations

```python
from textual.widgets import Button

class ButtonExamples(Widget):
    def compose(self) -> ComposeResult:
        yield Button("Default")
        yield Button("Primary", variant="primary")
        yield Button("Success", variant="success")
        yield Button("Warning", variant="warning")
        yield Button("Error", variant="error")
```

#### Checkbox and RadioButton
**Purpose**: Boolean and exclusive selection
**Use Cases**: Settings, options, forms

```python
from textual.widgets import Checkbox, RadioButton, RadioSet

class SelectionApp(App):
    def compose(self) -> ComposeResult:
        yield Checkbox("Enable notifications")
        with RadioSet():
            yield RadioButton("Option A")
            yield RadioButton("Option B")
            yield RadioButton("Option C")
```

### Display Widgets

#### DataTable Widget
**Purpose**: Tabular data display with sorting and selection
**Use Cases**: Data grids, reports, structured information

```python
from textual.widgets import DataTable

class DataApp(App):
    def compose(self) -> ComposeResult:
        table = DataTable(
            zebra_stripes=True,
            show_cursor=True,
            cursor_type="row"
        )
        table.add_columns("Name", "Age", "City")
        table.add_rows([
            ("Alice", 30, "New York"),
            ("Bob", 25, "London"),
            ("Charlie", 35, "Tokyo")
        ])
        yield table
```

---

## Custom Widget Development Lifecycle

### Basic Widget Structure

```python
from textual.widget import Widget
from textual.reactive import var, reactive
from textual.app import ComposeResult

class CustomWidget(Widget):
    """Template for custom widget development."""
    
    # Default CSS styles
    DEFAULT_CSS = """
    CustomWidget {
        background: $surface;
        border: solid $primary;
        padding: 1;
    }
    """
    
    # Component classes for styling
    COMPONENT_CLASSES = {
        "custom--header",
        "custom--body",
        "custom--footer",
    }
    
    # Reactive attributes
    value = reactive("")
    enabled = var(True)
    
    def __init__(self, initial_value: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.value = initial_value
    
    def render(self) -> str:
        """Simple widgets use render for display."""
        return f"Value: {self.value}"
    
    def watch_value(self, old_value: str, new_value: str) -> None:
        """React to value changes."""
        if old_value != new_value:
            self.refresh()
    
    def on_click(self) -> None:
        """Handle click events."""
        if self.enabled:
            self.post_message(self.ValueChanged(self, self.value))
    
    class ValueChanged(Message):
        """Custom message for value changes."""
        
        def __init__(self, sender: Widget, value: str) -> None:
            self.value = value
            super().__init__(sender)
```

### Advanced Custom Widget with Line API

```python
from textual.strip import Strip
from textual.segment import Segment
from textual.color import Color

class CheckerboardWidget(Widget):
    """High-performance widget using Line API."""
    
    def __init__(self, width: int = 80, height: int = 24, **kwargs) -> None:
        super().__init__(**kwargs)
        self.board_width = width
        self.board_height = height
    
    def render_line(self, y: int) -> Strip:
        """Render individual lines for performance."""
        segments: list[Segment] = []
        for x in range(self.board_width):
            if (x + y) % 2 == 0:
                segments.append(
                    Segment(" ", Color(255, 255, 255), Color(0, 0, 0))
                )
            else:
                segments.append(
                    Segment(" ", Color(0, 0, 0), Color(255, 255, 255))
                )
        return Strip(segments)
```

---

## Compound Widgets

### Form Components Pattern

```python
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Label, Input, Button

class LabeledInput(Widget):
    """Input with associated label."""
    
    DEFAULT_CSS = """
    LabeledInput {
        layout: horizontal;
        height: auto;
        margin: 1 0;
    }
    
    LabeledInput Label {
        width: 20;
        text-align: right;
        margin-right: 2;
    }
    
    LabeledInput Input {
        width: 1fr;
    }
    """
    
    def __init__(self, label: str, placeholder: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.label_text = label
        self.placeholder_text = placeholder
    
    def compose(self) -> ComposeResult:
        yield Label(self.label_text)
        yield Input(placeholder=self.placeholder_text, id="input")
    
    @property
    def value(self) -> str:
        """Get the input value."""
        return self.query_one("#input", Input).value
    
    @value.setter
    def value(self, new_value: str) -> None:
        """Set the input value."""
        self.query_one("#input", Input).value = new_value

class UserForm(Widget):
    """Complete form using compound widgets."""
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield LabeledInput("Name:", "Enter full name")
            yield LabeledInput("Email:", "user@example.com")
            yield LabeledInput("Phone:", "555-0123")
            with Horizontal():
                yield Button("Submit", variant="primary", id="submit")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            # Collect form data
            name = self.query_one("#name-input").value
            # Process form...
            self.post_message(self.FormSubmitted(self, form_data))
    
    class FormSubmitted(Message):
        def __init__(self, sender: Widget, data: dict) -> None:
            self.data = data
            super().__init__(sender)
```

### Multi-Panel Widget

```python
class MultiPanelWidget(Widget):
    """Widget with multiple collapsible panels."""
    
    DEFAULT_CSS = """
    MultiPanelWidget {
        layout: vertical;
    }
    
    Panel {
        border: solid $primary;
        margin: 1 0;
    }
    
    Panel .panel-header {
        background: $primary;
        color: $text;
        padding: 0 1;
        dock: top;
    }
    
    Panel .panel-content {
        padding: 1;
        height: auto;
    }
    """
    
    def __init__(self, panels: list[dict], **kwargs) -> None:
        super().__init__(**kwargs)
        self.panels_data = panels
        self.expanded_panels = set()
    
    def compose(self) -> ComposeResult:
        for i, panel_data in enumerate(self.panels_data):
            with Container(id=f"panel-{i}", classes="panel"):
                yield Button(
                    panel_data["title"], 
                    id=f"header-{i}",
                    classes="panel-header"
                )
                yield Container(
                    Static(panel_data["content"]),
                    id=f"content-{i}",
                    classes="panel-content"
                )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id.startswith("header-"):
            panel_index = int(event.button.id.split("-")[1])
            self.toggle_panel(panel_index)
    
    def toggle_panel(self, index: int) -> None:
        content = self.query_one(f"#content-{index}")
        if index in self.expanded_panels:
            content.display = False
            self.expanded_panels.remove(index)
        else:
            content.display = True
            self.expanded_panels.add(index)
```

---

## Form Components and Validation

### Validated Input Widget

```python
from textual.validation import Validator, ValidationResult, ValidationFailure

class EmailValidator(Validator):
    """Custom email validator."""
    
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return ValidationResult.success()
        
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            return ValidationResult.error("Please enter a valid email address")
        return ValidationResult.success()

class ValidatedForm(Widget):
    """Form with comprehensive validation."""
    
    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Enter email",
            validators=[EmailValidator()],
            id="email"
        )
        yield Input(
            placeholder="Enter password (min 8 chars)",
            password=True,
            validators=[Length(minimum=8)],
            id="password"
        )
        yield Button("Submit", variant="primary", id="submit")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Real-time validation feedback."""
        if event.validation_result and event.validation_result.is_valid:
            event.input.add_class("valid")
            event.input.remove_class("invalid")
        else:
            event.input.add_class("invalid")
            event.input.remove_class("valid")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            if self.validate_form():
                self.submit_form()
    
    def validate_form(self) -> bool:
        """Validate entire form before submission."""
        email_input = self.query_one("#email", Input)
        password_input = self.query_one("#password", Input)
        
        # Trigger validation
        email_valid = email_input.validate(email_input.value)
        password_valid = password_input.validate(password_input.value)
        
        return email_valid.is_valid and password_valid.is_valid
```

**Validation CSS**:
```css
Input.valid {
    border: solid $success;
}

Input.invalid {
    border: solid $error;
}

Input.valid::after {
    content: "✓";
    color: $success;
    margin-left: 1;
}

Input.invalid::after {
    content: "✗";
    color: $error;
    margin-left: 1;
}
```

---

## Data Display Widgets

### Advanced DataTable with Custom Cells

```python
from rich.text import Text
from rich.console import Console

class StatusCell(Widget):
    """Custom cell for status display."""
    
    def __init__(self, status: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.status = status
    
    def render(self) -> Text:
        color_map = {
            "active": "green",
            "inactive": "red",
            "pending": "yellow"
        }
        
        text = Text(self.status.upper())
        text.stylize(color_map.get(self.status, "white"))
        return text

class AdvancedDataTable(Widget):
    """DataTable with custom renderers and sorting."""
    
    def compose(self) -> ComposeResult:
        table = DataTable(
            zebra_stripes=True,
            show_cursor=True,
            cursor_type="row"
        )
        
        # Add columns with custom widths
        table.add_column("ID", width=8)
        table.add_column("Name", width=20)
        table.add_column("Status", width=12)
        table.add_column("Progress", width=15)
        
        # Add rows with rich content
        for i in range(100):
            status = ["active", "inactive", "pending"][i % 3]
            progress_bar = self.create_progress_bar(i * 10 % 100)
            
            table.add_row(
                str(i),
                f"Item {i}",
                StatusCell(status),
                progress_bar
            )
        
        yield table
    
    def create_progress_bar(self, percentage: int) -> Text:
        """Create a text-based progress bar."""
        width = 10
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return Text(f"{bar} {percentage}%")
```

### Tree Widget with Dynamic Loading

```python
from textual.widgets import Tree

class AsyncTree(Widget):
    """Tree widget with lazy loading."""
    
    def compose(self) -> ComposeResult:
        tree = Tree("Root")
        tree.root.expand()
        yield tree
    
    def on_mount(self) -> None:
        """Initialize tree with root nodes."""
        tree = self.query_one(Tree)
        self.populate_root_nodes(tree.root)
    
    def populate_root_nodes(self, root) -> None:
        """Add initial root-level nodes."""
        for i in range(5):
            node = root.add(f"Branch {i}", data=f"branch_{i}")
            # Add placeholder for lazy loading
            node.add("Loading...", data="placeholder")
    
    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle node expansion with lazy loading."""
        node = event.node
        
        # Remove placeholder
        if node.children and node.children[0].data == "placeholder":
            node.remove_children()
            
            # Load actual children
            self.load_children(node)
    
    async def load_children(self, node) -> None:
        """Simulate async data loading."""
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        for i in range(3):
            child = node.add(f"Child {i} of {node.label}")
            child.add("Loading...", data="placeholder")
```

---

## Modal and Dialog Patterns

### Basic Modal Dialog

```python
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical

class ConfirmDialog(ModalScreen[bool]):
    """Modal confirmation dialog."""
    
    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }
    
    ConfirmDialog > Container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2;
    }
    
    ConfirmDialog .dialog-title {
        text-align: center;
        text-style: bold;
        margin: 0 0 2 0;
    }
    
    ConfirmDialog .dialog-message {
        text-align: center;
        margin: 0 0 2 0;
    }
    
    ConfirmDialog .button-row {
        justify: center;
        margin: 1 0 0 0;
    }
    
    ConfirmDialog Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, title: str, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static(self.title, classes="dialog-title")
            yield Static(self.message, classes="dialog-message")
            with Horizontal(classes="button-row"):
                yield Button("Yes", variant="primary", id="yes")
                yield Button("No", id="no")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        result = event.button.id == "yes"
        self.dismiss(result)

# Usage in main app
class MainApp(App):
    def action_show_confirm(self) -> None:
        """Show confirmation dialog."""
        dialog = ConfirmDialog(
            "Confirm Action",
            "Are you sure you want to delete this item?"
        )
        self.push_screen(dialog, callback=self.handle_confirmation)
    
    def handle_confirmation(self, result: bool) -> None:
        """Handle dialog result."""
        if result:
            # User confirmed
            self.notify("Item deleted!")
        else:
            # User cancelled
            self.notify("Action cancelled.")
```

### Advanced Dialog with Form

```python
class FormDialog(ModalScreen[dict | None]):
    """Modal dialog with form inputs."""
    
    DEFAULT_CSS = """
    FormDialog {
        align: center middle;
    }
    
    FormDialog > Container {
        width: 80;
        height: auto;
        max-height: 90vh;
        background: $surface;
        border: thick $primary;
        padding: 2;
    }
    
    FormDialog .form-row {
        layout: horizontal;
        height: auto;
        margin: 1 0;
    }
    
    FormDialog .form-row Label {
        width: 20;
        text-align: right;
        margin-right: 2;
    }
    
    FormDialog .form-row Input {
        width: 1fr;
    }
    
    FormDialog .button-row {
        justify: center;
        margin: 2 0 0 0;
    }
    """
    
    def __init__(self, title: str, fields: list[dict], **kwargs) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.fields = fields
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static(self.title, classes="dialog-title")
            
            for field in self.fields:
                with Horizontal(classes="form-row"):
                    yield Label(f"{field['label']}:")
                    yield Input(
                        placeholder=field.get('placeholder', ''),
                        password=field.get('type') == 'password',
                        id=field['id']
                    )
            
            with Horizontal(classes="button-row"):
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            # Collect form data
            data = {}
            for field in self.fields:
                input_widget = self.query_one(f"#{field['id']}", Input)
                data[field['id']] = input_widget.value
            self.dismiss(data)
        else:
            self.dismiss(None)

# Usage
def show_user_form(self) -> None:
    fields = [
        {"id": "name", "label": "Name", "placeholder": "Enter full name"},
        {"id": "email", "label": "Email", "placeholder": "user@example.com"},
        {"id": "password", "label": "Password", "type": "password"}
    ]
    
    dialog = FormDialog("Create User", fields)
    self.push_screen(dialog, callback=self.handle_user_form)

def handle_user_form(self, result: dict | None) -> None:
    if result:
        # Process form data
        self.create_user(result)
```

### Toast Notifications System

```python
from textual.widgets import Toast

class NotificationManager:
    """Centralized notification management."""
    
    @staticmethod
    def success(app: App, message: str, timeout: float = 3.0) -> None:
        """Show success notification."""
        app.notify(message, severity="information", timeout=timeout)
    
    @staticmethod
    def warning(app: App, message: str, timeout: float = 5.0) -> None:
        """Show warning notification."""
        app.notify(message, severity="warning", timeout=timeout)
    
    @staticmethod
    def error(app: App, message: str, timeout: float = 10.0) -> None:
        """Show error notification."""
        app.notify(message, severity="error", timeout=timeout)

# Custom toast styling
"""
Toast {
    padding: 2;
    margin: 1;
    border-radius: 2;
}

Toast.-information {
    background: $success;
    color: white;
}

Toast.-warning {
    background: $warning;
    color: black;
}

Toast.-error {
    background: $error;
    color: white;
}
"""
```

---

## Tab and Accordion Interfaces

### Tabbed Content with Dynamic Tabs

```python
from textual.widgets import TabbedContent, TabPane, Markdown

class DynamicTabWidget(Widget):
    """Widget with dynamically manageable tabs."""
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tab_counter = 0
    
    def compose(self) -> ComposeResult:
        with TabbedContent(id="main-tabs"):
            with TabPane("Welcome", id="welcome"):
                yield Markdown("# Welcome\nClick 'Add Tab' to create new tabs.")
            
        with Horizontal():
            yield Button("Add Tab", id="add-tab")
            yield Button("Remove Tab", id="remove-tab")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        tabs = self.query_one("#main-tabs", TabbedContent)
        
        if event.button.id == "add-tab":
            self.add_new_tab(tabs)
        elif event.button.id == "remove-tab":
            self.remove_current_tab(tabs)
    
    def add_new_tab(self, tabs: TabbedContent) -> None:
        """Add a new tab dynamically."""
        self.tab_counter += 1
        tab_id = f"tab-{self.tab_counter}"
        
        # Create new tab pane
        with tabs:
            with TabPane(f"Tab {self.tab_counter}", id=tab_id):
                yield Markdown(f"# Tab {self.tab_counter}\nThis is dynamically added content.")
        
        # Switch to new tab
        tabs.active = tab_id
    
    def remove_current_tab(self, tabs: TabbedContent) -> None:
        """Remove the currently active tab."""
        if tabs.active and tabs.active != "welcome":
            tab_pane = tabs.query_one(f"#{tabs.active}")
            tab_pane.remove()
            tabs.active = "welcome"
```

### Accordion-Style Collapsible

```python
from textual.widgets import Collapsible

class AccordionWidget(Widget):
    """Accordion-style collapsible sections."""
    
    DEFAULT_CSS = """
    AccordionWidget {
        layout: vertical;
    }
    
    Collapsible {
        margin: 1 0;
        border: solid $primary;
    }
    
    Collapsible > .collapsible--title {
        background: $primary;
        color: $text;
        padding: 1 2;
        text-style: bold;
    }
    
    Collapsible > .collapsible--contents {
        padding: 2;
        background: $surface;
    }
    """
    
    def __init__(self, sections: list[dict], **kwargs) -> None:
        super().__init__(**kwargs)
        self.sections = sections
    
    def compose(self) -> ComposeResult:
        for i, section in enumerate(self.sections):
            with Collapsible(
                title=section["title"],
                collapsed=section.get("collapsed", True),
                id=f"section-{i}"
            ):
                if section["type"] == "markdown":
                    yield Markdown(section["content"])
                elif section["type"] == "text":
                    yield Static(section["content"])
                elif section["type"] == "widget":
                    yield section["widget"]
    
    def expand_section(self, section_id: str) -> None:
        """Programmatically expand a section."""
        collapsible = self.query_one(f"#{section_id}", Collapsible)
        collapsible.collapsed = False
    
    def collapse_all_except(self, except_id: str) -> None:
        """Collapse all sections except specified one."""
        for collapsible in self.query(Collapsible):
            if collapsible.id != except_id:
                collapsible.collapsed = True

# Usage
sections = [
    {
        "title": "System Information",
        "type": "text",
        "content": "CPU: Intel i7\nRAM: 16GB\nOS: Linux",
        "collapsed": False
    },
    {
        "title": "Recent Files",
        "type": "markdown",
        "content": "- file1.txt\n- file2.py\n- config.json"
    },
    {
        "title": "Custom Widget",
        "type": "widget",
        "widget": Button("Click me!")
    }
]

accordion = AccordionWidget(sections)
```

---

## Progress Indicators and Loading States

### Multi-Stage Progress Widget

```python
from textual.widgets import ProgressBar
import asyncio

class MultiStageProgress(Widget):
    """Progress widget with multiple stages."""
    
    DEFAULT_CSS = """
    MultiStageProgress {
        layout: vertical;
        border: solid $primary;
        padding: 2;
    }
    
    MultiStageProgress .stage {
        margin: 1 0;
        height: auto;
    }
    
    MultiStageProgress .stage-title {
        text-style: bold;
        margin: 0 0 1 0;
    }
    
    MultiStageProgress .stage.completed .stage-title::after {
        content: " ✓";
        color: $success;
    }
    
    MultiStageProgress .stage.active {
        background: $primary-lighten-3;
    }
    """
    
    def __init__(self, stages: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.stages = stages
        self.current_stage = 0
        self.progress_values = [0.0] * len(stages)
    
    def compose(self) -> ComposeResult:
        yield Static("Multi-Stage Progress", classes="title")
        
        for i, stage in enumerate(self.stages):
            with Container(classes="stage", id=f"stage-{i}"):
                yield Static(stage, classes="stage-title")
                yield ProgressBar(
                    total=100,
                    show_percentage=True,
                    id=f"progress-{i}"
                )
    
    def update_stage_progress(self, stage: int, progress: float) -> None:
        """Update progress for a specific stage."""
        if 0 <= stage < len(self.stages):
            self.progress_values[stage] = progress
            progress_bar = self.query_one(f"#progress-{stage}", ProgressBar)
            progress_bar.progress = progress
            
            # Update stage styling
            stage_container = self.query_one(f"#stage-{stage}")
            if progress >= 100:
                stage_container.add_class("completed")
                stage_container.remove_class("active")
                
                # Move to next stage
                if stage == self.current_stage and stage < len(self.stages) - 1:
                    self.current_stage += 1
                    next_stage = self.query_one(f"#stage-{self.current_stage}")
                    next_stage.add_class("active")
            elif stage == self.current_stage:
                stage_container.add_class("active")
    
    async def run_stages(self, stage_functions: list) -> None:
        """Execute stages with progress updates."""
        for i, stage_func in enumerate(stage_functions):
            # Make current stage active
            self.update_stage_progress(i, 0)
            
            # Run stage with progress callback
            await stage_func(lambda p: self.update_stage_progress(i, p))
            
            # Complete stage
            self.update_stage_progress(i, 100)

# Usage example
async def example_stage(progress_callback):
    """Example stage function."""
    for i in range(101):
        await asyncio.sleep(0.01)  # Simulate work
        progress_callback(i)
```

### Loading Indicators with Rich Animation

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from textual.widgets import Static

class AnimatedLoadingWidget(Static):
    """Loading widget with animated spinner."""
    
    def __init__(self, message: str = "Loading...", **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        )
        self.task = self.progress.add_task(self.message)
    
    def on_mount(self) -> None:
        """Start the animation when widget is mounted."""
        self.update_timer = self.set_interval(
            1/30,  # 30 FPS
            self.update_display
        )
    
    def update_display(self) -> None:
        """Update the spinner animation."""
        self.update(self.progress)
        self.progress.advance(self.task, 0)  # Advance to keep spinner moving
    
    def stop_loading(self) -> None:
        """Stop the loading animation."""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        self.update("Complete!")

class IndeterminateProgress(Static):
    """Indeterminate progress bar."""
    
    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            transient=False
        )
        self.task = self.progress.add_task("Processing...", total=None)
    
    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1/60, self.update_bar)
    
    def update_bar(self) -> None:
        self.update(self.progress)
        self.progress.advance(self.task)
```

---

## Charts and Data Visualization

### Text-Based Chart Widget

```python
from rich.text import Text
from textual.widgets import Static

class BarChart(Widget):
    """ASCII bar chart widget."""
    
    DEFAULT_CSS = """
    BarChart {
        border: solid $primary;
        padding: 1;
        background: $surface;
    }
    
    BarChart .chart-title {
        text-align: center;
        text-style: bold;
        margin: 0 0 1 0;
    }
    """
    
    def __init__(self, data: dict[str, float], title: str = "Chart", **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.title = title
        self.max_bar_width = 40
    
    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="chart-title")
        yield Static(self.render_chart(), id="chart-content")
    
    def render_chart(self) -> Text:
        """Render bar chart as text."""
        if not self.data:
            return Text("No data available")
        
        max_value = max(self.data.values()) if self.data else 1
        chart_text = Text()
        
        for label, value in self.data.items():
            # Calculate bar length
            bar_length = int((value / max_value) * self.max_bar_width)
            
            # Create bar
            bar = "█" * bar_length
            
            # Color based on value
            if value / max_value > 0.8:
                color = "green"
            elif value / max_value > 0.5:
                color = "yellow"
            else:
                color = "red"
            
            # Add label and bar
            line = Text()
            line.append(f"{label:>10}: ")
            line.append(bar, style=color)
            line.append(f" {value:.1f}")
            
            chart_text.append_text(line)
            chart_text.append("\n")
        
        return chart_text
    
    def update_data(self, new_data: dict[str, float]) -> None:
        """Update chart data."""
        self.data = new_data
        chart_content = self.query_one("#chart-content", Static)
        chart_content.update(self.render_chart())

class Sparkline(Widget):
    """Sparkline mini-chart widget."""
    
    COMPONENT_CLASSES = {
        "sparkline--high",
        "sparkline--medium", 
        "sparkline--low"
    }
    
    def __init__(self, data: list[float], **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
    
    def render(self) -> Text:
        """Render sparkline."""
        if not self.data:
            return Text("No data")
        
        min_val = min(self.data)
        max_val = max(self.data)
        range_val = max_val - min_val if max_val != min_val else 1
        
        # Unicode block characters for different heights
        chars = " ▁▂▃▄▅▆▇█"
        
        sparkline = Text()
        for value in self.data:
            normalized = (value - min_val) / range_val
            char_index = int(normalized * (len(chars) - 1))
            
            # Color based on value
            if normalized > 0.66:
                style = "sparkline--high"
            elif normalized > 0.33:
                style = "sparkline--medium"
            else:
                style = "sparkline--low"
            
            sparkline.append(chars[char_index], style=style)
        
        return sparkline
```

### Dashboard with Multiple Charts

```python
class Dashboard(Widget):
    """Dashboard with multiple visualization widgets."""
    
    DEFAULT_CSS = """
    Dashboard {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
    }
    
    Dashboard .chart-container {
        border: solid $primary;
        padding: 1;
    }
    
    .sparkline--high { color: $success; }
    .sparkline--medium { color: $warning; }
    .sparkline--low { color: $error; }
    """
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Generate sample data
        import random
        self.sales_data = {
            "Jan": 100 + random.randint(-20, 50),
            "Feb": 120 + random.randint(-20, 50),
            "Mar": 90 + random.randint(-20, 50),
            "Apr": 160 + random.randint(-20, 50),
        }
        self.performance_data = [random.randint(20, 100) for _ in range(30)]
    
    def compose(self) -> ComposeResult:
        with Container(classes="chart-container"):
            yield BarChart(self.sales_data, "Monthly Sales")
        
        with Container(classes="chart-container"):
            yield Sparkline(self.performance_data)
            yield Static("Performance Trend (30 days)")
        
        with Container(classes="chart-container"):
            yield self.create_metrics_widget()
        
        with Container(classes="chart-container"):
            yield self.create_status_widget()
    
    def create_metrics_widget(self) -> Widget:
        """Create a metrics display widget."""
        metrics = Container()
        metrics.mount(Static("Key Metrics", classes="title"))
        metrics.mount(Static("Active Users: 1,234"))
        metrics.mount(Static("Revenue: $45,678"))
        metrics.mount(Static("Conversion: 12.3%"))
        return metrics
    
    def create_status_widget(self) -> Widget:
        """Create a status indicator widget."""
        status = Container()
        status.mount(Static("System Status", classes="title"))
        status.mount(Static("🟢 Database: Online"))
        status.mount(Static("🟢 API: Healthy"))
        status.mount(Static("🟡 Cache: Degraded"))
        return status
```

---

## Responsive Widget Design

### Responsive Layout Container

```python
class ResponsiveContainer(Widget):
    """Container that adapts to screen size."""
    
    DEFAULT_CSS = """
    ResponsiveContainer {
        layout: grid;
        grid-gutter: 1;
    }
    
    /* Large screens - 3 columns */
    ResponsiveContainer.-large {
        grid-size: 3 1fr;
    }
    
    /* Medium screens - 2 columns */
    ResponsiveContainer.-medium {
        grid-size: 2 1fr;
    }
    
    /* Small screens - 1 column */
    ResponsiveContainer.-small {
        grid-size: 1 1fr;
    }
    """
    
    def __init__(self, items: list[Widget], **kwargs) -> None:
        super().__init__(**kwargs)
        self.items = items
        self.breakpoints = {
            "small": 60,   # columns
            "medium": 100,
            "large": 140
        }
    
    def compose(self) -> ComposeResult:
        for item in self.items:
            yield item
    
    def on_resize(self, event) -> None:
        """Respond to size changes."""
        width = self.size.width
        
        # Remove existing size classes
        self.remove_class("-small", "-medium", "-large")
        
        # Add appropriate class based on width
        if width >= self.breakpoints["large"]:
            self.add_class("-large")
        elif width >= self.breakpoints["medium"]:
            self.add_class("-medium")
        else:
            self.add_class("-small")

class FlexWidget(Widget):
    """Widget with flexible sizing."""
    
    def __init__(self, min_width: int = 20, preferred_width: int = 40, **kwargs) -> None:
        super().__init__(**kwargs)
        self.min_width = min_width
        self.preferred_width = preferred_width
    
    def get_content_width(self, container_width: int, available_width: int) -> int:
        """Calculate optimal width based on available space."""
        if available_width >= self.preferred_width:
            return self.preferred_width
        elif available_width >= self.min_width:
            return available_width
        else:
            return self.min_width
    
    def get_content_height(self, container_height: int, viewport_height: int) -> int:
        """Calculate height based on content and container."""
        # Auto-sizing based on content
        return len(str(self.renderable).split('\n'))
```

---

## Widget Styling with TCSS

### Advanced Component Styling

```css
/* Base widget styles */
.card {
    background: $surface;
    border: solid $primary;
    border-radius: 2;
    padding: 2;
    margin: 1;
}

.card-header {
    background: $primary;
    color: $text;
    padding: 1 2;
    text-style: bold;
    dock: top;
    border-radius: 2 2 0 0;
}

.card-body {
    padding: 2;
}

.card-footer {
    background: $surface-lighten-1;
    padding: 1 2;
    dock: bottom;
    border-radius: 0 0 2 2;
    text-align: center;
}

/* Interactive states */
.interactive:hover {
    background: $primary-lighten-2;
    border: solid $accent;
}

.interactive:focus {
    border: solid $accent;
    box-shadow: 0 0 8 $accent-alpha-50;
}

/* Status indicators */
.status-success {
    border-left: thick $success;
}

.status-warning {
    border-left: thick $warning;
}

.status-error {
    border-left: thick $error;
}

/* Utility classes */
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-bold { text-style: bold; }
.text-italic { text-style: italic; }

.m-0 { margin: 0; }
.m-1 { margin: 1; }
.p-0 { padding: 0; }
.p-1 { padding: 1; }

/* Animations */
.fade-in {
    opacity: 0;
    transition: opacity 500ms ease-in-out;
}

.fade-in:focus {
    opacity: 1;
}

.slide-up {
    offset-y: 100%;
    transition: offset-y 300ms ease-out;
}

.slide-up:focus {
    offset-y: 0;
}
```

### Theme-Aware Widget

```python
class ThemedWidget(Widget):
    """Widget that adapts to app theme."""
    
    DEFAULT_CSS = """
    ThemedWidget {
        background: $surface;
        color: $text;
        border: solid $primary;
    }
    
    /* Dark theme overrides */
    ThemedWidget.dark {
        background: $surface-darken-1;
        border: solid $primary-lighten-1;
    }
    
    /* Light theme overrides */
    ThemedWidget.light {
        background: $surface-lighten-1;
        border: solid $primary-darken-1;
    }
    """
    
    def on_mount(self) -> None:
        """Apply theme class based on app theme."""
        if self.app.dark:
            self.add_class("dark")
        else:
            self.add_class("light")
    
    def watch_dark(self, dark: bool) -> None:
        """Update theme class when app theme changes."""
        if dark:
            self.remove_class("light")
            self.add_class("dark")
        else:
            self.remove_class("dark")
            self.add_class("light")
```

---

## Animation and Transitions

### Animated Widget Transitions

```python
class AnimatedPanel(Widget):
    """Panel with smooth show/hide animations."""
    
    DEFAULT_CSS = """
    AnimatedPanel {
        background: $surface;
        border: solid $primary;
        padding: 2;
        transition: opacity 500ms ease-in-out,
                   offset-y 300ms ease-out;
    }
    
    AnimatedPanel.hidden {
        opacity: 0;
        offset-y: -100%;
    }
    
    AnimatedPanel.visible {
        opacity: 1;
        offset-y: 0;
    }
    """
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.is_visible = True
    
    def show(self) -> None:
        """Show panel with animation."""
        self.remove_class("hidden")
        self.add_class("visible")
        self.is_visible = True
    
    def hide(self) -> None:
        """Hide panel with animation."""
        self.remove_class("visible")
        self.add_class("hidden")
        self.is_visible = False
    
    def toggle(self) -> None:
        """Toggle panel visibility."""
        if self.is_visible:
            self.hide()
        else:
            self.show()

class SlideInWidget(Widget):
    """Widget that slides in from the side."""
    
    DEFAULT_CSS = """
    SlideInWidget {
        background: $primary;
        color: $text;
        padding: 2;
        offset-x: -100%;
        transition: offset-x 400ms ease-out;
    }
    
    SlideInWidget.entered {
        offset-x: 0;
    }
    """
    
    def on_mount(self) -> None:
        """Trigger slide-in animation when mounted."""
        # Use call_later to ensure the initial state is rendered
        self.call_later(self.animate_in)
    
    def animate_in(self) -> None:
        """Start the slide-in animation."""
        self.add_class("entered")
```

### Loading State Animations

```python
class PulsingWidget(Widget):
    """Widget with pulsing animation during loading."""
    
    DEFAULT_CSS = """
    PulsingWidget {
        background: $surface;
        border: solid $primary;
        padding: 2;
        transition: opacity 1000ms ease-in-out;
    }
    
    PulsingWidget.pulse {
        opacity: 0.5;
    }
    """
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.pulse_timer = None
    
    def start_pulsing(self) -> None:
        """Start pulsing animation."""
        if self.pulse_timer is None:
            self.pulse_timer = self.set_interval(1.0, self.toggle_pulse)
    
    def stop_pulsing(self) -> None:
        """Stop pulsing animation."""
        if self.pulse_timer:
            self.pulse_timer.stop()
            self.pulse_timer = None
        self.remove_class("pulse")
    
    def toggle_pulse(self) -> None:
        """Toggle pulse class."""
        self.toggle_class("pulse")
```

---

## Keyboard Navigation Patterns

### Custom Navigation Widget

```python
class NavigationWidget(Widget):
    """Widget with custom keyboard navigation."""
    
    BINDINGS = [
        ("up,k", "navigate_up", "Navigate up"),
        ("down,j", "navigate_down", "Navigate down"),
        ("left,h", "navigate_left", "Navigate left"),
        ("right,l", "navigate_right", "Navigate right"),
        ("enter", "activate", "Activate item"),
        ("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, items: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.items = items
        self.selected_index = 0
    
    def action_navigate_up(self) -> None:
        """Navigate to previous item."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self.refresh()
    
    def action_navigate_down(self) -> None:
        """Navigate to next item."""
        if self.selected_index < len(self.items) - 1:
            self.selected_index += 1
            self.refresh()
    
    def action_activate(self) -> None:
        """Activate selected item."""
        if 0 <= self.selected_index < len(self.items):
            item = self.items[self.selected_index]
            self.post_message(self.ItemActivated(self, item, self.selected_index))
    
    class ItemActivated(Message):
        def __init__(self, sender: Widget, item: str, index: int) -> None:
            self.item = item
            self.index = index
            super().__init__(sender)

class TabbableWidget(Widget):
    """Widget that manages tab navigation."""
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tabbable_children = []
        self.current_tab_index = 0
    
    def on_mount(self) -> None:
        """Identify tabbable children."""
        self.update_tabbable_children()
    
    def update_tabbable_children(self) -> None:
        """Update list of tabbable child widgets."""
        self.tabbable_children = [
            widget for widget in self.query("Input, Button, DataTable")
            if widget.can_focus
        ]
    
    def on_key(self, event: events.Key) -> None:
        """Handle tab navigation."""
        if event.key == "tab":
            self.focus_next()
            event.prevent_default()
        elif event.key == "shift+tab":
            self.focus_previous()
            event.prevent_default()
    
    def focus_next(self) -> None:
        """Focus next tabbable widget."""
        if self.tabbable_children:
            self.current_tab_index = (self.current_tab_index + 1) % len(self.tabbable_children)
            self.tabbable_children[self.current_tab_index].focus()
    
    def focus_previous(self) -> None:
        """Focus previous tabbable widget."""
        if self.tabbable_children:
            self.current_tab_index = (self.current_tab_index - 1) % len(self.tabbable_children)
            self.tabbable_children[self.current_tab_index].focus()
```

---

## Focus Management

### Focus Control Widget

```python
class FocusManager(Widget):
    """Widget that manages focus behavior for its children."""
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.focus_stack = []
        self.focus_traps = set()
    
    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        """Track focus changes."""
        self.focus_stack.append(event.widget)
        # Limit stack size
        if len(self.focus_stack) > 10:
            self.focus_stack.pop(0)
    
    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        """Handle focus loss."""
        if event.widget in self.focus_stack:
            self.focus_stack.remove(event.widget)
    
    def focus_previous(self) -> None:
        """Return focus to previous widget."""
        if len(self.focus_stack) > 1:
            # Remove current widget and focus previous
            self.focus_stack.pop()
            previous_widget = self.focus_stack[-1]
            if previous_widget.can_focus:
                previous_widget.focus()
    
    def trap_focus(self, widget: Widget) -> None:
        """Trap focus within a widget (useful for modals)."""
        self.focus_traps.add(widget)
    
    def release_focus_trap(self, widget: Widget) -> None:
        """Release focus trap."""
        self.focus_traps.discard(widget)
    
    def on_focus(self, event: events.Focus) -> None:
        """Handle focus events with trapping."""
        # Check if focus should be trapped
        for trap_widget in self.focus_traps:
            if not trap_widget.has_focus and event.widget not in trap_widget.query("*"):
                # Focus is trying to leave trapped widget
                if trap_widget.can_focus:
                    trap_widget.focus()
                    event.prevent_default()
                    break

class ModalFocusTrap(ModalScreen):
    """Modal screen with proper focus trapping."""
    
    def on_mount(self) -> None:
        """Set up focus trap when modal opens."""
        # Focus first focusable element
        focusable = self.query("Input, Button, DataTable").first()
        if focusable:
            focusable.focus()
    
    def on_key(self, event: events.Key) -> None:
        """Handle tab cycling within modal."""
        if event.key == "tab":
            focusable_widgets = list(self.query("Input, Button, DataTable"))
            if not focusable_widgets:
                return
            
            current_focus = self.focused
            if current_focus in focusable_widgets:
                current_index = focusable_widgets.index(current_focus)
                if event.key == "tab":
                    next_index = (current_index + 1) % len(focusable_widgets)
                else:  # shift+tab
                    next_index = (current_index - 1) % len(focusable_widgets)
                focusable_widgets[next_index].focus()
                event.prevent_default()
```

---

## Accessibility Considerations

### Screen Reader Support

```python
class AccessibleWidget(Widget):
    """Widget with accessibility features."""
    
    def __init__(self, label: str = "", description: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.aria_label = label
        self.aria_description = description
        self.role = "widget"  # ARIA role
    
    def get_accessibility_info(self) -> dict:
        """Return accessibility information."""
        return {
            "role": self.role,
            "label": self.aria_label,
            "description": self.aria_description,
            "state": self.get_state_description(),
            "position": f"{self.selected_index + 1} of {len(self.items)}" if hasattr(self, 'items') else None
        }
    
    def get_state_description(self) -> str:
        """Get current state for screen readers."""
        states = []
        if self.has_focus:
            states.append("focused")
        if hasattr(self, 'disabled') and self.disabled:
            states.append("disabled")
        if hasattr(self, 'selected') and self.selected:
            states.append("selected")
        return ", ".join(states) if states else "normal"
    
    def announce(self, message: str) -> None:
        """Announce message to screen readers."""
        # In a real implementation, this would interface with screen reader APIs
        self.app.bell()  # Fallback audio feedback

class AccessibleButton(Button):
    """Button with enhanced accessibility."""
    
    def __init__(self, label: str, action_description: str = "", **kwargs) -> None:
        super().__init__(label, **kwargs)
        self.action_description = action_description or f"Activate {label}"
        self.role = "button"
    
    def on_focus(self, event: events.Focus) -> None:
        """Announce button when focused."""
        super().on_focus(event)
        self.announce(f"Button: {self.label}. {self.action_description}")
    
    def on_press(self) -> None:
        """Provide feedback when pressed."""
        super().on_press()
        self.announce(f"Pressed {self.label}")

class AccessibleList(ListView):
    """List with screen reader announcements."""
    
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Announce highlighted item."""
        item = self.highlighted_child
        if item:
            position = event.list_view.index + 1
            total = len(event.list_view.children)
            self.announce(f"Item {position} of {total}: {item.renderable}")
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Announce selected item."""
        self.announce(f"Selected: {event.item.renderable}")
```

### High Contrast and Theming

```css
/* High contrast theme */
.high-contrast {
    --primary: white;
    --secondary: yellow;
    --accent: cyan;
    --foreground: black;
    --background: black;
    --surface: black;
    --success: lime;
    --warning: yellow;
    --error: red;
    --text: white;
}

/* Focus indicators for accessibility */
*:focus {
    outline: 2px solid $accent;
    outline-offset: 2px;
}

/* Increased text sizes for readability */
.large-text {
    text-size: 120%;
}

.extra-large-text {
    text-size: 150%;
}

/* Motion reduction support */
@media (prefers-reduced-motion) {
    * {
        transition: none !important;
        animation: none !important;
    }
}
```

---

## Advanced Patterns

### Widget Inheritance Strategies

```python
# Base widget with common functionality
class BaseDataWidget(Widget):
    """Base class for data-driven widgets."""
    
    def __init__(self, data_source: str, refresh_interval: float = 60.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data_source = data_source
        self.refresh_interval = refresh_interval
        self.last_update = None
        self.refresh_timer = None
    
    def on_mount(self) -> None:
        """Start auto-refresh when mounted."""
        self.refresh_data()
        self.refresh_timer = self.set_interval(self.refresh_interval, self.refresh_data)
    
    async def refresh_data(self) -> None:
        """Override in subclasses."""
        raise NotImplementedError("Subclasses must implement refresh_data")
    
    def on_unmount(self) -> None:
        """Clean up timer."""
        if self.refresh_timer:
            self.refresh_timer.stop()

# Mixin for common data operations
class DataFilterMixin:
    """Mixin for filtering data."""
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.filters = {}
        self.sort_key = None
        self.sort_reverse = False
    
    def add_filter(self, key: str, value: any) -> None:
        """Add a filter."""
        self.filters[key] = value
        self.apply_filters()
    
    def remove_filter(self, key: str) -> None:
        """Remove a filter."""
        self.filters.pop(key, None)
        self.apply_filters()
    
    def set_sort(self, key: str, reverse: bool = False) -> None:
        """Set sorting options."""
        self.sort_key = key
        self.sort_reverse = reverse
        self.apply_filters()
    
    def apply_filters(self) -> None:
        """Apply filters and sorting to data."""
        # Override in classes that use this mixin
        pass

# Combined usage
class FilterableDataTable(BaseDataWidget, DataFilterMixin):
    """Data table with filtering and auto-refresh."""
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.raw_data = []
        self.filtered_data = []
    
    async def refresh_data(self) -> None:
        """Fetch fresh data."""
        # Simulate API call
        await asyncio.sleep(0.1)
        self.raw_data = await self.fetch_data_from_source()
        self.apply_filters()
    
    def apply_filters(self) -> None:
        """Apply filters to raw data."""
        self.filtered_data = self.raw_data.copy()
        
        # Apply filters
        for key, value in self.filters.items():
            self.filtered_data = [
                item for item in self.filtered_data
                if self.match_filter(item, key, value)
            ]
        
        # Apply sorting
        if self.sort_key:
            self.filtered_data.sort(
                key=lambda x: x.get(self.sort_key, 0),
                reverse=self.sort_reverse
            )
        
        self.update_display()
    
    def update_display(self) -> None:
        """Update the visual display."""
        table = self.query_one(DataTable)
        table.clear()
        for row in self.filtered_data:
            table.add_row(*[str(row.get(col, "")) for col in table.columns])
```

### Event Bubbling and Capturing

```python
class EventLogger(Widget):
    """Widget that logs all events for debugging."""
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_log = []
        self.max_log_size = 1000
    
    def on_event(self, event: events.Event) -> None:
        """Log all events."""
        log_entry = {
            "timestamp": time.time(),
            "event_type": type(event).__name__,
            "sender": getattr(event, 'sender', None),
            "target": getattr(event, 'target', None),
            "bubble": getattr(event, 'bubble', False),
        }
        
        self.event_log.append(log_entry)
        
        # Limit log size
        if len(self.event_log) > self.max_log_size:
            self.event_log = self.event_log[-self.max_log_size:]
        
        # Don't prevent event handling
        return False
    
    def get_recent_events(self, count: int = 10) -> list:
        """Get recent events."""
        return self.event_log[-count:]

class EventBroadcaster(Widget):
    """Widget that broadcasts events to multiple handlers."""
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_handlers = {}
    
    def register_handler(self, event_type: str, handler: callable) -> None:
        """Register an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: str, handler: callable) -> None:
        """Unregister an event handler."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].remove(handler)
    
    def broadcast_event(self, event: events.Event) -> None:
        """Broadcast event to registered handlers."""
        event_type = type(event).__name__
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    self.app.log.error(f"Error in event handler: {e}")
```

### Widget Testing Strategies

```python
import pytest
from textual.app import App
from textual_testing import TextualTestRunner

class TestableWidget(Widget):
    """Widget designed for easy testing."""
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.test_hooks = {}
        self.state_history = []
    
    def add_test_hook(self, event: str, callback: callable) -> None:
        """Add hook for testing."""
        if event not in self.test_hooks:
            self.test_hooks[event] = []
        self.test_hooks[event].append(callback)
    
    def trigger_test_hook(self, event: str, *args, **kwargs) -> None:
        """Trigger test hooks."""
        if event in self.test_hooks:
            for callback in self.test_hooks[event]:
                callback(*args, **kwargs)
    
    def record_state(self, state: dict) -> None:
        """Record state for testing."""
        self.state_history.append({
            "timestamp": time.time(),
            "state": state.copy()
        })

# Test implementation
@pytest.fixture
def widget_app():
    """Create app with widget for testing."""
    class TestApp(App):
        def compose(self):
            yield TestableWidget(id="test-widget")
    
    return TestApp()

def test_widget_initialization(widget_app):
    """Test widget initializes correctly."""
    with TextualTestRunner(widget_app) as runner:
        widget = runner.app.query_one("#test-widget")
        assert widget is not None
        assert isinstance(widget, TestableWidget)

def test_widget_interaction(widget_app):
    """Test widget responds to interaction."""
    with TextualTestRunner(widget_app) as runner:
        widget = runner.app.query_one("#test-widget")
        
        # Set up test hook
        test_results = []
        widget.add_test_hook("click", lambda: test_results.append("clicked"))
        
        # Simulate click
        runner.click(widget)
        
        # Verify result
        assert "clicked" in test_results
```

### Performance Optimization

```python
class OptimizedListWidget(Widget):
    """List widget optimized for large datasets."""
    
    def __init__(self, items: list, visible_count: int = 20, **kwargs) -> None:
        super().__init__(**kwargs)
        self.items = items
        self.visible_count = visible_count
        self.start_index = 0
        self.item_height = 1
        self.total_height = len(items) * self.item_height
    
    def get_visible_items(self) -> list:
        """Get currently visible items."""
        end_index = min(self.start_index + self.visible_count, len(self.items))
        return self.items[self.start_index:end_index]
    
    def scroll_to_index(self, index: int) -> None:
        """Scroll to show specific item."""
        if index < self.start_index:
            self.start_index = index
        elif index >= self.start_index + self.visible_count:
            self.start_index = index - self.visible_count + 1
        
        self.start_index = max(0, self.start_index)
        self.refresh()
    
    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation."""
        if event.key == "up":
            if self.start_index > 0:
                self.start_index -= 1
                self.refresh()
        elif event.key == "down":
            if self.start_index + self.visible_count < len(self.items):
                self.start_index += 1
                self.refresh()
    
    def render_line(self, y: int) -> Strip:
        """Render only visible lines."""
        if y < len(self.get_visible_items()):
            item = self.get_visible_items()[y]
            return Strip([Segment(str(item))])
        return Strip([])

class WidgetPool:
    """Pool widgets for memory efficiency."""
    
    def __init__(self, widget_class: type, initial_size: int = 10):
        self.widget_class = widget_class
        self.available_widgets = []
        self.in_use_widgets = set()
        
        # Pre-create widgets
        for _ in range(initial_size):
            widget = widget_class()
            self.available_widgets.append(widget)
    
    def acquire_widget(self, **kwargs) -> Widget:
        """Get widget from pool or create new one."""
        if self.available_widgets:
            widget = self.available_widgets.pop()
        else:
            widget = self.widget_class()
        
        # Configure widget
        for key, value in kwargs.items():
            setattr(widget, key, value)
        
        self.in_use_widgets.add(widget)
        return widget
    
    def release_widget(self, widget: Widget) -> None:
        """Return widget to pool."""
        if widget in self.in_use_widgets:
            self.in_use_widgets.remove(widget)
            # Reset widget state
            widget.remove_children()
            widget.remove_class()  # Remove all classes
            self.available_widgets.append(widget)
```

---

## Summary

This comprehensive guide covers advanced Textual widget patterns for building sophisticated TUI applications. Key takeaways:

1. **Start Simple**: Begin with basic custom widgets using `render()` method
2. **Compose Thoughtfully**: Use compound widgets to build reusable components  
3. **Handle Events Properly**: Implement proper event handling and message passing
4. **Style Systematically**: Use TCSS for consistent, maintainable styling
5. **Consider Accessibility**: Include screen reader support and keyboard navigation
6. **Optimize Performance**: Use virtual scrolling and widget pooling for large datasets
7. **Test Thoroughly**: Implement testable patterns with proper state management

Each pattern includes complete implementation examples, CSS styling, and usage scenarios to help you build production-ready TUI applications with Textual.