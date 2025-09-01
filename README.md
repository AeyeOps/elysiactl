# elysiactl

A command-line utility for managing Elysia AI and Weaviate services in development and production environments. Provides unified control, monitoring, and maintenance for multi-node Weaviate clusters and Elysia AI services.

## Overview

elysiactl simplifies the orchestration of complex AI infrastructure by providing a single interface to manage both Weaviate vector database clusters and Elysia AI services. It handles service dependencies, monitors cluster health, and provides repair utilities for common configuration issues.

## Key Features

### Service Management
- Start, stop, and restart services with automatic dependency resolution
- Individual monitoring of multi-node Weaviate clusters
- Process tracking with PID management for reliable service control
- Docker container integration for accurate process monitoring

### Cluster Operations
- Real-time cluster health verification
- Replication factor validation across nodes
- RAFT consensus monitoring
- Collection distribution analysis

### Maintenance Tools
- Automated repair commands for replication issues
- Safe collection recreation with data loss protection
- Schema backup and recovery capabilities
- Dry-run mode for risk-free operation preview

## Requirements

- Python 3.8 or higher
- UV package manager ([Installation Guide](https://github.com/astral-sh/uv))
- Docker and Docker Compose
- Conda environment (for Elysia AI service)

## Installation

### Using UV (Recommended)

```bash
git clone https://github.com/your-org/elysiactl.git
cd elysiactl
uv sync
uv build
uv pip install dist/elysiactl-*.whl
```

### Development Setup

```bash
git clone https://github.com/your-org/elysiactl.git
cd elysiactl
uv sync
uv run elysiactl --version
```

## Quick Start

```bash
# Check version
elysiactl --version

# Start all services
elysiactl start

# Check status
elysiactl status

# Verify cluster health
elysiactl health --cluster

# Stop all services
elysiactl stop
```

## Command Reference

### Service Management

```bash
elysiactl start              # Start Weaviate and Elysia services
elysiactl stop               # Stop all services gracefully
elysiactl restart            # Restart all services
elysiactl status             # Display current service status
```

### Health Monitoring

```bash
elysiactl health                          # Basic health check
elysiactl health --verbose                # Detailed diagnostics
elysiactl health --verbose --last-errors 5   # Show recent logs
elysiactl health --cluster                # Verify cluster replication
elysiactl health --cluster --json         # JSON output for automation
```

### Maintenance Operations

```bash
elysiactl repair --help                      # View repair commands
elysiactl repair config-replication          # Fix replication issues
elysiactl repair config-replication --dry-run   # Preview changes
elysiactl repair config-replication --force     # Skip confirmations
```

## Detailed Documentation

### Cluster Verification

elysiactl provides comprehensive cluster verification to ensure proper replication across Weaviate nodes:

- **Replication Factor Validation**: Verifies collections are replicated according to configuration
- **Node Distribution**: Ensures shards are properly distributed across all nodes
- **RAFT Consensus**: Monitors cluster consensus for metadata synchronization
- **Collection Health**: Validates system collections (ELYSIA_CONFIG__, ELYSIA_FEEDBACK__, ELYSIA_METADATA__)

### Repair Operations

The repair system is designed to fix common cluster configuration issues while protecting data:

#### When to Use Repair

- Cluster health check reports replication issues
- Collections show incorrect replication factor
- After modifying RAFT consensus configuration
- When adding or removing cluster nodes

#### Safety Mechanisms

1. **Data Protection**: Operations refused if collections contain data
2. **Automatic Backups**: Schema exported before any modifications
3. **Confirmation Required**: Explicit user approval for destructive operations
4. **Dry Run Support**: Preview all changes before execution

### Verbose Diagnostics

The verbose mode (`--verbose` or `-v`) provides detailed system insights:

- Individual node health status with connection metrics
- Docker container statistics and resource usage
- Recent error logs from each service (configurable with `--last-errors`)
- Collection replication details and shard distribution
- Process information including PIDs and ports

## Architecture

### System Components

elysiactl manages a complex AI infrastructure consisting of:

#### Weaviate Cluster
- Three-node distributed configuration
- Docker Compose orchestration
- RAFT consensus for metadata synchronization
- Ports: 8080 (node1), 8081 (node2), 8082 (node3)
- Persistent volume storage per node

#### Elysia AI Service
- FastAPI-based application
- Conda environment isolation
- Process lifecycle management via PID tracking
- Port: 8000 (default)

### Technical Implementation

- **Process Control**: PID-based tracking with automatic cleanup
- **Container Management**: Docker API integration for monitoring
- **Health Monitoring**: Asynchronous HTTP health checks
- **Configuration Management**: Environment-based configuration
- **Error Handling**: Comprehensive error recovery and reporting

## Development

### Building and Testing

```bash
# Setup development environment
uv sync

# Run the tool in development
uv run elysiactl --version

# Build distribution package
uv build

# Run tests (when available)
uv run pytest tests/
```

### Code Structure

```
elysiactl/
├── pyproject.toml       # Package configuration (version, dependencies)
├── README.md            # User documentation
├── CHANGELOG.md         # Version history
├── ROADMAP.md           # Future development plans
├── src/
│   └── elysiactl/
│       ├── __init__.py  # Package initialization, version management
│       ├── cli.py       # CLI entry point and command routing
│       ├── commands/    # Command implementations
│       │   ├── health.py
│       │   ├── repair.py
│       │   ├── start.py
│       │   ├── status.py
│       │   └── stop.py
│       ├── services/    # Service management logic
│       │   ├── cluster_verification.py
│       │   ├── elysia.py
│       │   └── weaviate.py
│       └── utils/       # Utility functions
│           ├── display.py
│           └── process.py
└── docs/                # Additional documentation
```

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

## Contributing

Contributions are welcome. Please ensure:
- Code follows existing patterns and conventions
- Changes include appropriate error handling
- Documentation is updated for new features
- Tests are added for new functionality

## License

Copyright 2025 - Licensed under appropriate terms (to be specified)

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/elysiactl/issues)
- **Documentation**: [GitHub Wiki](https://github.com/your-org/elysiactl/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/elysiactl/discussions)

## Acknowledgments

- Weaviate team for the vector database platform
- Elysia AI team for the AI service framework
- UV team for modern Python package management
- Open source community for the excellent tooling ecosystem