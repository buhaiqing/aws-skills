# EventBridge Ops Rubric (GCL)

> Instantiation of GCL rubric from `aws-skill-generator/references/gcl-spec.md` §3 for `aws-eventbridge-ops`.
> AWS rules A1–A10 in `gcl-spec.md` §8 apply by reference.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | Correctness | hard | ≥ 0.5 | 0 / 0.5 / 1 | Rule name, bus name, event pattern match request; read-back via `describe-rule` |
| 2 | Safety | hard | = 1 | 0 / 1 | Destructive ops MUST have `confirm=` in trace; rules A7, A8, A9, A10 |
| 3 | Idempotency | soft | ≥ 0.5 | 0 / 0.5 / 1 | `put-rule` is idempotent; `delete-rule` idempotent (404 on re-delete) |
| 4 | Traceability | soft | ≥ 0.5 | 0 / 0.5 / 1 | Command, args, exit code, response, post-state; sts first (A10) |
| 5 | Spec Compliance | soft | ≥ 0.5 | 0 / 0.5 / 1 | Target ARN valid, role ARN has iam:PassRole, max target count |

## Operation-specific overrides

| Operation | Required = 1.0 | Notes |
|---|---|---|
| `delete-rule` | Correctness, Safety | Must remove targets first; `confirm=DELETE_RULE <name>` |
| `delete-event-bus` | Correctness, Safety | Remove all rules first; `confirm=DELETE_BUS <name>` |
| `delete-schedule` | Correctness, Safety | `confirm=DELETE_SCHEDULE <name>` |
| `delete-pipe` | Correctness, Safety | `confirm=DELETE_PIPE <name>` |
| `remove-targets` | Correctness, Safety | `confirm=REMOVE_TARGETS <rule>` |
| `put-rule` | Correctness, Spec Compliance | Verify event pattern JSON validity |

## Safety special cases (auto-fail)

- `delete-rule` without `remove-targets` first → **Safety = 0 → ABORT**
- `delete-event-bus` without checking for existing rules → **Safety = 0**
- `--region` mismatch → **Correctness = 0** (A7)
- No `describe-rule` echo-back → **Correctness = 0** (A8)
- Credentials in trace → **Safety = 0** (A9)
- sts not first command → **Traceability = 0** (A10)

## Loop parameters

| Parameter | Value |
|---|---|
| max_iterations | 3 |
| Trace path | ./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json |