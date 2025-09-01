# ADR-003: Collection Naming Strategy

## Status
Accepted (2025-01-01)

## Context
elysiactl manages multiple Weaviate collections with different purposes:
- `ELYSIA_CONFIG__`: Configuration storage
- `ELYSIA_TREES__`: Tree structures
- `SRC_ENTERPRISE__`: Source code indexing

The double underscore suffix pattern and ALL_CAPS naming emerged organically but needs formalization. We need a consistent naming strategy that:
- Prevents collisions with user collections
- Indicates collection purpose clearly
- Supports multi-tenant scenarios
- Allows collection versioning

## Decision
Adopt a structured naming convention:

```
[PREFIX]_[PURPOSE]__[VERSION]
```

Where:
- **PREFIX**: Application namespace (ELYSIA, SRC, etc.)
- **PURPOSE**: Functional area (CONFIG, TREES, ENTERPRISE)
- **Double underscore**: Marks elysiactl-managed collections
- **VERSION**: Optional version suffix (v1, v2)

Examples:
- `ELYSIA_CONFIG__`: Core configuration
- `SRC_ENTERPRISE__`: Enterprise source code
- `SRC_GITHUB__v2`: GitHub source (versioned)

## Consequences

**Positive:**
- Clear visual distinction of managed collections
- Namespace prevents user collection conflicts
- Version support enables migrations
- Self-documenting collection names

**Negative:**
- ALL_CAPS may conflict with SQL conventions
- Double underscore unusual in some contexts
- Existing collections need migration

**Neutral:**
- Collection listing shows clear groupings
- Requires documentation of naming rules

## Related
- Weaviate schema management
- Multi-tenant collection strategies
- Phase 1: Collection creation implementation