# ElastiCache Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-elasticache-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-replication-group` | 0 / 0.5 / 1 | Verifies `ReplicationGroupId` / `CacheClusterId` matches user request (rule A8). Read back via `describe-replication-groups` / `describe-cache-clusters` and compare against `ReplicationGroups[].ReplicationGroupId` and `CacheClusters[].CacheClusterId`. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-replication-group`, `delete-cache-cluster`, `delete-snapshot`) MUST have explicit user confirmation (`confirm=DELETE_RG <id>`, `confirm=DELETE_CLUSTER <id>`, `confirm=DELETE_SNAPSHOT <name>`) captured in trace. AWS rules A7 (region match), A8 (id echo), A9 (no secrets in trace), A10 (sts first) apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-replication-group` / `create-cache-cluster` MUST include consistent parameters (`EngineVersion`, `NodeType`, `NumCacheClusters`) on retry. Delete ops are idempotent at the API level. Score 0 if `--client-token` (or equivalent idempotency key) is not consistent across retries. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws elasticache <op>` command with args, exit code, raw response excerpt (≤ 2 KB, any `AuthToken` masked to `***<len>`), and a final `describe-replication-groups` or `describe-cache-clusters` snapshot. `aws sts get-caller-identity` MUST be first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: engine is `redis` or `memcached`, `--engine-version` is valid for engine, `--cache-node-type` is a valid instance type, `--cache-subnet-group-name` exists, `--num-cache-nodes` within service limits (default 6 per region for Redis, 20 for Memcached). |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-replication-group` | Correctness, **Spec Compliance** | Engine must be `redis`; num-cache-clusters ≥ 2 for HA |
| `create-cache-cluster` | Correctness, **Spec Compliance** | Engine check; subnet group check |
| `delete-replication-group` | Correctness, Safety, **Traceability** | Pre-delete: recommend `--final-snapshot-identifier` |
| `delete-cache-cluster` | Correctness, Safety | Pre-delete: recommend `--final-snapshot-identifier` |
| `delete-snapshot` | Correctness, Safety | Snapshot data lost |
| `modify-replication-group` | Correctness, **Safety** | `--apply-immediately` on running cluster needs confirm |
| `create-snapshot` | Correctness | Source cluster/group must exist and be available |

## Safety special cases (auto-fail)

- `delete-replication-group` / `delete-cache-cluster` without explicit `confirm=DELETE_RG <name>` / `confirm=DELETE_CLUSTER <name>` in trace → **Safety = 0 → ABORT**
- `modify-replication-group` with `--apply-immediately` without confirmation → **Safety = 0 → ABORT**
- Resource ID not echoed from a `describe-*` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` mismatch → **Correctness = 0 → ABORT** (rule A7)
- Secrets/credentials in trace → **Safety = 0 → ABORT** (rule A9)
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
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-elasticache-ops` GCL |