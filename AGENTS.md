# Repository Guidelines

## Project Structure & Module Organization
- `src/elysiactl/`: Main package and CLI entry (`elysiactl.cli:app`). Key modules: `commands/`, `services/`, `config/`, `tui/`, `utils/`.
- `tests/`: Pytest suite; integration specs under `tests/integration/`.
- `scripts/`: Helper tools (e.g., `performance_report.py`, `run_integration_tests.sh`).
- `docs/`, `dist`, `.env.example`: Documentation, build artifacts, and environment template.

## Build, Test, and Development Commands
- Install deps: `uv sync`
- Run CLI (no install): `uv run python -m elysiactl --version`
- Lint & format: `uv run ruff check .` and `uv run ruff format .`
- Type check: `uv run mypy src`
- Tests (quiet): `uv run pytest -q`
- Tests with coverage: `uv run pytest --cov=src/elysiactl --cov-report=term-missing`
- Build wheel: `uv build`
- Editable install: `uv pip install -e .` (then `uv run elysiactl --help`)

## Coding Style & Naming Conventions
- Python 3.11; 4-space indentation; max line length 100.
- Use double quotes; imports are isort-managed via Ruff.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`.
- Keep CLI commands consistent with existing verbs (`start`, `status`, `health`, `stop`).

## Testing Guidelines
- Framework: Pytest. File pattern `tests/test_*.py`; classes `Test*`; functions `test_*`.
- Markers: `unit`, `integration`, `slow`, `benchmark` (see `pyproject.toml`).
- Example selection: `uv run pytest -m "unit and not slow"`.
- Coverage targets source only (`src/elysiactl`); avoid testing scripts directly.

## Commit & Pull Request Guidelines
- Commits: Imperative, concise; prefer Conventional Commits prefixes (`feat:`, `fix:`, `docs:`, `refactor:`). Keep subject ≤72 chars.
- PRs must include: clear description, linked issues, test evidence (logs or coverage), and screenshots/GIFs for TUI or CLI UX changes.
- Before requesting review: run `ruff`, `mypy`, `pytest` (with markers as appropriate); update `README.md`/`docs/` and `CHANGELOG.md` when user-facing behavior changes.

## Security & Configuration Tips
- Never commit secrets. Start from `.env.example` to create a local `.env`.
- Configuration lives in `src/elysiactl/config/` and environment variables (loaded via `python-dotenv`). Prefer config over hardcoded values.
