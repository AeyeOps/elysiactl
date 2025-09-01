# Phase 1: Fix Hardcoded URLs in cluster_verification.py

## Objective
Replace 6 hardcoded `localhost:8080` URLs in `/opt/elysiactl/src/elysiactl/commands/cluster_verification.py` with configuration-based URLs using the existing `config.services.weaviate_base_url` pattern.

## Problem Summary
The cluster_verification.py file contains 6 hardcoded URLs that prevent the tool from working with non-local Weaviate instances:

- Line 178: `f"http://localhost:8080/v1/nodes/{node_name}"`
- Line 229: `f"http://localhost:8080/v1/nodes/{node_name}"`  
- Line 277: `f"http://localhost:8080/v1/nodes/{node_name}"`
- Line 306: `f"http://localhost:8080/v1/nodes/{node_name}"`
- Line 417: `f"http://localhost:8080/v1/nodes/{node_name}"`
- Line 435: `f"http://localhost:8080/v1/nodes/{node_name}"`

All URLs follow the same pattern and need to be replaced with the configured base URL.

## Implementation Details

### Required Import
Add config import at the top of the file after existing imports:
```python
from ..config import get_config
```

### URL Replacements
Replace all 6 occurrences of the hardcoded URL pattern:

**FROM:**
```python
f"http://localhost:8080/v1/nodes/{node_name}"
```

**TO:**
```python
f"{get_config().services.weaviate_base_url}/nodes/{node_name}"
```

### Specific Line Changes

**Line 178:**
- **Current:** `response = await client.get(f"http://localhost:8080/v1/nodes/{node_name}")`
- **Replace with:** `response = await client.get(f"{get_config().services.weaviate_base_url}/nodes/{node_name}")`

**Line 229:**
- **Current:** `response = await client.get(f"http://localhost:8080/v1/nodes/{node_name}")`
- **Replace with:** `response = await client.get(f"{get_config().services.weaviate_base_url}/nodes/{node_name}")`

**Line 277:**
- **Current:** `response = await client.get(f"http://localhost:8080/v1/nodes/{node_name}")`
- **Replace with:** `response = await client.get(f"{get_config().services.weaviate_base_url}/nodes/{node_name}")`

**Line 306:**
- **Current:** `response = await client.get(f"http://localhost:8080/v1/nodes/{node_name}")`
- **Replace with:** `response = await client.get(f"{get_config().services.weaviate_base_url}/nodes/{node_name}")`

**Line 417:**
- **Current:** `response = await client.get(f"http://localhost:8080/v1/nodes/{node_name}")`
- **Replace with:** `response = await client.get(f"{get_config().services.weaviate_base_url}/nodes/{node_name}")`

**Line 435:**
- **Current:** `response = await client.get(f"http://localhost:8080/v1/nodes/{node_name}")`
- **Replace with:** `response = await client.get(f"{get_config().services.weaviate_base_url}/nodes/{node_name}")`

## Testing Commands

### Basic Functionality Test
```bash
# Test with default localhost configuration
cd /opt/elysiactl
uv run python -m elysiactl.commands.cluster_verification --help

# Test cluster verification with local Weaviate
uv run python -m elysiactl cluster-verification
```

### Configuration Test
```bash
# Test with custom Weaviate URL
export WEAVIATE_URL="http://custom-host:8080"
uv run python -m elysiactl cluster-verification

# Verify URL construction
uv run python -c "
from src.elysiactl.config import get_config
print('Base URL:', get_config().services.weaviate_base_url)
"
```

### Integration Test
```bash
# Run full test suite focusing on cluster verification
uv run pytest tests/ -k cluster_verification -v
```

## Success Criteria

1. **No Hardcoded URLs**: All 6 hardcoded `localhost:8080` URLs are replaced
2. **Config Integration**: Import and usage of `get_config()` is correctly implemented
3. **URL Format Correctness**: All URLs use `weaviate_base_url` and maintain correct `/nodes/{node_name}` endpoint format
4. **Backward Compatibility**: Default behavior with `WEAVIATE_URL=http://localhost:8080` remains unchanged
5. **Custom URL Support**: Tool works with different Weaviate URLs via environment variables
6. **No Regression**: All existing cluster verification functionality continues to work
7. **Clean Import**: Config import is properly placed and does not cause circular dependencies

## Verification Steps

1. **Code Review**: Confirm all 6 URLs are replaced and import is added
2. **URL Construction**: Verify that `{config.services.weaviate_base_url}/nodes/{node_name}` produces correct URLs
3. **Environment Variable Test**: Confirm tool respects `WEAVIATE_URL` environment variable
4. **Local Test**: Ensure default localhost behavior is preserved
5. **Remote Test**: Verify tool can connect to non-localhost Weaviate instances

## Risk Assessment

- **Low Risk**: Simple string replacement with established pattern
- **No Breaking Changes**: Default configuration maintains existing behavior
- **Pattern Consistency**: Uses same config pattern as index.py command
- **Isolated Changes**: Only affects cluster_verification.py functionality