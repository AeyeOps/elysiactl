# CLAUDE.md - ElysiaCtl Documentation Standards

This file provides guidance for maintaining and extending the specification-driven development process for ElysiaCtl.

## Directory Structure

```
docs/
├── CLAUDE.md (this file)
├── ADR/                   # Architecture Decision Records
│   └── 001-no-automatic-fixes.md
└── specs/
    ├── cluster-verification/
    │   ├── overview.md    # Main specification
    │   ├── phases-done/   # Completed implementation phases
    │   └── phases-pending/ # Specifications awaiting implementation
    └── [feature-name]/    # Future feature specifications
        ├── overview.md
        ├── phases-done/
        └── phases-pending/
```

## Documentation Philosophy

ElysiaCtl follows a **specification-first, phase-driven** approach to development:

1. **Specifications Define Intent**: Major features begin with comprehensive specs
2. **Phases Enable Incremental Progress**: Large features broken into manageable phases
3. **ADRs Document Architecture**: Key decisions preserved for future reference
4. **Explicit Over Magic**: Document why we avoid automatic fixes and complex abstractions

## Phase Specification Standards

### Required Sections
Every phase specification MUST include these sections in order:

1. **# Phase N: [Descriptive Title]**
2. **## Objective** - Single sentence stating what this phase accomplishes
3. **## Problem Summary** - Brief description of the issue being solved
4. **## Implementation Details** - Exact changes with file paths and line numbers
5. **## Agent Workflow** - Step-by-step instructions for implementation
6. **## Testing** - How to verify the implementation works
7. **## Success Criteria** - Checklist of completion requirements

### Implementation Details Format
```markdown
### File: `/opt/elysiactl/src/elysiactl/commands/health.py`

**Change N: [Description]**
**Location:** Line XXX
**Current Code:**
```python
[exact current code]
```

**New Code:**
```python
[exact new code]
```
```

### ElysiaCtl-Specific Guidelines

1. **UV-First Development**
   - Always use `uv run elysiactl` for testing, not `python -m elysiactl`
   - Include UV commands in testing steps
   - Reference UV project structure in file paths

2. **CLI-Centric Design**
   - Phases focus on command-line interface improvements
   - Test using actual CLI invocations: `uv run elysiactl status`
   - Consider both human and script usage patterns

3. **Service Management Focus**
   - Specifications center on Weaviate and Elysia service management
   - Consider multi-node cluster scenarios
   - Document service interaction patterns

4. **Error Handling Emphasis**
   - Each phase must address failure scenarios
   - Include timeout and connectivity error cases
   - Document user-facing error messages

## Key Principles

1. **Precision Over Ambiguity**
   - Use exact line numbers, not "around line X"
   - Show complete code snippets, not fragments
   - Specify absolute file paths starting with `/opt/elysiactl/`

2. **Incremental Progress**
   - Each phase should be completable in 1-2 hours
   - Phases build on each other but remain independent
   - Critical fixes before enhancements

3. **Agent-Friendly Design**
   - Instructions should be executable without interpretation
   - Use numbered steps in workflows
   - Include verification steps using `uv run` commands

4. **Test-Driven Validation**
   - Every phase includes testing requirements
   - Prefer CLI integration tests over unit tests
   - Include manual testing checklists with actual commands

## Workflow Process

### Creating a New Phase Spec

1. **Identify the Problem**
   - Check existing ADRs for architectural guidance
   - Verify the issue hasn't been addressed
   - Determine criticality (blocking vs enhancement)

2. **Draft the Specification**
   - Use existing phase specs as templates
   - Verify line numbers by reading actual files
   - Include before/after code snippets
   - Test commands with `uv run elysiactl`

3. **Implementation**
   - Execute the agent workflow steps
   - Run specified tests using UV
   - Check all success criteria
   - Move spec to `phases-done/` when complete

### Phase Naming Convention

```
phase-[N]-[descriptive-kebab-case].md
```

Examples:
- `phase-1-cluster-topology-detection.md`
- `phase-2-replication-verification.md`
- `phase-3-data-consistency-checks.md`

## Architecture Decision Records (ADRs)

ADRs document key architectural and design decisions for ElysiaCtl:

### Required ADR Structure
1. **# ADR-XXX: [Title]**
2. **## Status** - Proposed/Accepted/Deprecated
3. **## Context** - The situation requiring a decision
4. **## Decision** - What was decided
5. **## Consequences** - Results of this decision
6. **## Related** - Links to related ADRs or specs

### ADR Naming Convention
```
XXX-kebab-case-title.md
```

Examples:
- `001-no-automatic-fixes.md`
- `002-cluster-detection-strategy.md`
- `003-error-reporting-format.md`

## Quality Standards

### DO:
- ✅ Include exact line numbers from actual code
- ✅ Show complete function signatures in changes
- ✅ Provide testable success criteria using `uv run`
- ✅ Reference relevant ADRs and policies
- ✅ Keep phases focused on single concerns
- ✅ Document service interaction patterns
- ✅ Include error scenarios and timeouts

### DON'T:
- ❌ Use vague descriptions like "update the function"
- ❌ Omit testing requirements
- ❌ Combine unrelated changes in one phase
- ❌ Create phases larger than 2 hours of work
- ❌ Skip verification steps
- ❌ Ignore cluster/multi-node scenarios

## ElysiaCtl Testing Standards

### CLI Integration Tests
```bash
# Verify basic functionality
uv run elysiactl status
uv run elysiactl health

# Test with flags
uv run elysiactl health --cluster
uv run elysiactl status --json
```

### Manual Testing Checklist Template
- [ ] Command executes without errors
- [ ] Output format matches specification
- [ ] Error handling works for invalid inputs
- [ ] Works with both single-node and cluster configurations
- [ ] JSON output (if applicable) is valid
- [ ] Help text is accurate: `uv run elysiactl [command] --help`

## Example Phase Spec Template

```markdown
# Phase N: [Title]

## Objective
[Single sentence goal related to ElysiaCtl functionality]

## Problem Summary
[2-3 sentences describing the service management issue]

## Implementation Details

### File: `/opt/elysiactl/src/elysiactl/commands/health.py`

**Change 1: [What changes]**
**Location:** Line XXX
**Current Code:**
```python
[current code]
```

**New Code:**
```python
[new code]
```

## Agent Workflow

### Step 1: [Action]
1. [Specific instruction using uv run]
2. [Specific instruction]
3. [Verification using elysiactl command]

### Step 2: [Action]
1. [Specific instruction]
2. [Test with cluster scenario]

## Testing

### CLI Integration Tests
```bash
uv run elysiactl health --cluster
uv run elysiactl status --json
```

### Manual Testing
- [ ] [Test scenario 1 with actual command]
- [ ] [Test scenario 2 with error case]
- [ ] [Verification step using CLI]

## Success Criteria
- [ ] [Criterion 1 with measurable outcome]
- [ ] [Criterion 2 tested via CLI]
- [ ] All commands execute without errors
- [ ] No regressions in existing functionality
- [ ] Works with both single-node and cluster setups
```

## Maintenance Guidelines

### Weekly Review
- Move completed specs from `phases-pending/` to `phases-done/`
- Archive obsolete specs with `OBSOLETE-` prefix
- Update phase numbers if reordering needed
- Test all documented commands still work

### Documentation Updates
- Update main spec document when phases complete
- Keep running list of completed phases in overview
- Document lessons learned about service management

## ElysiaCtl-Specific Tips

1. **Always Test with UV**: Use `uv run elysiactl` not `python -m elysiactl`
2. **Consider Both Modes**: Test single-node and cluster configurations
3. **Verify Service States**: Check actual Weaviate/Elysia status, not just API responses
4. **Document Timeouts**: Service management involves waiting - specify timeouts
5. **Error Message Quality**: Users need actionable error messages for service issues

## Common Pitfalls to Avoid

1. **Stale Line Numbers**: Code changes, verify before implementation
2. **Missing UV Usage**: Always use UV commands in testing
3. **Single-Node Assumptions**: Consider cluster scenarios
4. **Ignoring Timeouts**: Services take time to start/stop
5. **Vague Error Messages**: Users need specific guidance for service issues
6. **Skipping Service Interaction**: Test actual Weaviate/Elysia communication

## Questions or Improvements?

This process is designed to evolve with ElysiaCtl's needs. If you identify improvements:
1. Create an ADR proposing the change
2. Update this CLAUDE.md file
3. Apply the new process to future phases

Remember: The goal is sustainable, incremental progress with high confidence in each change while maintaining ElysiaCtl's focus on reliable service management.