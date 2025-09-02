# Phase 3: Fix Hardcoded Port Constants and Arrays

## Objective
Replace hardcoded port constants and port arrays in `/opt/elysiactl/src/elysiactl/commands/weaviate.py` and `/opt/elysiactl/src/elysiactl/commands/elysia.py` with configuration-based port detection and dynamic port arrays.

## Problem Summary
Two files contain hardcoded port constants and arrays that prevent proper multi-port or custom port configurations:

### weaviate.py (Line 14):
```python
WEAVIATE_PORT = 8080
```

### elysia.py (Line 13):
```python
ELYSIACTL_PORT = 8000
```

### Multiple files contain hardcoded port arrays:
```python
[8080, 8081, 8082]  # Common pattern for multi-node Weaviate clusters
```

These constants and arrays need to be replaced with configuration-based detection that can handle:
- Custom single ports via environment variables
- Dynamic multi-port detection for clusters
- Fallback to sensible defaults

## Implementation Details

### Configuration Enhancement
The existing `ServiceConfig` already supports custom URLs, but we need to add port extraction utilities.

Add to `/opt/elysiactl/src/elysiactl/config.py`:

```python
@dataclass
class ServiceConfig:
    # ... existing fields ...
    
    @property
    def weaviate_port(self) -> int:
        """Extract port from Weaviate URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.WCD_URL)
        return parsed.port or (443 if parsed.scheme == 'https' else 8080)
    
    @property
    def elysia_port(self) -> int:
        """Extract port from Elysia URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.elysia_url)
        return parsed.port or (443 if parsed.scheme == 'https' else 8000)
    
    def get_weaviate_port_range(self, count: int = 3) -> List[int]:
        """Get a range of Weaviate ports for multi-node clusters."""
        base_port = self.weaviate_port
        return [base_port + i for i in range(count)]
```

### weaviate.py Changes

**Line 14 Replacement:**
- **FROM:** `WEAVIATE_PORT = 8080`
- **TO:** Remove constant, use `get_config().services.weaviate_port` where needed

**Find all usages of WEAVIATE_PORT and replace with:**
```python
from ..config import get_config
# Replace WEAVIATE_PORT with get_config().services.weaviate_port
```

### elysia.py Changes

**Line 13 Replacement:**
- **FROM:** `ELYSIACTL_PORT = 8000`
- **TO:** Remove constant, use `get_config().services.elysia_port` where needed

**Find all usages of ELYSIACTL_PORT and replace with:**
```python
from ..config import get_config  
# Replace ELYSIACTL_PORT with get_config().services.elysia_port
```

### Port Array Replacements

**Find patterns like:**
```python
ports = [8080, 8081, 8082]
weaviate_ports = [8080, 8081, 8082]
```

**Replace with:**
```python
from ..config import get_config
ports = get_config().services.get_weaviate_port_range()
# or for custom count:
ports = get_config().services.get_weaviate_port_range(count=5)
```

## Testing Commands

### Configuration Test
```bash
# Test default port extraction
cd /opt/elysiactl
uv run python -c "
from src.elysiactl.config import get_config
config = get_config()
print('Weaviate port:', config.services.weaviate_port)
print('Elysia port:', config.services.elysia_port)
print('Port range:', config.services.get_weaviate_port_range())
"

# Test custom URL port extraction
export WCD_URL="http://custom-host:9080"
export ELYSIACTL_URL="http://elysia-host:9000"
uv run python -c "
from src.elysiactl.config import get_config
config = get_config()
print('Custom Weaviate port:', config.services.weaviate_port)
print('Custom Elysia port:', config.services.elysia_port)
print('Custom port range:', config.services.get_weaviate_port_range())
"
```

### HTTPS Port Test
```bash
# Test HTTPS URLs use correct default ports
export WCD_URL="https://cloud.weaviate.io"
export ELYSIACTL_URL="https://elysia.example.com"
uv run python -c "
from src.elysiactl.config import get_config
config = get_config()
print('HTTPS Weaviate port:', config.services.weaviate_port)  # Should be 443
print('HTTPS Elysia port:', config.services.elysia_port)      # Should be 443
"
```

### Integration Test  
```bash
# Test commands that use ports still work
uv run python -m elysiactl weaviate --help
uv run python -m elysiactl elysia --help

# Run full test suite
uv run pytest tests/ -v
```

## Success Criteria

1. **No Hardcoded Ports**: All hardcoded `WEAVIATE_PORT = 8080` and `ELYSIACTL_PORT = 8000` constants are removed
2. **Dynamic Port Detection**: Port values are extracted from configured URLs
3. **HTTPS Support**: URLs with HTTPS correctly default to port 443
4. **Custom Port Support**: Non-standard ports in URLs are correctly detected
5. **Multi-Port Arrays**: Port arrays are dynamically generated based on base port
6. **Backward Compatibility**: Default behavior with standard URLs remains unchanged
7. **Config Integration**: Uses existing ServiceConfig without breaking changes
8. **No Regression**: All commands that used port constants continue to work

## Implementation Steps

1. **Add port methods to ServiceConfig** in `/opt/elysiactl/src/elysiactl/config.py`
2. **Remove WEAVIATE_PORT constant** from weaviate.py
3. **Remove ELYSIACTL_PORT constant** from elysia.py
4. **Replace constant usage** with config method calls
5. **Find and replace hardcoded port arrays** with dynamic generation
6. **Add necessary imports** for config access
7. **Test port extraction** with various URL formats

## Verification Steps

1. **Constant Removal**: Confirm both port constants are completely removed
2. **URL Parsing**: Verify port extraction works for:
   - `http://localhost:8080` → 8080
   - `https://example.com` → 443
   - `http://custom:9080` → 9080
   - `https://secure:9443` → 9443
3. **Port Arrays**: Confirm dynamic arrays work:
   - Base port 8080 → [8080, 8081, 8082]
   - Base port 9080 → [9080, 9081, 9082]
4. **Command Testing**: All affected commands work with new port detection
5. **Environment Variables**: Port changes via URL environment variables work correctly

## Risk Assessment

- **Medium Risk**: Port detection logic needs to handle edge cases properly
- **URL Parsing**: Must handle various URL formats correctly
- **Default Ports**: HTTPS/HTTP default port logic must be sound
- **Backward Compatibility**: Existing deployments must continue working
- **Multi-Port Logic**: Port range generation must be predictable

## Dependencies

- **Requires**: Phases 1 & 2 completion to ensure consistent config usage patterns
- **Blocks**: None - this is the final phase of hardcoded URL/port removal

## Special Considerations

1. **URL Edge Cases**: Handle URLs without explicit ports correctly
2. **Port Range Logic**: Ensure port ranges don't conflict with other services
3. **Error Handling**: Invalid URLs should provide clear error messages  
4. **Performance**: URL parsing should be efficient for frequently called operations
5. **Testing Coverage**: Include tests for various URL formats and edge cases

## Post-Implementation Benefits

- **Flexible Deployment**: Support for any Weaviate/Elysia ports and hosts
- **Cloud Support**: Proper HTTPS and non-standard port handling
- **Multi-Node Clusters**: Dynamic port range generation for scaling
- **Configuration Consistency**: All port/URL logic centralized in config
- **Environment Driven**: Full control via environment variables