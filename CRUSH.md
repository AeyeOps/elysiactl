# elysiactl Development Guide

## Build/Test Commands

### Development Setup
```bash
uv sync                    # Install dependencies
uv run elysiactl --version # Test CLI in development mode
```

### Building
```bash
uv build                   # Build distribution package
uv pip install dist/elysiactl-*.whl  # Install built package
```

### Testing
```bash
uv run pytest tests/       # Run test suite (if tests exist)
uv run python -c "from elysiactl.services import weaviate; print('Import test')"  # Quick import test
```

### Running Single Test
```bash
uv run pytest tests/test_specific.py::TestClass::test_method -v  # Specific test
uv run pytest tests/ -k "test_name" -v  # Tests matching pattern
```

## Code Style Guidelines

### Imports
```python
# Standard library imports first
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Third-party imports
import httpx
import typer
from rich.console import Console

# Local imports (absolute paths)
from ..utils.process import run_command
from ..config import get_config
```

### Type Hints
- Use complete type hints for all function parameters and return values
- Use `Optional` for nullable types
- Use `Union` for multiple possible types
- Use `List`, `Dict`, `Tuple` for collections
- Use `Any` sparingly, prefer specific types

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `WeaviateService`, `ServiceConfig`)
- **Functions/Methods**: `snake_case` (e.g., `get_status()`, `run_command()`)
- **Variables**: `snake_case` (e.g., `weaviate_url`, `batch_size`)
- **Constants**: `UPPER_CASE` (e.g., `WEAVIATE_DIR`, `DEFAULT_PORT`)
- **Properties**: `snake_case` (e.g., `weaviate_base_url`)

### Class Structure
```python
@dataclass
class ServiceConfig:
    """Configuration for service endpoints and connections."""
    
    # Public attributes first
    weaviate_url: str = field(default_factory=lambda: _require_env("WEAVIATE_URL"))
    
    # Properties for computed values
    @property
    def weaviate_base_url(self) -> str:
        """Get the base Weaviate API URL."""
        return f"{self.weaviate_url}/v1"
```

### Error Handling
```python
try:
    response = client.get(url, timeout=5.0)
    response.raise_for_status()
    return response.json()
except httpx.TimeoutException as e:
    logger.error(f"Request timed out: {e}")
    return None
except httpx.HTTPStatusError as e:
    logger.error(f"HTTP error {e.response.status_code}: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return None
```

### Function Documentation
```python
def get_status(self) -> Dict[str, Any]:
    """Get Weaviate service status - returns cluster summary.
    
    Returns:
        Dict containing status information for the cluster
    """
```

### Configuration Pattern
```python
# Use environment variables with sensible defaults
batch_size: int = field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "100")))

# For required environment variables
def _require_env(var_name: str) -> str:
    """Require an environment variable or raise an error."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"{var_name} environment variable must be set")
    return value
```

### Async/Await Usage
- Use async methods for HTTP operations: `async def batch_insert_objects(...)`
- Use httpx.AsyncClient for async HTTP requests
- Handle async operations properly with await

### Logging
- Use descriptive error messages
- Include context in log messages
- Log at appropriate levels (INFO, ERROR, DEBUG)

### File Organization
- Keep related functionality in separate modules
- Use clear module names (services/, commands/, utils/)
- Avoid circular imports
- Use relative imports within the package

## Project-Specific Rules

### NEVER Create Files Except:
- Core source files in `src/elysiactl/`
- Test files in `tests/` directory (when explicitly requested)
- Only when implementing required functionality

### UV Package Management
- **ALWAYS use UV**: `uv sync`, `uv run`, `uv build`
- **NEVER use pip** directly: `pip install`, `pip freeze`
- **NEVER use python** directly: `python -m`, `python setup.py`

### Environment Variables
- Use uppercase with `ELYSIACTL_` prefix: `ELYSIACTL_BATCH_SIZE`
- Provide sensible defaults for optional variables
- Require explicit configuration for critical values
- Use `os.getenv()` with fallback values

### Service Management
- Handle both Docker containers and direct processes
- Use PID tracking for reliable process management
- Implement proper timeout handling
- Provide detailed error reporting

### Testing Approach
- Test actual CLI commands: `uv run elysiactl status`
- Use REPL for quick verification: `uv run python -c "import elysiactl"`
- No standalone test scripts outside `tests/` directory</content>
<parameter name="file_path">/opt/elysiactl/CRUSH.md