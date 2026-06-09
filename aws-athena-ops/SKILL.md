---
name: aws-athena-ops
description: >-
  Use when the user needs to manage Amazon Athena resources — workgroups, named
  queries, data catalogs, prepared statements, query execution, or notebook
  operations; user mentions "Athena", "workgroup", "named query", "data catalog",
  "SQL query", "query execution", "prepared statement", or "Athena notebook".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to Amazon Athena endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-06-10"
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
    - AWS_PROFILE
  cross_skill_deps:
    - aws-s3-ops          # Query result output location (S3 bucket)
    - aws-iam-ops         # Workgroup IAM policies / Service role
---

# Amazon Athena Operations Skill

## Common JSON Paths (Centralized)

```
# WorkGroup:      .WorkGroup.{Name,Configuration.{ResultConfiguration.{OutputLocation},EngineConfiguration},State,Description}
# NamedQuery:     .NamedQuery.{NamedQueryId,Name,Database,QueryString,Description,WorkGroup}
# DataCatalog:    .DataCatalog.{Name,Type,ConnectionType,Status,Error}
# QueryExec:      .QueryExecution.{QueryExecutionId,Query,StatementType,State,StateChangeReason,Statistics,{EngineExecutionTimeInMillis,DataScannedBytes},ResultConfiguration.OutputLocation}
# QueryResults:   .ResultSet.{Rows[{Data[{VarCharValue}]}],ResultSetMetadata.ColumnInfo[{Name,Type}]}
# PreparedStmt:   .PreparedStatement.{PreparedStatementName,StatementName,QueryStatement,WorkGroupName,Description}
```

## Overview

Amazon Athena is a serverless interactive query service for analyzing data in S3 using SQL. This skill is an **operational runbook** with pre-flight → execute → validate → recover.

## Trigger & Scope

### SHOULD Use When
- User mentions "Athena", "workgroup", "named query", "data catalog"
- Task involves CRUD on **workgroups**, **named queries**, **data catalogs**, or **prepared statements**
- Task involves **query execution** (start, poll, stop, get results)
- Keywords: athena, workgroup, named-query, data-catalog, query-execution, prepared-statement, sql-query

### SHOULD NOT Use When
- S3 bucket management → delegate to: `aws-s3-ops`
- IAM policy for Athena workgroup → delegate to: `aws-iam-ops`
- Cost analysis for Athena queries → use AWS Cost Explorer directly
- Standalone resource tagging → use `aws resourcegroupstaggingapi` CLI directly

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile over explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.workgroup_name}}` | User input | Workgroup name |
| `{{user.catalog_name}}` | User input | Data catalog name |
| `{{user.query_string}}` | User input | SQL query text |
| `{{user.output_location}}` | User input | S3 output path (s3://bucket/prefix/) |
| `{{user.database_name}}` | User input | Database name in catalog |
| `{{user.named_query_id}}` | User input | Named query ID |
| `{{user.execution_id}}` | User input | Query execution ID |
| `{{output.QueryExecutionId}}` | Last API response | Parse: `.QueryExecutionId` |
| `{{output.WorkGroupArn}}` | Last API response | Parse: `.WorkGroup Arn` |

## Execution Flow Pattern

Every operation: **Pre-flight** → **Execute** (CLI, boto3 fallback) → **Validate** → **Recover**.

### Common Pre-flight Steps (all ops)

```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] AWS CLI v2.x` and `[OK] Identity: arn:aws:iam::...`.

### Operation: Create Workgroup

#### Execute — CLI (Primary)
```bash
aws athena create-work-group \
  --name "{{user.workgroup_name}}" \
  --description "Created by Agent" \
  --configuration "ResultConfiguration={OutputLocation={{user.output_location}}}" \
  --region "{{user.region}}" \
  --output json
```

#### Validate
`aws athena get-work-group --work-group "{{user.workgroup_name}}"` → check name and state.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix args; retry once |
| ThrottlingException | Backoff; retry 3x |
| InternalServerException | Retry 3x; HALT |

### Operation: Create Named Query

```bash
aws athena create-named-query \
  --name "{{user.workgroup_name}}-query" \
  --database "{{user.database_name}}" \
  --query-string "{{user.query_string}}" \
  --work-group "{{user.workgroup_name}}" \
  --region "{{user.region}}" \
  --output json
```
Validate: `aws athena get-named-query --named-query-id {{output.NamedQueryId}}`.

### Operation: Start Query Execution (Async)

```bash
aws athena start-query-execution \
  --query-string "{{user.query_string}}" \
  --query-execution-context "Database={{user.database_name}}" \
  --result-configuration "OutputLocation={{user.output_location}}" \
  --work-group "{{user.workgroup_name}}" \
  --region "{{user.region}}" \
  --output json
```
Poll: `aws athena get-query-execution --query-execution-id {{output.QueryExecutionId}}` until State is `SUCCEEDED`, `FAILED`, or `CANCELLED`. Max wait: 300s, interval: 2s.

### Operation: Get Query Results

```bash
aws athena get-query-results \
  --query-execution-id "{{user.execution_id}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Stop Query Execution

```bash
aws athena stop-query-execution \
  --query-execution-id "{{user.execution_id}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Update Workgroup

```bash
aws athena update-work-group \
  --work-group "{{user.workgroup_name}}" \
  --description "Updated by Agent" \
  --configuration "ResultConfiguration={OutputLocation={{user.output_location}}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Delete Workgroup
**Safety Gate**: `confirm=DELETE_WORK_GROUP {{user.workgroup_name}}`

```bash
aws athena delete-work-group \
  --work-group "{{user.workgroup_name}}" \
  --region "{{user.region}}" \
  --output json
```
Validate: `get-work-group` returns error (resource not found).

### Operation: Delete Named Query
**Safety Gate**: `confirm=DELETE_NAMED_QUERY {{user.named_query_id}}`

```bash
aws athena delete-named-query \
  --named-query-id "{{user.named_query_id}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Delete Data Catalog
**Safety Gate**: `confirm=DELETE_CATALOG {{user.catalog_name}}`

```bash
aws athena delete-data-catalog \
  --name "{{user.catalog_name}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: Delete Prepared Statement
**Safety Gate**: `confirm=DELETE_PREPARED_STATEMENT {{user.prepared_statement_name}}`

```bash
aws athena delete-prepared-statement \
  --statement-name "{{user.prepared_statement_name}}" \
  --work-group "{{user.workgroup_name}}" \
  --region "{{user.region}}" \
  --output json
```

## Safety Gates

### Delete Workgroup
```
BEFORE delete-work-group:
1. Display: "Deleting workgroup {{user.workgroup_name}} — queries and results in this workgroup will be affected"
2. Ask: "Type 'DELETE_WORK_GROUP {{user.workgroup_name}}' to confirm"
3. Pre-flight: list named queries and running executions in workgroup
```

### Delete Named Query
```
BEFORE delete-named-query:
1. Display: "Deleting named query {{user.named_query_id}}"
2. Ask: "Type 'DELETE_NAMED_QUERY {{user.named_query_id}}' to confirm"
```

### Delete Data Catalog
```
BEFORE delete-data-catalog:
1. Display: "Deleting data catalog {{user.catalog_name}} — all databases/tables in this catalog will be inaccessible from Athena"
2. Ask: "Type 'DELETE_CATALOG {{user.catalog_name}}' to confirm"
```

### Delete Prepared Statement
```
BEFORE delete-prepared-statement:
1. Display: "Deleting prepared statement {{user.prepared_statement_name}}"
2. Ask: "Type 'DELETE_PREPARED_STATEMENT {{user.prepared_statement_name}}' to confirm"
```

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [GCL Rubric](references/rubric.md)
- [GCL Prompt Templates](references/prompt-templates.md)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-10, required). Every execution of
> `aws-athena-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |

| Operation | GCL | Notes |
|---|---|---|
| `delete-work-group` | required | `confirm=DELETE_WORK_GROUP <name>` |
| `delete-named-query` | required | `confirm=DELETE_NAMED_QUERY <id>` |
| `delete-data-catalog` | required | `confirm=DELETE_CATALOG <name>` |
| `delete-prepared-statement` | required | `confirm=DELETE_PREPARED_STATEMENT <name>` |
