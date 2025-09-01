# Phase 1: Enterprise Source Code Indexing Command

## Objective
Create a command to index Enterprise source code repositories from `/opt/pdi/Enterprise/` into Weaviate.

## Problem Summary
Need to index 100+ Visual Studio repositories for semantic search while excluding obsolete repositories. The implementation hardcoded "enterprise" as a command name, which is inflexible and should have been more generic.

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/commands/index.py`

**Change 1: Created new index command module**
**Location:** New file
**Implementation:**
- Created comprehensive source code indexing functionality
- Handles file filtering, language detection, and batch processing
- Includes progress tracking and error handling

**MISTAKE: Hardcoded "enterprise" as command name**
```python
@app.command()
def enterprise(...)  # Should have been more generic like "scan" or "directory"
```

### File: `/opt/elysiactl/src/elysiactl/cli.py`

**Change 2: Added index command to main CLI**
**Location:** Lines 14 and 42
**Added:**
```python
from .commands.index import app as index_app
app.add_typer(index_app, name="index", help="Index source code into Weaviate")
```

## What Should Have Been Done

### Better Design:
```python
@app.command()
def scan(
    directory: str = typer.Argument(..., help="Directory to scan"),
    pattern: str = typer.Option("*", "--pattern", help="File pattern to match"),
    exclude: str = typer.Option("", "--exclude", help="Pattern to exclude"),
    collection: str = typer.Option("SRC_ENTERPRISE__", "--collection"),
    clear: bool = typer.Option(False, "--clear"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Index source code from any directory into Weaviate."""
```

### Then use it like:
```bash
# Index Enterprise repos
elysiactl index scan /opt/pdi/Enterprise \
  --pattern "https-pdidev.visualstudio*" \
  --exclude "ZZ_Obsolete"

# Index any other codebase
elysiactl index scan ~/projects/myapp \
  --collection "SRC_MYAPP__"
```

## What Was Actually Built

### Hardcoded Enterprise Logic:
- Command name is literally "enterprise"
- Path is hardcoded to `/opt/pdi/Enterprise`
- Pattern is hardcoded to `https-pdidev.visualstudio*`
- Exclusion of `ZZ_Obsolete` is hardcoded

### Current Usage:
```bash
elysiactl index enterprise [--clear] [--dry-run] [--collection NAME]
```

## Agent Workflow

### Step 1: Initial Implementation
1. Created `/opt/elysiactl/src/elysiactl/commands/index.py`
2. Implemented all core functionality
3. Made the mistake of hardcoding Enterprise-specific logic

### Step 2: Integration
1. Updated `/opt/elysiactl/src/elysiactl/cli.py` to include index command
2. Tested with `uv run elysiactl index --help`
3. Verified with dry run

## Testing

### Commands Tested:
```bash
# Check help
uv run elysiactl index --help
uv run elysiactl index enterprise --help

# Check status
uv run elysiactl index status

# Dry run
uv run elysiactl index enterprise --dry-run
```

### Results:
- ✅ Command structure works
- ✅ Found 103 repositories correctly
- ✅ Excludes obsolete repos
- ❌ Not flexible for other use cases

## Success Criteria
- ✅ Index command created and integrated
- ✅ Can discover Enterprise repositories
- ✅ Filters obsolete repositories correctly
- ✅ Progress tracking implemented
- ✅ Batch processing works
- ❌ **FAILED**: Command is not generic/reusable

## Lessons Learned

### What Went Wrong:
1. **Premature Specialization** - Built for one specific use case instead of general purpose
2. **Hardcoded Values** - Path, pattern, and exclusions should be parameters
3. **Poor Command Naming** - "enterprise" is too specific, should be action-based

### Correct Approach Would Be:
1. Create generic `scan` command that takes directory as argument
2. Add pattern matching options for flexibility
3. Allow multiple exclusion patterns
4. Support different repository structures

## Recommendation for Fix

### Phase 2 Should:
1. Rename `enterprise` to `scan` or `directory`
2. Make directory a required argument
3. Add `--pattern` and `--exclude` options
4. Keep `enterprise` as an alias for backwards compatibility
5. Add preset shortcuts like `--preset=enterprise`

### Example Refactor:
```python
@app.command()
def scan(
    directory: Path = typer.Argument(...),
    pattern: List[str] = typer.Option(["*"], "--pattern"),
    exclude: List[str] = typer.Option([], "--exclude"),
    # ... other options
):
    """Index source code from specified directory."""
    
@app.command()
def enterprise(...):
    """Convenience command for Enterprise repos."""
    # Calls scan with Enterprise defaults
    scan(
        directory="/opt/pdi/Enterprise",
        pattern=["https-pdidev.visualstudio*"],
        exclude=["*ZZ_Obsolete*"]
    )
```

## Status
✅ COMPLETED (with architectural debt noted)