# Athena Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-athena-ops`. This
> file is the single source of truth for what the Critic scores against.
>
> GCL required skill (max_iter=2). See top-level `AGENTS.md` §11.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-*` operations | 0 / 0.5 / 1 | Verifies workgroup name, catalog name, named query ID, prepared statement name match user request. Read back via `describe-*`/`get-*` and compare (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-work-group`, `delete-named-query`, `delete-data-catalog`, `delete-prepared-statement`) MUST have explicit user confirmation captured in trace. AWS-specific rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-*` operations are idempotent if name already exists (returns existing). `delete-*` operations return success on re-delete of non-existent resources. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws athena` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `get-*` snapshot. `aws sts get-caller-identity` MUST be first (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: workgroup state is valid, output location is valid S3 path, database/catalog names exist, query syntax is valid SQL. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-work-group` | Correctness, Spec Compliance | Output location must be valid S3 path |
| `start-query-execution` | Correctness, Spec Compliance | Database must exist; query must be valid SQL; output location required |
| `delete-work-group` | Correctness, Safety, **Traceability** | `confirm=DELETE_WORK_GROUP <name>` required |
| `delete-named-query` | Correctness, Safety | `confirm=DELETE_NAMED_QUERY <id>` required |
| `delete-data-catalog` | Correctness, Safety | `confirm=DELETE_CATALOG <name>` required |
| `delete-prepared-statement` | Correctness, Safety | `confirm=DELETE_PREPARED_STATEMENT <name>` required |
| `stop-query-execution` | Correctness | Query must be in QUEUED or RUNNING state |

## Athena-specific Safety special cases (auto-fail)

- `delete-work-group` **without** explicit `confirm=DELETE_WORK_GROUP <name>` in the trace → **Safety = 0 → ABORT**
- `delete-named-query` **without** explicit `confirm=DELETE_NAMED_QUERY <id>` in the trace → **Safety = 0 → ABORT**
- `delete-data-catalog` **without** explicit `confirm=DELETE_CATALOG <name>` in the trace → **Safety = 0 → ABORT**
- `delete-prepared-statement` **without** explicit `confirm=DELETE_PREPARED_STATEMENT <name>` in the trace → **Safety = 0 → ABORT**
- `start-query-execution` with `OutputLocation` pointing to non-existent S3 bucket → **Correctness = 0 → ABORT**
- `start-query-execution` referencing non-existent database → **Correctness = 0 → ABORT**
- Any operation whose resource name was not echoed back from a `get-*` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` → **Correctness = 0 → ABORT** (rule A7)
- S3 bucket names or credentials appearing in trace unmasked → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not run before any mutating op → **Traceability = 0 → ABORT** (rule A10)

## Reference to AWS Rules A1–A10

This rubric enforces the following rules from `aws-skill-generator/references/gcl-spec.md` §8:

| Rule | Applicability to Athena Ops |
|---|---|
| **A1** | Not applicable — Athena has no `terminate-instances` equivalent |
| **A2** | S3 output bucket versioning: recommended but not enforced |
| **A3** | IAM policy checks: workgroup IAM policies should be verified before deletion |
| **A7** | Region match: All `--region` flags must match `{{user.region}}` |
| **A8** | Resource echo-back: All resource names must be echoed from `get-*` lookups |
| **A9** | Secret masking: S3 bucket names and credentials must be masked |
| **A10** | Identity provenance: `aws sts get-caller-identity` MUST be first command |

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (required class default) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |
