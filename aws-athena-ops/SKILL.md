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
  version: "1.1.0"
  last_updated: "2026-07-31"
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
    - aws-s3-ops          # Query result output location (S3 bucket)
    - aws-iam-ops         # Workgroup IAM policies / Service role
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'cost-forecast']
    produces_facts: ['metric', 'cost', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS Athena Operations Skill

Use for Athena workgroups, named queries, query execution/results, catalogs, prepared statements, data locations, cost controls, and analytics automation. Detailed commands remain in references.

## Common JSON Paths

Workgroups: .WorkGroups[].{Name,State,Configuration,Description}
StartQuery: .QueryExecutionId
Query: .QueryExecution.{QueryExecutionId,Query,Status,ResultConfiguration,Statistics}
Results: .ResultSet.{Rows,ResultSetMetadata}
Catalogs: .DataCatalogsSummary[].{CatalogName,Type,Description}

## Trigger & Scope

### SHOULD Use When
Athena SQL execution/results, workgroups, named queries, catalogs, prepared statements, cost controls, or query diagnostics.

### SHOULD NOT Use When
S3 data lifecycle → `aws-s3-ops`; Glue catalog → use Glue-specific tooling; Redshift → direct Redshift skill/SDK.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.workgroup_name}}`, `{{user.query_string}}`, `{{user.database}}` | User input | Query/workgroup payload |
| `{{user.query_execution_id}}`, `{{user.catalog_name}}`, `{{user.prepared_statement_name}}` | User input | Resource IDs |
| `{{output.*}}` | API response | Reuse execution/result IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify workgroup, catalog/database, S3 output location, encryption, query scope, and cost controls. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll query status and retrieve results; recover with bounded retries and halt on invalid SQL, access, quota, or ambiguous IDs. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/update workgroup | Diff bytes-scanned/result-location/encryption controls | Token for production cost-policy changes |
| Start/stop query | Echo SQL/workgroup and output location; poll terminal status | `confirm=STOP_QUERY {{user.query_execution_id}}` |
| Get results | Verify execution identity; mask sensitive rows | — |
| Delete workgroup | Inspect running queries and cost/result configuration | `confirm=DELETE_WORK_GROUP {{user.workgroup_name}}` |
| Delete named query/catalog/prepared statement | Verify exact ID and dependent consumers | `confirm=DELETE_NAMED_QUERY {{user.named_query_id}}` · `confirm=DELETE_CATALOG {{user.catalog_name}}` · `confirm=DELETE_PREPARED_STATEMENT {{user.prepared_statement_name}}` |

Mask SQL literals, result rows, credentials, and S3 output paths where sensitive.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live workgroup/catalog state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for query stop/cost-policy/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits bounded non-destructive workgroup changes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

