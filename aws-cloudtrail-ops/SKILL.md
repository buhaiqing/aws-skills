---
name: aws-cloudtrail-ops
description: >-
  Use when managing CloudTrail audit trails, querying AWS API events, or investigating "who did what when". Invoke when user mentions "CloudTrail", "audit trail", or needs event history and logging analysis.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access to CloudTrail endpoints.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-06-27"
  runtime: Harness AI Agent
  type: base
  provides:
  - lookup-events
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  cross_skill_deps:
    - aws-s3-ops              # S3 bucket for trail logs
    - aws-kms-ops           # KMS key for trail encryption
    - aws-cloudwatch-ops    # CloudWatch Logs integration
    - aws-iam-ops           # IAM roles for CloudTrail access
  gcl:
    enabled: true
    class: optional
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['rca', 'change-impact', 'forensic']
    produces_facts: ['event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS CloudTrail Operations Skill

Use for CloudTrail trails, logging, event/insight selectors, event lookup, status, organization trails, S3/CloudWatch destinations, auditing, and forensic RCA. Detailed commands remain in references.

## Common JSON Paths

Trails: .trailList[].{Name,TrailARN,S3BucketName,IsMultiRegionTrail,IsOrganizationTrail,LogFileValidationEnabled}
Status: .{IsLogging,LatestDeliveryTime,LatestDeliveryError,LatestCloudWatchLogsDeliveryTime}
Events: .Events[].{EventId,EventName,EventTime,Username,Resources,CloudTrailEvent}
Selectors: .EventSelectors[]

## Trigger & Scope

### SHOULD Use When
CloudTrail trails/logging, event selectors, insights, event lookup, organization audit, delivery status, or forensic investigation.

### SHOULD NOT Use When
CloudWatch metrics/log groups → `aws-cloudwatch-ops`; S3 bucket lifecycle → `aws-s3-ops`; Security Hub/GuardDuty → respective skills.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.TrailName}}`, `{{user.TrailArn}}`, `{{user.region}}` | User input | Trail identity |
| `{{user.event_selectors}}`, `{{user.lookup_attributes}}` | User input | Audit filters |
| `{{output.*}}` | API response | Reuse trail/status/event IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Verify STS identity, trail scope, organization/multi-region status, S3/KMS/CloudWatch destinations, current logging, selectors, validation, and delivery errors. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back trail/status and test delivery; recover with bounded retries and halt on access, destination, or ambiguous trail identity. See references for commands.

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/update trail | Validate destinations, policy, KMS, org/multi-region scope | Token for audit coverage reduction |
| Start logging | Validate delivery and status | — |
| Stop logging | Display audit gap, scope, compliance impact and duration | `STOP_LOGGING <trail>` |
| Delete trail | Verify exact trail and destinations; show permanent audit loss | `DELETE_TRAIL <name>` |
| Put event/insight selectors | Diff included/excluded event sources and coverage | Human confirmation for reduced coverage |
| Lookup events | Read-only; mask CloudTrailEvent secrets/personal data | — |

AUTO_HEAL may restore logging/delivery, never stop or delete a trail or reduce selectors.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live trail/delivery state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for stop/delete/coverage reduction; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits restore-only audit actions; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

