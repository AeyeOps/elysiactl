# Phase 2: Extract Configuration to Environment Variables

## Objective
Replace all hardcoded values in `/opt/elysiactl/src/elysiactl/commands/index.py` with configuration-driven alternatives using the existing config system.

## Problem Summary
The index command contains 24+ hardcoded values including URLs, batch sizes, file limits, and business-specific patterns. This violates configuration-over-hardcoding principles and makes the command inflexible for different deployments. The config system exists but is not fully utilized in the index.py file.

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/commands/index.py`

**Change 1: Remove hardcoded Weaviate URLs**
**Location:** Lines 158, 263, 381, 479, 551, 592, 603
**Current Code:**
```python
response = await client.get(f"http://localhost:8080/v1/schema/{collection_name}")
# and similar hardcoded URLs throughout
```

**New Code:**
```python
response = await client.get(f"{config.services.weaviate_base_url}/schema/{collection_name}")
# Apply to all URL references consistently
```

**Change 2: Fix config usage in ensure_collection_schema function**
**Location:** Line 155
**Current Code:**
```python
async with httpx.AsyncClient(timeout=config.processing.medium_timeout) as client:
```

**New Code:**
```python
config = get_config()
async with httpx.AsyncClient(timeout=config.processing.medium_timeout) as client:
```

**Change 3: Replace hardcoded enterprise help text**
**Location:** Lines 403-408
**Current Code:**
```python
"""Index Enterprise source code repositories into Weaviate.
    
    Indexes all repositories matching the configured pattern.
    
    Default: /opt/pdi/Enterprise/https-pdidev.visualstudio* (excluding ZZ_Obsolete)
    Use elysiactl_ENTERPRISE_DIR, elysiactl_REPO_PATTERN, elysiactl_EXCLUDE_PATTERN to customize.
    """
```

**New Code:**
```python
"""Index Enterprise source code repositories into Weaviate.
    
    Indexes all repositories matching the configured pattern.
    
    Configuration via environment variables:
    - elysiactl_ENTERPRISE_DIR: Base directory for repositories 
    - elysiactl_REPO_PATTERN: Repository name pattern to match
    - elysiactl_EXCLUDE_PATTERN: Pattern to exclude from indexing
    - elysiactl_DEFAULT_SOURCE_COLLECTION: Target collection name
    """
```

**Change 4: Replace hardcoded display text**
**Location:** Line 438
**Current Code:**
```python
f"• Pattern: [dim]{config.repositories.repo_pattern}* (excluding {config.repositories.exclude_pattern})[/dim]\n"
```

**New Code:**
```python
f"• Pattern: [dim]{config.repositories.repo_pattern}* (excluding {config.repositories.exclude_pattern})[/dim]\n"
```
(This is already correct but needs to be verified as using config)

**Change 5: Remove hardcoded string replacement**
**Location:** Line 506
**Current Code:**
```python
repo_name = repo.name.replace("https-pdidev.visualstudio.com-DefaultCollection-PDI-_git-", "")
```

**New Code:**
```python
# Make string replacement configurable based on repo_pattern
prefix_to_remove = f"{config.repositories.repo_pattern}.com-DefaultCollection-PDI-_git-"
repo_name = repo.name.replace(prefix_to_remove, "") if repo.name.startswith(prefix_to_remove) else repo.name
```

**Change 6: Add config validation function**
**Location:** After line 147 (add new function)
**Current Code:**
(No existing code - this is a new addition)

**New Code:**
```python
def validate_config():
    """Validate configuration values and provide helpful error messages."""
    config = get_config()
    errors = []
    
    if not config.repositories.enterprise_dir:
        errors.append("elysiactl_ENTERPRISE_DIR must be set")
    
    if not config.repositories.repo_pattern:
        errors.append("elysiactl_REPO_PATTERN must be set")
        
    if config.processing.batch_size <= 0:
        errors.append("elysiactl_BATCH_SIZE must be > 0")
        
    if config.processing.max_file_size <= 0:
        errors.append("elysiactl_MAX_FILE_SIZE must be > 0")
        
    if config.collections.replication_factor < 1:
        errors.append("elysiactl_REPLICATION_FACTOR must be >= 1")
    
    if errors:
        console.print("[red]Configuration errors:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        return False
    
    return True
```

**Change 7: Add config validation to enterprise command**
**Location:** Line 411 (after config = get_config())
**Current Code:**
```python
config = get_config()
if collection is None:
    collection = config.collections.default_source_collection
```

**New Code:**
```python
config = get_config()
if not validate_config():
    raise typer.Exit(1)
        
if collection is None:
    collection = config.collections.default_source_collection
```

## Agent Workflow

### Step 1: Update URL references to use config
1. Open `/opt/elysiactl/src/elysiactl/commands/index.py`
2. Find all hardcoded `http://localhost:8080/v1` URLs
3. Replace with `{config.services.weaviate_base_url}` pattern
4. Ensure `config = get_config()` is called at function start where needed
5. Test with: `uv run elysiactl index status`

### Step 2: Add configuration validation
1. Add the `validate_config()` function after line 147
2. Call validation in the `enterprise()` command after getting config
3. Test configuration errors with invalid environment variables
4. Verify helpful error messages appear

### Step 3: Update string replacement logic
1. Replace hardcoded string replacement on line 506
2. Make it derive from repo_pattern configuration
3. Test with different elysiactl_REPO_PATTERN values
4. Ensure repository names display correctly

### Step 4: Update help documentation
1. Replace hardcoded help text with environment variable references
2. Remove specific path references
3. Test help display: `uv run elysiactl index enterprise --help`

## Testing

### CLI Integration Tests
```bash
# Test with default configuration
uv run elysiactl index status

# Test with custom configuration
export WCD_URL="http://weaviate.example.com:8080"
export elysiactl_DEFAULT_SOURCE_COLLECTION="TEST_SRC__"
uv run elysiactl index status

# Test configuration validation
export elysiactl_BATCH_SIZE="0"
uv run elysiactl index enterprise --dry-run

# Test help text
uv run elysiactl index enterprise --help
```

### Configuration Environment Tests
```bash
# Test different Weaviate URLs
export WCD_URL="http://localhost:9080"
uv run elysiactl index status

# Test custom enterprise directory
export elysiactl_ENTERPRISE_DIR="/custom/path"
uv run elysiactl index enterprise --dry-run

# Test custom repository patterns
export elysiactl_REPO_PATTERN="custom-repo-prefix" 
export elysiactl_EXCLUDE_PATTERN="DEPRECATED"
uv run elysiactl index enterprise --dry-run
```

### Manual Testing Checklist
- [ ] All commands execute without hardcoded URL references
- [ ] Configuration validation catches invalid values with clear messages
- [ ] Help text reflects environment variable configuration approach
- [ ] Repository name display logic works with different patterns
- [ ] Status command uses configured Weaviate URL
- [ ] Enterprise command respects all configuration settings
- [ ] Error messages reference environment variables, not hardcoded paths

## Success Criteria
- [ ] Zero hardcoded URLs remain in index.py
- [ ] All 24+ hardcoded values identified in hardcoded-problems.md are replaced with config
- [ ] Configuration validation provides clear error messages for invalid settings
- [ ] Help text documents environment variables instead of hardcoded examples
- [ ] Repository pattern replacement is configurable, not hardcoded
- [ ] Commands work with non-default Weaviate URLs (test with localhost:9080)
- [ ] All existing functionality preserved with no regressions
- [ ] `uv run elysiactl index status` works with custom WCD_URL
- [ ] `uv run elysiactl index enterprise --dry-run` shows configurable patterns