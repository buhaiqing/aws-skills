# EKS Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-eks-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-cluster` | 0 / 0.5 / 1 | Verifies `ClusterName` / `NodegroupName` / `AddonName` matches user request (rule A8). Read back via `describe-cluster` (compare `Cluster.Name`) / `describe-nodegroup` / `describe-addon`. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-cluster`, `delete-nodegroup`, `delete-addon`) MUST have explicit user confirmation (`confirm=DELETE_CLUSTER <name>`, `confirm=DELETE_NODEGROUP <name>`, `confirm=DELETE_ADDON <name>`) in trace. **`delete-cluster` requires sequenced pre-cleanup: Fargate profiles → addons → nodegroups → cluster.** AWS rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-cluster` with same name fails with `ResourceInUseException` (NOT idempotent). `delete-cluster` / `delete-nodegroup` are idempotent after deletion completes (returns `ResourceNotFoundException`). |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws eks <op>` command with args, exit code, raw response excerpt (≤ 2 KB, no kubeconfig or CA data), and final `describe-cluster` / `describe-nodegroup` snapshot with `Status` and `Version`. `aws sts get-caller-identity` MUST be first (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: valid K8s version (e.g. `1.27`, `1.28` — one minor upgrade at a time), VPC/subnets must exist and have at least 2 subnets in different AZs, `--role-arn` is valid IAM role for EKS, `--ami-type` is `AL2_x86_64`, `AL2_ARM_64`, `BOTTLEROCKET_x86_64`, `WINDOWS_CORE_2022_x86_64`, or `WINDOWS_FULL_2022_x86_64`. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-cluster` | Correctness, **Spec Compliance** | Role ARN must exist; subnet count ≥ 2; K8s version valid |
| `delete-cluster` | Correctness, Safety, **Traceability** | Pre-delete sequence: Fargate → addons → nodegroups → cluster |
| `delete-nodegroup` | Correctness, Safety | Terminates all EC2 instances in the nodegroup |
| `create-nodegroup` | Correctness, **Spec Compliance** | Instance types valid; scaling config min/max/desired |
| `create-fargate-profile` | Correctness | Selectors valid; subnets must exist |
| `describe-cluster` | Correctness | Read-only |
| `update-cluster-version` | Correctness, **Safety** | Version upgrade — confirm with user; check compat |
| `create-addon` | Correctness | Addon name must be valid; version check |

## Safety special cases (auto-fail)

- `delete-cluster` **without** explicit `confirm=DELETE_CLUSTER <name>` → **Safety = 0 → ABORT**
- `delete-cluster` without verifying sequenced cleanup (Fargate profiles → addons → nodegroups) → **Safety = 0 → ABORT**
- `delete-nodegroup` without `confirm=DELETE_NODEGROUP <name>` → **Safety = 0 → ABORT**
- Resource ID not echoed from `describe-*` / `list-*` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` mismatch → **Correctness = 0 → ABORT** (rule A7)
- Secrets/credentials in trace → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not first → **Traceability = 0 → ABORT** (rule A10)
- `update-cluster-version` skipping minor versions (e.g., 1.28 → 1.30) → **Correctness = 0 → ABORT** (EKS only supports one minor version upgrade at a time)

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-eks-ops` GCL |