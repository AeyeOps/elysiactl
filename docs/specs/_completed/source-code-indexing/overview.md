# Source Code Indexing: From Batch to Continuous Intelligence

## Evolution Overview

The elysiactl source code indexing capability has evolved from a simple batch operation to a sophisticated incremental synchronization system designed for enterprise scale.

## Architecture Evolution

### Phase 1: Batch Indexing (✅ COMPLETED)
- **Specification**: [batch-indexing-spec.md](./batch-indexing-spec.md)
- **Command**: `elysiactl index enterprise`
- **Status**: Implemented and operational
- **Purpose**: Initial full indexing of repositories
- **Limitations**: 
  - Static snapshot - becomes stale immediately
  - Full re-index required for updates
  - Doesn't scale to 76+ repositories

### Phase 2: Incremental Synchronization (🚧 CURRENT FOCUS)
- **Specification**: [sync-architecture.md](./sync-architecture.md)
- **Implementation**: [index-sync-specification.md](./index-sync-specification.md)
- **Command**: `elysiactl index sync`
- **Status**: Architecture complete, implementation pending
- **Purpose**: Continuous updates via changeset tracking
- **Innovations**:
  - Changeset-based delta synchronization
  - Smart three-tier content embedding (0-10KB plain, 10-100KB base64, 100KB+ reference)
  - Checkpoint recovery with SQLite
  - 4× performance improvement through I/O optimization
  - Cross-provider support (GitHub, Azure DevOps, BitBucket)

### Phase 3: Real-Time Intelligence (🔮 FUTURE)
- **Concept**: Event-driven updates via webhooks
- **Purpose**: Sub-second index updates
- **Technologies**: WebSockets, GitHub webhooks, file watchers

## When to Use Each Approach

### Use Batch Indexing (`index enterprise`) for:
- Initial repository setup
- Complete re-indexing after major changes
- One-time analysis projects
- Simple use cases with few repositories

### Use Incremental Sync (`index sync`) for:
- Daily/hourly updates
- Large repository fleets (50+ repos)
- Cross-provider environments
- Production systems requiring freshness
- CI/CD pipeline integration

## Key Architectural Decisions

### Why We Moved Beyond Batch Indexing

1. **Scale**: 76+ repositories across 4 providers made full scans impractical
2. **Freshness**: Code changes constantly; static indexes become stale in hours
3. **Efficiency**: Full re-indexing wastes 99% of effort on unchanged files
4. **Recovery**: Batch operations that fail after 50% lose all progress

### Innovations in the New Architecture

1. **Changeset Tracking**: Store commit SHA per repo, only process deltas
2. **Smart Content Embedding**: Reduce I/O by 80% through intelligent embedding
3. **Provider Abstraction**: Unified interface for Git, OneDrive, Confluence (future)
4. **Checkpoint Recovery**: Resume exactly where failures occurred
5. **Stream Processing**: Handle millions of files without memory exhaustion

## File Organization

```
source-code-indexing/
├── overview.md                    # This file - architectural overview
├── batch-indexing-spec.md         # Phase 1 - Original batch implementation
├── sync-architecture.md           # Phase 2 - Incremental sync design
└── index-sync-specification.md    # Phase 2 - Implementation details
```

## Performance Comparison

| Metric | Batch Indexing | Incremental Sync |
|--------|---------------|------------------|
| Initial Index | 10 min for 100K files | Same |
| Daily Updates | 10 min (full re-scan) | 30 sec (only changes) |
| Memory Usage | 500MB constant | 50MB streaming |
| Failure Recovery | Start over | Resume from checkpoint |
| I/O Operations | 200K for 100K files | 20K for typical updates |
| Provider Support | Local repos only | Git + future OneDrive/Confluence |

## Migration Path

1. **Today**: Use `elysiactl index enterprise` for initial indexing
2. **Week 1-2**: Implement basic `index sync` with file lists
3. **Week 3-4**: Add changeset tracking and smart embedding
4. **Month 2**: Production deployment with monitoring
5. **Future**: Add real-time updates and additional providers

## Success Metrics

### Batch Indexing (Achieved)
- ✅ Index 100+ repositories
- ✅ Process 10,000+ files
- ✅ Sub-second search times

### Incremental Sync (Target)
- 📊 Process 1000 changes in < 5 seconds
- 📊 Reduce I/O operations by 80%
- 📊 Support 76+ repositories across 4 providers
- 📊 Zero data loss with checkpoint recovery
- 📊 4× faster than batch for updates

## Next Steps

1. Review [sync-architecture.md](./sync-architecture.md) for detailed design
2. Implement MVP per [index-sync-specification.md](./index-sync-specification.md)
3. Test with subset of repositories
4. Deploy progressively with monitoring
5. Extend to additional providers as needed

## Key Insight

**The evolution from batch to incremental isn't just an optimization - it's a fundamental shift from "indexing as a one-time operation" to "indexing as a continuous intelligence stream" that keeps Weaviate perpetually fresh with minimal resource usage.**

  
For mgit diff implementation details, see:
/opt/aeo/mgit/docs/specs/change-pipeline-feature/**/*.md
  
