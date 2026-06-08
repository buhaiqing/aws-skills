# Security Hub Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-securityhub-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | >= 0.5; **= 1.0 required** for `disable-security-hub`, `delete-insight`, `delete-action-target`, `disable-import-findings-for-product`, `delete-automation-rule`, `delete-configuration-policy` | 0 / 0.5 / 1 | Verifies resource ARN matches user request. Read back via `describe-*` / `get-*` and compare (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`disable-security-hub`, `delete-insight`, `delete-action-target`, `disable-import-findings-for-product`, `delete-automation-rule`, `delete-configuration-policy`) MUST have explicit user confirmation in trace. |
| 3 | **Idempotency** | soft | >= 0.5 | 0 / 0.5 / 1 | `enable-security-hub` returns same hub on re-run; `delete-*` is idempotent at API level. `batch-import-findings` with same `Id` updates existing finding. |
| 4 | **Traceability** | soft | >= 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws securityhub <op>` command, args, exit code, raw response excerpt (<= 2 KB), and a final `describe-hub` or `get-*` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | >= 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: region has Security Hub available; standard ARN is valid; control ID exists in the standard; finding schema version is `2018-10-08`; automation rule criteria use valid finding fields. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `enable-security-hub` | Correctness, Spec Compliance | Verify region supports Security Hub |
| `disable-security-hub` | Correctness, **Safety** | Loss of security aggregation; `confirm=DISABLE_SECURITY_HUB` in trace |
| `create-insight` | Correctness, Spec Compliance | Filters must use valid finding fields |
| `delete-insight` | Correctness, **Safety** | `confirm=DELETE_INSIGHT {{user.insight_arn}}` in trace |
| `create-action-target` | Correctness | Routine |
| `delete-action-target` | Correctness, **Safety** | `confirm=DELETE_ACTION_TARGET {{user.action_target_arn}}` in trace |
| `batch-import-findings` | Correctness, Spec Compliance | SchemaVersion must be `2018-10-08`; required fields present |
| `batch-update-findings` | Correctness | FindingIdentifiers must match existing findings |
| `enable-import-findings-for-product` | Correctness, Spec Compliance | ProductArn must be valid and available |
| `disable-import-findings-for-product` | Correctness, **Safety** | `confirm=DISABLE_PRODUCT {{user.product_subscription_arn}}` in trace |
| `create-automation-rule` | Correctness, Spec Compliance | Criteria use valid finding fields; RuleOrder unique |
| `delete-automation-rule` | Correctness, **Safety** | `confirm=DELETE_AUTOMATION_RULE {{user.automation_rule_arn}}` in trace |
| `create-configuration-policy` | Correctness, Spec Compliance | Valid SecurityHub configuration JSON |
| `delete-configuration-policy` | Correctness, **Safety** | Pre-flight: verify not attached to any target; `confirm=DELETE_POLICY {{user.policy_id}}` in trace |
| `update-standards-control` | Correctness | ControlStatus must be `ENABLED` or `DISABLED` |

## Safety special cases (auto-fail)

- `disable-security-hub` without `confirm=DISABLE_SECURITY_HUB` in trace
  -> **Safety = 0 -> ABORT**.
- `delete-insight` without `confirm=DELETE_INSIGHT <arn>` in trace
  -> **Safety = 0 -> ABORT**.
- `delete-action-target` without `confirm=DELETE_ACTION_TARGET <arn>` in trace
  -> **Safety = 0 -> ABORT**.
- `disable-import-findings-for-product` without `confirm=DISABLE_PRODUCT <arn>` in trace
  -> **Safety = 0 -> ABORT**.
- `delete-automation-rule` without `confirm=DELETE_AUTOMATION_RULE <arn>` in trace
  -> **Safety = 0 -> ABORT**.
- `delete-configuration-policy` without `confirm=DELETE_POLICY <id>` in trace
  -> **Safety = 0 -> ABORT**.
- Resource ARN in request not echoed from a `describe-*` / `get-*` lookup
  -> **Correctness = 0 -> ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
  -> **Correctness = 0 -> ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op
  -> **Traceability = 0 -> ABORT** (rule A10).

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (Phase 1 default for destructive skills) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial rubric for `aws-securityhub-ops` GCL rollout (required) |
