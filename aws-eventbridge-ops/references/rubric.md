# EventBridge Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-eventbridge-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL skill (AGENTS.md §11.5, recommended class, max_iter=3). See
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.
>
> **AWS rules A1–A10** in `gcl-spec.md` §8 apply by reference and are
> extended with EventBridge-specific rules EB1–EB8 below.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-rule` / `delete-event-bus` / `delete-schedule` / `delete-pipe` | 0 / 0.5 / 1 | Verifies `rule-name`, `event-bus-name`, `schedule-name`, `pipe-name`, `target-id` match the user request. Read back via `describe-rule`, `describe-event-bus`, `get-schedule`, `describe-pipe` and compare against ARN, State, and configuration. Event pattern JSON must be valid and match intent. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-rule`, `delete-event-bus`, `delete-api-destination`, `delete-connection`, `delete-archive`, `remove-targets`, `delete-schedule`, `delete-pipe`, `disable-rule` on critical paths) MUST have explicit user confirmation captured in trace. AWS-specific rules A7, A8, A9, A10 in `gcl-spec.md` §8 apply. EventBridge-specific safety rules EB1–EB8 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `put-rule` is idempotent (same name+bus updates existing rule). `put-targets` is idempotent (same Id replaces target). `delete-rule` is idempotent (returns success for non-existent rule after target cleanup). `create-schedule` and `create-pipe` require unique names — collision returns error, not idempotent. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws events` / `aws scheduler` / `aws pipes` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-*` snapshot. `aws sts get-caller-identity` MUST be the first command in the trace (rule A10). For target modifications, trace MUST include pre-modification target list. Score 1 only if all elements present. |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: event bus name follows naming rules (1–256 chars, no `aws.` prefix for custom); rule name unique per bus; schedule expression valid rate/cron/at format; target ARN valid and in same region; IAM role has `iam:PassRole` and service trust; pipe source/target compatibility verified. |

## EventBridge-specific Safety Rules (EB1–EB8)

| # | Rule | Description | Auto-fail |
|---|---|---|---|
| EB1 | **Target Cleanup Pre-flight** | `delete-rule` MUST first call `list-targets-by-rule` and `remove-targets` if any exist | Safety = 0 if targets exist at delete time |
| EB2 | **Event Bus Empty Pre-flight** | `delete-event-bus` MUST first call `list-rules` and delete all rules (with EB1 applied) | Safety = 0 if rules exist at delete time |
| EB3 | **Connection Dependency Check** | `delete-connection` MUST verify no API destinations reference it via `describe-connection` or `list-api-destinations` | Safety = 0 if connection still referenced |
| EB4 | **Schedule Active Invocation Guard** | `delete-schedule` on a schedule with recent invocations (within last hour) requires explicit `confirm=DELETE_SCHEDULE_ACTIVE <name>` | Safety = 0 if active and not confirmed |
| EB5 | **Pipe Event Flow Impact** | `delete-pipe` or `update-pipe` that changes `Source` or `Target` requires `confirm=PIPE_FLOW_IMPACT <name>` | Safety = 0 if flow-changing and not confirmed |
| EB6 | **Archive Data Loss** | `delete-archive` is irreversible — events cannot be recovered; requires `confirm=DELETE_ARCHIVE <name>` | Safety = 0 without confirmation |
| EB7 | **Cross-Account Permission Guard** | `put-permission` with `Principal: *` or broad account patterns requires `confirm=BUS_PERMISSION_PUBLIC <bus-name>` | Safety = 0 for overly permissive without confirmation |
| EB8 | **Managed Rule Protection** | `delete-rule` / `disable-rule` on rules with `ManagedBy` attribute (AWS-managed) → **Correctness = 0** | Correctness = 0 (not Safety) |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `put-rule` (Create/Update) | Correctness, Spec Compliance | Event pattern JSON must be valid; schedule expression must parse; state must be ENABLED or DISABLED |
| `put-rule` (Modify existing) | Correctness, Safety, Spec Compliance | Changing event pattern on active rule = routing change; requires `confirm=MODIFY_RULE <name>` |
| `delete-rule` | Correctness, Safety, **Traceability** | Pre-flight: `list-targets-by-rule`; must remove all targets first (EB1); `confirm=DELETE_RULE <name>` |
| `enable-rule` / `disable-rule` | Correctness, Safety (if disable) | Disable on production-critical rules requires confirmation; EB8 applies for AWS-managed rules |
| `put-targets` | Correctness, Spec Compliance | Target ARN must be valid; IAM role must have trust policy for `events.amazonaws.com` (or `scheduler.amazonaws.com` for schedules); max 5 targets per rule (soft limit) |
| `remove-targets` | Correctness, Safety | Pre-flight must list current targets; `confirm=REMOVE_TARGETS <rule>`; specify exact target IDs |
| `create-event-bus` | Correctness, Spec Compliance | Name cannot start with `aws.` (reserved); cannot be `default` (already exists) |
| `delete-event-bus` | Correctness, Safety, **Traceability** | Pre-flight: `list-rules` on bus; must delete all rules first (EB2); cannot delete `default` bus; `confirm=DELETE_BUS <name>` |
| `put-permission` | Correctness, Safety | EB7 applies for `Principal: *` or overly broad patterns; verify statement-id uniqueness |
| `remove-permission` | Correctness | Statement ID must exist; not destructive but verify impact on cross-account flows |
| `create-connection` | Correctness, Spec Compliance | Auth type must be API_KEY, BASIC, or OAUTH_CLIENT_CREDENTIALS; secret values masked in trace (A9) |
| `delete-connection` | Correctness, Safety | EB3 applies — check API destination dependencies; `confirm=DELETE_CONNECTION <name>` |
| `create-api-destination` | Correctness, Spec Compliance | HTTP method must be valid; endpoint must be HTTPS; connection ARN must exist; rate limit 1–300 invocations/sec |
| `delete-api-destination` | Correctness, Safety | Check if any rules reference it; `confirm=DELETE_API_DEST <name>` |
| `create-archive` | Correctness, Spec Compliance | Event source ARN must be valid event bus; retention days 1–1200 |
| `delete-archive` | Correctness, Safety | EB6 applies — irreversible data loss; `confirm=DELETE_ARCHIVE <name>` |
| `start-replay` | Correctness, Spec Compliance | Source archive must exist; destination event bus must exist; time range must be valid |
| `create-schedule` | Correctness, Spec Compliance | Schedule expression rate/cron/at format; target ARN valid; role ARN with `scheduler.amazonaws.com` trust; flexible time window valid |
| `update-schedule` | Correctness, Safety | Changing target or schedule expression on active schedule requires `confirm=MODIFY_SCHEDULE <name>` |
| `delete-schedule` | Correctness, Safety | EB4 applies for active schedules; `confirm=DELETE_SCHEDULE <name>` |
| `create-pipe` | Correctness, Spec Compliance | Source ARN valid (SQS, DynamoDB, Kinesis, MQ, MSK, S3); target ARN valid; enrichment/filtering optional; role ARN with `pipes.amazonaws.com` trust |
| `update-pipe` | Correctness, Safety | EB5 applies for source/target changes; `confirm=UPDATE_PIPE <name>` |
| `delete-pipe` | Correctness, Safety | EB5 applies — stops event flow; `confirm=DELETE_PIPE <name>` |
| `describe-*` / `list-*` | Correctness | Read-only; no Safety requirement but verify correct resource identifier |

## Safety special cases (auto-fail)

- `delete-rule` called without first calling `list-targets-by-rule` and
  `remove-targets` when targets exist → **Safety = 0 → ABORT** (EB1)
- `delete-event-bus` called without first deleting all rules on that bus
  (via `list-rules` + EB1 for each) → **Safety = 0 → ABORT** (EB2)
- `delete-connection` called while API destinations still reference it
  (via `describe-connection` or `list-api-destinations`) → **Safety = 0 → ABORT** (EB3)
- `delete-schedule` on a schedule with invocations in the last hour without
  `confirm=DELETE_SCHEDULE_ACTIVE <name>` → **Safety = 0 → ABORT** (EB4)
- `delete-pipe` or `update-pipe` changing source/target without
  `confirm=PIPE_FLOW_IMPACT <name>` → **Safety = 0 → ABORT** (EB5)
- `delete-archive` without `confirm=DELETE_ARCHIVE <name>` → **Safety = 0 → ABORT** (EB6)
- `put-permission` with `Principal: "*"` or overly broad account patterns
  without `confirm=BUS_PERMISSION_PUBLIC <bus-name>` → **Safety = 0 → ABORT** (EB7)
- `delete-rule` or `disable-rule` on an AWS-managed rule (has `ManagedBy`
  attribute) → **Correctness = 0 → ABORT** (EB8)
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`,
  OR resource region does not match `--region` → **Correctness = 0 → ABORT** (rule A7)
- Resource name in the request was not echoed back from a `describe-*` or
  `list-*` lookup → **Correctness = 0 → ABORT** (rule A8)
- `AuthParameters` containing `ApiKeyValue`, `Password`, `ClientSecret`, or
  `AccessToken` appears unmasked in the trace → **Safety = 0 → ABORT** (rule A9;
  mask to `***<len>`)
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10)

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **3** | `AGENTS.md` §11.5 (recommended class for EventBridge) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial comprehensive rubric for `aws-eventbridge-ops` with EventBridge-specific safety rules EB1–EB8, detailed operation-specific overrides for all EventBridge operations (rules, targets, buses, schedules, pipes, archives, API destinations, connections), and reference to AWS rules A1–A10 |
