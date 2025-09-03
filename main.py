#!/usr/bin/env python3
"""Main entry point for elysiactl TUI development."""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from elysiactl.tui.app import RepoManagerApp

if __name__ == "__main__":
    theme_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    app = RepoManagerApp(theme_name=theme_name)
    app.run()