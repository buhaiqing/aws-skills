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
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS DynamoDB Operations Skill

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

## Overview

Amazon DynamoDB is a fully managed NoSQL database service. This skill is an
**operational runbook** with explicit scope, credential rules, pre-flight checks,
dual-path execution (AWS CLI + boto3 SDK), validation, and recovery.

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
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile (SSO / AssumeRole); overrides explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.TableName}}` | User input | Ask once; reuse |
| `{{user.PrimaryKey}}` | User input | Partition key name |
| `{{user.SortKey}}` | User input | Sort key name (optional) |
| `{{user.RCU}}` | User input | Read Capacity Units |
| `{{user.WCU}}` | User input | Write Capacity Units |
| `{{user.IndexName}}` | User input | GSI/L SI name |
| `{{user.TTLAttributeName}}` | User input | TTL attribute name; must be `Number` type |
| `{{output.TableArn}}` | API response | Parse: `.Table.TableArn` after Create/Describe |
| `{{output.TableStatus}}` | API response | Parse: `.Table.TableStatus`; must be `ACTIVE` before write ops |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{env.AWS_ACCOUNT_ID}}` | `.env` or runtime env | Substitute before use |
| `{{user.TableName}}` | User input | Ask once; substitute |
| `{{user.PrimaryKey}}` | User input | Ask once; substitute |

Before using `example-config.yaml`:
1. Load `.env` from project root (if present)
2. Substitute `{{env.*}}` placeholders with loaded values
3. Collect `{{user.*}}` values from user input
4. Use rendered config for CLI/SDK commands

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Common Pre-flight Steps (all ops)

#### Step 1: Check CLI
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: pip install awscli`

#### Step 2: Load & Verify Credentials
```bash
aws sts get-caller-identity --output json
```
Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from env)
[OK]   AWS_ACCESS_KEY_ID=**** (masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```
On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/troubleshooting.md for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide to troubleshooting.md |
| Region valid | `aws dynamodb list-tables --region {{user.region}}` | Suggest valid region |
| Quota | `aws dynamodb describe-limits` | HALT; request increase |

## Safety Gates

| Operation | Gate | Confirm Token |
|-----------|------|---------------|
| `delete-table` | Table deletion is IRREVERSIBLE; pre-flight: `describe-table` (ACTIVE), `list-event-source-mappings` (Lambda consumers empty), GSIs/LSIs deleted first | `confirm=DELETE_TABLE <table-name>` |
| `update-table` (GSI REMOVE) | GSI deletion is IRREVERSIBLE | `confirm=DELETE_GSI <table>:<index>` |
| `update-time-to-live` (enable) | Items with `attr <= now` deleted within 48 h; irreversible without backup | `confirm=ENABLE_TTL <table>:<attr>` |
| `delete-backup` | Point-in-time recovery target destroyed | `confirm=DELETE_BACKUP <arn>` |
| `delete-replication-group-member` | Removes region from Global Table | `confirm=DELETE_REPLICA <table>:<region>` |
| `delete-item` (core entity) | Single-item data loss | `confirm=DELETE_ITEM <table>:<pk>` |
| `transact-write-items` (Delete) | Transactional delete | `confirm=DELETE_TRANSACT <table>:<pk>` |

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

### Operation: Create Table

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Table name unique | `aws dynamodb list-tables` | Suggest unique name |
| Quota not exceeded | `aws dynamodb describe-limits` | HALT; request increase |

#### Execute — CLI (Primary)
```bash
# Provisioned
aws dynamodb create-table \
  --table-name "{{user.TableName}}" \
  --attribute-definitions AttributeName={{user.PrimaryKey}},AttributeType=S \
  --key-schema AttributeName={{user.PrimaryKey}},KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits={{user.RCU:5}},WriteCapacityUnits={{user.WCU:5}} \
  --region "{{user.region}}" --output json

# On-demand
aws dynamodb create-table \
  --table-name "{{user.TableName}}" \
  --attribute-definitions AttributeName={{user.PrimaryKey}},AttributeType=S \
  --key-schema AttributeName={{user.PrimaryKey}},KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.create_table(
    TableName='{{user.TableName}}',
    AttributeDefinitions=[{'AttributeName': '{{user.PrimaryKey}}', 'AttributeType': 'S'}],
    KeySchema=[{'AttributeName': '{{user.PrimaryKey}}', 'KeyType': 'HASH'}],
    BillingMode='PAY_PER_REQUEST'
)
```

#### Validate
Poll until `ACTIVE` (max 600s, interval 10s):
```bash
for i in $(seq 1 60); do
  STATUS=$(aws dynamodb describe-table --table-name "{{user.TableName}}" \
    --region "{{user.region}}" --output json | jq -r '.Table.TableStatus')
  [ "$STATUS" = "ACTIVE" ] && break
  sleep 10
done
```

#### Recover
| Error | Action |
|-------|--------|
| TableAlreadyExists | HALT — provide existing table info |
| LimitExceededException | HALT; request quota increase |
| ThrottlingException | Backoff; retry 3x |

### Operation: Describe Table

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Table exists | `aws dynamodb describe-table --table-name {{user.TableName}}` | HALT — table does not exist |

#### Execute — CLI (Primary)
```bash
aws dynamodb describe-table --table-name "{{user.TableName}}" \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.describe_table(TableName='{{user.TableName}}')
table = response['Table']
print(f"{table['TableName']}: {table['TableStatus']} ({table.get('BillingModeSummary',{}).get('BillingMode','PROVISIONED')})")
```

#### Validate
Verify response contains the requested table.

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | HALT — verify table name and region |
| ThrottlingException | Backoff; retry 3x |

### Operation: Delete Table (Destructive)

#### Safety Gate (Mandatory)
> "Delete {{user.TableName}}? This action is **IRREVERSIBLE** — all data, indexes, and backups will be permanently lost. Confirm: type `DELETE_TABLE {{user.TableName}}`."

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Table exists and ACTIVE | `aws dynamodb describe-table` | HALT — table must be ACTIVE |
| No Lambda consumers | `aws lambda list-event-source-mappings --query "EventSourceMappings[?contains(DynamodbTableArn,'{{user.TableName}}')]"` (must be empty) | HALT — require `confirm=DELETE_TABLE_WITH_TRIGGERS {{user.TableName}}` |
| Capture item count + size | `aws dynamodb describe-table --query "{ItemCount,TableSizeBytes}"` | Log for traceability |

#### Execute — CLI (Primary)
```bash
aws dynamodb delete-table --table-name "{{user.TableName}}" \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.delete_table(TableName='{{user.TableName}}')
print(f"Deleting: {response['TableDescription']['TableName']}")
```

#### Validate
Poll until `table-not-exists` (max 300s, interval 5s):
```bash
for i in $(seq 1 60); do
  aws dynamodb wait table-not-exists --table-name "{{user.TableName}}" \
    --region "{{user.region}}" 2>/dev/null && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | Table already deleted; confirm |
| ThrottlingException | Backoff; retry 3x |

### Operation: Update Table (Capacity / Billing Mode)

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Table ACTIVE | `aws dynamodb describe-table` | HALT — table must be ACTIVE |
| New RCU/WCU within quota | `aws dynamodb describe-limits` | HALT; request increase |

#### Execute — CLI (Primary) — Switch to On-Demand
```bash
aws dynamodb update-table --table-name "{{user.TableName}}" \
  --billing-mode PAY_PER_REQUEST \
  --region "{{user.region}}" --output json
```

#### Execute — CLI (Primary) — Update Provisioned Throughput
```bash
aws dynamodb update-table --table-name "{{user.TableName}}" \
  --provisioned-throughput ReadCapacityUnits={{user.RCU}},WriteCapacityUnits={{user.WCU}} \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.update_table(
    TableName='{{user.TableName}}',
    ProvisionedThroughput={'ReadCapacityUnits': {{user.RCU:5}}, 'WriteCapacityUnits': {{user.WCU:5}}}
)
```

#### Validate
Poll until `ACTIVE`:
```bash
for i in $(seq 1 60); do
  STATUS=$(aws dynamodb describe-table --table-name "{{user.TableName}}" \
    --region "{{user.region}}" --output json | jq -r '.Table.TableStatus')
  [ "$STATUS" = "ACTIVE" ] && break
  sleep 10
done
```

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | HALT — table does not exist |
| LimitExceededException | HALT; request quota increase |
| ThrottlingException | Backoff; retry 3x |

### Operation: Query Table

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Table exists | `aws dynamodb describe-table` | HALT — table does not exist |

#### Execute — CLI (Primary)
```bash
aws dynamodb query \
  --table-name "{{user.TableName}}" \
  --key-condition-expression "{{user.PrimaryKey}} = :pk" \
  --expression-attribute-values '{":pk":{"S":"{{user.pk_value}}"}}' \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.query(
    TableName='{{user.TableName}}',
    KeyConditionExpression='{{user.PrimaryKey}} = :pk',
    ExpressionAttributeValues={':pk': {'S': '{{user.pk_value}}'}}
)
for item in response['Items']: print(item)
```

#### Validate
Verify response contains expected items.

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | HALT — verify table name |
| ValidationException | Fix key condition expression; retry once |
| ProvisionedThroughputExceededException | Backoff; retry 3x |

### Operation: Put Item / Get Item

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Table exists | `aws dynamodb describe-table` | HALT — table does not exist |

#### Execute — CLI (Primary) — Put Item
```bash
aws dynamodb put-item \
  --table-name "{{user.TableName}}" \
  --item '{"{{user.PrimaryKey}}":{"S":"{{user.pk_value}}"}}' \
  --region "{{user.region}}" --output json
```

#### Execute — CLI (Primary) — Get Item
```bash
aws dynamodb get-item \
  --table-name "{{user.TableName}}" \
  --key '{"{{user.PrimaryKey}}":{"S":"{{user.pk_value}}"}}' \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.get_item(TableName='{{user.TableName}}', Key={'{{user.PrimaryKey}}': {'S': '{{user.pk_value}}'}})
print(response.get('Item'))
```

#### Validate
Verify response (Item present for Get, empty for successful Put).

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | HALT — verify table name |
| ConditionalCheckFailedException | HALT — condition failed; item may already exist |
| ProvisionedThroughputExceededException | Backoff; retry 3x |

### Operation: Update Time-to-Live (TTL)

#### Safety Gate
> "Enable TTL on {{user.TableName}}.{{user.TTLAttributeName}}? Items with `{{user.TTLAttributeName}} <= now` will be deleted within 48 h. This is nearly irreversible without backup. Confirm: type `ENABLE_TTL {{user.TableName}}:{{user.TTLAttributeName}}`."

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Attribute is `Number` type | `aws dynamodb describe-table` (scan AttributeDefinitions) | HALT — TTL attribute must be `Number` |

#### Execute — CLI (Primary)
```bash
aws dynamodb update-time-to-live \
  --table-name "{{user.TableName}}" \
  --time-to-live-specification "{\"AttributeName\":\"{{user.TTLAttributeName}}\",\"Enabled\":true}" \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
client.update_time_to_live(
    TableName='{{user.TableName}}',
    TimeToLiveSpecification={'AttributeName': '{{user.TTLAttributeName}}', 'Enabled': True}
)
```

#### Validate
```bash
aws dynamodb describe-time-to-live --table-name "{{user.TableName}}" \
  --region "{{user.region}}" --output json | jq -r '.TimeToLiveSpecification'
```

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | HALT — verify table name |
| ValidationException | HALT — attribute not found or wrong type |

### Operation: Create GSI

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Table ACTIVE | `aws dynamodb describe-table` | HALT — table must be ACTIVE |
| Index name unique | `aws dynamodb describe-table --query GlobalSecondaryIndexes` | Suggest unique name |

#### Execute — CLI (Primary)
```bash
aws dynamodb update-table \
  --table-name "{{user.TableName}}" \
  --attribute-definitions AttributeName={{user.GSIKey}},AttributeType=S \
  --global-secondary-index-updates '[{"Create":{"IndexName":"{{user.GSIName}}","KeySchema":[{"AttributeName":"{{user.GSIKey}}","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}}]' \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.update_table(
    TableName='{{user.TableName}}',
    AttributeDefinitions=[{'AttributeName': '{{user.GSIKey}}', 'AttributeType': 'S'}],
    GlobalSecondaryIndexUpdates=[{
        'Create': {
            'IndexName': '{{user.GSIName}}',
            'KeySchema': [{'AttributeName': '{{user.GSIKey}}', 'KeyType': 'HASH'}],
            'Projection': {'ProjectionType': 'ALL'},
            'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        }
    }]
)
```

#### Validate
Poll until GSI `ACTIVE`:
```bash
for i in $(seq 1 60); do
  STATUS=$(aws dynamodb describe-table --table-name "{{user.TableName}}" \
    --region "{{user.region}}" --output json | \
    jq -r '.Table.GlobalSecondaryIndexes[] | select(.IndexName=="{{user.GSIName}}") | .IndexStatus')
  [ "$STATUS" = "ACTIVE" ] && break
  sleep 10
done
```

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | HALT — verify table name |
| LimitExceededException | HALT — max 20 GSIs per table |
| IndexAlreadyExistsException | HALT — choose unique index name |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)
- [Example Configuration](assets/example-config.yaml)
- [Prompt Examples](references/prompt-examples.md)

## Token Efficiency Guidelines (P0)

The following 6 rules minimize Token consumption:

### TE-1: API Query > Static Tables
Use API commands instead of hardcoding capacity mode or quota tables.
```markdown
# DO: describe-limits to discover account quotas
aws dynamodb describe-limits --region {{user.region}}
```
### TE-2: No docstrings in boto3 SDK
```python
# DO: inline comments only
def create_table(client, name, pk):
    try: return client.create_table(TableName=name, KeySchema=pk)
    except ClientError as e: handle_error(e)
```
### TE-3: Compact error tables
```markdown
| Error | Resolution |
|-------|-----------|
| TableAlreadyExists | HALT — provide existing table info |
| LimitExceededException | HALT — request quota increase |
| ProvisionedThroughputExceededException | Backoff, retry once |
| ResourceNotFoundException | HALT — table does not exist |
| ValidationException | Fix args; retry once |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |
```
### TE-4: Centralized JSON paths
File-top `## Common JSON Paths` block; one path per resource type.
### TE-5: YAML anchors in example-config.yaml
Use `&defaults` anchors in `assets/example-config.yaml`.
### TE-6: Eliminate cross-file duplicate flows
SKILL.md already has full flow → no Complete Workflow in reference files.

## Related Skills

- `aws-lambda-ops` — Lambda triggers for DynamoDB Streams
- `aws-cloudwatch-ops` — DynamoDB metrics and alarms
- `aws-iam-ops` — IAM roles for DynamoDB access
- `aws-kms-ops` — Encryption key management
- `aws-s3-ops` — Export/import DynamoDB data

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-dynamodb-ops` MUST be wrapped by the Generator-Critic-Loop defined
> in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value | Source |
|---|---|---|
| Class | `required` | `gcl-spec.md` §10 |
| `max_iterations` | `2` | `gcl-spec.md` §10 (Phase 1 default) |
| Rubric | `references/rubric.md` (v1) | this skill |
| Prompts | `references/prompt-templates.md` (v1) | this skill |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |

### Per-operation gating

The Orchestrator applies GCL on every execution. The following operations
are **destructive** and require `{{user.safety_confirm}}` in the trace
(exact format `confirm=<OPERATION> <resource-id>`):

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

### AWS-specific rules in force

This skill's rubric instantiates the repo-wide AWS rules from
`gcl-spec.md` §8. The ones most relevant to DynamoDB:

- **A7** — `--region` must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
- **A8** — `TableName` / `IndexName` in request must be echoed from a `describe-table` lookup
- **A9** — Item values MUST NOT appear in trace (mask to `***<len>`); attribute names matching `*password*`/`*secret*`/`*token*`/`*api_key*` with literal secret patterns → Safety=0 → ABORT
- **A10** — `aws sts get-caller-identity` MUST be the first command in trace

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric + safety special cases
- `references/prompt-templates.md` — Generator / Critic / Orchestrator skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## AIOps: DynamoDB Metrics & Diagnostics

### AIOps Data Collection: DynamoDB Health Metrics for RCA

| Metric | Namespace | AIOps Use |
|--------|-----------|-----------|
| `ConsumedReadCapacityUnits` | AWS/DynamoDB | Hot partition detection, throttling RCA |
| `ConsumedWriteCapacityUnits` | AWS/DynamoDB | Write throughput saturation |
| `ThrottledRequests` | AWS/DynamoDB | Throttling root cause — identify spike time |
| `UserErrors` | AWS/DynamoDB | Application-level errors |
| `SystemErrors` | AWS/DynamoDB | DynamoDB internal errors |
| `ItemCount` | AWS/DynamoDB | Table size anomaly (sudden drop = TTL purge) |
| `ConditionalCheckFailedRequests` | AWS/DynamoDB | Race-condition detection |

### AIOps Diagnostic Flows (Cross-Skill)

```
DynamoDB Throttling RCA Flow:
  1. [aws-cloudwatch-ops] Query ConsumedReadCapacityUnits + ThrottledRequests (last 1 h)
  2. [aws-dynamodb-ops] Check describe-table BillingModeSummary + ConsumedCapacity
  3. [aws-dynamodb-ops] Determine: hot partition vs. global throughput exhaustion
  4. [aws-cloudwatch-ops] Check Contributor Insights for top keys (if enabled)
  5. [aws-dynamodb-ops] Recommend:
     - Hot partition → [AI_ASSIST] redesign key schema
     - Global exhaustion → [AI_ASSIST] switch to on-demand or increase provisioned
```

### Self-Healing Actions

#### AH-DDB-01: Switch to On-Demand Billing [AI_ASSIST]

Trigger: ConsumedReadCapacityUnits > 80% of provisioned RCU for 15+ min.

```
Decision: [AI_ASSIST] (cost-neutral for DynamoDB; reduces throttling)
```

```bash
# Switch to on-demand billing
aws dynamodb update-table \
  --table-name "{{user.TableName}}" \
  --billing-mode PAY_PER_REQUEST \
  --region "{{user.region}}" \
  --output json
```

#### AH-DDB-02: Enable TTL for Expired Items [AI_ASSIST]

Trigger: ItemCount dropping suddenly with no delete activity (TTL purge visible).

```
Decision: [AI_ASSIST] (irreversible within 48 h; user must confirm)
```

```bash
aws dynamodb update-time-to-live \
  --table-name "{{user.TableName}}" \
  --time-to-live-specification "{\"AttributeName\":\"{{user.TTLAttributeName}}\",\"Enabled\":true}" \
  --region "{{user.region}}" \
  --output json
```
**Safety gate**: `confirm=ENABLE_TTL <table>:<attr>` MUST be in trace.

#### AH-DDB-03: Read/Write Capacity Auto-Scaling [AI_ASSIST]

Trigger: Consistent throttling with provisioned billing.

```
Decision: [AI_ASSIST] (AWS managed; no data loss risk)
```

```bash
# Enable auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id "table/{{user.TableName}}" \
  --scalable-dimension "dynamodb:table:ReadCapacityUnits" \
  --min-capacity {{user.min_rcu:5}} \
  --max-capacity {{user.max_rcu:100}} \
  --region "{{user.region}}"
```

### Cross-Module Integration

| Condition | Delegate To |
|-----------|-------------|
| DynamoDB metrics / alarms | `aws-cloudwatch-ops` |
| Lambda Streams consumer check | `aws-lambda-ops` |
| IAM role for DynamoDB access | `aws-iam-ops` |
| KMS key for table encryption | `aws-kms-ops` |
| S3 export / import | `aws-s3-ops` |

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
