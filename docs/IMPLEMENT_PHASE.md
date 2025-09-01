# IMPLEMENT_PHASE Command

## User-Level Command for Phase Implementation

Save this as a user command in `~/.claude/commands/implement_phase.md`:

```markdown
---
description: Implement a phase specification with multi-agent coordination
category: project-task-management
argument-hint: <phase-spec-path>
---

# Implement Phase Specification

When the user provides a path to a phase spec, implement it following these critical requirements: 

CRITICAL REQUIREMENTS:

1. AGENT SELECTION & COORDINATION
- Recruit AT LEAST 2 sub-agents: one primary implementer and one QA/reviewer
- Consider recruiting: backend-architect, qa, test-writer-fixer, or others based on the phase needs
- Agents must reach CONSENSUS that the implementation is complete and correct
- Healthy push-pull between agents is expected - disagreement leads to quality

2. SCOPE DISCIPLINE  
- Implement EXACTLY what's in the spec - no more, no less
- Do NOT add "nice to have" features or "while we're here" fixes
- Do NOT skip any requirements even if they seem minor
- If the spec is ambiguous, STOP and ask for clarification

3. ADHERENCE TO STANDARDS
- Follow ALL CLAUDE.md files (user-level, project-level, folder-level if exists)
- Respect ALL ADRs (Architecture Decision Records) 
- Maintain current architecture patterns - don't introduce new patterns
- Use existing conventions for naming, structure, and style

4. KNOWLEDGE OVER GUESSWORK
- When uncertain, use Context7 or Perplexity to research current best practices
- Do NOT guess at implementation details
- Do NOT use outdated patterns from training data
- Research actual Weaviate APIs, actual Python patterns, actual CLI conventions

5. CONTEXT PRESERVATION
- You should COORDINATE, not implement directly
- Let sub-agents do the work while you maintain oversight
- This preserves your context for longer, more valuable coordination
- Use parallel agent execution when possible

6. TESTING & VERIFICATION
- Implementation agent and QA agent must BOTH verify success criteria
- Run actual commands from the spec's Testing section
- Achieve consensus through actual testing, not theoretical agreement

7. REPORTING
- Focus on WHAT REMAINS UNSOLVED, not what was completed
- Document blockers and uncertainties discovered during implementation  
- If something couldn't be implemented, explain WHY and what's needed
- Success is assumed - report the exceptions and gaps

WORKFLOW:
1. Read and understand the phase spec completely
2. Recruit appropriate sub-agents based on the work required
3. Have implementation agent execute while QA agent reviews
4. Iterate until both agents agree requirements are met
5. Run all tests specified in the phase
6. Report what couldn't be done and why

Remember: The goal is not speed but correctness. Two agents in healthy tension produce better results than one agent working alone.
```

## Example Usage

```
User: Implement the phase spec at /opt/elysiactl/docs/specs/cluster-verification/phases-pending/phase-1-fix-config-replication.md using appropriate sub-agents for coordination and quality assurance.