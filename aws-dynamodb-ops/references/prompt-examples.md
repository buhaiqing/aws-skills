# DynamoDB Skill — Prompt Examples

_Last updated: 2026-06-27_

This document provides concrete user prompts for DynamoDB table management,
item operations, capacity tuning, and cross-service diagnostics.

---

## Scenario 1: Table creation with on-demand billing

### User Prompt
```
Create a DynamoDB table called my-table with partition key userId
(string) and sort key timestamp (number). Use on-demand billing.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Verify table name uniqueness | `aws dynamodb list-tables` | |
| 2. Check quotas | `aws dynamodb describe-limits` | |
| 3. Create table | `aws dynamodb create-table --billing-mode PAY_PER_REQUEST` | |
| 4. Poll until ACTIVE | `aws dynamodb wait table-exists` | max 10 min |

---

## Scenario 2: Table throttling RCA

### User Prompt
```
Our DynamoDB table orders-prod is getting throttled. Can you investigate?
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Check consumed capacity | `aws cloudwatch get-metric-statistics ConsumedReadCapacityUnits` | |
| 2. Check throttled requests | `aws cloudwatch get-metric-statistics ThrottledRequests` | |
| 3. Identify hot partition | CloudWatch Contributor Insights (if enabled) | |
| 4. Recommend capacity mode change | | `[AI_ASSIST]` switch to on-demand |

---

## Scenario 3: Enable TTL on a table

### User Prompt
```
Enable TTL on our DynamoDB table user-sessions with attribute expiresAt.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Describe table schema | `aws dynamodb describe-table` | Verify `expiresAt` is `Number` type |
| 2. Safety gate | Require `confirm=ENABLE_TTL <table>:<attr>` | |
| 3. Enable TTL | `aws dynamodb update-time-to-live --time-to-live-specification` | |
| 4. Warn user | Items matching `now >= expiresAt` deleted within 48 h | |

---

## Scenario 4: GSI deletion (irreversible)

### User Prompt
```
Remove the GSI old-index from table my-table.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Describe table GSIs | `aws dynamodb describe-table --query GlobalSecondaryIndexes` | |
| 2. Safety gate | Require `confirm=DELETE_GSI <table>:<index>` | |
| 3. Delete GSI | `aws dynamodb update-table --global-secondary-index-updates` | |
| 4. Poll until ACTIVE | `aws dynamodb wait table-exists` | |

---

## Scenario 5: Delete table with Lambda stream

### User Prompt
```
Delete the table my-data-table.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Describe table | `aws dynamodb describe-table` | TableStatus must be ACTIVE |
| 2. Check event source mappings | `aws lambda list-event-source-mappings --query "EventSourceMappings[?contains(DynamodbTableArn,'my-data-table')]"` | |
| 3. If Lambda consumers exist | HALT — require `confirm=DELETE_TABLE_WITH_TRIGGERS <table>` | |
| 4. Check backups | `aws dynamodb list-backups --table-name my-data-table` | |
| 5. Safety gate | Require `confirm=DELETE_TABLE <table-name>` | |
| 6. Capture item count + size | `aws dynamodb describe-table --query "{ItemCount,TableSizeBytes}"` | Log for traceability |
| 7. Delete table | `aws dynamodb delete-table` | |
| 8. Poll until deleted | `aws dynamodb wait table-not-exists` | max 5 min |

---

## Quick Reference

| User says | Scenario | Decision | Modules |
|-----------|----------|----------|---------|
| "Create table with on-demand billing" | Table creation | `[AUTO_HEAL]` | dynamodb |
| "Table is getting throttled" | Throttling RCA | `[AI_ASSIST]` | dynamodb + cloudwatch |
| "Enable TTL on expiresAt" | TTL enablement | `[AI_ASSIST]` confirm irreversible | dynamodb |
| "Remove GSI old-index" | GSI deletion | `[AI_ASSIST]` confirm irreversible | dynamodb |
| "Delete my-data-table" | Table deletion | `[MANUAL]` strong safety gate | dynamodb + lambda |
