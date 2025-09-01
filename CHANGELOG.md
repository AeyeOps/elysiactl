# Changelog

All notable changes to ElysiaCtl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Elysia health check now uses correct `/api/health` endpoint instead of `/docs`
- Weaviate multi-node cluster detection now checks all nodes (8080, 8081, 8082)
- Docker container process detection enhanced with fallback to `ss` command
- Service status correctly shows "Running" for multi-node Weaviate clusters

### Known Issues
- PID file (`/tmp/elysia.pid`) persists after Elysia crashes
- No detection of zombie Elysia processes
- ELYSIA_CONFIG__ collection not replicated to Weaviate nodes 8081/8082
- No configurable timeout for slow Weaviate startup (hardcoded 60s)
- Cannot detect partial docker-compose failures

## [0.2.0] - 2025-08-31

### Added
- Verbose health diagnostics with `--verbose` flag
  - Individual Weaviate node health checks (ports 8080, 8081, 8082)
  - ELYSIA_CONFIG__ collection replication status monitoring
  - Container/process statistics (CPU, memory, status)
  - Active connection counting
- `--last-errors` option for viewing recent logs (per-container count)
- Three-panel layout for verbose health output:
  - Elysia AI Health (top)
  - Weaviate Cluster Health (middle)
  - Weaviate Node Logs (bottom)
- JSON log parsing with color-coded severity levels
- Comprehensive CLAUDE.md with project discipline rules
- Communication policy focusing on failures (90/10 rule)

### Changed
- Health command now shows complete logs without truncation
- Log count is per-container, not total (3 logs × 3 nodes = 9 total)
- Improved error visibility with unfiltered log display
- README documentation clarified for per-container behavior

### Removed
- install.sh script (redundant with UV's built-in `uv sync`)
- Presumptuous error filtering in log display
- Log truncation at 120 characters

### Fixed
- UV PATH conflicts between conda and system installations
- UV not found in PATH after conda activation

## [0.1.0] - 2025-08-30

### Added
- Initial release of ElysiaCtl
- Core commands: start, stop, restart, status, health
- Service management for Weaviate (docker-compose) and Elysia AI (FastAPI)
- Rich terminal output with colored status indicators
- PID-based process tracking for Elysia
- Docker-compose integration for Weaviate cluster
- Basic health endpoint checking
- UV package manager integration
- Typer CLI framework with type hints

### Dependencies
- typer for CLI framework
- rich for terminal formatting
- httpx for health checks
- psutil for process management