# Textual Design Patterns and Architecture Guide

A comprehensive guide to design patterns and architectural best practices for building scalable, maintainable text UI applications with Textual, Rich, and Typer.

## Table of Contents
- [Core Architectural Patterns](#core-architectural-patterns)
- [Component Design Patterns](#component-design-patterns)
- [State Management Patterns](#state-management-patterns)
- [Testing Patterns](#testing-patterns)
- [Integration Patterns](#integration-patterns)
- [Performance Patterns](#performance-patterns)
- [Advanced Patterns](#advanced-patterns)

---

## Core Architectural Patterns

### Model-View-Controller (MVC) Pattern

**Intent**: Separate data management, business logic, and presentation concerns in Textual applications.

**Structure**:
```
┌─────────┐    Updates    ┌────────┐    Manipulates    ┌───────┐
│  View   │◄─────────────►│Controller│─────────────────►│ Model │
│(Textual)│               │ (App)    │                  │(Data) │
└─────────┘               └────────┘                   └───────┘
```

**Implementation**:
```python
from textual.app import App, ComposeResult
from textual.widgets import Input, DataTable, Button
from textual.containers import Vertical, Horizontal
from typing import List, Dict

# Model Layer
class TaskModel:
    def __init__(self):
        self._tasks: List[Dict] = []
        self._observers = []
    
    def add_task(self, description: str, priority: str = "medium"):
        task = {
            "id": len(self._tasks),
            "description": description,
            "priority": priority,
            "completed": False
        }
        self._tasks.append(task)
        self._notify_observers("task_added", task)
    
    def get_tasks(self) -> List[Dict]:
        return self._tasks.copy()
    
    def toggle_task(self, task_id: int):
        if 0 <= task_id < len(self._tasks):
            self._tasks[task_id]["completed"] = not self._tasks[task_id]["completed"]
            self._notify_observers("task_updated", self._tasks[task_id])
    
    def subscribe(self, observer):
        self._observers.append(observer)
    
    def _notify_observers(self, event, data):
        for observer in self._observers:
            observer.on_model_change(event, data)

# View Layer
class TaskView(Vertical):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter task description", id="task_input")
        yield Horizontal(
            Button("Add Task", id="add_task", variant="primary"),
            Button("Toggle Priority", id="toggle_priority"),
        )
        yield DataTable(id="task_table")
    
    def on_mount(self):
        table = self.query_one("#task_table", DataTable)
        table.add_columns("ID", "Description", "Priority", "Status")
        self.update_view()
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "add_task":
            self.controller.add_task()
        elif event.button.id == "toggle_priority":
            self.controller.toggle_selected_priority()
    
    def on_model_change(self, event: str, data: Dict):
        """Observer method called when model changes"""
        if event in ["task_added", "task_updated"]:
            self.update_view()
    
    def update_view(self):
        table = self.query_one("#task_table", DataTable)
        table.clear()
        for task in self.controller.get_tasks():
            status = "✓" if task["completed"] else "○"
            table.add_row(
                str(task["id"]),
                task["description"],
                task["priority"],
                status
            )

# Controller Layer
class TaskController:
    def __init__(self, model: TaskModel, view: TaskView):
        self.model = model
        self.view = view
        self.model.subscribe(self.view)
    
    def add_task(self):
        input_widget = self.view.query_one("#task_input", Input)
        description = input_widget.value.strip()
        if description:
            self.model.add_task(description)
            input_widget.value = ""
    
    def get_tasks(self):
        return self.model.get_tasks()
    
    def toggle_selected_priority(self):
        # Implementation for priority toggling logic
        pass

# Application (Assembly)
class TaskApp(App):
    def compose(self) -> ComposeResult:
        model = TaskModel()
        view = TaskView(None)  # Temporary reference
        controller = TaskController(model, view)
        view.controller = controller  # Set actual controller reference
        yield view
```

**When to Use**: 
- Complex applications with significant business logic
- Multiple views of the same data
- Need for testability and separation of concerns

**Performance Implications**: 
- Slight overhead from observer pattern
- Better maintainability outweighs performance cost

---

### Model-View-ViewModel (MVVM) Pattern

**Intent**: Bind view state to data models using reactive programming principles.

**Structure**:
```
┌──────────┐    Binds to    ┌───────────┐    Updates    ┌───────┐
│   View   │◄──────────────►│ ViewModel │◄─────────────►│ Model │
│(Textual) │                │(Reactive) │               │(Data) │
└──────────┘                └───────────┘               └───────┘
```

**Implementation**:
```python
from textual.app import App
from textual.reactive import reactive, var
from textual.widgets import Static, Input, Button
from textual.containers import Vertical

# ViewModel with Reactive Properties
class CounterViewModel:
    def __init__(self):
        self.count = var(0)
        self.display_text = var("Count: 0")
        self.is_even = var(True)
        
        # Computed properties that update when count changes
        self.count.watch(self._update_display)
        self.count.watch(self._update_even_status)
    
    def _update_display(self, count: int):
        self.display_text.set_value(f"Count: {count}")
    
    def _update_even_status(self, count: int):
        self.is_even.set_value(count % 2 == 0)
    
    def increment(self):
        self.count.set_value(self.count.value + 1)
    
    def decrement(self):
        self.count.set_value(self.count.value - 1)

# View with Data Binding
class CounterView(Vertical):
    def __init__(self, viewmodel: CounterViewModel):
        super().__init__()
        self.viewmodel = viewmodel
        self._setup_bindings()
    
    def _setup_bindings(self):
        # Bind viewmodel properties to view updates
        self.viewmodel.display_text.watch(self._update_counter_display)
        self.viewmodel.is_even.watch(self._update_style)
    
    def compose(self) -> ComposeResult:
        yield Static("Count: 0", id="counter_display")
        yield Button("Increment", id="increment", variant="primary")
        yield Button("Decrement", id="decrement", variant="default")
    
    def _update_counter_display(self, text: str):
        display = self.query_one("#counter_display", Static)
        display.update(text)
    
    def _update_style(self, is_even: bool):
        display = self.query_one("#counter_display", Static)
        if is_even:
            display.add_class("even")
            display.remove_class("odd")
        else:
            display.add_class("odd")
            display.remove_class("even")
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "increment":
            self.viewmodel.increment()
        elif event.button.id == "decrement":
            self.viewmodel.decrement()

class CounterApp(App):
    CSS = """
    .even { color: green; }
    .odd { color: red; }
    """
    
    def compose(self) -> ComposeResult:
        viewmodel = CounterViewModel()
        yield CounterView(viewmodel)
```

**When to Use**:
- Rich data binding requirements
- Complex computed properties
- Real-time UI updates based on data changes

---

### Component Composition Pattern

**Intent**: Build complex UI components by composing simpler, reusable components.

**Structure**:
```
┌─────────────────────────┐
│    Composite Widget     │
│  ┌─────┐ ┌─────┐ ┌────┐ │
│  │Comp1│ │Comp2│ │Comp│ │
│  └─────┘ └─────┘ └────┘ │
└─────────────────────────┘
```

**Implementation**:
```python
from textual.app import App, ComposeResult
from textual.widgets import Input, Button, Label, Switch
from textual.containers import Horizontal, Vertical
from textual.widget import Widget

# Atomic Components
class LabeledInput(Widget):
    """Atomic component: Input with Label"""
    
    def __init__(self, label: str, placeholder: str = "", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.placeholder = placeholder
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.label, classes="input-label")
            yield Input(placeholder=self.placeholder, classes="labeled-input")
    
    @property
    def value(self) -> str:
        return self.query_one(".labeled-input", Input).value
    
    @value.setter
    def value(self, val: str):
        self.query_one(".labeled-input", Input).value = val

class ToggleButton(Widget):
    """Atomic component: Button with Toggle State"""
    
    def __init__(self, text: str, initial_state: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.toggle_state = initial_state
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Switch(value=self.toggle_state, id="toggle_switch")
            yield Label(self.text, classes="toggle-label")
    
    @property
    def is_enabled(self) -> bool:
        return self.query_one("#toggle_switch", Switch).value
    
    def on_switch_changed(self, event: Switch.Changed):
        self.toggle_state = event.value
        # Emit custom message for parent components
        self.post_message(self.StateChanged(self.toggle_state))
    
    class StateChanged(Widget.Event):
        def __init__(self, state: bool):
            super().__init__()
            self.state = state

# Molecular Components
class UserForm(Widget):
    """Molecular component: Form composed of atomic components"""
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="user-form"):
            yield LabeledInput("Username:", "Enter username", id="username")
            yield LabeledInput("Email:", "user@example.com", id="email")
            yield ToggleButton("Enable Notifications", True, id="notifications")
            yield ToggleButton("Admin Access", False, id="admin")
            yield Button("Submit", variant="primary", id="submit")
    
    def get_form_data(self) -> dict:
        return {
            "username": self.query_one("#username", LabeledInput).value,
            "email": self.query_one("#email", LabeledInput).value,
            "notifications": self.query_one("#notifications", ToggleButton).is_enabled,
            "admin": self.query_one("#admin", ToggleButton).is_enabled,
        }
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "submit":
            form_data = self.get_form_data()
            self.post_message(self.FormSubmitted(form_data))
    
    class FormSubmitted(Widget.Event):
        def __init__(self, data: dict):
            super().__init__()
            self.data = data

# Organism Component
class UserManagementPanel(Widget):
    """Organism: Complex component using molecular components"""
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="user-panel"):
            yield Label("User Management", classes="panel-title")
            yield UserForm(id="user_form")
            yield Label("", id="status_message", classes="status")
    
    def on_user_form_form_submitted(self, event: UserForm.FormSubmitted):
        # Handle form submission
        status = self.query_one("#status_message", Label)
        status.update(f"User created: {event.data['username']}")
        status.add_class("success")

# Template (Page-level)
class UserManagementApp(App):
    CSS = """
    .user-form { padding: 1; border: solid; }
    .input-label { width: 15; text-align: right; }
    .labeled-input { width: 1fr; }
    .toggle-label { padding-left: 1; }
    .panel-title { text-style: bold; text-align: center; }
    .status { margin-top: 1; }
    .status.success { color: green; }
    .status.error { color: red; }
    """
    
    def compose(self) -> ComposeResult:
        yield UserManagementPanel()
```

**Benefits**:
- High reusability
- Consistent UI patterns
- Easier testing of individual components
- Clear separation of concerns

---

## State Management Patterns

### Centralized State Pattern

**Intent**: Manage application state in a single, centralized store with predictable state updates.

**Implementation**:
```python
from typing import Dict, Any, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from textual.app import App
from textual.widgets import Static, Button
from textual.containers import Vertical

# Action Types
class ActionType(Enum):
    INCREMENT = "INCREMENT"
    DECREMENT = "DECREMENT"
    SET_USER = "SET_USER"
    RESET = "RESET"

@dataclass
class Action:
    type: ActionType
    payload: Any = None

# State Definition
@dataclass
class AppState:
    counter: int = 0
    user: Dict[str, Any] = field(default_factory=dict)
    loading: bool = False

# Reducer Functions
def counter_reducer(state: AppState, action: Action) -> AppState:
    if action.type == ActionType.INCREMENT:
        return AppState(**{**state.__dict__, "counter": state.counter + 1})
    elif action.type == ActionType.DECREMENT:
        return AppState(**{**state.__dict__, "counter": state.counter - 1})
    elif action.type == ActionType.RESET:
        return AppState(**{**state.__dict__, "counter": 0})
    return state

def user_reducer(state: AppState, action: Action) -> AppState:
    if action.type == ActionType.SET_USER:
        return AppState(**{**state.__dict__, "user": action.payload})
    return state

# Store Implementation
class Store:
    def __init__(self, initial_state: AppState):
        self._state = initial_state
        self._reducers: List[Callable[[AppState, Action], AppState]] = []
        self._subscribers: List[Callable[[AppState], None]] = []
    
    def add_reducer(self, reducer: Callable[[AppState, Action], AppState]):
        self._reducers.append(reducer)
    
    def subscribe(self, subscriber: Callable[[AppState], None]):
        self._subscribers.append(subscriber)
    
    def dispatch(self, action: Action):
        new_state = self._state
        for reducer in self._reducers:
            new_state = reducer(new_state, action)
        
        if new_state != self._state:
            self._state = new_state
            self._notify_subscribers()
    
    def get_state(self) -> AppState:
        return self._state
    
    def _notify_subscribers(self):
        for subscriber in self._subscribers:
            subscriber(self._state)

# Connected Components
class CounterDisplay(Static):
    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        self.store.subscribe(self.on_state_change)
    
    def on_mount(self):
        self.update_display()
    
    def on_state_change(self, state: AppState):
        self.update_display()
    
    def update_display(self):
        state = self.store.get_state()
        self.update(f"Counter: {state.counter}")

class CounterControls(Vertical):
    def __init__(self, store: Store):
        super().__init__()
        self.store = store
    
    def compose(self) -> ComposeResult:
        yield Button("Increment", id="increment")
        yield Button("Decrement", id="decrement")
        yield Button("Reset", id="reset")
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "increment":
            self.store.dispatch(Action(ActionType.INCREMENT))
        elif event.button.id == "decrement":
            self.store.dispatch(Action(ActionType.DECREMENT))
        elif event.button.id == "reset":
            self.store.dispatch(Action(ActionType.RESET))

# Application with Store
class StateApp(App):
    def __init__(self):
        super().__init__()
        self.store = Store(AppState())
        self.store.add_reducer(counter_reducer)
        self.store.add_reducer(user_reducer)
    
    def compose(self) -> ComposeResult:
        yield CounterDisplay(self.store)
        yield CounterControls(self.store)
```

**When to Use**:
- Complex applications with shared state
- Multiple components need access to the same data
- Need for time-travel debugging
- Predictable state updates required

---

### Event-Driven State Pattern

**Intent**: Manage state through domain events that represent business occurrences.

**Implementation**:
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from textual.app import App
from textual.widgets import Label, Button, ListView, ListItem

# Domain Events
@dataclass
class DomainEvent(ABC):
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class TaskCreated(DomainEvent):
    task_id: str
    description: str
    priority: str

@dataclass
class TaskCompleted(DomainEvent):
    task_id: str

@dataclass
class TaskDeleted(DomainEvent):
    task_id: str

# Event Store
class EventStore:
    def __init__(self):
        self._events: List[DomainEvent] = []
        self._handlers: Dict[type, List[Callable]] = {}
    
    def append_event(self, event: DomainEvent):
        self._events.append(event)
        self._dispatch_event(event)
    
    def get_events(self) -> List[DomainEvent]:
        return self._events.copy()
    
    def subscribe(self, event_type: type, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def _dispatch_event(self, event: DomainEvent):
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            handler(event)

# Projections (Read Models)
class TaskProjection:
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self._tasks: Dict[str, Dict] = {}
        self._setup_handlers()
        self._rebuild_from_events()
    
    def _setup_handlers(self):
        self.event_store.subscribe(TaskCreated, self._on_task_created)
        self.event_store.subscribe(TaskCompleted, self._on_task_completed)
        self.event_store.subscribe(TaskDeleted, self._on_task_deleted)
    
    def _on_task_created(self, event: TaskCreated):
        self._tasks[event.task_id] = {
            "id": event.task_id,
            "description": event.description,
            "priority": event.priority,
            "completed": False,
            "created_at": event.timestamp
        }
    
    def _on_task_completed(self, event: TaskCompleted):
        if event.task_id in self._tasks:
            self._tasks[event.task_id]["completed"] = True
            self._tasks[event.task_id]["completed_at"] = event.timestamp
    
    def _on_task_deleted(self, event: TaskDeleted):
        self._tasks.pop(event.task_id, None)
    
    def _rebuild_from_events(self):
        """Rebuild projection from event history"""
        self._tasks.clear()
        for event in self.event_store.get_events():
            if isinstance(event, TaskCreated):
                self._on_task_created(event)
            elif isinstance(event, TaskCompleted):
                self._on_task_completed(event)
            elif isinstance(event, TaskDeleted):
                self._on_task_deleted(event)
    
    def get_all_tasks(self) -> List[Dict]:
        return list(self._tasks.values())
    
    def get_active_tasks(self) -> List[Dict]:
        return [task for task in self._tasks.values() if not task["completed"]]
```

**Benefits**:
- Complete audit trail
- Easy to implement undo/redo functionality
- Temporal queries possible
- Decoupled components

---

## Testing Patterns

### Snapshot Testing Pattern

**Intent**: Capture and compare visual output to detect unintended UI changes.

**Implementation**:
```python
import pytest
from textual.app import App
from textual.widgets import Button, Label
from textual.containers import Vertical

class SimpleApp(App):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Hello, World!", id="greeting"),
            Button("Click me!", id="click_button"),
        )
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "click_button":
            greeting = self.query_one("#greeting", Label)
            greeting.update("Button was clicked!")

# Basic snapshot test
def test_simple_app_initial_state(snap_compare):
    """Test the initial state of the application"""
    app = SimpleApp()
    assert snap_compare(app)

# Test with interaction
def test_simple_app_after_click(snap_compare):
    """Test application state after button click"""
    app = SimpleApp()
    assert snap_compare(app, press=["tab", "enter"])

# Test with custom terminal size
def test_simple_app_small_terminal(snap_compare):
    """Test application in a smaller terminal"""
    app = SimpleApp()
    assert snap_compare(app, terminal_size=(40, 20))

# Test with custom setup
def test_simple_app_complex_interaction(snap_compare):
    """Test complex user interaction sequence"""
    app = SimpleApp()
    
    async def run_before(pilot):
        # Custom setup before screenshot
        await pilot.press("tab")  # Focus button
        await pilot.pause(0.1)    # Small pause for animation
        await pilot.press("enter") # Click button
        await pilot.pause(0.1)    # Allow update to complete
    
    assert snap_compare(app, run_before=run_before)
```

**Running Tests**:
```bash
# Run snapshot tests
pytest test_ui.py

# Update snapshots when changes are intentional
pytest test_ui.py --snapshot-update

# View differences in your editor (set environment variable)
export TEXTUAL_SNAPSHOT_FILE_OPEN_PREFIX="code://file/"
pytest test_ui.py  # Failed tests will show clickable links
```

### Unit Testing Pattern

**Intent**: Test individual components in isolation using mocks and test doubles.

**Implementation**:
```python
import pytest
from unittest.mock import Mock, AsyncMock
from textual.app import App
from textual.widgets import Input, Button
from textual.containers import Vertical

# Component to test
class LoginForm(Vertical):
    def __init__(self, auth_service):
        super().__init__()
        self.auth_service = auth_service
    
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Username", id="username")
        yield Input(placeholder="Password", password=True, id="password")
        yield Button("Login", id="login_button")
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "login_button":
            username = self.query_one("#username", Input).value
            password = self.query_one("#password", Input).value
            
            try:
                result = await self.auth_service.authenticate(username, password)
                if result.success:
                    self.post_message(self.LoginSuccess(result.user))
                else:
                    self.post_message(self.LoginFailed(result.error))
            except Exception as e:
                self.post_message(self.LoginFailed(str(e)))
    
    class LoginSuccess(Vertical.Event):
        def __init__(self, user):
            super().__init__()
            self.user = user
    
    class LoginFailed(Vertical.Event):
        def __init__(self, error):
            super().__init__()
            self.error = error

# Test with mocked dependencies
@pytest.mark.asyncio
async def test_successful_login():
    # Setup mocks
    mock_auth_service = Mock()
    mock_auth_service.authenticate = AsyncMock()
    mock_result = Mock()
    mock_result.success = True
    mock_result.user = {"id": 1, "username": "testuser"}
    mock_auth_service.authenticate.return_value = mock_result
    
    # Create app with test component
    class TestApp(App):
        def __init__(self):
            super().__init__()
            self.login_form = LoginForm(mock_auth_service)
            self.messages = []
        
        def compose(self):
            yield self.login_form
        
        def on_login_form_login_success(self, event):
            self.messages.append(("success", event.user))
        
        def on_login_form_login_failed(self, event):
            self.messages.append(("failed", event.error))
    
    # Run test
    async with TestApp().run_test() as pilot:
        # Enter credentials
        await pilot.click("#username")
        await pilot.type("testuser")
        await pilot.click("#password")
        await pilot.type("password123")
        
        # Click login
        await pilot.click("#login_button")
        await pilot.pause()  # Allow async operation to complete
        
        # Verify
        app = pilot.app
        assert len(app.messages) == 1
        assert app.messages[0][0] == "success"
        assert app.messages[0][1]["username"] == "testuser"
        
        mock_auth_service.authenticate.assert_called_once_with("testuser", "password123")

@pytest.mark.asyncio
async def test_failed_login():
    # Setup mocks for failure case
    mock_auth_service = Mock()
    mock_auth_service.authenticate = AsyncMock()
    mock_result = Mock()
    mock_result.success = False
    mock_result.error = "Invalid credentials"
    mock_auth_service.authenticate.return_value = mock_result
    
    class TestApp(App):
        def __init__(self):
            super().__init__()
            self.login_form = LoginForm(mock_auth_service)
            self.messages = []
        
        def compose(self):
            yield self.login_form
        
        def on_login_form_login_failed(self, event):
            self.messages.append(("failed", event.error))
    
    async with TestApp().run_test() as pilot:
        await pilot.click("#username")
        await pilot.type("wronguser")
        await pilot.click("#password")
        await pilot.type("wrongpass")
        await pilot.click("#login_button")
        await pilot.pause()
        
        app = pilot.app
        assert len(app.messages) == 1
        assert app.messages[0] == ("failed", "Invalid credentials")
```

---

## Integration Patterns

### Rich + Textual Integration

**Intent**: Leverage Rich's advanced rendering capabilities within Textual applications.

**Implementation**:
```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from textual.app import App, ComposeResult
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal

# Rich-Enhanced Static Widget
class RichTable(Static):
    def __init__(self, data: List[Dict]):
        super().__init__()
        self.data = data
        self.table = self._create_rich_table()
    
    def _create_rich_table(self) -> Table:
        table = Table(show_header=True, header_style="bold magenta")
        
        if self.data:
            # Add columns based on first row keys
            for key in self.data[0].keys():
                table.add_column(key.title(), style="cyan", no_wrap=True)
            
            # Add rows
            for row in self.data:
                table.add_row(*[str(value) for value in row.values()])
        
        return table
    
    def update_data(self, new_data: List[Dict]):
        self.data = new_data
        self.table = self._create_rich_table()
        self.update(self.table)
    
    def on_mount(self):
        self.update(self.table)

class RichSyntaxHighlighter(Static):
    def __init__(self, code: str, language: str):
        super().__init__()
        self.code = code
        self.language = language
    
    def on_mount(self):
        syntax = Syntax(
            self.code,
            self.language,
            theme="monokai",
            line_numbers=True,
            code_width=80
        )
        panel = Panel(syntax, title=f"{self.language.title()} Code", border_style="blue")
        self.update(panel)

class RichProgressBar(Static):
    def __init__(self):
        super().__init__()
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        self.task_id = None
    
    def on_mount(self):
        self.task_id = self.progress.add_task("Processing...", total=100)
        self.update(self.progress)
    
    def update_progress(self, completed: int):
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=completed)
            self.update(self.progress)

# Dashboard with Rich Components
class RichDashboard(App):
    CSS = """
    .dashboard-section {
        border: solid;
        margin: 1;
        padding: 1;
    }
    
    .code-section {
        height: 20;
    }
    
    .table-section {
        height: 15;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.sample_data = [
            {"Name": "Alice", "Age": 30, "City": "New York"},
            {"Name": "Bob", "Age": 25, "City": "Los Angeles"},
            {"Name": "Charlie", "Age": 35, "City": "Chicago"},
        ]
        self.sample_code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Generate first 10 numbers
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
'''
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Rich Integration Dashboard", classes="dashboard-title")
            
            with Horizontal():
                with Vertical(classes="dashboard-section table-section"):
                    yield Static("Data Table", classes="section-title")
                    yield RichTable(self.sample_data, id="data_table")
                    yield Button("Refresh Data", id="refresh_data")
                
                with Vertical(classes="dashboard-section code-section"):
                    yield Static("Code Viewer", classes="section-title")
                    yield RichSyntaxHighlighter(self.sample_code, "python")
            
            with Vertical(classes="dashboard-section"):
                yield Static("Progress Tracker", classes="section-title")
                yield RichProgressBar(id="progress_bar")
                yield Button("Start Task", id="start_task")
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh_data":
            # Simulate data update
            new_data = [
                {"Name": f"User {i}", "Score": i * 10, "Status": "Active"}
                for i in range(1, 6)
            ]
            table = self.query_one("#data_table", RichTable)
            table.update_data(new_data)
        
        elif event.button.id == "start_task":
            # Simulate progress
            progress_bar = self.query_one("#progress_bar", RichProgressBar)
            for i in range(0, 101, 10):
                progress_bar.update_progress(i)
                await self.sleep(0.2)
```

### Typer + Textual Hybrid Pattern

**Intent**: Create applications that work both as CLI tools and interactive TUI applications.

**Implementation**:
```python
import typer
from typing import Optional, List
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import DirectoryTree, Header, Footer, TextLog
from textual.containers import Horizontal, Vertical

# Shared Business Logic
class FileAnalyzer:
    def __init__(self, root_path: Path):
        self.root_path = root_path
    
    def analyze_directory(self) -> dict:
        """Analyze directory structure and return statistics"""
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "file_types": {},
            "largest_files": [],
        }
        
        for path in self.root_path.rglob("*"):
            if path.is_file():
                stats["total_files"] += 1
                suffix = path.suffix.lower() or "no extension"
                stats["file_types"][suffix] = stats["file_types"].get(suffix, 0) + 1
                
                size = path.stat().st_size
                stats["largest_files"].append((str(path), size))
            elif path.is_dir():
                stats["total_dirs"] += 1
        
        # Keep only top 10 largest files
        stats["largest_files"].sort(key=lambda x: x[1], reverse=True)
        stats["largest_files"] = stats["largest_files"][:10]
        
        return stats

# TUI Implementation
class FileAnalyzerTUI(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]
    
    def __init__(self, root_path: Path):
        super().__init__()
        self.root_path = root_path
        self.analyzer = FileAnalyzer(root_path)
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield DirectoryTree(str(self.root_path), id="dir_tree")
            with Vertical():
                yield TextLog(id="analysis_log", auto_scroll=True)
        yield Footer()
    
    def on_mount(self):
        self.run_analysis()
    
    def action_refresh(self):
        self.run_analysis()
    
    def run_analysis(self):
        log = self.query_one("#analysis_log", TextLog)
        log.clear()
        log.write("Analyzing directory structure...")
        
        stats = self.analyzer.analyze_directory()
        
        log.write(f"[bold green]Analysis Results for: {self.root_path}[/bold green]")
        log.write(f"Total Files: {stats['total_files']}")
        log.write(f"Total Directories: {stats['total_dirs']}")
        log.write("")
        log.write("[bold blue]File Types:[/bold blue]")
        for ext, count in sorted(stats['file_types'].items()):
            log.write(f"  {ext}: {count}")
        log.write("")
        log.write("[bold blue]Largest Files:[/bold blue]")
        for file_path, size in stats['largest_files']:
            size_mb = size / (1024 * 1024)
            log.write(f"  {size_mb:.2f} MB - {file_path}")

# CLI Implementation with Typer
app = typer.Typer(help="File Analysis Tool - CLI and TUI modes")

@app.command("analyze")
def analyze_cli(
    path: Path = typer.Argument(..., help="Directory path to analyze"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to file")
):
    """Analyze directory structure (CLI mode)"""
    if not path.exists():
        typer.echo(f"Error: Path {path} does not exist", err=True)
        raise typer.Exit(1)
    
    analyzer = FileAnalyzer(path)
    stats = analyzer.analyze_directory()
    
    # Format output
    output_lines = [
        f"Analysis Results for: {path}",
        f"Total Files: {stats['total_files']}",
        f"Total Directories: {stats['total_dirs']}",
        "",
        "File Types:",
    ]
    
    for ext, count in sorted(stats['file_types'].items()):
        output_lines.append(f"  {ext}: {count}")
    
    output_lines.extend(["", "Largest Files:"])
    for file_path, size in stats['largest_files']:
        size_mb = size / (1024 * 1024)
        output_lines.append(f"  {size_mb:.2f} MB - {file_path}")
    
    result_text = "\n".join(output_lines)
    
    if output:
        output.write_text(result_text)
        typer.echo(f"Results saved to {output}")
    else:
        typer.echo(result_text)

@app.command("tui")
def launch_tui(
    path: Path = typer.Argument(".", help="Directory path to analyze")
):
    """Launch interactive TUI mode"""
    if not path.exists():
        typer.echo(f"Error: Path {path} does not exist", err=True)
        raise typer.Exit(1)
    
    tui_app = FileAnalyzerTUI(path)
    tui_app.run()

@app.command("watch")
def watch_directory(
    path: Path = typer.Argument(".", help="Directory path to watch"),
    interval: int = typer.Option(5, "--interval", "-i", help="Check interval in seconds")
):
    """Watch directory for changes and show live updates"""
    import time
    import hashlib
    
    typer.echo(f"Watching {path} for changes (interval: {interval}s)")
    typer.echo("Press Ctrl+C to stop")
    
    analyzer = FileAnalyzer(path)
    last_hash = ""
    
    try:
        while True:
            stats = analyzer.analyze_directory()
            current_hash = hashlib.md5(str(stats).encode()).hexdigest()
            
            if current_hash != last_hash:
                typer.echo(f"\n[{time.strftime('%H:%M:%S')}] Directory changed:")
                typer.echo(f"Files: {stats['total_files']}, Dirs: {stats['total_dirs']}")
                last_hash = current_hash
            
            time.sleep(interval)
    except KeyboardInterrupt:
        typer.echo("\nStopped watching.")

if __name__ == "__main__":
    app()
```

**Usage Examples**:
```bash
# CLI mode - quick analysis
python file_analyzer.py analyze /path/to/directory

# CLI mode - save to file  
python file_analyzer.py analyze /path/to/directory --output results.txt

# TUI mode - interactive analysis
python file_analyzer.py tui /path/to/directory

# Watch mode - monitor changes
python file_analyzer.py watch /path/to/directory --interval 10
```

---

## Performance Patterns

### Async/Await Concurrency Pattern

**Intent**: Handle I/O-bound operations efficiently without blocking the UI.

**Implementation**:
```python
import asyncio
import aiohttp
from typing import List, Dict
from textual.app import App, ComposeResult
from textual.widgets import Button, Static, ProgressBar
from textual.containers import Vertical, Horizontal
from textual.worker import Worker, get_current_worker

class DataFetcher:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_url(self, url: str) -> Dict:
        """Fetch data from a single URL"""
        try:
            async with self.session.get(url) as response:
                return {
                    "url": url,
                    "status": response.status,
                    "size": len(await response.text()),
                    "success": True
                }
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "success": False
            }
    
    async def fetch_multiple(self, urls: List[str], progress_callback=None) -> List[Dict]:
        """Fetch data from multiple URLs concurrently"""
        results = []
        
        # Create tasks for concurrent execution
        tasks = [self.fetch_url(url) for url in urls]
        
        # Process results as they complete
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results.append(result)
            
            # Report progress if callback provided
            if progress_callback:
                await progress_callback(i + 1, len(urls))
        
        return results

class AsyncDataApp(App):
    CSS = """
    .status-section {
        height: 10;
        border: solid;
        padding: 1;
        margin: 1;
    }
    
    .results-section {
        height: 1fr;
        border: solid;
        padding: 1;
        margin: 1;
    }
    
    .progress-section {
        height: 5;
        padding: 1;
        margin: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.urls = [
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/2", 
            "https://httpbin.org/json",
            "https://httpbin.org/headers",
            "https://httpbin.org/user-agent",
        ]
    
    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal():
                yield Button("Start Async Fetch", id="start_async", variant="primary")
                yield Button("Start Sync Fetch", id="start_sync", variant="default")
                yield Button("Cancel", id="cancel", variant="error")
            
            with Vertical(classes="progress-section"):
                yield Static("Ready", id="status")
                yield ProgressBar(id="progress", show_percentage=True)
            
            yield Static("", id="results", classes="results-section")
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "start_async":
            self.start_async_fetch()
        elif event.button.id == "start_sync":
            self.start_sync_fetch()
        elif event.button.id == "cancel":
            self.cancel_current_operation()
    
    @Worker(exclusive=True)
    async def start_async_fetch(self) -> None:
        """Fetch URLs concurrently using async pattern"""
        status = self.query_one("#status", Static)
        progress = self.query_one("#progress", ProgressBar)
        results = self.query_one("#results", Static)
        
        status.update("Starting async fetch...")
        progress.update(progress=0)
        results.update("")
        
        async def progress_callback(completed: int, total: int):
            progress.update(progress=completed / total * 100)
            status.update(f"Fetching... {completed}/{total}")
        
        try:
            async with DataFetcher() as fetcher:
                fetch_results = await fetcher.fetch_multiple(
                    self.urls, 
                    progress_callback=progress_callback
                )
            
            # Format and display results
            result_text = "Async Fetch Results:\n\n"
            for result in fetch_results:
                if result["success"]:
                    result_text += f"✅ {result['url']} - Status: {result['status']}, Size: {result['size']} bytes\n"
                else:
                    result_text += f"❌ {result['url']} - Error: {result['error']}\n"
            
            results.update(result_text)
            status.update("Async fetch completed!")
            progress.update(progress=100)
            
        except Exception as e:
            results.update(f"Error during async fetch: {e}")
            status.update("Async fetch failed!")
    
    @Worker(exclusive=True)
    async def start_sync_fetch(self) -> None:
        """Fetch URLs sequentially to demonstrate the difference"""
        status = self.query_one("#status", Static)
        progress = self.query_one("#progress", ProgressBar)
        results = self.query_one("#results", Static)
        
        status.update("Starting sequential fetch...")
        progress.update(progress=0)
        results.update("")
        
        try:
            async with DataFetcher() as fetcher:
                fetch_results = []
                total = len(self.urls)
                
                for i, url in enumerate(self.urls):
                    result = await fetcher.fetch_url(url)
                    fetch_results.append(result)
                    
                    progress.update(progress=(i + 1) / total * 100)
                    status.update(f"Sequential fetch... {i + 1}/{total}")
            
            # Format and display results
            result_text = "Sequential Fetch Results:\n\n"
            for result in fetch_results:
                if result["success"]:
                    result_text += f"✅ {result['url']} - Status: {result['status']}, Size: {result['size']} bytes\n"
                else:
                    result_text += f"❌ {result['url']} - Error: {result['error']}\n"
            
            results.update(result_text)
            status.update("Sequential fetch completed!")
            
        except Exception as e:
            results.update(f"Error during sequential fetch: {e}")
            status.update("Sequential fetch failed!")
    
    def cancel_current_operation(self):
        """Cancel any running worker"""
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        status = self.query_one("#status", Static)
        status.update("Operation cancelled")
```

**Benefits**:
- Non-blocking UI during I/O operations
- Better resource utilization
- Responsive user experience
- Scalable to many concurrent operations

---

### Lazy Loading Pattern

**Intent**: Load data only when needed to improve application startup time and memory usage.

**Implementation**:
```python
from typing import Optional, List, Dict, Any
from textual.app import App, ComposeResult
from textual.widgets import TreeNode, Tree, Static, LoadingIndicator
from textual.containers import Horizontal
import asyncio

class LazyDataNode:
    def __init__(self, id: str, label: str, has_children: bool = False, data: Any = None):
        self.id = id
        self.label = label
        self.has_children = has_children
        self.data = data
        self.children: Optional[List['LazyDataNode']] = None
        self.loaded = False
    
    async def load_children(self) -> List['LazyDataNode']:
        """Override in subclasses to implement actual data loading"""
        if self.loaded:
            return self.children or []
        
        # Simulate network/database delay
        await asyncio.sleep(0.5)
        
        # Mock data loading based on node type
        if self.id.startswith("folder"):
            self.children = [
                LazyDataNode(f"{self.id}_file_{i}", f"File {i}.txt", False)
                for i in range(3)
            ]
        elif self.id == "root":
            self.children = [
                LazyDataNode("folder_1", "Documents", True),
                LazyDataNode("folder_2", "Images", True),
                LazyDataNode("folder_3", "Projects", True),
            ]
        else:
            self.children = []
        
        self.loaded = True
        return self.children

class LazyTree(Tree):
    def __init__(self, root_node: LazyDataNode):
        super().__init__(root_node.label)
        self.node_map: Dict[str, LazyDataNode] = {}
        self.root_data = root_node
        self.node_map[str(self.root.id)] = root_node
        
        # Show expansion indicator if node has children
        if root_node.has_children:
            # Add a placeholder child to show expansion arrow
            placeholder = self.root.add("Loading...", data="placeholder")
            placeholder.allow_expand = False
    
    async def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle node expansion with lazy loading"""
        node = event.node
        data_node = self.node_map.get(str(node.id))
        
        if data_node and data_node.has_children and not data_node.loaded:
            # Show loading indicator
            self.app.query_one("#loading", LoadingIndicator).display = True
            
            # Remove placeholder children
            node.remove_children()
            
            try:
                # Load children data
                children = await data_node.load_children()
                
                # Add real children to tree
                for child_data in children:
                    child_node = node.add(child_data.label, data=child_data.data)
                    self.node_map[str(child_node.id)] = child_data
                    
                    # Add placeholder for expandable children
                    if child_data.has_children:
                        placeholder = child_node.add("Loading...", data="placeholder")
                        placeholder.allow_expand = False
            
            finally:
                # Hide loading indicator
                self.app.query_one("#loading", LoadingIndicator).display = False
    
    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection to show details"""
        data_node = self.node_map.get(str(event.node.id))
        if data_node:
            details = self.app.query_one("#details", Static)
            details.update(f"Selected: {data_node.label}\nID: {data_node.id}\nType: {'Folder' if data_node.has_children else 'File'}")

class LazyLoadingApp(App):
    CSS = """
    #tree_container {
        width: 1fr;
        height: 1fr;
        border: solid;
        padding: 1;
    }
    
    #details {
        width: 1fr;
        height: 1fr;
        border: solid;
        padding: 1;
        margin-left: 1;
    }
    
    #loading {
        dock: bottom;
        height: 3;
    }
    """
    
    def compose(self) -> ComposeResult:
        root_node = LazyDataNode("root", "File System", has_children=True)
        
        with Horizontal():
            yield LazyTree(root_node, id="file_tree")
            yield Static("Select a node to view details", id="details")
        
        yield LoadingIndicator(id="loading")
        self.query_one("#loading").display = False

# More complex lazy loading with caching and error handling
class CachedLazyLoader:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._loading: Dict[str, bool] = {}
    
    async def load_data(self, key: str, loader_func) -> Any:
        """Load data with caching and prevent duplicate requests"""
        
        # Return cached data if available
        if key in self._cache:
            return self._cache[key]
        
        # Prevent duplicate loading
        if self._loading.get(key, False):
            # Wait for ongoing load to complete
            while self._loading.get(key, False):
                await asyncio.sleep(0.1)
            return self._cache.get(key)
        
        # Start loading
        self._loading[key] = True
        
        try:
            data = await loader_func()
            self._cache[key] = data
            return data
        except Exception as e:
            # Cache errors for a short time to avoid retry storms
            self._cache[key] = {"error": str(e)}
            raise
        finally:
            self._loading[key] = False
    
    def invalidate(self, key: str):
        """Invalidate cached data"""
        self._cache.pop(key, None)
        self._loading.pop(key, False)
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._loading.clear()
```

**Benefits**:
- Faster application startup
- Reduced memory usage
- Better user experience for large datasets
- Scalable to very large data structures

---

## Advanced Patterns

### Plugin Architecture Pattern

**Intent**: Allow extending application functionality through dynamically loaded plugins.

**Implementation**:
```python
import os
import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Dict, List, Type, Any
from textual.app import App, ComposeResult
from textual.widgets import Static, Button, ListView, ListItem, Label
from textual.containers import Horizontal, Vertical

# Plugin Interface
class TextualPlugin(ABC):
    """Base class for all Textual plugins"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass
    
    @property
    def description(self) -> str:
        """Plugin description"""
        return "No description provided"
    
    @abstractmethod
    async def initialize(self, app: App) -> None:
        """Initialize plugin when app starts"""
        pass
    
    @abstractmethod
    async def shutdown(self, app: App) -> None:
        """Cleanup when app shuts down"""
        pass
    
    def get_widget(self) -> Any:
        """Return widget for this plugin (optional)"""
        return None
    
    def get_commands(self) -> Dict[str, callable]:
        """Return commands this plugin provides (optional)"""
        return {}

# Plugin Manager
class PluginManager:
    def __init__(self, plugin_directory: str):
        self.plugin_directory = plugin_directory
        self.plugins: Dict[str, TextualPlugin] = {}
        self.plugin_classes: Dict[str, Type[TextualPlugin]] = {}
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugin files"""
        plugin_files = []
        
        if not os.path.exists(self.plugin_directory):
            return plugin_files
        
        for file in os.listdir(self.plugin_directory):
            if file.endswith('.py') and not file.startswith('_'):
                plugin_files.append(file[:-3])  # Remove .py extension
        
        return plugin_files
    
    async def load_plugin(self, plugin_name: str) -> bool:
        """Load a specific plugin by name"""
        try:
            # Import the plugin module
            module_path = f"{self.plugin_directory.replace('/', '.')}.{plugin_name}"
            module = importlib.import_module(module_path)
            
            # Find plugin classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, TextualPlugin) and 
                    obj != TextualPlugin):
                    
                    # Instantiate plugin
                    plugin_instance = obj()
                    self.plugin_classes[plugin_instance.name] = obj
                    self.plugins[plugin_instance.name] = plugin_instance
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    async def load_all_plugins(self, app: App) -> None:
        """Load all discovered plugins"""
        plugin_files = self.discover_plugins()
        
        for plugin_file in plugin_files:
            success = await self.load_plugin(plugin_file)
            if success:
                plugin_name = list(self.plugins.keys())[-1]  # Get last added
                await self.plugins[plugin_name].initialize(app)
    
    async def unload_plugin(self, plugin_name: str, app: App) -> bool:
        """Unload a specific plugin"""
        if plugin_name in self.plugins:
            await self.plugins[plugin_name].shutdown(app)
            del self.plugins[plugin_name]
            return True
        return False
    
    def get_plugin(self, name: str) -> TextualPlugin:
        """Get loaded plugin by name"""
        return self.plugins.get(name)
    
    def get_all_plugins(self) -> Dict[str, TextualPlugin]:
        """Get all loaded plugins"""
        return self.plugins.copy()

# Example Plugin Implementations
class ClockPlugin(TextualPlugin):
    @property
    def name(self) -> str:
        return "clock"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Displays current time"
    
    async def initialize(self, app: App) -> None:
        self.app = app
        # Set up any necessary resources
    
    async def shutdown(self, app: App) -> None:
        # Clean up resources
        pass
    
    def get_widget(self) -> Static:
        import datetime
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        return Static(f"Time: {current_time}", classes="clock-widget")
    
    def get_commands(self) -> Dict[str, callable]:
        return {
            "show_time": self._show_time,
            "show_date": self._show_date,
        }
    
    def _show_time(self):
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")
    
    def _show_date(self):
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d")

class CalculatorPlugin(TextualPlugin):
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Simple calculator functionality"
    
    async def initialize(self, app: App) -> None:
        pass
    
    async def shutdown(self, app: App) -> None:
        pass
    
    def get_commands(self) -> Dict[str, callable]:
        return {
            "add": lambda a, b: a + b,
            "subtract": lambda a, b: a - b,
            "multiply": lambda a, b: a * b,
            "divide": lambda a, b: a / b if b != 0 else "Error: Division by zero",
        }

# Application with Plugin System
class PluginApp(App):
    CSS = """
    .plugin-list {
        width: 1fr;
        height: 1fr;
        border: solid;
        padding: 1;
    }
    
    .plugin-area {
        width: 2fr;
        height: 1fr;
        border: solid;
        padding: 1;
        margin-left: 1;
    }
    
    .plugin-info {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid;
    }
    """
    
    def __init__(self, plugin_directory: str = "plugins"):
        super().__init__()
        self.plugin_manager = PluginManager(plugin_directory)
    
    async def on_mount(self) -> None:
        await self.plugin_manager.load_all_plugins(self)
        self.refresh_plugin_list()
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Label("Available Plugins", classes="section-title")
                yield ListView(id="plugin_list", classes="plugin-list")
                yield Button("Refresh Plugins", id="refresh_plugins")
            
            with Vertical():
                yield Label("Plugin Area", classes="section-title")
                yield Static("Select a plugin to view details", id="plugin_info", classes="plugin-info")
                yield Static("", id="plugin_widget_area", classes="plugin-area")
    
    def refresh_plugin_list(self):
        """Refresh the plugin list display"""
        plugin_list = self.query_one("#plugin_list", ListView)
        plugin_list.clear()
        
        for name, plugin in self.plugin_manager.get_all_plugins().items():
            item = ListItem(Label(f"{plugin.name} v{plugin.version}"), data=name)
            plugin_list.append(item)
    
    async def on_list_view_selected(self, event: ListView.Selected):
        """Handle plugin selection"""
        plugin_name = event.item.data
        plugin = self.plugin_manager.get_plugin(plugin_name)
        
        if plugin:
            # Update plugin info
            info = self.query_one("#plugin_info", Static)
            info.update(f"Name: {plugin.name}\nVersion: {plugin.version}\nDescription: {plugin.description}")
            
            # Show plugin widget if available
            widget_area = self.query_one("#plugin_widget_area", Static)
            plugin_widget = plugin.get_widget()
            
            if plugin_widget:
                # Clear existing content and add plugin widget
                widget_area.remove_children()
                await widget_area.mount(plugin_widget)
            else:
                widget_area.update("This plugin doesn't provide a widget.")
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh_plugins":
            await self.plugin_manager.load_all_plugins(self)
            self.refresh_plugin_list()
    
    def execute_plugin_command(self, plugin_name: str, command: str, *args, **kwargs):
        """Execute a command from a plugin"""
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if plugin:
            commands = plugin.get_commands()
            if command in commands:
                return commands[command](*args, **kwargs)
        return None

if __name__ == "__main__":
    app = PluginApp()
    app.run()
```

**Plugin Directory Structure**:
```
plugins/
├── __init__.py
├── clock_plugin.py      # ClockPlugin implementation
├── calculator_plugin.py # CalculatorPlugin implementation
└── weather_plugin.py   # Additional plugins...
```

**Benefits**:
- Extensible architecture
- Clean separation of concerns
- Dynamic loading/unloading
- Third-party plugin support

---

### Command Pattern with Undo/Redo

**Intent**: Encapsulate operations as objects to support undo/redo functionality.

**Implementation**:
```python
from abc import ABC, abstractmethod
from typing import List, Optional, Any
from dataclasses import dataclass
from textual.app import App, ComposeResult
from textual.widgets import Input, Button, TextArea, Static
from textual.containers import Horizontal, Vertical

# Command Interface
class Command(ABC):
    @abstractmethod
    async def execute(self) -> Any:
        """Execute the command"""
        pass
    
    @abstractmethod
    async def undo(self) -> Any:
        """Undo the command"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the command"""
        pass

# Concrete Commands
@dataclass
class TextInsertCommand(Command):
    text_area: TextArea
    position: int
    text: str
    
    async def execute(self) -> Any:
        # Insert text at position
        current_text = self.text_area.text
        new_text = current_text[:self.position] + self.text + current_text[self.position:]
        self.text_area.text = new_text
        # Move cursor to end of inserted text
        self.text_area.cursor_position = self.position + len(self.text)
    
    async def undo(self) -> Any:
        # Remove the inserted text
        current_text = self.text_area.text
        new_text = current_text[:self.position] + current_text[self.position + len(self.text):]
        self.text_area.text = new_text
        # Move cursor back to original position
        self.text_area.cursor_position = self.position
    
    @property
    def description(self) -> str:
        return f"Insert '{self.text[:20]}...' at position {self.position}"

@dataclass
class TextDeleteCommand(Command):
    text_area: TextArea
    position: int
    length: int
    deleted_text: Optional[str] = None
    
    async def execute(self) -> Any:
        current_text = self.text_area.text
        self.deleted_text = current_text[self.position:self.position + self.length]
        new_text = current_text[:self.position] + current_text[self.position + self.length:]
        self.text_area.text = new_text
        self.text_area.cursor_position = self.position
    
    async def undo(self) -> Any:
        if self.deleted_text is not None:
            current_text = self.text_area.text
            new_text = current_text[:self.position] + self.deleted_text + current_text[self.position:]
            self.text_area.text = new_text
            self.text_area.cursor_position = self.position + len(self.deleted_text)
    
    @property
    def description(self) -> str:
        return f"Delete {self.length} characters at position {self.position}"

@dataclass
class TextReplaceCommand(Command):
    text_area: TextArea
    position: int
    old_text: str
    new_text: str
    
    async def execute(self) -> Any:
        current_text = self.text_area.text
        new_full_text = (current_text[:self.position] + 
                        self.new_text + 
                        current_text[self.position + len(self.old_text):])
        self.text_area.text = new_full_text
        self.text_area.cursor_position = self.position + len(self.new_text)
    
    async def undo(self) -> Any:
        current_text = self.text_area.text
        old_full_text = (current_text[:self.position] + 
                        self.old_text + 
                        current_text[self.position + len(self.new_text):])
        self.text_area.text = old_full_text
        self.text_area.cursor_position = self.position + len(self.old_text)
    
    @property
    def description(self) -> str:
        return f"Replace '{self.old_text[:10]}...' with '{self.new_text[:10]}...'"

# Command Manager
class CommandManager:
    def __init__(self, max_history: int = 100):
        self.history: List[Command] = []
        self.current_index: int = -1
        self.max_history = max_history
    
    async def execute_command(self, command: Command) -> None:
        """Execute a command and add it to history"""
        await command.execute()
        
        # Remove any commands after current index (when doing something after undo)
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
        
        # Add new command
        self.history.append(command)
        self.current_index += 1
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.current_index -= 1
    
    async def undo(self) -> Optional[Command]:
        """Undo the last command"""
        if self.can_undo():
            command = self.history[self.current_index]
            await command.undo()
            self.current_index -= 1
            return command
        return None
    
    async def redo(self) -> Optional[Command]:
        """Redo the next command"""
        if self.can_redo():
            self.current_index += 1
            command = self.history[self.current_index]
            await command.execute()
            return command
        return None
    
    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return self.current_index >= 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return self.current_index < len(self.history) - 1
    
    def get_history(self) -> List[str]:
        """Get command history descriptions"""
        return [cmd.description for cmd in self.history]
    
    def clear_history(self) -> None:
        """Clear all command history"""
        self.history.clear()
        self.current_index = -1

# Text Editor with Command Pattern
class CommandTextEditor(App):
    BINDINGS = [
        ("ctrl+z", "undo", "Undo"),
        ("ctrl+y", "redo", "Redo"),
        ("ctrl+r", "replace_text", "Replace"),
    ]
    
    CSS = """
    #text_area {
        height: 1fr;
        border: solid;
        padding: 1;
    }
    
    #controls {
        height: 3;
        padding: 1;
    }
    
    #status {
        height: 5;
        border: solid;
        padding: 1;
        margin-top: 1;
    }
    
    .history {
        height: 10;
        border: solid;
        padding: 1;
        margin-left: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.command_manager = CommandManager()
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield TextArea("Type some text here...", id="text_area")
                
                with Horizontal(id="controls"):
                    yield Input(placeholder="Text to insert", id="insert_input")
                    yield Button("Insert", id="insert_button")
                    yield Button("Delete Selection", id="delete_button")
                    yield Button("Undo", id="undo_button")
                    yield Button("Redo", id="redo_button")
                
                yield Static("Ready", id="status")
            
            yield Static("Command History:\n", id="history", classes="history")
    
    async def on_button_pressed(self, event: Button.Pressed):
        text_area = self.query_one("#text_area", TextArea)
        
        if event.button.id == "insert_button":
            await self.handle_insert()
        elif event.button.id == "delete_button":
            await self.handle_delete()
        elif event.button.id == "undo_button":
            await self.action_undo()
        elif event.button.id == "redo_button":
            await self.action_redo()
    
    async def handle_insert(self):
        """Handle text insertion"""
        insert_input = self.query_one("#insert_input", Input)
        text_area = self.query_one("#text_area", TextArea)
        
        text_to_insert = insert_input.value
        if text_to_insert:
            cursor_pos = text_area.cursor_position
            command = TextInsertCommand(text_area, cursor_pos, text_to_insert)
            await self.command_manager.execute_command(command)
            
            insert_input.value = ""
            self.update_status(f"Inserted: {text_to_insert}")
            self.update_history()
    
    async def handle_delete(self):
        """Handle text deletion"""
        text_area = self.query_one("#text_area", TextArea)
        
        # For simplicity, delete 1 character at cursor position
        cursor_pos = text_area.cursor_position
        if cursor_pos > 0:
            command = TextDeleteCommand(text_area, cursor_pos - 1, 1)
            await self.command_manager.execute_command(command)
            
            self.update_status("Deleted 1 character")
            self.update_history()
    
    async def action_undo(self):
        """Undo last command"""
        command = await self.command_manager.undo()
        if command:
            self.update_status(f"Undid: {command.description}")
        else:
            self.update_status("Nothing to undo")
        self.update_history()
    
    async def action_redo(self):
        """Redo next command"""
        command = await self.command_manager.redo()
        if command:
            self.update_status(f"Redid: {command.description}")
        else:
            self.update_status("Nothing to redo")
        self.update_history()
    
    async def action_replace_text(self):
        """Replace selected text (simplified)"""
        text_area = self.query_one("#text_area", TextArea)
        insert_input = self.query_one("#insert_input", Input)
        
        replacement = insert_input.value
        if replacement:
            # For demo: replace first occurrence of "text" with input
            current_text = text_area.text
            if "text" in current_text:
                pos = current_text.find("text")
                command = TextReplaceCommand(text_area, pos, "text", replacement)
                await self.command_manager.execute_command(command)
                
                insert_input.value = ""
                self.update_status(f"Replaced 'text' with '{replacement}'")
                self.update_history()
    
    def update_status(self, message: str):
        """Update status display"""
        status = self.query_one("#status", Static)
        can_undo = "Yes" if self.command_manager.can_undo() else "No"
        can_redo = "Yes" if self.command_manager.can_redo() else "No"
        
        status.update(f"{message}\nCan Undo: {can_undo} | Can Redo: {can_redo}")
    
    def update_history(self):
        """Update command history display"""
        history_widget = self.query_one("#history", Static)
        history = self.command_manager.get_history()
        
        if history:
            history_text = "Command History:\n" + "\n".join(
                f"{'>' if i == self.command_manager.current_index else ' '} {i+1}. {cmd}"
                for i, cmd in enumerate(history)
            )
        else:
            history_text = "Command History:\n(empty)"
        
        history_widget.update(history_text)

if __name__ == "__main__":
    app = CommandTextEditor()
    app.run()
```

**Benefits**:
- Undo/redo functionality
- Command queuing and batching
- Audit trail of operations
- Macro recording possibilities
- Transactional operations

---

## Summary

This guide covers the essential design patterns and architectural approaches for building robust, scalable Textual applications. Key takeaways:

1. **Choose the right architectural pattern** based on your application's complexity and requirements
2. **Leverage composition** over inheritance for flexible, reusable components  
3. **Use async patterns** for I/O-bound operations to maintain responsive UIs
4. **Implement proper state management** for complex applications with shared data
5. **Use snapshot testing** for visual regression detection and unit tests for component logic
6. **Consider hybrid CLI/TUI approaches** for maximum versatility
7. **Implement plugin architectures** for extensible applications
8. **Use command patterns** when undo/redo functionality is required

Remember to always consider performance implications, testability, and maintainability when choosing patterns for your specific use case.