# CloudTrail Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-cloudtrail-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-trail` | 0 / 0.5 / 1 | Verifies `TrailName` / `TrailARN` matches user request (rule A8). Read back via `describe-trails` / `get-trail-status` and compare `TrailList[].Name` and `TrailList[].TrailARN`. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-trail`, `stop-logging`) MUST have explicit user confirmation (`confirm=DELETE_TRAIL <name>`, `confirm=STOP_LOGGING <name>`) in trace. `delete-trail` stops ALL audit logging — warn user. AWS rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-trail` with same `--name` updates existing trail (idempotent). `delete-trail` is idempotent (no-op on already-deleted trail). `start-logging` / `stop-logging` are idempotent (toggle state, safe to retry). |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws cloudtrail <op>` command with args, exit code, raw response excerpt (≤ 2 KB, any event data with credential-like values masked), and a final `get-trail-status` snapshot with `IsLogging`, `LatestDeliveryTime`, `LatestNotificationTime`. `aws sts get-caller-identity` MUST be first (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: S3 bucket for `--s3-bucket-name` exists (verified via `aws s3api head-bucket`), KMS key exists if `--kms-key-id` specified, `--is-multi-region-trail` flag consistent with org trail requirements, `--event-selectors` with valid `ReadWriteType` (All, ReadOnly, WriteOnly) and `IncludeManagementEvents`. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-trail` | Correctness, **Spec Compliance** | S3 bucket must exist with CloudTrail write policy |
| `delete-trail` | Correctness, Safety, **Traceability** | Stops ALL audit logging — SEVERE; confirm DELETE <trail-name> |
| `stop-logging` | Correctness, Safety | No events recorded until restarted; confirm |
| `start-logging` | Correctness | Read-like; no safety gate |
| `lookup-events` | Correctness | Read-only |
| `describe-trails` | Correctness | Read-only |
| `get-trail-status` | Correctness | Read-only |
| `put-event-selectors` | Correctness | Valid event selector types |
| `update-trail` | Correctness, **Safety** | Changing S3 bucket or KMS key — data could be lost |

## Safety special cases (auto-fail)

- `delete-trail` **without** explicit `confirm=DELETE_TRAIL <name>` → **Safety = 0 → ABORT**
- `stop-logging` without user confirmation → **Safety = 0 → ABORT**
- `update-trail` changing S3 bucket without confirming no log loss → **Safety = 0 → ABORT**
- Trail name not echoed from `describe-trails` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` mismatch → **Correctness = 0 → ABORT** (rule A7)
- Event data containing credential-like values in trace → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not first → **Traceability = 0 → ABORT** (rule A10)

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **3** | `gcl-spec.md` §10 (optional skills) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-cloudtrail-ops` GCL |