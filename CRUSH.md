# elysiactl Development Guide

## Build/Test Commands
```bash
uv sync                    # Install dependencies
uv run elysiactl --version # Test CLI in development mode
uv build                   # Build distribution package
uv run pytest tests/       # Run test suite
uv run pytest tests/test_specific.py::TestClass::test_method -v  # Single test
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
- Complete type hints for all functions: `def func(param: str) -> Dict[str, Any]`
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

### Project Rules
- **ALWAYS use UV**: `uv sync`, `uv run`, `uv build` - NEVER pip/python directly
- **NEVER create files** except core source in `src/elysiactl/` or tests in `tests/`
- Use environment variables with `ELYSIACTL_` prefix
- Focus on configuration over hardcoding - no URLs, paths, or patterns hardcoded
- Keep commits atomic, describe WHAT changed, never HOW it was created
- Git user: Steve Antonakakis (steve.antonakakis@gmail.com)