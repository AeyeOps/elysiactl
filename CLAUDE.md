# Claude Code Configuration - elysiactl Project

## CRITICAL: File Discipline Rules

### ABSOLUTELY FORBIDDEN - NO EXCEPTIONS
- **NO test scripts** outside of `tests/` directory (no test_*.py, demo_*.py, example_*.py)
- **NO summary files** (no SUMMARY.md, OVERVIEW.md, NOTES.md, TODO.md)
- **NO duplicate documentation** (README.md and ROADMAP.md are sufficient)
- **NO backup files** (no *.bak, *.old, *.tmp, *_backup.*)
- **NO experimental scripts** in root (no quick_test.py, try_this.py, scratch.py)
- **NO generated reports** (no output.txt, results.log, analysis.md)
- **NO AI attribution** in commits or code comments

### File Creation Policy
**NEVER create a new file unless:**
1. It's a core source file in `src/elysiactl/` that implements required functionality
2. It's a proper test in `tests/` directory
3. User EXPLICITLY requests it by name and location

**If tempted to create a file, STOP and:**
- First check if existing files can be modified instead
- If it's for testing, use the Python REPL or inline verification
- If it's documentation, update README.md or add to ROADMAP.md
- If it's a note or reminder, DON'T CREATE IT

### Project Structure - FROZEN
```
elysiactl/
├── pyproject.toml          # UV configuration (DO NOT create requirements.txt, setup.py, etc.)
├── README.md               # User documentation only
├── ROADMAP.md             # Future features only  
├── CLAUDE.md              # This file
├── src/elysiactl/         # Source code ONLY
│   ├── __init__.py
│   ├── cli.py            # Main entry point
│   ├── commands/         # Command implementations
│   ├── services/         # Service management
│   └── utils/            # Utilities
└── tests/                # Tests ONLY (when explicitly requested)
```

### Development Guidelines

**CRITICAL: This is a UV project - ALWAYS use UV, never pip or python directly**
- Use `uv run elysiactl` for testing, NOT `python -m elysiactl`
- Use `uv sync` for dependencies, NOT `pip install`
- Use `uv run python` for REPL testing, NOT `python`

**When modifying this project:**
1. Edit existing files rather than creating new ones
2. Keep all logic within the established module structure
3. Test changes using actual CLI commands: `uv run elysiactl status`
4. Use `uv run elysiactl status` and `uv run elysiactl health` to verify functionality

**When adding features:**
1. Add to existing command files or create new ones ONLY in `commands/`
2. Update ROADMAP.md to track completion
3. Update README.md only if user-facing changes occur

**When debugging:**
- Use UV for REPL tests: `uv run python -c "from elysiactl.services import weaviate; print(weaviate.check_health())"`
- Use UV for CLI: `uv run elysiactl status --debug` (if debug flag exists)
- DO NOT create debug_*.py or test_*.py files

### Git Commit Rules
- Describe WHAT changed, not HOW it was created
- NEVER include "Generated with Claude Code" or any AI attribution in commit messages
- NEVER use "Claude" as git user name or "noreply@anthropic.com" as email
- Keep commits atomic and purposeful
- NEVER use emojis in commits or code comments
- No Co-Authored-By: Claude entries

### Git User Configuration
**Author**: Steve Antonakakis (steve.antonakakis@gmail.com)
```bash
git config user.name "Steve Antonakakis"
git config user.email "steve.antonakakis@gmail.com"
```
**IMPORTANT**: Always use the above user configuration, never Claude or AI-related identities

### Testing Policy
- Production code goes in `src/elysiactl/`
- Test code goes in `tests/` (only when explicitly requested)
- Experimental code should be tested in REPL and then integrated or discarded
- No standalone scripts for "trying things out"

### The Prime Directive
**Keep this project clean and minimal.** Every file should have a clear purpose within the application architecture. If you can't explain why a file needs to exist as part of the core application, it shouldn't exist.

## Project Context

**Purpose**: Control utility for managing Elysia AI and Weaviate services  
**Style**: Linux utility convention (like systemctl, kubectl)  
**Dependencies**: Managed via UV, not pip  
**Environment**: Uses conda environment "elysia"  

**Service Paths**:
- Weaviate: `/opt/weaviate/` (docker-compose)
- Elysia: `/opt/elysia/` (FastAPI app)
- This tool: `/opt/weaviate/elysiactl/`

**Core Commands**:
- `start` - Start both services in correct order
- `stop` - Stop both services gracefully  
- `restart` - Stop then start
- `status` - Show current state
- `health` - Detailed health checks

## Communication Policy - FOCUS ON FAILURES

### STOP Doing This:
- ❌ "Successfully implemented X, Y, and Z features!"
- ❌ "Everything is working great! The services start perfectly!"
- ❌ "I've added these wonderful capabilities..."
- ❌ Long lists of what was accomplished
- ❌ Self-congratulatory summaries

### START Doing This:
- ✅ "The health check times out when Weaviate is slow to start"
- ✅ "Error: Elysia fails to find conda environment on some shells"
- ✅ "Problem: Status shows 'Running' but service is actually crashed"
- ✅ "Cannot detect when docker-compose partially fails"
- ✅ "Race condition between service startup and health check"

### The 90/10 Rule
Spend 90% of communication on:
- What's broken
- What's unreliable  
- What's missing
- Edge cases not handled
- Errors encountered

Spend 10% (or less) on:
- What's working (only if directly relevant to the problem)

### When Reporting Status:
**Bad**: "I've successfully created the elysiactl tool with start, stop, restart, status, and health commands. It uses typer and rich for beautiful output!"

**Good**: "elysiactl fails to detect zombie Elysia processes. The PID file persists after crashes. No timeout handling for slow Weaviate startup."

### Why This Matters
- Working features don't need discussion - they work
- Broken features need immediate attention
- Problems hidden behind success theater don't get fixed
- Real collaboration happens when we face issues honestly

## Configuration Over Hardcoding

### NEVER Hardcode - Always Configure
- **NEVER hardcode URLs** - use config files or environment variables
- **NEVER hardcode paths** - accept as parameters or discover dynamically
- **NEVER hardcode patterns** - make them configurable options
- **NEVER hardcode service locations** - localhost:8080 assumptions break
- **Commands should describe WHAT, not WHO/WHERE**
  - ✅ Good: `index scan <directory> --pattern <pattern>`
  - ❌ Bad: `index enterprise` (hardcoded location/purpose)

### Configuration Hierarchy
1. **Command-line arguments** - highest precedence for flexibility
2. **Environment variables** - for deployment configuration
3. **Config files** - for project defaults
4. **Sensible defaults** - only as last resort, must be overridable

### Anti-Patterns to Avoid
- **Embedding business logic in commands** (specific company patterns)
- **Function names that describe specific use cases** rather than operations
- **String replacements that assume specific formats**
- **Hardcoded replication factors, batch sizes, or limits**
- **Assuming single instance** (always consider multi-node/cluster scenarios)

## Lessons Learned

### Redundant Files Are Debt
- **install.sh was deleted** - UV already handles installation with `uv sync`
- Every extra file needs maintenance and causes confusion
- If a tool already does the job, don't wrap it unnecessarily

### Log Display Pitfalls
- **Don't truncate errors** - Complete information is better than pretty formatting
- **Don't filter presumptively** - Let users see what's actually happening
- **Be explicit about multipliers** - "per container" vs "total" matters with 3 nodes

### PATH Management in WSL2/Conda
- **UV can exist in multiple locations** - conda's version vs .local/bin
- **PATH order matters** - .local/bin should come first to override system tools
- **Post-conda hooks may be needed** - Conda activation can reset PATH

### Design Decisions
- **Three-panel layout works** - Separate concerns visually (Elysia, Weaviate, Logs)
- **Verbose mode should be VERBOSE** - Show everything, hide nothing
- **Per-container counting is intuitive** - Users think in terms of individual services

## Remember
Less is more. A clean, focused codebase is better than a sprawling mess of "helpful" files that nobody uses. When in doubt, DON'T create the file.

If it's working, stop talking about it. If it's broken, let's fix it.