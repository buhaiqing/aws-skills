# RAM Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-ram-ops`. This
> file is the single source of truth for what the Critic scores against.
>
> GCL required skill (max_iter=2). See top-level `AGENTS.md` §11.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-*` operations | 0 / 0.5 / 1 | Verifies resource share name/ARN, permission name/ARN, principal ARNs match user request. Read back via `get-resource-shares` and compare (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-resource-share`, `delete-permission`, `delete-permission-version`, `reject-resource-share-invitation`) MUST have explicit user confirmation captured in trace. AWS-specific rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-resource-share` with same name returns existing. `delete-*` operations return success on re-delete. `accept-resource-share-invitation` is idempotent for already-accepted. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws ram` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `get-resource-shares` snapshot. `aws sts get-caller-identity` MUST be first (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: resource ARNs are valid, principal ARNs/account IDs are valid 12-digit, share is in ACTIVE state before operations, org sharing enabled when needed. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-resource-share` | Correctness, Spec Compliance | Resource ARNs must be valid; principals must be valid account IDs or ARNs |
| `accept-resource-share-invitation` | Correctness | Invitation ARN must be valid and in PENDING state |
| `delete-resource-share` | Correctness, Safety, **Traceability** | `confirm=DELETE_RESOURCE_SHARE <arn>` required; breaks dependent accounts |
| `delete-permission` | Correctness, Safety | `confirm=DELETE_PERMISSION <arn>` required; affects all associated shares |
| `delete-permission-version` | Correctness, Safety | `confirm=DELETE_PERMISSION_VERSION <arn> <version>` required |
| `reject-resource-share-invitation` | Correctness, Safety | `confirm=REJECT_INVITATION <arn>` required |
| `update-resource-share` | Correctness | Share must be in ACTIVE state |

## RAM-specific Safety special cases (auto-fail)

- `delete-resource-share` **without** explicit `confirm=DELETE_RESOURCE_SHARE <arn>` in the trace → **Safety = 0 → ABORT**
- `delete-resource-share` when share has **active associations** without first disassociating → **Safety = 0 → ABORT**
- `delete-permission` **without** explicit `confirm=DELETE_PERMISSION <arn>` in the trace → **Safety = 0 → ABORT**
- `delete-permission-version` **without** explicit `confirm=DELETE_PERMISSION_VERSION <arn> <version>` in the trace → **Safety = 0 → ABORT**
- `reject-resource-share-invitation` **without** explicit `confirm=REJECT_INVITATION <arn>` in the trace → **Safety = 0 → ABORT**
- `create-resource-share` with **external principals** without `--allow-external-principals` → **Spec Compliance = 0 → ABORT**
- Any operation whose resource share ARN was not echoed back from a `get-resource-shares` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` → **Correctness = 0 → ABORT** (rule A7)
- Account IDs or ARNs containing credentials appearing in trace unmasked → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not run before any mutating op → **Traceability = 0 → ABORT** (rule A10)

## Reference to AWS Rules A1–A10

This rubric enforces the following rules from `aws-skill-generator/references/gcl-spec.md` §8:

| Rule | Applicability to RAM Ops |
|---|---|
| **A1** | Not applicable — RAM has no `terminate-instances` equivalent |
| **A2** | Not directly applicable — RAM shares resources, not S3 buckets |
| **A3** | IAM policy checks: shared resources should have proper IAM policies before sharing |
| **A7** | Region match: All `--region` flags must match `{{user.region}}` |
| **A8** | Resource echo-back: All resource share ARNs must be echoed from `get-resource-shares` lookups |
| **A9** | Secret masking: Account IDs and ARNs with credentials must be masked |
| **A10** | Identity provenance: `aws sts get-caller-identity` MUST be first command |

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (required class default) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |
