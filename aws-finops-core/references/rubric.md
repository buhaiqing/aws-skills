# aws-finops-core Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3. Read-only composite skill
> (no destructive AWS operations). Delegates to base skills for any
> resource-level actions.

## Rubric version

`v1`

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5 | 0 / 0.5 / 1 | Correct API calls, correct time periods, correct JSON paths, correct region matching `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Read-only composite: no destructive ops. Safety = 0 only if a delegated base skill attempts a destructive op without user confirmation. |
| 3 | **Idempotency** | soft | ≥ 0.8 | 0 / 0.5 / 1 | Repeated runs with same period/targets yield same result. No side effects. |
| 4 | **Traceability** | soft | ≥ 0.8 | 0 / 0.5 / 1 | Trace includes all CLI calls with exit codes, response excerpts, and delegation chains. |
| 5 | **Spec Compliance** | soft | ≥ 0.8 | 0 / 0.5 / 1 | Follows `2026-07-19-finops-core-design.md`; all 5 idle resource types covered; anomaly baseline logic correct. |

## Loop parameters

| Parameter | Value |
|---|---|
| `max_iterations` | 3 |
| `gcl_tier` | recommended |
| Rubric version | v1 |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-19 | Initial rubric for aws-finops-core |
