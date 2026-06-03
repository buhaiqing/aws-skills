---
name: aws-dynamodb-ops
description: Use when managing DynamoDB tables, items, indexes, or capacity modes.
  Invoke when user mentions "DynamoDB", "NoSQL", or needs table/query operations,
  backups, or TTL configuration.
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network
  access to DynamoDB endpoints.
metadata:
  author: aws
  version: 1.1.0
  last_updated: '2026-06-04'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_DEFAULT_REGION
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
---
# AWS DynamoDB Ops Skill

## Common JSON Paths (Centralized)

```
# Create Table:      .TableDescription.{TableName,TableStatus,TableArn}
# Describe Table:    .Table.{TableStatus,KeySchema,ItemCount,TableSizeBytes,BillingModeSummary}
# List Tables:       .TableNames[]
# Update Table:      .TableDescription.TableStatus
# Get Item:          .Item
# Put Item:          Empty (success, or .Attributes if ReturnValues)
# Query/Scan:        .{Items[],Count,ScannedCount,LastEvaluatedKey}
# Create Backup:     .BackupDetails.{BackupStatus,BackupArn}
# Create GSI:        .TableDescription.GlobalSecondaryIndexes
```

## Trigger & Scope

### SHOULD Use When
- User requests DynamoDB table creation, modification, or deletion
- User asks about DynamoDB items, queries, or scans
- User needs to configure Global Secondary Index (GSI) or Local Secondary Index (LSI)
- User mentions "DynamoDB", "NoSQL database", "key-value store", "DAX"
- User needs backup/restore or point-in-time recovery operations
- User asks about provisioned capacity (RCU/WCU) or on-demand mode

### SHOULD NOT Use When
- RDS relational database operations → delegate to: `aws-rds-ops`
- ElastiCache Redis/Memcached operations → delegate to: `aws-elasticache-ops`
- DocumentDB / Neptune operations

### Delegation
- Lambda triggers → `aws-lambda-ops` (DynamoDB Streams integration)
- CloudWatch alarms → `aws-cloudwatch-ops` (monitoring setup)
- IAM roles → `aws-iam-ops` (role creation for DynamoDB access)
- KMS keys → `aws-kms-ops` (encryption key setup)
- S3 export/import → `aws-s3-ops` (data export to S3)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.TableName}}` | User input | Ask once; reuse |
| `{{user.PrimaryKey}}` | User input | Partition key name |
| `{{user.SortKey}}` | User input | Sort key name (optional) |
| `{{user.RCU}}` | User input | Read Capacity Units |
| `{{user.WCU}}` | User input | Write Capacity Units |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify table name uniqueness, check quotas.

**CLI (primary)**: `aws dynamodb [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Poll `describe-table` until TableStatus=ACTIVE (create, max 10 min) or DELETING (delete, max 5 min). Use `wait table-exists` / `wait table-not-exists`.

**Common Recovery**:
| Error | Action |
|-------|--------|
| TableAlreadyExists | HALT — provide existing table info |
| LimitExceededException | HALT — wait or reduce capacity |
| ProvisionedThroughputExceededException | Backoff, retry with exponential backoff |
| ResourceNotFoundException | HALT — table does not exist |
| ValidationException | Fix args; retry once |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Safety Gates

### Table Deletion (Critical)
```
⚠️ Deleting {{user.TableName}} will permanently remove all data and indexes.
Confirm no Lambda triggers, no Streams consumers.
Confirm: Type DELETE {{user.TableName}} to proceed.
```

### GSI Deletion
```
⚠️ GSI {{user.IndexName}} will be permanently deleted.
Confirm: Type DELETE GSI {{user.IndexName}} to proceed.
```

## Related Skills

- `aws-lambda-ops` — Lambda triggers for DynamoDB Streams
- `aws-cloudwatch-ops` — DynamoDB metrics and alarms
- `aws-iam-ops` — IAM roles for DynamoDB access
- `aws-kms-ops` — Encryption key management
- `aws-s3-ops` — Export/import DynamoDB data

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)
## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-dynamodb-ops` MUST be wrapped by the Generator-Critic-Loop defined
> in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-table` — **IRREVERSIBLE**; pre-flight: `describe-table`
  (state must be `ACTIVE`) + `list-event-source-mappings` (Streams
  consumers must be empty) + GSIs/LSIs must be removed first
- `update-table` with `GlobalSecondaryIndexUpdates: REMOVE` —
  `confirm=DELETE_GSI <table>:<index>`
- `update-time-to-live` enable — `confirm=ENABLE_TTL <table>:<attr>`;
  irreversible effect within 48 h
- `delete-backup` / `delete-replication-group-member` (Global Tables)
- `delete-item` on "core" entities
- `transact-write-items` with `Delete` on "core" entities

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource
echo-back), A9 (no item values in trace; no literal secrets in
secret-named attributes; SSM / Secrets Manager ARN only), A10 (sts
first command).

See `references/rubric.md` for the 5-dimension rubric and `references/prompt-templates.md` for G/C/O skeletons.
