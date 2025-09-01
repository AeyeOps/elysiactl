# ADR-005: Batch Processing Strategy

## Status
Accepted

## Context
Indexing large codebases requires careful resource management:
- Enterprise has 100+ repositories with thousands of files each
- Weaviate API has rate limits and timeout constraints
- Memory usage must be controlled for large files
- Network efficiency requires batching API calls
- Progress feedback needed for long operations

Key constraints:
- Weaviate batch API optimal size: 50-200 objects
- Python memory overhead per file: ~2-3x file size
- HTTP timeout limits: 60 seconds for batch operations
- User experience: feedback every 5-10 seconds

## Decision
Implement a multi-level batching strategy:

1. **File batching**: Process 100 files per batch (configurable)
2. **Async I/O**: Use asyncio for concurrent file reading
3. **Memory limits**: 
   - Skip files > 1MB
   - Truncate content to 500KB for indexing
   - Process one batch in memory at a time
4. **Progress tracking**:
   - Repository-level progress (X of Y repos)
   - Batch-level progress within repositories
   - Rich terminal UI with progress bars
5. **Error handling**: Continue on errors, report summary

## Consequences

**Positive:**
- Predictable memory usage (~50-100MB per batch)
- Efficient API usage (fewer round trips)
- Responsive user feedback
- Graceful handling of large repositories

**Negative:**
- Complexity of batch error handling
- Potential data loss if batch partially fails
- Tuning required for optimal batch size

**Neutral:**
- Batch size becomes configuration parameter
- Need for batch retry logic
- Progress tracking overhead (~1-2% performance)

## Related
- ADR-004: Source Code Indexing Design
- Configuration hierarchy for batch settings
- Weaviate batch API documentation
- Phase 1: Initial batch implementation