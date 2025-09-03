# elysiactl Development Guide

## Build/Test Commands
```bash
uv sync                    # Install dependencies
uv run ruff check src/ --fix    # Auto-fix linting/code quality issues
uv run ruff format src/         # Auto-format code
uv run mypy src/          # Type checking (catch issues before runtime)
uv run pytest tests/       # Run all tests
uv run pytest tests/test_file.py::TestClass::test_method -v  # Single test
uv run pytest tests/ -k "test_name" -v  # Tests matching pattern
```

## Code Style Guidelines

### Imports
```python
# Standard library first, then third-party, then local
from typing import Dict, Any, Optional, List
import httpx
from ..utils.process import run_command
```

### Type Hints & Naming
- Complete type hints: `def func(param: str) -> Dict[str, Any]`
- Classes: `PascalCase`, Functions/Variables: `snake_case`, Constants: `UPPER_CASE`
- Use `Optional` for nullable types, `Union` for multiple types

### Error Handling
```python
try:
    response = client.get(url, timeout=5.0)
    response.raise_for_status()
    return response.json()
except httpx.TimeoutException as e:
    logger.error(f"Request timed out: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Critical Project Rules
- **ALWAYS use UV**: `uv sync`, `uv run`, `uv build` - NEVER pip/python directly
- **NEVER create files** except core source in `src/elysiactl/` or tests in `tests/`
- **NO test scripts** outside `tests/` directory, **NO backup files**, **NO summary files**
- Use environment variables with `ELYSIACTL_` prefix
- Focus on configuration over hardcoding - no URLs, paths, or patterns hardcoded
- Keep commits atomic, describe WHAT changed, never HOW it was created
- **NEVER include AI attribution** in commits, code comments, or git user config
- Git user: Steve Antonakakis (steve.antonakakis@gmail.com)
- **Communication**: Focus on failures/issues, not successes
- **⚠️ IMPORTANT**: Do NOT run interactive TUI applications as they will block the terminal</content>
<parameter name="file_path">/opt/elysiactl/CRUSH.md