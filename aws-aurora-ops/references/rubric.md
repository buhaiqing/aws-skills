# Aurora Ops Rubric (GCL)

> Instantiation of `aws-skill-generator/references/gcl-spec.md` §3 for `aws-aurora-ops`.

## Rubric version

`v1`

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0** for `delete-db-cluster` | 0 / 0.5 / 1 | `DBClusterIdentifier` echoed from `describe-db-clusters` (rule A8) |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops require explicit confirmation in trace |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-db-cluster` idempotent on `DBClusterAlreadyExists`; `delete-*` idempotent at API |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Full CLI command, exit code, response excerpt; `sts get-caller-identity` first (A10) |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Engine is `aurora-*`; subnet group spans ≥2 AZs; password is Secrets Manager ARN |

## Operation-specific overrides

| Operation | Required = 1.0 | Notes |
|---|---|---|
| `create-db-cluster` | Correctness, Spec Compliance | Engine must be `aurora-mysql` or `aurora-postgresql`; password = Secrets Manager ARN |
| `create-db-instance` (cluster member) | Correctness | Must reference existing cluster; engine matches cluster |
| `modify-db-cluster` | Correctness | Changing backup retention / HTTP endpoint is reversible |
| `failover-db-cluster` | Correctness, **Safety** | Brief outage; confirm required |
| `stop-db-cluster` | Correctness, **Safety** | Reversible within 7 days |
| `delete-db-cluster` (with snapshot) | Correctness, Safety, Traceability | Default `--final-db-snapshot-identifier`; deletes all members |
| `delete-db-cluster` (`--skip-final-snapshot`) | Correctness, Safety | Needs literal `DELETE_NO_SNAPSHOT <cluster-id>` (rule A14; supersedes legacy A5 reference) |
| `delete-db-cluster-snapshot` | Correctness, Safety | `confirm=DELETE_DB_CLUSTER_SNAPSHOT <snap-id>` |
| `delete-db-cluster-parameter-group` | Correctness, Safety | Pre-flight: no cluster references group |
| `delete-global-cluster` | Correctness, Safety | All secondaries removed first |
| `remove-from-global-cluster` | Correctness, **Safety** | Breaks cross-region DR link |
| `backtrack-db-cluster` | Correctness, **Safety** | Irreversible data rewind within window |
| `restore-db-cluster-to-point-in-time` | Correctness | `RestoreTime` ≤ `LatestRestorableTime` |

## Safety special cases (auto-fail)

- `delete-db-cluster` with `--skip-final-snapshot` without `DELETE_NO_SNAPSHOT <cluster-id>` → **Safety = 0 → ABORT** (rule A5)
- Cluster tagged `env=prod` deleted without `confirm=DELETE_PROD_CLUSTER <id>` → **Safety = 0 → ABORT**
- `delete-db-cluster-parameter-group` while cluster still uses it → **Correctness = 0 → ABORT**
- Literal `MasterUserPassword` in trace → **Safety = 0 → ABORT** (rule A9)
- `--region` mismatch → **Correctness = 0 → ABORT** (rule A7)
- No `aws sts get-caller-identity` before mutating op → **Traceability = 0 → ABORT** (rule A10)
- `failover-db-cluster` without confirmation → **Safety = 0 → ABORT**
- `backtrack-db-cluster` without confirmation → **Safety = 0 → ABORT**

## Loop parameters

| Parameter | Value |
|---|---|
| `max_iterations` | **2** |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |
| Rubric version | `v1` |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-13 | Initial rubric for `aws-aurora-ops` |
