# GuardDuty Skill Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-guardduty-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §3 and §11 changelog.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for destructive ops | 0 / 0.5 / 1 | Resource id / detector-id / arn matches the user request. Read back via matching `describe-*` / `get-*` / `list-*` call (rule A8). |
| 2 | **Safety** | hard | **= 1** | 0 / 1 | Destructive ops MUST have explicit user confirmation in trace (`confirm=DELETE_GUARDDUTY_<RESOURCE> <id>`). |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `enable-guardduty` / `disable-guardduty` is state-machine; `create-*` returns existing resource on retry. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain `aws guardduty <op> --output json`, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-*` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Region supports GuardDuty; detector not already in target state; IAM `guardduty:` pre-reqs satisfied. |

## Hard termination rule

Per `gcl-spec.md` §3: if `Safety = 0`, the GCL loop MUST **ABORT** immediately,
regardless of total score, weighted aggregate, or remaining iterations. This
overrides any "best-so-far" return.

## Operation-specific overrides

| Operation | GCL Class | Safety Special Case |
|---|---|---|
| `list-*`, `describe-*`, `get-*`, `list-findings`, `get-findings` | read-only | None; default thresholds apply |
| `create-filter`, `update-filter`, `create-ip-set`, `update-ip-set`, `create-threat-intel-set`, `update-threat-intel-set`, `create-member`, `update-member`, `create-admin` | mutate | Correctness = 1.0 required; idempotency re-check required |
| `enable-guardduty`, `disable-guardduty` | state-change | Safety = 1.0 required; must not flip an in-progress detector |
| `delete-filter`, `delete-ip-set`, `delete-threat-intel-set`, `delete-member`, `delete-admin` | destructive | Safety = 1.0 required; trace MUST contain literal `confirm=DELETE_GUARDDUTY_<RESOURCE> <name>` |

## Safety special cases (auto-fail)

| Operation | Auto-fail condition |
|---|---|
| `delete-filter` | No `confirm=DELETE_GUARDDUTY_FILTER <filter-name>` in trace → **Safety = 0 → ABORT** |
| `delete-ip-set` | No `confirm=DELETE_GUARDDUTY_IPSET <ip-set-id>` in trace → **Safety = 0 → ABORT** |
| `delete-threat-intel-set` | No `confirm=DELETE_GUARDDUTY_THREATINTELSET <threat-intel-set-id>` in trace → **Safety = 0 → ABORT** |
| `delete-member` | No `confirm=DELETE_GUARDDUTY_MEMBER <account-id>` in trace → **Safety = 0 → ABORT** |
| `delete-admin` | No `confirm=DELETE_GUARDDUTY_ADMIN <account-id>` in trace → **Safety = 0 → ABORT** |
| `disable-guardduty` | No `confirm=DISABLE_GUARDDUTY <detector-id>` in trace → **Safety = 0 → ABORT** |
| any op | `--region` does not match `{{output.requested_region}}` (rule A7) → **Correctness = 0** |
| any op | Detector / filter / ip-set id was not echoed from a `get-*` / `list-*` lookup (rule A8) → **Correctness = 0** |
| any op | Plaintext secret (`GuardDutyDetector` admin credentials if any) appears in trace (rule A9) → **Safety = 0 → ABORT** |
| any op | `aws sts get-caller-identity` not first command in trace (rule A10) → **Traceability = 0** |

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §11 changelog 1.8.0 (Group 5 rollout) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Repo-wide AWS rules compliance

This rubric incorporates the following rules from `gcl-spec.md` §8 by reference:
- **A7** — `--region` must match `{{output.requested_region}}` or `{{env.AWS_DEFAULT_REGION}}`
- **A8** — resource id echoed back from a `describe-*` / `get-*` lookup
- **A9** — plaintext credentials must be masked in logs
- **A10** — `aws sts get-caller-identity` is the first trace command

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-12 | Initial GuardDuty rubric (Group 5 rollout). **Updated 2026-06-27:** migrated from continuous 1.0/0.8/0.7 weights to the spec-mandated 0/0.5/1 discrete scale; added explicit ABORT termination clause per `gcl-spec.md` §3; expanded per-operation overrides; added repo-wide A-rules reference table. |
