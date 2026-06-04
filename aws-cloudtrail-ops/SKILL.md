---
name: aws-cloudtrail-ops
description: >-
  Use when managing CloudTrail audit trails, querying AWS API events, or investigating "who did what when". Invoke when user mentions "CloudTrail", "audit trail", or needs event history and logging analysis.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access to CloudTrail endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-15"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  gcl:
    enabled: true
    class: optional
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
---
# AWS CloudTrail Ops Skill

## Common JSON Paths (Centralized)

```
# Create Trail:      .Trail.{TrailARN,Name,S3BucketName}
# Describe Trails:   .trailList[].{Name,TrailARN,S3BucketName,IsMultiRegionTrail,HomeRegion}
# Get Trail Status:  .{IsLogging,LatestDeliveryTime,LatestDeliveryError}
# Lookup Events:     .Events[].{EventId,EventTime,EventSource,EventName,Username}
# Get Event Sel:     .EventSelectors[].{ReadWriteType,IncludeManagementEvents}
# Get Insight Sel:   .InsightSelectors[].InsightType
```

## Trigger & Scope

### SHOULD Use When
- User requests CloudTrail trail creation, modification, or deletion
- User asks to query events with `lookup-events`
- User needs to enable/disable trail logging
- User mentions "CloudTrail", "audit trail", "API logging", "event history"
- User needs to troubleshoot "who did what when" in AWS
- User asks about CloudTrail Insights or anomaly detection
- User needs multi-region or organization trail setup

### SHOULD NOT Use When
- General monitoring/alarms → delegate to: `aws-cloudwatch-ops`
- S3 bucket operations → delegate to: `aws-s3-ops`
- IAM operations → delegate to: `aws-iam-ops`
- Log analysis → delegate to: `aws-cloudwatch-ops`

### Delegation
- S3 bucket → `aws-s3-ops` (trail logging bucket)
- KMS key → `aws-kms-ops` (trail encryption)
- CloudWatch Logs → `aws-cloudwatch-ops` (CloudWatch integration)
- IAM → `aws-iam-ops` (trail role permissions)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.TrailName}}` | User input | Ask once; reuse |
| `{{user.S3BucketName}}` | User input | my-cloudtrail-logs |
| `{{user.S3KeyPrefix}}` | User input | audit/ |
| `{{user.KmsKeyId}}` | User input | alias/cloudtrail |
| `{{user.StartTime}}` | User input | ISO 8601 timestamp |
| `{{user.EndTime}}` | User input | ISO 8601 timestamp |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify S3 bucket exists, check bucket policy allows CloudTrail writes.

**CLI (primary)**: `aws cloudtrail [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `get-trail-status` to confirm IsLogging=true (max wait 5 min). Use `describe-trails` for config verification.

**Common Recovery**:
| Error | Action |
|-------|--------|
| TrailAlreadyExists | HALT — provide existing trail info |
| TrailNotFound | HALT — verify trail name |
| InsufficientS3BucketPolicy | FIX — update bucket policy for CloudTrail |
| InvalidCloudWatchLogsLogGroup | FIX — verify log group exists |
| KMSKeyNotFound | FIX — verify KMS key exists |
| S3BucketNotFound | FIX — create bucket first |
| Throttling | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Safety Gates

### Trail Deletion (Critical)
```
⚠️ Deleting {{user.TrailName}} will stop all audit logging.
Confirm: Type DELETE {{user.TrailName}} to proceed.
```

### Stop Logging
```
⚠️ Logging will stop. No events will be recorded until restarted.
Continue? (yes/no)
```

## Related Skills

- `aws-s3-ops` — S3 bucket for trail logs
- `aws-kms-ops` — KMS key for trail encryption
- `aws-iam-ops` — IAM roles for CloudTrail access
- `aws-cloudwatch-ops` — CloudWatch Logs integration

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, optional). Every execution of
> `aws-cloudtrail-ops` MUST be wrapped by the Generator-Critic-Loop
> defined in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `optional` |
| `max_iterations` | `3` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-trail` — SEVERE; stops ALL audit logging; all event history lost; confirm `DELETE_TRAIL <name>`
- `stop-logging` — audit gap from stop to restart; confirm with user
- `update-trail` — changing S3 bucket or KMS key could affect log delivery; confirm

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (TrailName echoed from `describe-trails`), A9 (event data secrets masked), A10 (sts first command).

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric
- `references/prompt-templates.md` — G/C/O skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)