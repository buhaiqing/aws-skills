# Progress

## Status
Completed

## Tasks
- [x] Read current aws-config-ops/references/rubric.md (2.2 KB, simplified)
- [x] Reference aws-ec2-ops/references/rubric.md (4.7 KB) for structure
- [x] Reference aws-s3-ops/references/rubric.md (8.1 KB) for comprehensive examples
- [x] Reference gcl-spec.md for AWS rules A1-A10
- [x] Read SKILL.md and aws-cli-usage.md for Config operations
- [x] Expand rubric with detailed dimension descriptions
- [x] Add Config-specific operation overrides (15+ operations)
- [x] Add Config-specific Safety special cases (17 auto-fail rules)
- [x] Reference AWS rules A1-A10 from gcl-spec.md with Config-specific notes

## Files Changed
- `/Users/bohaiqing/opensource/git/aws-skills/aws-config-ops/references/rubric.md` (expanded from ~2.2 KB to ~10.2 KB)

## Notes
The expanded rubric now matches the depth of aws-ec2-ops and aws-s3-ops rubrics with:

**Detailed dimension descriptions** covering:
- Config rule name, recorder name, delivery channel name, conformance pack name, aggregator name verification
- Read-back via describe-* operations with JSON path validation
- Service-linked role, S3 bucket, SNS topic, IAM permission compliance

**Comprehensive operation-specific overrides (15+ operations)**:
- `put-configuration-recorder` (Create/Update) — role verification
- `put-delivery-channel` (Create/Update) — S3 bucket pre-flight
- `start-configuration-recorder` / `stop-configuration-recorder` — state management
- `delete-configuration-recorder` / `delete-delivery-channel` — destructive guards
- `put-config-rule` (Managed & Custom rules) — validation differences
- `delete-config-rule` — conformance pack dependency check
- `put-conformance-pack` / `delete-conformance-pack` — template validation
- `put-configuration-aggregator` / `delete-configuration-aggregator` — multi-account guards
- `put-organization-config-rule` / `delete-organization-config-rule` — org-level impact
- `put-retention-configuration` / `delete-retention-configuration` — data lifecycle
- `delete-aggregation-authorization` — cross-account break

**Config-specific Safety special cases (17 auto-fail rules)**:
- Recorder deletion while actively recording (must stop first)
- Delivery channel deletion when only channel exists
- Rule deletion when part of conformance pack
- Short retention period (<30 days) without explicit confirmation
- Non-existent S3 bucket for delivery channel
- Invalid/missing IAM role ARN for recorder
- Non-existent Lambda ARN for custom rules
- Missing `confirm=` patterns for all destructive ops

**A1-A10 rule reference table** with Config-specific applicability notes.

**Changelog** tracking v1.0.0 expansion date and scope.
