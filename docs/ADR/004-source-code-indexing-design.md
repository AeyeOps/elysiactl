# ADR-004: Source Code Indexing Design

## Status
Accepted

## Context
elysiactl needs to index large source code repositories (100+ repos, 10,000+ files) into Weaviate for semantic search and code analysis. The primary use case is the Enterprise codebase, but the solution should be extensible to other sources.

Design considerations:
- Repository discovery and filtering
- File type detection and filtering
- Batch processing for large codebases
- Progress tracking for long operations
- Memory management for large files
- Character encoding handling

## Decision
Implement source code indexing as a subcommand structure under `elysiactl index` with:

1. **Modular command structure**: Separate commands for different sources
   - `index status`: Check collection status
   - `index enterprise`: Index Enterprise repos (initial implementation)
   - `index github`: Future GitHub support
   - `index gitlab`: Future GitLab support

2. **Batch processing**: Process files in configurable batches (default 100)
3. **Smart filtering**: Language detection, size limits, exclude patterns
4. **Progress tracking**: Repository-level and file-level progress indication
5. **Async I/O**: Non-blocking file operations for performance

## Consequences

**Positive:**
- Extensible to multiple source types
- Clear separation of concerns
- Follows elysiactl command patterns
- Supports future remote repository indexing

**Negative:**
- Initial implementation tied to Enterprise patterns
- Requires refactoring for generalization
- Command proliferation potential

**Neutral:**
- Sets precedent for other indexing commands
- Requires consistent filtering rules

## Related
- ADR-005: Batch Processing Strategy
- Phase 1: Core indexing implementation
- Phase 2: Configuration extraction