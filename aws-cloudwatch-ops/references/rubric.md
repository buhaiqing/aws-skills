# CloudWatch Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-cloudwatch-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-alarms` | 0 / 0.5 / 1 | Verifies alarm name / metric / log group matches user request (rule A8). Read back via `describe-alarms` (compare `MetricAlarms[].AlarmName`) / `describe-log-groups` (compare `LogGroups[].logGroupName`). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-alarms`, `delete-insight-rules`, `delete-dashboards`, `delete-canary`, `put-retention-policy`) MUST have explicit user confirmation in trace. `put-metric-alarm` with empty `--alarm-actions` (silent alarm) MUST warn. AWS rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `put-metric-alarm` with same `--alarm-name` replaces existing alarm (idempotent). `delete-alarms` is idempotent (no-op on already-deleted alarms). `put-metric-data` is additive (NOT idempotent — each call adds a data point). |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws cloudwatch <op>` command with args, exit code, raw response excerpt (≤ 2 KB, any metric data with credential-like values masked), and a final `describe-alarms` or `describe-log-groups` snapshot. `aws sts get-caller-identity` MUST be first (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: `--namespace` / `--metric-name` match existing metric, `--stat` is valid (SampleCount, Average, Sum, Minimum, Maximum), `--comparison-operator` is valid (GreaterThanThreshold, LessThanThreshold, etc.), `--period` is valid multiple (60, 120, 300, 600...), `--retention-period-in-days` is 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653, or 0 (never expire). |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `put-metric-alarm` | Correctness, **Spec Compliance** | `--alarm-actions` empty → warn silent-failure |
| `delete-alarms` | Correctness, Safety | Delete multiple alarms = high impact; confirm each |
| `put-composite-alarm` | Correctness | Referenced alarms must exist |
| `delete-insight-rules` | Correctness, Safety | Removes contributor data permanently |
| `put-retention-policy` | Correctness, Safety | Data loss for logs older than retention period |
| `start-query` | Correctness | Valid query string; log group exists |
| `put-dashboard` | Correctness, **Spec Compliance** | Dashboard body JSON valid; widget count within limits |
| `delete-dashboards` | Correctness, Safety | Confirm `DELETE_DASHBOARD <name>` |
| `delete-canary` | Correctness, Safety | Irreversible; confirm required |

## Safety special cases (auto-fail)

- `delete-alarms` **without** explicit `confirm=DELETE_ALARMS <names>` → **Safety = 0 → ABORT**
- `delete-insight-rules` without confirmation → **Safety = 0 → ABORT**
- `put-retention-policy` without user acknowledging data loss → **Safety = 0 → ABORT**
- `delete-dashboards` / `delete-canary` without confirmation → **Safety = 0 → ABORT**
- Resource name not echoed from `describe-*` / `list-*` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` mismatch → **Correctness = 0 → ABORT** (rule A7)
- Metric data or log content containing credential-like values in trace → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not first → **Traceability = 0 → ABORT** (rule A10)

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **3** | `gcl-spec.md` §10 (recommended skills) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-cloudwatch-ops` GCL |