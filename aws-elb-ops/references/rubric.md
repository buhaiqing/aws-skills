# ELB Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-elb-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-load-balancer` / `deregister-targets` | 0 / 0.5 / 1 | Verifies arn, target id, listener arn. Read back via `describe-load-balancers` / `describe-target-health` (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-load-balancer`, `deregister-targets` ≥ 1, `delete-listener`, `delete-rule`, `delete-target-group`, `delete-trust-store`) MUST have explicit user confirmation. **Drain threshold critical**: large deregistration batches can drain production traffic. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-load-balancer` returns same `LoadBalancerArn`; `delete-load-balancer` is idempotent; `register-targets` / `deregister-targets` are idempotent. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws elbv2 <op>` (or `aws elb <op>` for Classic), args, exit code, raw response excerpt (≤ 2 KB), and final `describe-target-health` snapshot for register/deregister (rule A10 — sts first). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: target group health check protocol matches target type (`HTTP` / `HTTPS` for ALB, `TCP` for NLB); listener port 1-65535; rule priority unique within listener; target group `Matcher.HttpCode` is valid. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-load-balancer` | Correctness, Spec Compliance | Scheme is `internal` / `internet-facing`; subnets span ≥ 2 AZs; SG allow at least 1 inbound rule |
| `create-listener` | Correctness, Spec Compliance | Default action is `forward` / `redirect` / `fixed-response` / `authenticate-cognito` |
| `create-rule` | Correctness, Spec Compliance | Priority is unique and within range |
| `register-targets` (small batch) | Correctness | Routine; trace target arn list |
| `deregister-targets` (small batch, < 50% of healthy targets) | Correctness, **Safety** | Confirm; pre-flight: `describe-target-health` to check `TargetHealth.State` and current `healthy` count |
| `deregister-targets` (≥ 50% of healthy targets) | Correctness, Safety, **Traceability** | **CRITICAL DRAIN**; require `confirm=DEREGISTER_DRAIN <target-group-arn> count=<n>/<total>`; pre-flight MUST compute `(to-deregister / current-healthy)` ratio and emit a warning if ≥ 50% (rule A12) |
| `deregister-targets` (ALL healthy targets) | Correctness, Safety, **Traceability** | **TOTAL OUTAGE**; require `confirm=DEREGISTER_ALL <target-group-arn>` |
| `deregister-targets` (target currently has `draining` state) | Correctness | Wait for drain to complete (ConnectionDraining enabled, default 300 s); do not register a new target until drain finishes |
| `delete-load-balancer` | Correctness, Safety, **Traceability** | `confirm=DELETE_LB <lb-arn>`; pre-flight: list listeners + target groups; refuse if listeners exist (delete listeners first) |
| `delete-listener` | Correctness, Safety | `confirm=DELETE_LISTENER <listener-arn>`; pre-flight: list rules; refuse if rules exist |
| `delete-rule` (default rule) | Correctness, **Safety** | Refuse — default rule cannot be deleted, only modified |
| `delete-rule` (non-default) | Correctness, Safety | `confirm=DELETE_RULE <rule-arn>` |
| `delete-target-group` (in use) | Correctness, **Safety** | Pre-flight: list load balancers / rules referencing the target group; refuse if any |
| `delete-trust-store` (in use) | Correctness, **Safety** | Same family as target group; pre-flight checks |
| `modify-load-balancer-attributes` (access logs, deletion protection) | Correctness, **Safety** | Disabling deletion protection is irreversible in effect; require `confirm=DISABLE_DELETION_PROTECTION <lb-arn>` |
| `modify-target-group-attributes` (deregistration delay change) | Correctness, **Safety** | Lowering `deregistration_delay.timeout_seconds` from 300 to 0 cuts in-flight connections; require confirm |

## Safety special cases (auto-fail)

- `deregister-targets` where the batch size is ≥ 50% of currently
  `healthy` targets without `confirm=DEREGISTER_DRAIN <tg-arn> count=<n>/<total>`
  → **Safety = 0 → ABORT**.
- `deregister-targets` where ALL `healthy` targets are being removed
  without `confirm=DEREGISTER_ALL <tg-arn>` → **Safety = 0 → ABORT**
  (this is a total outage for the target group).
- `delete-load-balancer` while any listener exists (rubric: list
  listeners first; refuse if non-empty) → **Correctness = 0 → ABORT**.
- `delete-rule` called on the **default rule** (priority = `default`)
  → **Correctness = 0 → ABORT** (default rule cannot be deleted).
- `delete-target-group` called while any load balancer / listener rule
  references it → **Correctness = 0 → ABORT**.
- `delete-trust-store` called while any listener uses it (mTLS) →
  **Correctness = 0 → ABORT**.
- `modify-load-balancer-attributes` disabling `deletion_protection`
  without `confirm=DISABLE_DELETION_PROTECTION <lb-arn>` →
  **Safety = 0 → ABORT**.
- LB arn / target id / listener arn in the request not echoed from
  `describe-*` lookup → **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or
  `{{env.AWS_DEFAULT_REGION}}` → **Correctness = 0 → ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10).
- LB `Tags` value matching `*password*` / `*secret*` / `*token*` and
  containing literal secret → **Safety = 0 → ABORT** (rule A9).
- Target group `Matcher.HttpCode` value is `200-399` (overly permissive,
  treats 3xx as healthy) without `confirm=PERMISSIVE_MATCHER <tg-arn>` →
  **Spec Compliance = 0 → ABORT**.

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **3** | `gcl-spec.md` §10 (Phase 1 default for `recommended` skills) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-elb-ops` GCL rollout (Phase 1, **recommended**, not pilot) |
