# Changelog

All notable changes to ElysiaCtl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-09-01

### Added
- Comprehensive collection management specification documentation
- Phase 1-3 implementation plans for collection operations
- Prioritization matrix for 6-day development sprints
- Integration documentation with existing catalog system

### Changed
- Fixed Elysia service startup to use proper Python module path
- Updated documentation to clarify Elysia's read-only nature for Weaviate collections

### Documentation
- Added collection management overview and architecture design
- Created detailed implementation specifications for core CRUD operations
- Documented backup/restore strategies with checkpoint recovery
- Added advanced features roadmap including real-time monitoring and cross-cluster migration

## [0.1.0] - 2025-09-01

### Added
- Initial release of ElysiaCtl
- Service orchestration for Weaviate and Elysia AI services
- Multi-node Weaviate cluster support (3 nodes)
- Individual node health monitoring with Docker integration
- Comprehensive cluster verification with replication status
- Repair command for fixing collection replication issues
- Detailed health diagnostics with verbose mode
- JSON output support for programmatic access
- Dry-run mode for repair operations
- Version management with --version flag

### Features
- `start` - Start both Weaviate and Elysia services with dependency management
- `stop` - Gracefully stop both services
- `restart` - Stop and start services in correct order
- `status` - Show current status of all services and nodes
- `health` - Perform health checks with optional verbose diagnostics
- `health --cluster` - Verify cluster replication and node distribution
- `repair config-replication` - Fix ELYSIA_CONFIG__ replication issues

### Technical Details
- Built with UV package manager for dependency management
- Uses Typer for CLI framework with Rich for terminal output
- Process tracking via PID files for service management
- Docker container integration for accurate process monitoring
- RAFT consensus verification for Weaviate cluster health
- Automatic schema backup before repair operations

### Safety Features
- Data loss protection in repair operations
- Confirmation prompts for destructive operations
- Dry-run mode for previewing changes
- Automatic backup creation before modifications

### Known Issues
- Elysia AI service management requires manual conda environment setup
- Test record writing for lag detection may fail on read-only collections

## [Unreleased]

### Planned
- Enhanced service diagnostics commands
- Performance monitoring capabilities
- Backup and restore functionality
- Migration tools for version upgrades
- Extended repair commands for other collections