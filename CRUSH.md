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
- **⚠️ IMPORTANT**: Do NOT run interactive TUI applications as they will block the terminal
- **🚫 NO BACKWARDS COMPATIBILITY**: This is a new application. We will NEVER maintain backwards compatibility, legacy code, or deprecated APIs. If something needs to change, it changes immediately without consideration for existing usage. Complexity from backwards compatibility is not tolerated.

## Architectural Guardrails

### Core Thesis Protection
- **mgit Authority**: `mgit` is the sole source for repository discovery and differentials. `elysiactl` only consumes streams.
- **No Filesystem Scanning**: Never implement local file walking—always delegate to mgit subprocess.
- **Stream Consumption**: All operations must process mgit output streams, not parse local git repos.
- **Configuration Over Hardcoding**: All paths, patterns, and endpoints must be configurable.

### Development Checkpoints
Before implementing any feature:
1. Does this use mgit as the authority? (Must answer YES)
2. Is there any local filesystem scanning? (Must answer NO)
3. Are streams consumed properly? (Must answer YES)
4. Is everything configurable? (Must answer YES)

### Past Deviations (Lessons Learned)
- **Filesystem Pivot**: Attempted local repo scanning—corrected back to mgit integration.
- **Direct Git Calls**: Replaced with mgit subprocess for single source of truth.
- **Hardcoded URLs**: Moved to environment variables and config files.
- **User Message Drift**: Fixed to reflect actual mgit operations, not filesystem actions.

### Validation Commands
Run these to verify alignment:
```bash
# Check for mgit integration
grep -r "mgit" src/elysiactl/

# Check for filesystem scanning (should be minimal/only for config)
grep -r "Path\|os\.walk\|glob" src/elysiactl/

# Check for hardcoded paths (should use config)
grep -r "http://localhost\|/opt/weaviate" src/elysiactl/
```

### Quick Reference
- **Wrong**: `elysiactl` scans local filesystem for repos
- **Right**: `elysiactl` calls `mgit list` and processes the JSONL stream
- **Wrong**: Parse local .git directories
- **Right**: Consume `mgit diff` output streams
- **Wrong**: Hardcoded `/opt/weaviate/repos/*`
- **Right**: Configurable `sync.destination_path`</content>
<parameter name="file_path">/opt/elysiactl/CRUSH.md