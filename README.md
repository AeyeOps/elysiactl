# ElysiaCtl

A command-line utility for managing Elysia AI and Weaviate services in development environments. Provides unified control and monitoring for multi-node Weaviate clusters and Elysia AI services.

## Acknowledgments

Special recognition to the **Weaviate** team for their innovative vector database technology that powers modern AI applications, and to the **Elysia AI** team for their groundbreaking work in artificial intelligence. We look forward to the production release of Elysia AI and its continued evolution.

## Features

- **Service Orchestration** - Start, stop, and restart services with proper dependency management
- **Individual Node Monitoring** - Track each Weaviate node separately with accurate PIDs
- **Health Diagnostics** - Comprehensive health checks with verbose mode for troubleshooting
- **Docker Integration** - Automatic Docker container detection and PID resolution
- **Detailed Logging** - Per-container log viewing with configurable output
- **Cluster Awareness** - Replication status and node distribution monitoring

## Prerequisites

- UV package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker and docker-compose
- Conda with "elysia" environment
- Python 3.12+

## Installation

### From Source
```bash
git clone https://github.com/AeyeOps/elysiactl.git
cd elysiactl
uv sync
```

### Local Development
```bash
cd /opt/elysiactl
uv sync
```

## Usage

```bash
# Run directly with UV
uv run elysiactl start

# Or activate environment
source .venv/bin/activate
elysiactl start

# Stop both services
elysiactl stop

# Restart both services
elysiactl restart

# Check service status
elysiactl status

# Health check (basic)
elysiactl health

# Detailed health diagnostics with verbose output
elysiactl health --verbose
elysiactl health -v  # Short form

# Verbose with custom log count per container (default is 3)
# Note: --last-errors specifies lines PER CONTAINER, not total
# With 3 Weaviate nodes: 3 logs per container = 9 total logs displayed
elysiactl health --verbose --last-errors 5  # Shows 15 total logs (5 × 3 nodes)
elysiactl health -v --last-errors 2  # Shows 6 total logs (2 × 3 nodes)
```

### Health Check Verbose Mode

The `--verbose` flag provides detailed diagnostics including:
- Individual Weaviate node health (ports 8080, 8081, 8082)
- ELYSIA_CONFIG__ collection replication status
- Container/process statistics
- Recent error logs from services
- Connection metrics

This is particularly useful for diagnosing "save stuck" issues related to collection replication.

## Service Management

- **Weaviate**: Managed via docker-compose from `/opt/weaviate/`
- **Elysia**: Run from `/opt/elysia/` using conda environment "elysia"


## Architecture

### Service Management
ElysiaCtl provides unified control over:
- **Weaviate Cluster**: Three-node configuration (ports 8080, 8081, 8082) managed through Docker Compose
- **Elysia AI Service**: FastAPI application running in conda environment with process monitoring

### Technical Details
- Process tracking via PID file (`/tmp/elysia.pid`)
- Docker container integration for accurate process monitoring
- Automatic dependency resolution during service startup
- Graceful shutdown sequences with proper cleanup

### Health Monitoring
The tool monitors multiple health endpoints:
- Weaviate nodes: `http://localhost:{8080,8081,8082}/v1/nodes`
- Elysia service: `http://localhost:8000/docs`
- Collection replication status across cluster nodes

## Development

### Project Structure
```
elysiactl/
├── pyproject.toml          # UV package configuration
├── README.md               # This file
├── ROADMAP.md             # Future development plans
├── src/elysiactl/         # Source code
│   ├── cli.py            # Main CLI entry point
│   ├── commands/         # Command implementations
│   ├── services/         # Service management logic
│   └── utils/            # Utility functions
└── tests/                # Test suite
```

### Contributing
This project uses UV for dependency management. All contributions should maintain the established code structure and follow existing patterns.

## License

Copyright 2025 AeyeOps

## Support

For issues, feature requests, or questions, please visit the [GitHub repository](https://github.com/AeyeOps/elysiactl).