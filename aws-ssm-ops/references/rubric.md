# SSM Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-ssm-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5 | 0 / 0.5 / 1 | Verifies `InstanceId` / `CommandId` / `DocumentName` match user request (rule A8). Read back via `describe-instance-information` (compare `InstanceId`, `PingStatus`) / `list-command-invocations` (compare `CommandId`, `Status`). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`send-command` remote exec, `delete-parameter`, `cancel-command`) MUST have explicit user confirmation (`confirm=SEND_COMMAND <doc>`, `confirm=DELETE_PARAM <name>`, `confirm=CANCEL_COMMAND <id>`) in trace. `send-command` MUST pre-flight `PingStatus=Online`. `get-parameter --with-decryption` value masked to `***<len>` in trace. AWS rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `send-command` with same parameters creates separate invocations (not idempotent). `delete-parameter` is idempotent (no-op on retry). `put-parameter` with same `--name` and `--overwrite` updates existing (idempotent). |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws ssm <op>` command with args, exit code, raw response excerpt (≤ 2 KB, any command output with credential-like values masked), and a final `get-command-invocation` / `describe-parameters` snapshot. `aws sts get-caller-identity` MUST be first (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: valid SSM document name (`AWS-*` or custom), target instances have SSM Agent `PingStatus=Online`, `--timeout-seconds` within valid range (15 s to 48 h), `--parameters` well-formed JSON. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `send-command` | Correctness, Safety, **Traceability** | Remote execution — high blast radius; pre-flight SSM Agent check via `describe-instance-information` |
| `delete-parameter` | Correctness, Safety | Parameter data permanently lost |
| `cancel-command` | Correctness, Safety | Confirm cancellation with user |
| `start-session` | Correctness, Safety | Interactive session — confirm with user |
| `describe-instance-information` | Correctness | Read-only |
| `get-command-invocation` | Correctness | Read-only |
| `list-commands` | Correctness | Read-only |

## Safety special cases (auto-fail)

- `send-command` **without** explicit `confirm=SEND_COMMAND <instance-ids>` in trace → **Safety = 0 → ABORT**
- `send-command` targeting `*` or more than 50 instances without batch confirmation → **Safety = 0 → ABORT**
- `delete-parameter` without `confirm=DELETE_PARAMETER <name>` → **Safety = 0 → ABORT**
- `cancel-command` without user confirmation → **Safety = 0 → ABORT**
- Resource ID not echoed from a `describe-*` / `list-*` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` mismatch → **Correctness = 0 → ABORT** (rule A7)
- Command output containing credential-like values in trace → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not first → **Traceability = 0 → ABORT** (rule A10)

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-ssm-ops` GCL |