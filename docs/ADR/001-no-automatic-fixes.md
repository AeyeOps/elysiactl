# ADR-001: No Automatic Fixes in Cluster Verification

## Status
Accepted

## Context

The initial cluster verification specification included a `--fix` flag that would automatically attempt to repair detected issues in Weaviate clusters. This seemed beneficial for automation and reducing manual intervention.

However, during architectural review, several concerns emerged:

1. **Complexity of Repairs**: Cluster issues often require context-specific decisions that simple automation cannot handle safely
2. **Data Integrity Risks**: Automatic fixes could corrupt data or make situations worse without proper safeguards
3. **Hidden Failures**: Users might rely on fixes without understanding the underlying problems
4. **Maintenance Burden**: Fix logic requires extensive testing and edge case handling
5. **User Control**: System administrators need visibility and control over infrastructure changes

The principle of "explicit over magic" suggests that diagnostic tools should inform rather than act.

## Decision

ElysiaCtl will NOT implement automatic repair functionality. Instead:

1. **Detection Only**: The `--cluster` flag will identify and report issues clearly
2. **Actionable Guidance**: Error messages will include specific remediation steps
3. **Manual Commands**: Separate commands may be provided for common repair operations
4. **Documentation**: Comprehensive troubleshooting guides will be maintained

## Implementation

### Removed from Specification:
- `--fix` command line flag
- `RepairResult` and `RepairAttempt` data classes  
- `attempt_repair()` method in `ClusterVerifier`
- Safety measures and rollback functionality
- All repair-related testing requirements

### Retained Functionality:
- Complete cluster topology verification
- Replication factor validation
- Data consistency checking
- Clear issue reporting with severity levels
- JSON output for automation integration

## Consequences

### Positive:
- **Reduced Complexity**: Simpler codebase focused on reliable detection
- **Increased Safety**: No risk of automated changes making problems worse
- **Better User Understanding**: Forces administrators to understand issues before acting
- **Faster Development**: Focus on detection quality rather than repair edge cases
- **Clear Responsibility**: Users remain in control of their infrastructure changes

### Negative:
- **Manual Intervention Required**: Users must execute repair steps manually
- **Slower Issue Resolution**: No one-command fixes for common problems
- **Repeated Work**: Similar issues require similar manual steps each time

### Mitigation Strategies:
- Provide exact commands in error messages where possible
- Create separate, focused commands for common operations (e.g., `elysiactl cluster recreate-collection`)
- Maintain comprehensive documentation with copy-paste solutions
- Consider future workflow automation tools that chain manual commands

## Related

This decision aligns with ElysiaCtl's philosophy of explicit control over service management operations. Future ADRs may revisit this decision if:

1. Significant user feedback indicates the burden outweighs the safety benefits
2. Safer repair mechanisms are identified (e.g., staging environments, atomic operations)
3. Comprehensive testing frameworks prove repair reliability

## Examples of Retained Guidance

Instead of `--fix`, the tool provides actionable messages:

```bash
$ uv run elysiactl health --cluster
ISSUES FOUND: ELYSIA_METADATA__ not replicated

Recommended action:
1. Backup collection: elysiactl backup ELYSIA_METADATA__
2. Recreate with replication:
   curl -X DELETE http://localhost:8080/v1/schema/ELYSIA_METADATA__
   curl -X POST http://localhost:8080/v1/schema -d '{"class": "ELYSIA_METADATA__", "replicationConfig": {"factor": 3}}'
3. Restore data: elysiactl restore ELYSIA_METADATA__
```

This approach maintains user control while providing specific guidance for resolution.