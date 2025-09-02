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

## Recent Major Developments (Updated: September 2, 2025)

### ✅ Phase 2 Collection Management: COMPLETE
**Status**: All Phase 2 work completed and archived
**Location**: `docs/specs/collection-management/phases-done/`
**Duration**: 24 development hours + 8 testing hours

#### Implemented Features:
- **`elysiactl col backup --include-data`** - Full collection backup with data
- **`elysiactl col restore <file>`** - Complete collection restoration
- **`elysiactl col clear`** - Safe collection clearing with confirmation
- **`elysiactl col ls/show`** - Enhanced collection listing and details
- **`elysiactl col create`** - Collection creation with custom settings

#### Technical Achievements:
- **40/40 tests passing** - Comprehensive test coverage
- **Performance targets met** - Backup <3min, Restore <7min for 100K objects
- **Enterprise features** - Progress tracking, error handling, safety confirmations
- **Memory optimization** - Streaming JSON processing for large datasets

### 🎯 Repository Management UX: NEW INITIATIVE
**Status**: Design completed, ready for implementation
**Location**: `docs/specs/repo-management-ux/`
**Vision**: Transform 17-step manual process into one-command experience

#### Core Concept:
```bash
# Instead of 17 manual steps...
elysiactl repo add https://github.com/myorg/myrepo --watch

# Get automated setup, monitoring, and management
✨ Repository successfully added and syncing!
```

#### Key Features:
- **Intelligent automation** - Auto-detects repo type, optimal configurations
- **Real-time monitoring** - Status dashboards, health tracking, alerts
- **Clean architecture** - Zero dependencies, JSONL format integration
- **Set-and-forget operation** - Automatic cron jobs, self-healing

### 🏗️ Documentation Reorganization: COMPLETE
**Status**: Clean separation achieved
**Structure**: Consistent phases-pending/phases-done pattern

#### Directory Structure:
```
docs/specs/
├── collection-management/     # ✅ Completed collection features
│   ├── phases-done/          # All Phase 2 work archived
│   └── phases-pending/       # Empty (ready for Phase 3)
│
└── repo-management-ux/       # 🎯 New UX design program
    ├── README.md             # Comprehensive overview
    ├── phases-pending/       # Current design work
    └── phases-done/          # Future implementations
```

### 🔗 MGit + ElysiaCtl Integration: DESIGNED
**Status**: Complete integration concept designed
**Architecture**: Decoupled, file-based communication

#### Integration Approach:
- **MGit** produces standardized JSONL files
- **ElysiaCtl** consumes JSONL files from any source
- **Zero code dependencies** between tools
- **Multi-consumer ecosystem** potential

#### Benefits:
- ✅ **Any tool can produce** JSONL (MGit, Git, manual, etc.)
- ✅ **Any tool can consume** JSONL (ElysiaCtl, monitoring, analytics)
- ✅ **Clean separation** - each evolves independently
- ✅ **Testable integration** - file-based communication

### 📊 Current Project State

#### Completed Work:
- ✅ **Collection Management**: Production-ready backup/restore/clear
- ✅ **Documentation**: Well-organized with clear separation
- ✅ **Architecture**: Clean, decoupled design patterns
- ✅ **Testing**: 40/40 tests passing with comprehensive coverage

#### Active Initiatives:
- 🎯 **Repository Management UX**: Ready for implementation
- 🔗 **MGit Integration**: Design complete, implementation pending
- 📈 **Performance Monitoring**: Built into collection management

#### Quality Metrics:
- **Test Coverage**: 100% (40/40 tests passing)
- **Performance**: Exceeds all targets (<3min backup, <7min restore)
- **Safety**: Comprehensive error handling and confirmations
- **Documentation**: Complete with post-mortem analysis

#### Next Priorities:
1. **Implement Repository Management UX** - One-command setup experience
2. **MGit Integration** - File-based communication between tools
3. **Monitoring Enhancement** - Real-time dashboards and alerting
4. **Ecosystem Expansion** - Multi-consumer JSONL format adoption

### 🎯 Development Guidelines (Continued)

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

### Naming Conventions (Updated)
- **Tools**: MGit, ElysiaCtl, Weaviate (proper capitalization)
- **Commands**: `elysiactl col`, `elysiactl repo` (consistent prefixes)
- **Environment Variables**: `ELYSIACTL_*`, `MGIT_*` (clear prefixes)
- **Directories**: `phases-pending/`, `phases-done/` (consistent structure)