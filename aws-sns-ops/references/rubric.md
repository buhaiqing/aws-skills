# SNS Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-sns-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-topic` | 0 / 0.5 / 1 | Verifies `TopicArn` matches user request (rule A8). Read back via `aws sns get-topic-attributes` and compare `TopicArn`. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-topic`, `unsubscribe`) MUST have explicit user confirmation (`confirm=DELETE_TOPIC <arn>`, `confirm=UNSUBSCRIBE <arn>`) captured in trace. AWS rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-topic` returns same `TopicArn` for same `--name` (idempotent). `delete-topic` is idempotent (no-op on already deleted topic). `publish` is NOT idempotent (each call is a new message). |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws sns <op>` command with args, exit code, raw response excerpt (≤ 2 KB, any `MessageBody` or `MessageAttributes` masked), and a final `get-topic-attributes` or `list-subscriptions-by-topic` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: topic name uses valid characters (alphanumeric, hyphens, underscores), subscription protocol is valid (`email`, `email-json`, `sqs`, `lambda`, `http`, `https`, `sms`, `application`, `firehose`), endpoint format matches protocol requirements. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-topic` | Correctness | Topic name valid; attributes (FIFO, delivery policy) valid |
| `delete-topic` | Correctness, Safety, **Traceability** | Pre-delete: list subscriptions; confirm `DELETE <topic-arn>` |
| `list-topics` | Correctness | Read-only; light verification |
| `publish` | Correctness, **Spec Compliance** | Message ≤ 256 KB; `MessageStructure=json` for multi-protocol |
| `subscribe` | Correctness, **Spec Compliance** | Protocol-endpoint match; pending confirmation |
| `unsubscribe` | Correctness, Safety | Confirm impact on downstream subscribers |
| `set-subscription-attributes` | Correctness | `FilterPolicy` JSON valid |
| `confirm-subscription` | Correctness | Token valid; `AuthenticateOnUnsubscribe` |

## Safety special cases (auto-fail)

- `delete-topic` **without** an explicit `confirm=DELETE_TOPIC <topic-arn>` in the trace → **Safety = 0 → ABORT**
- `unsubscribe` **without** confirmation → **Safety = 0 → ABORT** when the subscription is the only one for a critical endpoint
- `TopicArn` not echoed from a `list-topics` / `get-topic-attributes` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` → **Correctness = 0 → ABORT** (rule A7)
- `MessageBody` or `MessageAttributes` containing credential-like values appears in trace → **Safety = 0 → ABORT** (rule A9)
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
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-sns-ops` GCL |