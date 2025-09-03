# Textual DevTools and Debugging Guide

A comprehensive guide to debugging, performance profiling, and development workflows for Textual Python TUI applications.

## Table of Contents

- [Overview](#overview)
- [Installation and Setup](#installation-and-setup)
- [Core DevTools Features](#core-devtools-features)
- [Console Debugging Workflow](#console-debugging-workflow)
- [Development Mode Features](#development-mode-features)
- [Logging and Print Debugging](#logging-and-print-debugging)
- [Testing and Automated Debugging](#testing-and-automated-debugging)
- [Performance Profiling](#performance-profiling)
- [Web-Based Development](#web-based-development)
- [Advanced Debugging Techniques](#advanced-debugging-techniques)
- [Troubleshooting Decision Trees](#troubleshooting-decision-trees)
- [Error Handling and Exception Tracking](#error-handling-and-exception-tracking)
- [Development Environment Setup](#development-environment-setup)
- [Best Practices and Patterns](#best-practices-and-patterns)

## Overview

Textual provides a comprehensive development and debugging ecosystem designed specifically for Terminal User Interface (TUI) applications. The DevTools suite includes console debugging, live CSS editing, performance profiling, testing frameworks, and web-based development tools.

### Key DevTools Components

- **Textual Console**: Real-time debugging output capture
- **Developer Mode**: Live CSS editing and enhanced logging
- **Testing Framework**: Automated UI testing with snapshot comparison
- **Web Server**: Browser-based development and sharing
- **Performance Tools**: Memory profiling with Memray integration
- **Inspector Tools**: Widget introspection and DOM analysis

## Installation and Setup

### Core Installation

```bash
# Install Textual with development tools
pip install textual textual-dev

# Alternative: using conda-forge
micromamba install -c conda-forge textual textual-dev

# For web development features
pipx install textual-web

# For memory profiling
pipx install memray
```

### Verify Installation

```bash
# Check Textual version
textual --version

# View available commands
textual --help

# Test installation with demo
python -m textual
```

## Core DevTools Features

### Textual CLI Commands

The `textual` command provides comprehensive development utilities:

```bash
# Core commands
textual console          # Start debug console
textual run <app.py>     # Run application
textual serve <app.py>   # Serve in web browser
textual --help           # Show all commands

# Interactive tools
textual borders          # Explore border styles
textual colors           # Color palette viewer
textual easing           # Animation easing preview
textual keys             # Key binding explorer
```

### Development Workflow Commands

```bash
# Run app in development mode
textual run --dev my_app.py

# Run with custom port
textual run --dev --port 7342 my_app.py

# Generate screenshots after 5 seconds
textual run my_app.py --screenshot 5

# Serve app via command
textual serve "textual keys"

# Serve module-based app
textual serve "python -m textual"
```

## Console Debugging Workflow

### Dual-Terminal Setup

The primary debugging approach uses two terminals for clean separation of concerns:

**Terminal 1 - Debug Console:**
```bash
# Start the debug console
textual console

# With increased verbosity
textual console -v

# Filter specific message types
textual console -x SYSTEM -x EVENT -x DEBUG -x INFO

# Use custom port
textual console --port 7342
```

**Terminal 2 - Application:**
```bash
# Run app in development mode
textual run --dev my_app.py

# Connect to custom console port
textual run --dev --port 7342 my_app.py
```

### Console Output Analysis

The debug console provides comprehensive application insights:

- **Mount Operations**: Widget lifecycle events
- **Focus Changes**: UI navigation tracking  
- **Event Handling**: Key presses, mouse interactions
- **CSS Updates**: Live style changes
- **Custom Logging**: Application-specific debug output
- **Performance Warnings**: Slow operation detection

### Console Configuration

```bash
# Environment variables for enhanced debugging
export TEXTUAL_DEBUG=1           # Enable debug mode
export TEXTUAL_LOG=/path/to.log  # Fallback log file
export TEXTUAL_SLOW_THRESHOLD=100 # Performance warning threshold (ms)

# Run with environment
DEBUG=1 textual run --dev my_app.py
```

## Development Mode Features

### Live CSS Editing

Development mode enables real-time CSS modifications:

```bash
# Enable live CSS editing
textual run --dev my_app.py
```

**Workflow:**
1. Run application in development mode
2. Edit CSS files in your preferred editor
3. Save changes
4. See updates reflected immediately in terminal
5. No application restart required

### Enhanced Logging

Development mode provides detailed event tracking:

- Widget mounting and unmounting
- CSS rule application and conflicts  
- Event propagation chains
- Focus management operations
- Performance bottleneck identification

## Logging and Print Debugging

### Textual Logging API

```python
from textual import log
from textual.app import App
from textual.logging import TextualHandler

class DebugApp(App):
    def on_mount(self) -> None:
        # Simple string logging
        log("Application mounted")
        
        # Log local variables
        log(locals())
        
        # Key-value logging
        log(children=self.children, screen_size=self.size)
        
        # Rich renderables
        log(self.tree)
```

### Widget and App Logging Shortcuts

```python
from textual.app import App
from textual.widgets import Widget

class MyWidget(Widget):
    def on_mount(self) -> None:
        # Direct logging from widgets/apps
        self.log("Widget mounted", widget_id=self.id)
        self.log(self.tree)
        
class MyApp(App):
    def on_load(self) -> None:
        self.log("Application loading", pi=3.141592)
```

### Python Standard Logging Integration

```python
import logging
from textual.app import App
from textual.logging import TextualHandler

# Configure standard logging to use Textual
logging.basicConfig(
    level="NOTSET",
    handlers=[TextualHandler()],
)

class LogApp(App):
    def on_mount(self) -> None:
        # Standard logging calls appear in console
        logging.debug("Debug message via TextualHandler")
        logging.info("Info message")
        logging.error("Error message")
```

## Testing and Automated Debugging

### Basic Testing Setup

```python
from textual.testing import AppTester
from textual.app import App
import pytest

class TestApp(App):
    pass

@pytest.fixture
async def app():
    return TestApp()

async def test_app_starts(app):
    async with app.run_test() as pilot:
        assert app.is_running
```

### Simulating User Interactions

```python
async def test_user_interactions():
    app = MyApp()
    async with app.run_test() as pilot:
        # Simulate key presses
        await pilot.press("r")  # Press 'r' key
        await pilot.press("ctrl+c")  # Ctrl+C combination
        
        # Simulate mouse clicks
        await pilot.click("#button-id")  # Click by CSS selector
        await pilot.click(x=10, y=5)    # Click at coordinates
        
        # Double-click with modifiers
        await pilot.click(x=10, y=5, count=2, shift=True)
        
        # Hover over elements
        await pilot.hover("#element-id")
        
        # Change terminal size
        await pilot.resize(width=80, height=24)
```

### Snapshot Testing

Install snapshot testing plugin:
```bash
pip install pytest-textual-snapshot
```

Create snapshot tests:
```python
def test_app_appearance(snap_compare):
    # Basic snapshot test
    assert snap_compare("path/to/app.py")

def test_app_with_interactions(snap_compare):
    # Snapshot with simulated interactions
    assert snap_compare(
        "path/to/app.py",
        press="3,.,1,4,1,5,9,2,wait:400"
    )

def test_app_with_setup(snap_compare):
    async def run_before(pilot) -> None:
        await pilot.hover("#number-5")
        await pilot.press("enter")
    
    assert snap_compare("path/to/app.py", run_before=run_before)
```

### Testing Configuration

```python
# Configure pytest for async testing
# In pytest.ini or pyproject.toml:
[pytest]
asyncio_mode = auto

# Or use decorator
@pytest.mark.asyncio
async def test_async_function():
    # Your async test logic
    pass
```

## Performance Profiling

### Memory Profiling with Memray

Textual integrates with Memray for comprehensive memory profiling:

```bash
# Install Memray
pipx install memray

# Profile application locally
memray run --live my_app.py

# Serve profiling interface over web
textual-web -r "memray run --live -m http.server"
```

### Performance Monitoring

```python
from textual.app import App
import time

class PerformanceApp(App):
    def on_mount(self) -> None:
        # Monitor slow operations
        start = time.time()
        # ... expensive operation ...
        duration = time.time() - start
        
        if duration > 0.5:  # Log operations over 500ms
            self.log(f"Slow operation: {duration:.3f}s")
```

### Asyncio Task Overhead Analysis

```python
from asyncio import create_task, wait, run
from time import process_time as time

async def benchmark_tasks(count=100_000) -> float:
    """Benchmark asyncio task creation overhead."""
    
    async def nop_task() -> None:
        """Minimal task for benchmarking."""
        pass

    start = time()
    tasks = [create_task(nop_task()) for _ in range(count)]
    await wait(tasks)
    elapsed = time() - start
    return elapsed

# Run benchmark
for count in range(100_000, 1_000_000 + 1, 100_000):
    create_time = run(benchmark_tasks(count))
    tasks_per_second = count / create_time
    print(f"{count:,} tasks\t{tasks_per_second:0,.0f} tasks/s")
```

### Performance Best Practices

- **Widget Visibility Optimization**: Avoid work on invisible widgets
- **Batch Operations**: Group updates to minimize redraws
- **Async Task Management**: Monitor task creation overhead
- **Memory Usage**: Profile with Memray for memory leaks
- **Event Handling**: Optimize expensive event handlers

## Web-Based Development

### Textual-Web Server

```bash
# Install textual-web
pipx install textual-web

# Serve current terminal
textual-web -t

# Serve specific app
textual-web my_app.py

# Run welcome application
textual-web
```

### Configuration Files

Create `serve.toml` for multiple applications:
```toml
# Multiple app configuration
[app.Calculator]
command = "python calculator.py"

[app.Dictionary] 
command = "python dictionary.py"
slug = "dict"  # Custom URL slug

# Terminal configurations
[terminal.Terminal]  # Default terminal

[terminal.HTOP]
command = "htop"
```

### Account Setup and Permanent URLs

```bash
# Create account for permanent URLs
textual-web --signup

# Generated ganglion.toml
[account]
api_key = "YOUR_API_KEY_HERE"

# Use configuration file
textual-web --config ganglion.toml

# Enable debug output
DEBUG=1 textual-web --config ganglion.toml
```

## Advanced Debugging Techniques

### Rich Inspect Integration

```python
from textual.app import App, ComposeResult
from textual.widgets import RichLog
from rich.inspect import inspect

class InspectApp(App):
    def compose(self) -> ComposeResult:
        yield RichLog()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        
        # Inspect any Python object
        my_object = {"key": "value", "data": [1, 2, 3]}
        log.write(inspect(my_object, console=log.console))
        
        # Inspect widget properties
        log.write(inspect(self, methods=True))
```

### Custom Debug Modes

```python
from textual.app import App

class DebugApp(App):
    def __init__(self, debug_level: str = "INFO"):
        super().__init__()
        self.debug_level = debug_level
    
    @property 
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._debug
        
    def action_toggle_debug(self) -> None:
        """Toggle debug mode via key binding."""
        self._debug = not self._debug
        self.log(f"Debug mode: {'ON' if self._debug else 'OFF'}")
```

### Widget State Introspection

```python
from textual.widgets import Widget

class DebuggableWidget(Widget):
    def debug_state(self) -> dict:
        """Return comprehensive widget state."""
        return {
            "id": self.id,
            "classes": list(self.classes),
            "size": self.size,
            "offset": self.offset,
            "visible": self.visible,
            "focused": self.has_focus,
            "children_count": len(self.children),
            "styles": dict(self.styles),
        }
    
    def on_mount(self) -> None:
        self.log("Widget state:", **self.debug_state())
```

## Troubleshooting Decision Trees

### Application Won't Start

```
App won't start
├── Check installation
│   ├── Run: textual --version
│   ├── Reinstall: pip install textual textual-dev
│   └── Test: python -m textual
├── Check Python version
│   ├── Requires Python 3.8+
│   └── Check: python --version
├── Check import errors
│   ├── Run app with: python -m your_app
│   └── Check dependencies in traceback
└── Check console for errors
    ├── Run: textual console (Terminal 1)
    ├── Run: textual run --dev app.py (Terminal 2)
    └── Check console output for issues
```

### Console Not Showing Output

```
No console output
├── Check console connection
│   ├── Console running: textual console
│   ├── App in dev mode: textual run --dev app.py  
│   └── Same port: --port 7342 on both
├── Check verbosity level
│   ├── Increase: textual console -v
│   └── Reduce filters: textual console -x EVENT
├── Check app logging
│   ├── Add: self.log("test message")
│   ├── Import: from textual import log
│   └── Use: log("debug message")
└── Check environment variables
    ├── Set: TEXTUAL_DEBUG=1
    └── Set: TEXTUAL_LOG=/tmp/debug.log
```

### Performance Issues

```
App running slowly
├── Check widget count
│   ├── Log: self.log(len(self.query("*")))
│   ├── Optimize: Remove unnecessary widgets
│   └── Lazy load: Create widgets on demand
├── Check event handlers
│   ├── Profile: Add timing to handlers
│   ├── Optimize: Reduce expensive operations
│   └── Async: Use workers for heavy tasks
├── Check CSS complexity
│   ├── Simplify: Reduce complex selectors
│   ├── Cache: Avoid dynamic style changes
│   └── Debug: Use console CSS output
└── Profile memory usage
    ├── Install: pipx install memray
    ├── Profile: memray run --live app.py
    └── Analyze: Check for memory leaks
```

### CSS Not Applying

```
CSS styles not working
├── Check CSS file loading
│   ├── Set: CSS_PATH = "styles.css"
│   ├── Verify: File exists and readable
│   └── Test: Add obvious style changes
├── Check selector specificity
│   ├── Use: More specific selectors
│   ├── Debug: Add !important temporarily
│   └── Log: self.log(widget.styles)
├── Check inheritance
│   ├── Verify: Parent-child relationships
│   ├── Test: Direct widget styling
│   └── Debug: Widget tree with self.tree
└── Use live CSS editing
    ├── Run: textual run --dev app.py
    ├── Edit: CSS file and save
    └── Observe: Immediate changes
```

## Error Handling and Exception Tracking

### Structured Error Handling

```python
from textual.app import App
from textual.widgets import Widget
import traceback

class RobustApp(App):
    def on_exception(self, exception: Exception) -> None:
        """Handle uncaught exceptions."""
        self.log("Uncaught exception:", str(exception))
        self.log("Traceback:", traceback.format_exc())
        
        # Optionally show error dialog
        self.push_screen(ErrorScreen(exception))

class SafeWidget(Widget):
    def safe_operation(self) -> None:
        try:
            # Potentially dangerous operation
            result = self.risky_function()
            self.log("Operation successful:", result)
        except Exception as e:
            self.log("Operation failed:", str(e), exc_info=True)
            self.post_message(ErrorOccurred(str(e)))
    
    def on_mount(self) -> None:
        # Use preflight checks in debug mode
        if self.app.debug:
            self.preflight_checks()
    
    def preflight_checks(self) -> None:
        """Perform validation checks."""
        if not self.id:
            self.log("WARNING: Widget has no ID")
        if not self.parent:
            self.log("WARNING: Widget not mounted")
```

### Custom Error Messages

```python
from textual.message import Message

class ErrorOccurred(Message):
    """Custom error message."""
    
    def __init__(self, error_text: str) -> None:
        super().__init__()
        self.error_text = error_text

class ErrorAwareApp(App):
    def on_error_occurred(self, message: ErrorOccurred) -> None:
        """Handle custom error messages."""
        self.log(f"Error reported: {message.error_text}")
        
        # Show notification or error dialog
        self.notify(f"Error: {message.error_text}", severity="error")
```

### Debug Assertions

```python
from textual.widgets import Widget

class ValidatedWidget(Widget):
    def validate_state(self) -> None:
        """Assert widget is in valid state."""
        assert self.size.width > 0, "Widget width must be positive"
        assert self.size.height > 0, "Widget height must be positive" 
        assert self.parent is not None, "Widget must be mounted"
        
    def on_resize(self) -> None:
        if self.app.debug:
            self.validate_state()
```

## Development Environment Setup

### IDE Integration

**VS Code Configuration:**
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "tasks": {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "Run Textual App",
                "type": "shell", 
                "command": "textual run --dev ${file}",
                "group": "build"
            },
            {
                "label": "Start Debug Console",
                "type": "shell",
                "command": "textual console",
                "group": "build"
            }
        ]
    }
}
```

### Project Structure

```
my-textual-app/
├── src/
│   ├── __init__.py
│   ├── app.py              # Main application
│   ├── widgets/            # Custom widgets  
│   ├── screens/            # Screen definitions
│   └── styles.css          # Application styles
├── tests/
│   ├── test_app.py         # Application tests
│   ├── test_widgets.py     # Widget tests
│   └── snapshots/          # UI snapshots
├── requirements.txt        # Dependencies
├── pyproject.toml          # Project configuration
└── README.md
```

### Environment Variables

```bash
# Create .env file for development
TEXTUAL_DEBUG=1
TEXTUAL_LOG=/tmp/textual.log
TEXTUAL_SLOW_THRESHOLD=100

# Source in development
source .env
textual run --dev src/app.py
```

### Development Scripts

```bash
#!/bin/bash
# dev.sh - Development startup script

# Start debug console in background
textual console --port 7342 &
CONSOLE_PID=$!

# Wait for console to start
sleep 1

# Run application
textual run --dev --port 7342 src/app.py

# Cleanup
kill $CONSOLE_PID
```

## Best Practices and Patterns

### Code Organization

1. **Separation of Concerns**: Keep widgets, screens, and business logic separate
2. **Async Patterns**: Use workers for heavy operations
3. **Error Boundaries**: Implement error handling at widget level
4. **Testing Strategy**: Write tests for critical user flows
5. **Performance Monitoring**: Profile regularly during development

### Debugging Workflow

1. **Start with Console**: Always use debug console for development
2. **Incremental Development**: Add logging as you build features
3. **Test Early**: Write tests alongside features
4. **Profile Regularly**: Check performance with realistic data
5. **Document Patterns**: Keep notes on debugging techniques

### Performance Guidelines

1. **Widget Lifecycle**: Understand mount/unmount patterns
2. **Event Efficiency**: Optimize expensive event handlers  
3. **Memory Management**: Profile memory usage with Memray
4. **Batch Operations**: Group related updates
5. **Visibility Optimization**: Skip work for invisible widgets

### Production Considerations

1. **Disable Debug Mode**: Remove debug flags for production
2. **Error Handling**: Implement comprehensive error recovery
3. **Logging Levels**: Use appropriate logging verbosity
4. **Performance Monitoring**: Monitor key metrics in production
5. **User Experience**: Ensure graceful degradation

---

This guide provides comprehensive coverage of Textual's debugging and development tools. For the latest features and updates, refer to the [official Textual documentation](https://textual.textualize.io/).