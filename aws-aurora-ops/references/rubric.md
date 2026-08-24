# Amazon Aurora Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-aurora-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for destructive ops | 0 / 0.5 / 1 | Verifies the resource id / arn / name matches the user request. Read back via the matching `describe-*` / `get-*` / `list-*` call and compare (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops MUST have explicit user confirmation in trace. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Service-specific: see per-op overrides below. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws aurora <op>` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-*` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: region supports the resource, IAM pre-reqs satisfied, quota within limits. |

## Operation-specific overrides

<!-- LLM_FILL: Operation-specific overrides (auto-generated) -->
<!-- TODO: list every operation in this skill and its required-dimensions=1.0 cells. -->

## Safety special cases (auto-fail)

<!-- LLM_FILL: Safety special cases (auto-generated) -->
<!-- TODO: list every AWS-API silent-failure / data-loss pattern this service can hit. -->

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (Phase 1 default) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-aurora-ops` GCL rollout (Phase 1) |
