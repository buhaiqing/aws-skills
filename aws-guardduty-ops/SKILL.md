---
name: aws-guardduty-ops
description: >-
  Use when operating AWS GuardDuty detectors, findings, filters, IP sets,
  threat intel sets, member accounts, or publishing destinations. Covers
  detector lifecycle, finding archive/unarchive, filter and threat list
  management, master/member administration, and S3/KMS publishing setup.
  Keywords: GuardDuty, threat detection, security findings, detector,
  IP set, threat intel, security account, publishing destination.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to GuardDuty endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-06-08"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'compliance-scan']
    produces_facts: ['finding']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

## Common JSON Paths (Centralized)

```
# Detectors:       .DetectorIds[]
# Detector Details:.Status, .ServiceRole, .FindingPublishingFrequency, .DataSources
# Findings:        .FindingIds[]
# Finding Details: .Severity, .Type, .Title, .Description, .Resource, .Service
# IP Sets:         .IpSetIds[]
# IP Set Details:  .Name, .Format, .Location, .Status
# Threat Intel:    .ThreatIntelSetIds[]
# TI Set Details:  .Name, .Format, .Location, .Status
# Members:         .Members[].{AccountId,DetectorId,MasterId,RelationshipStatus}
# Filters:         .FilterNames[]
# Destinations:    .Destinations[].{DestinationId,DestinationType,DestinationProperties}
```

AWS GuardDuty operational skill for AI Agent automation.

## Trigger & Scope

### SHOULD Use When
- User mentions "GuardDuty", "threat detector", "security findings"
- Detector create, enable, disable, update, or delete
- Finding list, filter, archive, or unarchive
- IP set or threat intel set management
- Member account invitation/association (master account)
- Publishing destination (S3/KMS) configuration
- Keywords: guardduty, detector, finding, threat, ipset, intelset, archive

### SHOULD NOT Use When
- IAM policies → delegate to: `aws-iam-ops`
- KMS encryption keys → delegate to: `aws-kms-ops`
- S3 bucket for publishing destination → delegate to: `aws-s3-ops`
- EventBridge automated response → delegate to: `aws-eventbridge-ops`
- Security Hub integration → delegate to `aws-securityhub-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER log (rule A9) |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.detector_id}}` | User input | Ask once; reuse |
| `{{user.finding_ids}}` | User input | Comma-separated; ask once |
| `{{user.filter_name}}` | User input | Ask once; reuse |
| `{{user.ip_set_id}}` | User input | Ask once; reuse |
| `{{user.threat_intel_set_id}}` | User input | Ask once; reuse |
| `{{user.destination_id}}` | User input | Ask once; reuse |
| `{{output.DetectorId}}` | Last API response | Parse: `.DetectorId` |

## Execution Flow

### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] Region={{env.AWS_DEFAULT_REGION}} Credential verified.`
On failure: `[FAIL] AWS credential verification failed. Action: Check .env`
```bash
aws guardduty list-detectors --region {{env.AWS_DEFAULT_REGION}} --output json
```
Log: `[OK] GuardDuty accessible in {{env.AWS_DEFAULT_REGION}}`

### Execute (Primary: CLI)
See [references/aws-cli-usage.md](references/aws-cli-usage.md) for full command reference.

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

### Validate
1. Poll: `aws guardduty get-detector --detector-id {{user.detector_id}}`
2. Verify state matches intent (`Status=ENABLED|DISABLED`)
3. For findings: `aws guardduty list-findings` to confirm archive/unarchive

### Recover
| Error Type | Action |
|------------|--------|
| BadRequestException | HALT — fix params |
| AccessDeniedException | HALT — check IAM permissions |
| Throttling (429) | Exponential backoff, max 3 retries |
| 5xx Internal | Retry 3x; HALT |

## Safety Gates

### Detector Deletion
```
BEFORE delete-detector:
1. Display: "Deleting detector {{user.detector_id}} will stop all threat monitoring"
2. Ask: "Type 'DELETE_DETECTOR {{user.detector_id}}' to confirm"
```

### Filter Deletion
```
BEFORE delete-filter:
1. Display: "Deleting filter {{user.filter_name}}"
2. Ask: "Type 'DELETE_FILTER {{user.filter_name}}' to confirm"
```

### IP Set / Threat Intel Set Deletion
```
BEFORE delete-ip-set / delete-threat-intel-set:
1. Display: "Deleting set will remove threat intelligence source"
2. Ask: "Type 'DELETE_IP_SET {{user.ip_set_id}}' or 'DELETE_THREAT_INTEL_SET {{user.threat_intel_set_id}}' to confirm"
```

### Finding Archive
```
BEFORE archive-findings:
1. Display: "Archiving findings will hide them from default views"
2. Ask: "Type 'ARCHIVE_FINDINGS {{user.finding_ids}}' to confirm"
```

### Publishing Destination Deletion
```
BEFORE delete-publishing-destination:
1. Display: "Deleting destination will stop finding exports"
2. Ask: "Type 'DELETE_PUBLISHING_DESTINATION {{user.destination_id}}' to confirm"
```

## Output Convention
All commands use `--output json`. Key JSON paths:
- `.DetectorIds[0]` (list-detectors)
- `.Status` (get-detector)
- `.FindingIds[]` (list-findings)
- `.IpSetIds[]` (list-ip-sets)
- `.ThreatIntelSetIds[]` (list-threat-intel-sets)

## Related Skills
- `aws-iam-ops` — IAM roles/policies | `aws-kms-ops` — Encryption keys
- `aws-s3-ops` — Publishing destination bucket | `aws-eventbridge-ops` — Automated response

## Cross-Skill Orchestration
| Scenario | Chain |
|----------|-------|
| GuardDuty → EventBridge alert | guardduty → eventbridge (finding notification) |
| GuardDuty → S3 export | guardduty → s3 (publishing destination) |
| GuardDuty → IAM remediation | guardduty → iam (compromised credential response) |

## Reference Files
- `references/aws-cli-usage.md` — CLI command reference
- `references/boto3-sdk-usage.md` — Python SDK patterns
- `references/core-concepts.md` — GuardDuty architecture, quotas
- `references/troubleshooting.md` — Error codes, recovery procedures
- `references/rubric.md` — GCL 5-dimension rubric
- `references/prompt-templates.md` — G/C/O prompt skeletons
- `assets/example-config.yaml` — Configuration examples

## Quality Gate (GCL)

> Every execution of `aws-guardduty-ops` MUST be wrapped by the
> Generator-Critic-Loop defined in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace
(exact format `confirm=<OPERATION> <resource>`):

- `delete-detector` — `confirm=DELETE_DETECTOR {{user.detector_id}}`
- `delete-filter` — `confirm=DELETE_FILTER {{user.filter_name}}`
- `delete-ip-set` — `confirm=DELETE_IP_SET {{user.ip_set_id}}`
- `delete-threat-intel-set` — `confirm=DELETE_THREAT_INTEL_SET {{user.threat_intel_set_id}}`
- `archive-findings` — `confirm=ARCHIVE_FINDINGS {{user.finding_ids}}`
- `delete-publishing-destination` — `confirm=DELETE_PUBLISHING_DESTINATION {{user.destination_id}}`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource echo-back),
A9 (no secrets in trace), A10 (sts first command).

## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse and return
   `aiops_context.status: "failed"` with summary
   `"confirmation_token required for destructive op"`.
3. **Decision tier respect**:
   - `decision_tier: MANUAL` — never execute writes; recommendations only.
   - `decision_tier: AI_ASSIST` — recommendations; execute only if
     `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` — execute non-destructive writes
     directly; destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` JSON
   block in the response, even on failure.

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.

