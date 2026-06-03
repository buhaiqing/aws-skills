# DynamoDB Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-dynamodb-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-table` / `delete-index` | 0 / 0.5 / 1 | Verifies `TableName` / `IndexName` matches. Read back via `describe-table` and compare (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-table`, `delete-index` / `update-table` with `GlobalSecondaryIndexUpdates: REMOVE`, throughput SHRINK, `delete-backup`, `delete-replication-group-member`, `update-time-to-live` enabling expiration) MUST have explicit user confirmation in trace. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-table` returns `ResourceInUseException` for existing table name; acceptable. `delete-table` is idempotent. `put-item` with same key overwrites; idempotent at the key level. `update-item` is NOT naturally idempotent (a `SET` is an overwrite but `ADD` / `REMOVE` / `DELETE` are order-dependent). |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws dynamodb <op>` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-table` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). For `delete-table`, trace MUST include item count + size snapshot. |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: throughput within `AccountMaxReadCapacityUnits` / `AccountMaxWriteCapacityUnits` quota; partition key + sort key are defined; GSI projection is `KEYS_ONLY` / `INCLUDE` / `ALL`; TTL attribute is `Number`. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-table` | Correctness, Spec Compliance | Refuse if any attribute is named `*password*` / `*secret*` / `*token*` / `*api_key*`; rubric treats attribute names with secret semantics as suspicious (rule A9) |
| `update-table` (throughput SHRINK to on-demand) | Correctness, **Safety** | Throttling risk on live traffic; pre-flight: read CloudWatch `ConsumedReadCapacityUnits` over 7 days |
| `update-table` (throughput SHRINK by > 50%) | Correctness, **Safety** | Same family; pre-flight required |
| `update-table` (`GlobalSecondaryIndexUpdates: REMOVE`) | Correctness, **Safety** | **GSI deletion is irreversible**; pre-flight: `describe-contributor-insights`; require `confirm=DELETE_GSI <table>:<index>` |
| `update-table` (`GlobalSecondaryIndexUpdates: UPDATE` with throughput SHRINK) | Correctness, **Safety** | Same family |
| `update-time-to-live` (enabling TTL) | Correctness, **Safety** | Pre-flight: confirm the TTL attribute is `Number` type and points to a timestamp; once enabled, items with `attr <= now` are removed within 48 h (irrecoverable without backup) |
| `update-time-to-live` (disabling) | Correctness | Reversible; no safety gate |
| `delete-table` | Correctness, Safety, **Traceability** | **IRREVERSIBLE**; require `confirm=DELETE_TABLE <table-name>` literal in trace; pre-flight: list Lambda event source mappings + Streams consumers + backups; capture item count + size |
| `delete-backup` | Correctness, Safety | Point-in-time recovery target; `confirm=DELETE_BACKUP <arn>` |
| `delete-replication-group-member` (Global Tables) | Correctness, Safety | Removes region from Global Table; `confirm=DELETE_REPLICA <table>:<region>` |
| `restore-table-from-backup` | Correctness | Routine |
| `restore-table-to-point-in-time` | Correctness | Routine |
| `update-item` with `REMOVE` action | Correctness, **Safety** | Removes attribute(s); pre-flight confirm if attribute name is in any "required" schema |
| `delete-item` | Correctness, Safety | Single-item delete; require confirm if key references a "core" entity |
| `batch-write-item` (large batch) | Correctness, **Traceability** | Trace MUST include total request count and PutRequest / DeleteRequest split |
| `transact-write-items` with `Delete` | Correctness, **Safety** | Transactional delete; require confirm if any Delete is on a "core" entity |

## Safety special cases (auto-fail)

- `delete-table` called without `confirm=DELETE_TABLE <table-name>` literal
  in trace → **Safety = 0 → ABORT**.
- `delete-table` called while `list-event-source-mappings` (Lambda
  consumers) returned non-empty without explicit override
  `confirm=DELETE_TABLE_WITH_TRIGGERS <table>` →
  **Correctness = 0 → ABORT**.
- `delete-table` called while `describe-table` shows
  `TableStatus != "ACTIVE"` (e.g. `CREATING`, `UPDATING`, `DELETING`) →
  **Correctness = 0 → ABORT**.
- `delete-table` while the table has any `GlobalSecondaryIndexes` or
  `LocalSecondaryIndexes` still defined → **Correctness = 0 → ABORT**
  (rubric demands the GSIs be deleted first; DynamoDB does this
  automatically in `delete-table` only for empty GSIs).
- `update-table` with `GlobalSecondaryIndexUpdates: REMOVE` without
  `confirm=DELETE_GSI <table>:<index>` → **Safety = 0 → ABORT**.
- `update-time-to-live` (enable) with the TTL attribute not of `Number`
  type → **Correctness = 0 → ABORT**.
- `update-time-to-live` (enable) with `Enabled=true` **without**
  `confirm=ENABLE_TTL <table>:<attr>` → **Safety = 0 → ABORT**.
- `TableName` / `IndexName` in the request not echoed from a
  `describe-table` / `list-tables` lookup → **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or
  `{{env.AWS_DEFAULT_REGION}}` → **Correctness = 0 → ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10).
- `put-item` / `update-item` with attribute name matching
  `*password*` / `*secret*` / `*token*` / `*api_key*` and value matching
  `AKIA*` or `*-----BEGIN .* PRIVATE KEY-----*` or any literal secret
  pattern → **Safety = 0 → ABORT** (rule A9). The rubric refuses to
  store literal secrets in DynamoDB; require SSM Parameter Store or
  Secrets Manager ARN instead.
- Item value (any) appears un-masked in the trace → **Safety = 0 → ABORT**
  (rule A9). Mask to `***<len>` only; capture the schema (attribute
  names + types) but not the values.

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (Phase 1 default) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-dynamodb-ops` GCL rollout (Phase 1, required, not pilot) |
