# Amazon Topo Discovery Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-topo-discovery`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.
> `aws-topo-discovery` is a **read-only** discovery skill: it issues only
> Describe/List/Get and writes local artifacts (HCL / baseline snapshots);
> it never creates, modifies, or deletes AWS resources. Its GCL tier is
> `optional` (see `AGENTS.md` §11 read-only tier downgrade strategy).

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for any artifact claiming a resource identity | 0 / 0.5 / 1 | Verifies the discovered resource id / arn / name matches the user request. Read back via the matching `describe-*` / `list-*` / `get-*` call and compare (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Read-only skill: trace MUST contain **no** `create-*`, `delete-*`, `modify-*` AWS call (rule S1). Destructive ops are banned by design; Safety = 0 if any write verb appears. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Same input → same output. Re-running `scan-topo` / `baseline` must not mutate prior artifacts; `baseline` overwrite is idempotent when the snapshot is identical. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws <svc> <op> --output json` command, args, exit code, raw response excerpt (≤ 2 KB, credential-like values masked), and a `describe-*` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md` / `execution-commands.md`: region supports the resource, IAM ReadOnlyAccess pre-reqs satisfied, output schema matches `manifest-schema.json`. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `scan-topo` | Correctness, **Traceability** | Cross-product read-only scan (VPC/EC2/RDS/ELB/NAT/EIP/EKS/Lambda/S3/SG). Every `aws <svc> <op>` must be Describe/List/Get; identity echoed back (rule A8). |
| `export-hcl` | Correctness, **Spec Compliance** | Emits Terraform HCL from discovered state; field mapping must match `manifest-schema.json`; no live AWS write. |
| `baseline` (create snapshot) | Correctness, **Idempotency** | Writes local baseline under `audit-results/`; overwrite idempotent when snapshot identical; never deletes prior baseline without explicit confirm. |
| `baseline-diff` | Correctness, **Traceability** | Read-only diff between two baselines; report includes timestamps and a risk rating; no mutation. |
| `describe-*` / `list-*` / `get-*` (underlying) | — | Read-only; Correctness = 1 whenever the returned identity matches the request. |

## Safety special cases (auto-fail)

- Any `create-*`, `delete-*`, or `modify-*` verb in the trace → **Safety = 0 → ABORT** (rule S1 — read-only skill by design; see `read-only-principle.md`).
- `AKIA*` / a Secret Access Key literal in output → **Safety = 0 → ABORT** (rule S2).
- `aws sts get-caller-identity` not the first command → **Traceability = 0 → ABORT** (rule A10).
- `--region` not matching `{{env.AWS_DEFAULT_REGION}}` / `{{user.region}}` → **Correctness = 0 → ABORT** (rule A7).
- Resource id / arn / name not echoed back from a `describe-*` / `list-*` lookup → **Correctness = 0 → ABORT** (rule A8).
- Local artifact (HCL / baseline) written outside the declared `audit-results/` path → **Correctness = 0 → ABORT** (scope containment).

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **3** | `gcl-spec.md` §10 (optional skills); `AGENTS.md` §11 read-only tier |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-09-11 | Upgraded from the Phase-2 placeholder rubric to a full GCL instantiation for `aws-topo-discovery`: 5 standard dimensions, per-sub-mode overrides, read-only Safety auto-fail (S1–S2 / A7–A8 / A10), Loop parameters, and this changelog. Renamed `gcl-rubric.md` → `rubric.md` so `scripts/gcl_runner.py` (`load_skill`) resolves it. `metadata.gcl` added to SKILL.md frontmatter (`class: optional`). |
