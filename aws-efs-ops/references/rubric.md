# EFS Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-efs-ops`. This
> file is the single source of truth for what the Critic scores against.
>
> GCL rollout: required, max_iter=2 (see AGENTS.md §11.5).

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-file-system` / `delete-mount-target` / `delete-access-point` | 0 / 0.5 / 1 | Verifies `file-system-id` matches the user request. Read back via `describe-file-systems` and compare against `.FileSystems[0].FileSystemId` and `LifeCycleState`. Mount target and access point IDs MUST be echoed from a `describe-mount-targets` / `describe-access-points` lookup. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-file-system`, `delete-mount-target`, `delete-access-point`) MUST have explicit user confirmation captured in trace. `delete-file-system` requires pre-flight deletion of all mount targets and access points. AWS-specific rules A8, A9, A10 in `gcl-spec.md` §8 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-file-system` MUST include `--creation-token` with a fresh UUID v4. `create-mount-target` is idempotent for the same subnet (returns existing ID). `delete-file-system` / `delete-mount-target` / `delete-access-point` are idempotent (return success for non-existent resources). |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws efs` command (or boto3 call), args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-file-systems` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). Score 1 only if all five present. |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: `--performance-mode` / `--throughput-mode` are valid choices for the use case; mount target subnet belongs to the correct VPC; security groups are valid for the target subnet's VPC; `--region` matches the file system region (rule A7). |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-file-system` | Correctness, **Idempotency** | Must use `--creation-token` |
| `describe-file-systems` / `describe-mount-targets` / `describe-access-points` | Correctness | Read-only; Safety is automatically 1 |
| `create-mount-target` | Correctness, Spec Compliance | Subnet + SG must belong to same VPC |
| `delete-mount-target` | Correctness, Safety | `confirm=DELETE_MOUNT_TARGET <mount-target-id>` required |
| `create-access-point` | Correctness, Spec Compliance | Root directory path must be valid POSIX |
| `delete-access-point` | Correctness, Safety | `confirm=DELETE_ACCESS_POINT <access-point-id>` required |
| `delete-file-system` (no mount targets / access points) | Correctness, Safety | Pre-flight: verify no mount targets or access points remain |
| `delete-file-system` (with dependencies) | Correctness, Safety, **Traceability** | Pre-flight MUST list and delete mount targets + access points first; `confirm=DELETE_FS <file-system-id>` required |
| `put-file-system-policy` (no cross-account) | Correctness | Routine |
| `put-file-system-policy` (cross-account / `Principal: "*"`) | Correctness, **Safety** | `confirm=PUT_POLICY_PUBLIC <file-system-id>` required |

## Safety special cases (auto-fail)

- `delete-file-system` called without `confirm=DELETE_FS <file-system-id>`
  in the trace → **Safety = 0 → ABORT**.
- `delete-file-system` called while mount targets or access points still
  exist (pre-flight `describe-mount-targets` / `describe-access-points`
  shows non-empty) → **Correctness = 0 → ABORT** (must delete dependencies first).
- `delete-mount-target` called without `confirm=DELETE_MOUNT_TARGET <mount-target-id>`
  in the trace → **Safety = 0 → ABORT**.
- `delete-access-point` called without `confirm=DELETE_ACCESS_POINT <access-point-id>`
  in the trace → **Safety = 0 → ABORT**.
- `put-file-system-policy` adds `Principal: "*"` with `Effect: Allow`
  without `confirm=PUT_POLICY_PUBLIC <file-system-id>`
  → **Safety = 0 → ABORT** (rule A15 analogous).
- `file-system-id` in the request not echoed from a `describe-file-systems`
  lookup → **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
  → **Correctness = 0 → ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10).
- `UserData`, `KeyMaterial`, `PasswordData`, or plaintext credentials appear
  anywhere in the trace → **Safety = 0 → ABORT** (rule A9).

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (default for destructive skills) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-12 | Initial rubric for `aws-efs-ops` GCL rollout (required) |
