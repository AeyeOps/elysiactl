# Foundation: Collection Management Core

## Overview
This phase establishes the fundamental collection management capabilities for elysiactl, providing essential CRUD operations and data management for Weaviate collections.

## Core Commands Implemented

### Collection CRUD Operations (`col ls`, `col show`, `col rm`, `col create`)

**File**: `/opt/elysiactl/src/elysiactl/commands/collection.py`

#### List Collections (`col ls`)
- Query Weaviate API for all collections
- Support filtering with patterns
- Multiple output formats (table, json, yaml)
- Show collection metadata (name, object count, replication, shards)

#### Show Collection (`col show`)
- Detailed information about specific collection
- Optional schema and statistics display
- Replication and sharding configuration

#### Remove Collection (`col rm`)
- Safe deletion with confirmation prompts
- Protection for system collections using patterns
- Dry-run mode for safety
- Interactive confirmation flow

#### Create Collection (`col create`)
- Create new collections with custom schema
- Support for schema files and templates
- Replication and sharding configuration
- Default schema generation

### Data Operations (`col backup`, `col restore`, `col clear`)

#### Backup Collection (`col backup`)
- Full collection backup with schema and data
- Multiple formats: JSON, Parquet, compressed
- Batch processing for large collections
- Progress indicators and error recovery
- Backup catalog management

#### Restore Collection (`col restore`)
- Restore from backup files
- Support for merging with existing collections
- Checkpoint-based recovery for failed restores
- Batch import with configurable sizes
- Schema-only or full data restoration

#### Clear Collection (`col clear`)
- Remove all objects while preserving schema
- Option to recreate collection completely
- Batch deletion for performance
- Safety confirmations

## Service Integration

### WeaviateCollectionManager
**File**: `/opt/elysiactl/src/elysiactl/services/weaviate_collections.py`

- REST API integration with Weaviate
- Error handling and custom exceptions
- Protected collection patterns
- Object counting and metadata retrieval

## Key Features

### Safety Mechanisms
- Protected collection patterns prevent accidental deletion
- Interactive confirmations for destructive operations
- Dry-run modes for validation
- Checkpoint recovery for long operations

### Performance Optimizations
- Batch processing for large datasets
- Streaming for memory-efficient operations
- Configurable batch sizes based on collection size
- Progress indicators for user feedback

### Error Handling
- Custom exception hierarchy
- Detailed error messages with suggestions
- Connection and permission error handling
- Recovery mechanisms for failed operations

## Testing Strategy

### Unit Tests
- Command parsing and validation
- Service method functionality
- Error condition handling
- Protected collection logic

### Integration Tests
- Full command execution cycles
- Weaviate API interaction
- Data consistency verification
- Performance benchmarking

## Implementation Details

### Dependencies
- httpx: HTTP client for Weaviate API
- typer: CLI framework
- rich: Terminal formatting and progress bars
- fnmatch: Pattern matching for filters
- pyarrow/pandas: Optional for Parquet format

### Configuration
- Base URL configuration for Weaviate
- Protected pattern definitions
- Batch size defaults
- Timeout settings

## Success Metrics

1. **Functionality**: All 7 core commands working reliably
2. **Safety**: Zero accidental data loss, protected collections intact
3. **Performance**: Operations complete efficiently regardless of collection size
4. **Usability**: Clear output, helpful errors, intuitive command structure

## File Structure
```
src/elysiactl/
├── commands/
│   └── collection.py          # All collection commands
├── services/
│   └── weaviate_collections.py # Weaviate API integration
└── tests/
    ├── test_collection_commands.py
    └── integration/
        └── test_collection_lifecycle.py
```

## Next Steps
This foundation enables advanced features like:
- Automated backup scheduling
- Cross-collection operations
- Performance monitoring
- Advanced filtering and search
- Multi-tenant collection management

All foundation commands are production-ready and tested.