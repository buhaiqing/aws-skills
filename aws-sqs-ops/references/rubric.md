# SQS Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-sqs-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-queue` | 0 / 0.5 / 1 | Verifies `QueueUrl` matches user request (rule A8). Read back via `aws sqs get-queue-url` and compare `QueueUrl` against the requested queue name. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-queue`, `purge-queue`) MUST have explicit user confirmation (`confirm=DELETE_QUEUE <name>`, `confirm=PURGE_QUEUE <name>`) captured in trace. `purge-queue` irreversibly deletes all messages — require additional acknowledgement. AWS rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-queue` MUST include `--attributes` consistently on retry (`--attributes` changes update the existing queue). `delete-queue` / `purge-queue` are idempotent at the API level. Score 0 if attribute drift between retries. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws sqs <op>` command with args, exit code, raw response excerpt (≤ 2 KB, any `MessageBody` or `ReceiptHandle` masked), and a final `get-queue-attributes` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: queue name follows FIFO naming convention (`<name>.fifo` for FIFO), `--attributes` values within valid ranges (VisibilityTimeout 0-43200, MessageRetentionPeriod 60-1209600, MaximumMessageSize 1024-262144, DelaySeconds 0-900). |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-queue` | Correctness, **Idempotency** | `--attributes` must be consistent on retry |
| `get-queue-url` | Correctness | Queue name must match `list-queues` output |
| `send-message` | Correctness, **Spec Compliance** | Message body ≤ 256 KB; FIFO queues require `--message-group-id` |
| `receive-message` | Correctness | Use `--wait-time-seconds` 20 for long polling |
| `delete-message` | Correctness, **Safety** | `ReceiptHandle` MUST be from a `receive-message` call |
| `delete-queue` | Correctness, Safety, **Traceability** | Include pre-delete state snapshot |
| `purge-queue` | Correctness, Safety | All messages lost — confirm with user |
| `set-queue-attributes` | Correctness, **Spec Compliance** | Valid attribute values only |

## Safety special cases (auto-fail)

- `delete-queue` **without** an explicit `confirm=DELETE_QUEUE <queue-name>` in the trace → **Safety = 0 → ABORT**
- `purge-queue` **without** an explicit `confirm=PURGE_QUEUE <queue-name>` in the trace → **Safety = 0 → ABORT**
- `QueueUrl` not echoed from a `get-queue-url` / `list-queues` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` → **Correctness = 0 → ABORT** (rule A7)
- Any `MessageBody`, `MessageAttributes`, or `MessageDeduplicationId` containing credential-like values appears in trace → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not run before any mutating op → **Traceability = 0 → ABORT** (rule A10)

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (Phase 1 default for destructive skills) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-sqs-ops` GCL |