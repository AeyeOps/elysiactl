# Phase 2: Fix Hardcoded URLs in repair.py

## Objective
Replace 8 hardcoded `localhost:8080` URLs in `/opt/elysiactl/src/elysiactl/commands/repair.py` with configuration-based URLs using the existing `config.services.weaviate_base_url` pattern.

## Problem Summary
The repair.py file contains 8 hardcoded URLs that prevent the tool from working with non-local Weaviate instances:

- Line 132: `"http://localhost:8080/v1/schema"` 
- Line 151: `"http://localhost:8080/v1/schema"`
- Line 219: `f"http://localhost:8080/v1/objects/{obj['id']}"`
- Line 247: `f"http://localhost:8080/v1/objects/{obj['id']}"`
- Line 270: `"http://localhost:8080/v1/batch/objects"`
- Line 288: `f"http://localhost:8080/v1/objects/{obj['id']}"`
- Line 308: `"http://localhost:8080/v1/batch/objects"`
- Line 322: `f"http://localhost:8080/v1/objects/{obj['id']}"`

These URLs span multiple repair functions and need to be replaced with the configured base URL.

## Implementation Details

### Required Import
Add config import at the top of the file after existing imports:
```python
from ..config import get_config
```

### URL Replacement Patterns

**Schema URLs (Lines 132, 151):**
- **FROM:** `"http://localhost:8080/v1/schema"`
- **TO:** `f"{get_config().services.weaviate_base_url}/schema"`

**Object URLs (Lines 219, 247, 288, 322):**
- **FROM:** `f"http://localhost:8080/v1/objects/{obj['id']}"`
- **TO:** `f"{get_config().services.weaviate_base_url}/objects/{obj['id']}"`

**Batch URLs (Lines 270, 308):**
- **FROM:** `"http://localhost:8080/v1/batch/objects"`
- **TO:** `f"{get_config().services.weaviate_base_url}/batch/objects"`

### Specific Line Changes

**Line 132:**
- **Current:** `response = await client.get("http://localhost:8080/v1/schema")`
- **Replace with:** `response = await client.get(f"{get_config().services.weaviate_base_url}/schema")`

**Line 151:**
- **Current:** `response = await client.get("http://localhost:8080/v1/schema")`
- **Replace with:** `response = await client.get(f"{get_config().services.weaviate_base_url}/schema")`

**Line 219:**
- **Current:** `response = await client.delete(f"http://localhost:8080/v1/objects/{obj['id']}")`
- **Replace with:** `response = await client.delete(f"{get_config().services.weaviate_base_url}/objects/{obj['id']}")`

**Line 247:**
- **Current:** `response = await client.delete(f"http://localhost:8080/v1/objects/{obj['id']}")`
- **Replace with:** `response = await client.delete(f"{get_config().services.weaviate_base_url}/objects/{obj['id']}")`

**Line 270:**
- **Current:** `response = await client.post("http://localhost:8080/v1/batch/objects", json=batch_data)`
- **Replace with:** `response = await client.post(f"{get_config().services.weaviate_base_url}/batch/objects", json=batch_data)`

**Line 288:**
- **Current:** `response = await client.delete(f"http://localhost:8080/v1/objects/{obj['id']}")`
- **Replace with:** `response = await client.delete(f"{get_config().services.weaviate_base_url}/objects/{obj['id']}")`

**Line 308:**
- **Current:** `response = await client.post("http://localhost:8080/v1/batch/objects", json=batch_data)`
- **Replace with:** `response = await client.post(f"{get_config().services.weaviate_base_url}/batch/objects", json=batch_data)`

**Line 322:**
- **Current:** `response = await client.delete(f"http://localhost:8080/v1/objects/{obj['id']}")`
- **Replace with:** `response = await client.delete(f"{get_config().services.weaviate_base_url}/objects/{obj['id']}")`

## Testing Commands

### Basic Functionality Test
```bash
# Test repair command help
cd /opt/elysiactl
uv run python -m elysiactl.commands.repair --help

# Test repair with local Weaviate (dry run first)
uv run python -m elysiactl repair --dry-run
```

### Configuration Test
```bash
# Test with custom Weaviate URL
export WCD_URL="http://custom-host:8080"
uv run python -m elysiactl repair --dry-run

# Verify URL construction for different endpoints
uv run python -c "
from src.elysiactl.config import get_config
base = get_config().services.weaviate_base_url
print('Schema URL:', f'{base}/schema')
print('Objects URL:', f'{base}/objects/{{id}}')
print('Batch URL:', f'{base}/batch/objects')
"
```

### Integration Test
```bash
# Run repair-specific tests
uv run pytest tests/ -k repair -v

# Test repair functions individually if available
uv run python -m elysiactl repair --collection-name TEST_COLLECTION --dry-run
```

## Success Criteria

1. **No Hardcoded URLs**: All 8 hardcoded `localhost:8080` URLs are replaced
2. **Config Integration**: Import and usage of `get_config()` is correctly implemented
3. **Endpoint Variety**: All different endpoint types (schema, objects, batch) use config URLs
4. **String Formatting**: Proper f-string formatting for dynamic URLs with object IDs
5. **Backward Compatibility**: Default behavior with `WCD_URL=http://localhost:8080` remains unchanged
6. **Custom URL Support**: Tool works with different Weaviate URLs via environment variables
7. **No Regression**: All repair functionality (delete, recreate, batch operations) continues to work
8. **Clean Import**: Config import is properly placed and does not cause circular dependencies

## Verification Steps

1. **Code Review**: Confirm all 8 URLs are replaced and import is added
2. **URL Construction**: Verify that URLs are correctly constructed for each endpoint type:
   - Schema: `{base}/schema`
   - Objects: `{base}/objects/{id}`
   - Batch: `{base}/batch/objects`
3. **Environment Variable Test**: Confirm tool respects `WCD_URL` environment variable
4. **Dry Run Test**: Ensure repair dry-run mode works with new URLs
5. **HTTP Method Test**: Verify GET, POST, DELETE operations work with config URLs

## Risk Assessment

- **Medium Risk**: More complex than Phase 1 due to multiple endpoint types and HTTP methods
- **No Breaking Changes**: Default configuration maintains existing behavior
- **Pattern Consistency**: Uses same config pattern as index.py and cluster_verification.py
- **Critical Functionality**: Repair operations are important for data integrity

## Dependencies

- **Requires**: Phase 1 completion (cluster_verification.py) for pattern consistency
- **Blocks**: Phase 3 (port constants) as repair.py may reference port constants

## Special Considerations

1. **Multiple HTTP Methods**: URLs are used with GET, POST, and DELETE operations
2. **Dynamic Object IDs**: Object-specific URLs require proper f-string formatting
3. **Batch Operations**: Batch endpoints handle multiple objects and require stable URLs
4. **Error Handling**: Ensure URL construction errors are properly handled
5. **Testing Safety**: Use dry-run mode extensively to avoid data corruption during testing