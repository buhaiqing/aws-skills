# Athena Skill — Prompt Examples

_Last updated: 2026-06-27_

This document provides concrete user prompts for Athena workgroup management,
query execution, data catalog operations, and cross-service scenarios.

---

## Scenario 1: Create workgroup with S3 output

### User Prompt
```
Create an Athena workgroup called analytics-wg that outputs results
to s3://my-company-athena-results/analytics/. Use us-east-1.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Verify CLI | `aws --version` | |
| 2. Verify credentials | `aws sts get-caller-identity` | |
| 3. Verify workgroup name | `aws athena list-work-groups --region us-east-1` | Reject duplicate name |
| 4. Create workgroup | `aws athena create-work-group --name analytics-wg --configuration ResultConfiguration={OutputLocation=s3://my-company-athena-results/analytics/}` | |
| 5. Poll until active | `aws athena get-work-group --work-group analytics-wg` | Max 60s |

---

## Scenario 2: Run SQL query and wait for results

### User Prompt
```
Run the query "SELECT count(*) FROM events WHERE date = '2026-01-01'"
against the mydb database in the analytics-wg workgroup.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Start execution | `aws athena start-query-execution --query-string "SELECT count(*) FROM events WHERE date = '2026-01-01'" --query-execution-context Database=mydb --result-configuration OutputLocation=s3://...` | |
| 2. Poll for completion | `aws athena get-query-execution --query-execution-id <id>` | State = SUCCEEDED/FAILED/CANCELLED |
| 3. Get results | `aws athena get-query-results --query-execution-id <id>` | Parse ResultSet |

---

## Scenario 3: Delete a workgroup safely

### User Prompt
```
Delete the workgroup called old-wg.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Request confirmation | Display: "Type DELETE_WORK_GROUP old-wg to confirm" | Wait for user input |
| 2. List named queries | `aws athena list-named-queries --work-group old-wg` | Warn if any exist |
| 3. List running queries | `aws athena list-query-executions --work-group old-wg --query-state RUNNING` | Warn if any running |
| 4. Confirm with token | `confirm=DELETE_WORK_GROUP old-wg` | |
| 5. Delete | `aws athena delete-work-group --work-group old-wg` | |
| 6. Validate | `aws athena get-work-group --work-group old-wg` | Expect ResourceNotFoundException |

---

## Scenario 4: Data catalog management

### User Prompt
```
Create a Lambda-backed Athena data catalog called my-catalog
pointing to a function arn:aws:lambda:us-east-1:123456789012:function:glue-catalog.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Verify Lambda function | `aws lambda get-function --function-name glue-catalog` | Verify exists and invoke permissions |
| 2. Create catalog | `aws athena create-data-catalog --name my-catalog --type LAMBDA --configuration '{"LambdaFunctionArn":"arn:aws:lambda:us-east-1:123456789012:function:glue-catalog"}'` | |
| 3. Validate | `aws athena get-data-catalog --name my-catalog` | Check Status = AVAILABLE |

---

## Scenario 5: Stop a runaway query

### User Prompt
```
A query is stuck running in the production-wg workgroup with
execution ID abc123-def456. Stop it.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Verify execution | `aws athena get-query-execution --query-execution-id abc123-def456` | Confirm State = RUNNING |
| 2. Stop | `aws athena stop-query-execution --query-execution-id abc123-def456` | |
| 3. Validate | Poll `get-query-execution` | State → CANCELLED |

---

## Scenario 6: Cross-service — Athena + S3

### User Prompt
```
List all Athena workgroups and check which S3 buckets are used
as their result output locations.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. List workgroups | `aws athena list-work-groups --output json` | |
| 2. For each active wg | `aws athena get-work-group --work-group <name>` | Extract OutputLocation |
| 3. Verify buckets | `aws s3 ls s3://<bucket>/` | Confirm bucket exists and is accessible |
