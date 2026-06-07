# Config Ops Rubric (GCL)

> Instantiation of the GCL rubric from `aws-skill-generator/references/gcl-spec.md` §3 for `aws-config-ops`.
>
> **Repo-wide AWS rules A1–A10** are in `gcl-spec.md` §8. This rubric references them by ID.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | Correctness | hard | ≥ 0.5 | 0 / 0.5 / 1 | Verifies rule name, recorder name, region match; read-back via `describe-config-rules` |
| 2 | Safety | hard | = 1 | 0 / 1 | Destructive ops MUST have `confirm=` in trace; rule A7, A8, A9, A10 apply |
| 3 | Idempotency | soft | ≥ 0.5 | 0 / 0.5 / 1 | `put-*` ops are idempotent; `delete-*` ops are idempotent (404 on re-delete) |
| 4 | Traceability | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace must contain command, args, exit code, response excerpt, post-state snapshot; `sts get-caller-identity` first (A10) |
| 5 | Spec Compliance | soft | ≥ 0.5 | 0 / 0.5 / 1 | Region support, service-linked role exists, S3/SNS pre-verified |

## Operation-specific overrides

| Operation | Required = 1.0 | Notes |
|---|---|---|
| `delete-config-rule` | Correctness, Safety | `confirm=DELETE_RULE <name>`; verify rule exists |
| `delete-configuration-recorder` | Correctness, Safety | Must stop recorder first; `confirm=DELETE_RECORDER <name>` |
| `delete-delivery-channel` | Correctness, Safety | `confirm=DELETE_CHANNEL <name>` |
| `stop-configuration-recorder` | Safety | Pauses compliance evaluation; confirm required |
| `put-configuration-recorder` | Correctness | Verify role ARN exists |
| `put-delivery-channel` | Correctness | Verify S3 bucket exists before setting |

## Safety special cases (auto-fail)

- `delete-configuration-recorder` without first checking recording status → **Safety = 0 → ABORT**
- Any op without `describe-*` resource echo-back → **Correctness = 0** (rule A8)
- `--region` mismatch → **Correctness = 0** (rule A7)
- Credentials in trace → **Safety = 0** (rule A9)
- `sts get-caller-identity` not first → **Traceability = 0** (rule A10)

## Loop parameters

| Parameter | Value |
|---|---|
| `max_iterations` | 3 |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |
| Rubric version | v1 |