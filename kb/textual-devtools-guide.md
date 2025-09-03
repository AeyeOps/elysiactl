# Textual DevTools and Server Complete Guide

## Installation and Setup

### Requirements
- Python 3.8 or later (latest version recommended)
- Supported platforms: Linux, macOS, Windows, any OS where Python runs

### Platform-Specific Recommendations
- **Linux**: All distros include compatible terminal emulators
- **macOS**: Default Terminal limited to 256 colors. Recommended terminals: iTerm2, Ghostty, Kitty, WezTerm
- **Windows**: Use Windows Terminal for best experience

### Installation Commands

```bash
# Core Textual framework
pip install textual

# Development tools (required for DevTools)
pip install textual-dev

# Both packages together
pip install textual textual-dev

# With syntax highlighting support
pip install "textual[syntax]"

# Using conda-forge (recommended: micromamba)
micromamba install -c conda-forge textual
micromamba install -c conda-forge textual-dev
```

### Virtual Environment Setup (Recommended)
```bash
python -m venv textual-env
source textual-env/bin/activate  # Windows: textual-env\Scripts\activate
pip install textual textual-dev
```

### Verification
```bash
textual --help  # Should show available commands
python -m textual  # Run demo application
```

## DevTools Components Overview

### 1. Console - Real-Time Debugging
**Purpose**: Separate terminal for logging and debugging while your TUI runs
**Problem Solved**: TUIs take over the terminal, hiding print() output and errors

**Basic Usage:**
```bash
# Terminal 1: Start console
textual console

# Terminal 2: Run app with development mode
textual run --dev my_app.py
```

**Console Features:**
- Real-time event logging (key presses, clicks, widget mounts)
- Custom log message display
- System event monitoring
- Error messages and stack traces
- State change tracking

**Verbosity Control:**
```bash
# More verbose (show all events)
textual console -v

# Exclude specific message types
textual console -x SYSTEM -x EVENT -x DEBUG -x INFO

# Custom port
textual console --port 7342
textual run --dev --port 7342 my_app.py
```

**Message Categories:**
- EVENT: User interactions
- DEBUG: Debug information
- INFO: General information
- WARNING: Warning messages
- ERROR: Error messages
- SYSTEM: Internal Textual operations
- LOGGING: Standard Python logging
- WORKER: Background task information

### 2. Run Command - Development Mode
**Purpose**: Enhanced app execution with debugging features

**Basic Syntax:**
```bash
# Run Python file
textual run my_app.py

# With development mode (enables console)
textual run --dev my_app.py

# Run from module import
textual run music.play
textual run music.play:MusicPlayerApp  # specific app instance/class

# Run from command
textual run -c "textual colors"
```

**Development Mode Features:**
- Enables Console connectivity
- Enhanced error messages
- Live CSS editing
- Performance monitoring
- State inspection capabilities

### 3. Serve - Browser Preview
**Purpose**: Transform terminal app into web application for easy preview and sharing

**Basic Usage:**
```bash
# Serve Python file
textual serve my_app.py

# Serve command
textual serve "textual keys"

# Serve module (note: full command required)
textual serve "python -m textual"
```

**Serve Features:**
- Browser-based app preview
- Multiple concurrent instances
- Development aid (refresh browser for code changes)
- Shareable demos without terminal setup
- Custom host/port configuration

**Advanced Options:**
```bash
textual serve --help  # See all options
```

### 4. Live CSS Editing
**Purpose**: Real-time style updates without app restart

**How It Works:**
1. Run app with `--dev` flag: `textual run --dev my_app.py`
2. Edit CSS files in your editor
3. Save changes
4. See updates in terminal within milliseconds

**Benefits:**
- Instant visual feedback
- Rapid iteration on design
- No app restart required
- Works with external CSS files and DEFAULT_CSS

## Logging System

### Textual Log Function
```python
from textual import log

# In your app
def on_mount(self) -> None:
    log("Hello, World")              # Simple string
    log(locals())                    # Log local variables
    log(children=self.children, pi=3.141592)  # Key/value pairs
    log(self.tree)                   # Rich renderables
```

### Widget/App Log Method
```python
from textual.app import App

class MyApp(App):
    def on_load(self):
        self.log("In the log handler!", pi=3.141529)
    
    def on_mount(self):
        self.log(self.tree)
```

### Python Logging Integration
```python
import logging
from textual.app import App
from textual.logging import TextualHandler

logging.basicConfig(
    level="NOTSET",
    handlers=[TextualHandler()],
)

class LogApp(App):
    def on_mount(self) -> None:
        logging.debug("Logged via TextualHandler")
```

## AI Agent Development Best Practices

### Setting Up Visibility
```bash
# Terminal setup for AI agents
# Terminal 1: Always have console running
textual console -v

# Terminal 2: Run with development mode
textual run --dev my_app.py

# Alternative: Browser preview for visual feedback
textual serve my_app.py
```

### Verification Workflow for AI Agents

**1. Visual Verification**
- Can you see expected widgets in correct positions?
- Are colors, borders, and layouts as specified?

**2. Interactive Verification** 
- Do buttons respond to clicks?
- Do inputs accept text?
- Do keyboard shortcuts work?

**3. State Verification**
- Does app maintain state between interactions?
- Are reactive attributes updating correctly?

**4. Error Verification**
- Are errors caught and displayed properly?
- Do error messages appear in console?

### Structured Feedback Template for AI Agents
```
CURRENT STATE:
- Widgets visible: [list what's shown]
- Working features: [list functional elements]
- Errors/issues: [list problems]

CONSOLE OUTPUT:
- Recent log messages: [copy from console]
- Error messages: [any errors shown]

DESIRED STATE:
- Required changes: [specific modifications needed]
- Expected behavior: [how it should work]

VERIFICATION:
- Test steps: [how to verify fixes work]
```

### Common Debugging Patterns

**Debug Widget State:**
```python
def on_button_pressed(self):
    log(f"Button state: {self.button.disabled}")
    log(f"App state: {self.state}")
    log(f"Current focus: {self.focused}")
```

**Debug Layout Issues:**
```python
def on_mount(self):
    log(f"Widget tree: {self.tree}")
    log(f"Container size: {self.size}")
    for widget in self.query():
        log(f"{widget}: {widget.region}")
```

**Debug CSS/Styling:**
```python
def on_mount(self):
    log(f"Computed styles: {self.styles}")
    log(f"CSS classes: {self.classes}")
```

## Command Reference Quick Guide

### Essential Commands
```bash
# Help and information
textual --help
textual run --help
textual console --help
textual serve --help

# Development workflow
textual console                    # Start debugging console
textual run --dev app.py          # Run with development features
textual serve app.py              # Browser preview

# Advanced options
textual console -v                 # Verbose logging
textual console --port 7342        # Custom port
textual run --dev --port 7342 app.py  # Matching port
```

### File and Module Execution
```bash
# Python files
textual run my_app.py
textual serve my_app.py

# Module imports
textual run module.submodule
textual run module.submodule:app_instance

# Commands
textual run -c "textual colors"
textual serve "python -m textual"
```

## Troubleshooting Common Issues

### Console Not Working
- Verify `textual-dev` is installed: `pip install textual-dev`
- Check Python version: Must be 3.8+
- Try custom port if default conflicts: `--port 7342`

### App Not Connecting to Console
- Ensure both terminals use same port
- Run app with `--dev` flag
- Check for firewall blocking localhost connections

### CSS Changes Not Reflecting
- Verify running with `--dev` flag
- Check CSS file syntax
- Ensure file is saved before expecting changes

### Browser Serve Issues
- Try different port: `textual serve --port 8080 app.py`
- Check browser console for errors
- Verify app runs normally in terminal first

## Integration with AI Development Workflows

### For AI Agents Building TUIs
1. **Always start with console running** - provides immediate feedback
2. **Use browser serve for visual confirmation** - easier to see layouts
3. **Implement logging early** - add log() calls to track execution
4. **Test incrementally** - verify each widget before adding next
5. **Document state in logs** - helps agents understand current status

### Recommended Development Flow
1. Start console: `textual console`
2. Create basic app structure with placeholders
3. Run with dev mode: `textual run --dev app.py`
4. Add one widget at a time, testing each addition
5. Use browser serve for layout verification: `textual serve app.py`
6. Iterate with live CSS editing for styling
7. Add logging throughout for debugging visibility

This guide provides everything needed for AI agents to effectively use Textual DevTools for TUI development with proper visibility and debugging capabilities.