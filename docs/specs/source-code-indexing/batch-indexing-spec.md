# Source Code Indexing Specification

## Overview
elysiactl needs the ability to index large source code repositories into Weaviate for semantic search and code analysis. The primary use case is indexing the Enterprise codebase containing 100+ Visual Studio repositories.

## Business Requirements
1. Index all Enterprise repositories from `/opt/pdi/Enterprise/`
2. Filter repositories by pattern: `https-pdidev.visualstudio*`
3. Exclude deprecated repositories containing `ZZ_Obsolete`
4. Support incremental updates without full re-indexing
5. Provide progress tracking for long-running operations
6. Ensure proper replication for production use

## Technical Requirements
1. Create `SRC_ENTERPRISE__` collection with replication factor=3
2. Index only source code files, skip binaries and build artifacts
3. Batch processing for efficiency (100 files per batch)
4. Store file metadata: path, language, size, hash, timestamps
5. Use OpenAI embeddings for semantic search capability
6. Handle multiple character encodings (UTF-8, Latin-1)
7. Limit file content to 500KB to avoid memory issues

## Architecture Decisions

### ADR-004: Source Code Indexing Design
**Status**: Accepted
**Decision**: Implement as a subcommand under `elysiactl index` with separate commands for different repository sources
**Rationale**: 
- Allows future expansion to other code sources
- Clear separation of concerns
- Follows existing elysiactl patterns

### ADR-005: Batch Processing Strategy
**Status**: Accepted  
**Decision**: Process files in batches of 100 and use async/await for I/O operations
**Rationale**:
- Balances memory usage with API efficiency
- Prevents timeout issues with large repositories
- Allows progress tracking per repository

## Implementation Phases

### Phase 1: Core Indexing Command ✅ COMPLETED
- Create `index` command structure
- Implement Enterprise repository discovery
- Add file filtering and language detection
- Create batch processing system
- Add progress tracking

### Phase 2: Collection Management (Future)
- Add collection backup/restore
- Implement incremental updates
- Add duplicate detection
- Support collection versioning

### Phase 3: Search Interface (Future)
- Add semantic search command
- Implement code similarity search
- Add language-specific filters
- Create export functionality

## Success Metrics
1. Successfully index 100+ repositories
2. Process 10,000+ source files
3. Maintain sub-second search response times
4. Zero data loss during indexing
5. Clear progress indication for long operations

## Command Interface

```bash
# Check collection status
elysiactl index status

# Dry run to preview
elysiactl index enterprise --dry-run

# Index all Enterprise repos
elysiactl index enterprise

# Clear and re-index
elysiactl index enterprise --clear

# Use custom collection
elysiactl index enterprise --collection MY_COLLECTION
```

## File Filtering Rules

### Included Extensions
- Web: .js, .jsx, .ts, .tsx, .html, .css, .scss
- Backend: .py, .cs, .java, .go, .rs, .rb, .php
- Config: .json, .yaml, .xml, .toml, .env
- Docs: .md, .rst, .txt

### Excluded Directories
- Version control: .git
- Dependencies: node_modules, packages, .nuget
- Build: build, dist, bin, obj, target
- Cache: __pycache__, .pytest_cache
- IDE: .vscode, .idea, .vs

### Size Limits
- Skip files > 1MB
- Truncate content to 500KB for indexing
- No limit on total repository size

## Error Handling
1. Skip files that cannot be decoded
2. Continue on repository access errors
3. Retry failed batches once
4. Report summary of failures
5. Non-zero exit only on complete failure

## Security Considerations
1. No credentials or secrets indexed (skip .env patterns)
2. Local access only (no remote repository support)
3. Read-only operations on source files
4. No execution of discovered code

## Performance Targets
- Index 1,000 files per minute
- Memory usage < 500MB
- Support repositories up to 1GB
- Batch API calls for efficiency
- Async I/O for file operations

## Future Enhancements
1. Support for other repository sources (GitHub, GitLab)
2. Incremental updates based on git commits
3. Language-specific parsing for better embeddings
4. Integration with Elysia AI for code analysis
5. Real-time indexing via file watchers