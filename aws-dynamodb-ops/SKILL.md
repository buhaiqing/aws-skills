---
name: aws-dynamodb-ops
description: >-
  Use when managing DynamoDB tables, items, indexes, or capacity modes.
  Invoke when user mentions "DynamoDB", "NoSQL database", "key-value store",
  "partition key", "sort key", "GSI", "LSI", "TTL", "DAX", or needs
  table/query/scan operations, backups, point-in-time recovery, TTL
  configuration, capacity mode switch (on-demand vs provisioned), or
  Global Tables replication. Also when user says "create a DynamoDB table",
  "query by partition key", "enable time-to-live", "switch to on-demand",
  "set up global secondary index", or "export DynamoDB data to S3".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to DynamoDB endpoints.
metadata:
  author: aws
  version: "1.3.0"
  last_updated: "2026-06-27"
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
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  cross_skill_deps:
    - aws-lambda-ops           # DynamoDB Streams integration
    - aws-cloudwatch-ops       # DynamoDB metrics & alarms
    - aws-iam-ops             # IAM roles for DynamoDB access
    - aws-kms-ops             # Encryption key management
    - aws-s3-ops              # Export/import DynamoDB data to S3
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS DynamoDB Operations Skill

Use for DynamoDB tables, items, indexes, streams, TTL, backups/PITR, Global Tables, capacity, transactions, and performance diagnostics. Detailed commands remain in references.

## Common JSON Paths

Table: .Table.{TableName,TableStatus,TableArn,ItemCount,KeySchema,GlobalSecondaryIndexes,LocalSecondaryIndexes}
Items: .Items[]
Backups: .BackupSummaries[].{BackupArn,BackupName,BackupStatus,BackupCreationDateTime}
TTL: .TimeToLiveDescription.{TimeToLiveStatus,AttributeName}

## Trigger & Scope

### SHOULD Use When
DynamoDB tables/items, indexes, TTL, backups, streams, Global Tables, capacity, transactions, or diagnostics.

### SHOULD NOT Use When
RDS → `aws-rds-ops`; Lambda function CRUD → `aws-lambda-ops`; KMS key lifecycle → `aws-kms-ops`; IAM → `aws-iam-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.TableName}}`, `{{user.IndexName}}`, `{{user.TTLAttributeName}}` | User input | Table/index/TTL identity |
| `{{user.key}}`, `{{user.item}}`, `{{user.backup_arn}}` | User input | Item/backup payload |
| `{{output.*}}` | API response | Reuse table/index/backup state |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Verify table ACTIVE, keys/schema, indexes, streams/Lambda mappings, backups/PITR, replica regions, TTL, capacity, and exact item scope. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll table/index/backup state; recover with bounded retries and halt on resource-in-use, quota, or ambiguous keys. See references for commands.

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/update table/capacity | Validate schema/index/capacity and live traffic | Token for production billing/index changes |
| Delete table | Describe ACTIVE; inspect GSIs/LSIs, backups, streams and Lambda mappings | `DELETE_TABLE <table>`; with mappings use `DELETE_TABLE_WITH_TRIGGERS <table>` |
| Delete GSI | Show index consumers and irreversibility | `DELETE_GSI <table>:<index>` |
| Enable TTL | Preview items where attr≤now; backup/PITR required | `ENABLE_TTL <table>:<attr>` |
| Delete backup/replica | Show recovery/region impact | `DELETE_BACKUP <arn>` / `DELETE_REPLICA <table>:<region>` |
| Delete item/transaction | Echo exact table/key/count; no wildcard or ambiguous keys | `DELETE_ITEM` / `DELETE_TRANSACT <table>:<pk>` |

Mask all item values in traces (`***<len>`); secret/password/token/api_key literals cause Safety=0.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live table/index state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for data/index/table actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits bounded non-destructive capacity tuning; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
