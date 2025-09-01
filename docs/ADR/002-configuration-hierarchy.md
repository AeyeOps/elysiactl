# ADR-002: Configuration Hierarchy

## Status
Accepted (2025-01-01)

## Context
elysiactl has 24+ hardcoded values across the index.py command, including service URLs, processing constants, and business-specific paths. This limits deployment flexibility and violates the project's "Configuration Over Hardcoding" principle documented in CLAUDE.md.

We need a configuration system that:
- Supports multiple deployment environments
- Maintains backwards compatibility
- Allows progressive configuration sophistication
- Follows Unix conventions

## Decision
Implement a three-tier configuration hierarchy with clear precedence:

1. **Command-line arguments** (highest precedence)
2. **Environment variables** (middle precedence)
3. **Configuration files** (lowest precedence)
4. **Hardcoded defaults** (fallback only)

Environment variables use the `elysiactl_` prefix for tool-specific settings and respect standard variables like `WEAVIATE_URL` for service locations.

## Consequences

**Positive:**
- Deployment flexibility across environments
- Standard Unix configuration patterns
- Gradual migration path from hardcoded values
- Clear precedence rules prevent confusion

**Negative:**
- Multiple configuration sources to check
- Potential for configuration sprawl
- Documentation burden for all options

**Neutral:**
- Requires configuration validation layer
- Need for configuration debugging tools

## Related
- CLAUDE.md: Configuration Over Hardcoding principle
- Phase 2 specification: Environment variable implementation
- Future Phase 3: Configuration file support