---
name: aws-aurora-ops
description: >-
  Use when operating Amazon Aurora database clusters (Aurora MySQL or Aurora
  PostgreSQL); create or delete Aurora clusters; add reader instances;
  perform cluster failover; configure Serverless v2 scaling; manage Global
  Database; create or restore cluster snapshots; tune cluster parameter groups;
  enable Backtrack (MySQL) or Data API; diagnose Aurora replica lag, connection
  storms, Serverless capacity, or Global DB lag (AIOps), even if the user says
  "Aurora cluster", "Aurora reader", "Global Database", or "Aurora Serverless"
  instead of "RDS".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to RDS endpoints.
metadata:
  author: aws
  version: "1.2.0"
  last_updated: "2026-06-27"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: [health-check, rca, self-heal, change-impact, compliance-scan, capacity-forecast]
    produces_facts: [metric, state, event, finding]
    idempotency_ttl: PT24H
    destructive_ops_require_confirm: true
---

# AWS Aurora Operations Skill

## Common JSON Paths (Centralized)

```
# Cluster:   .DBClusters[0].{Status,Endpoint,ReaderEndpoint,DBClusterMembers,Engine,EngineVersion}
# Instance:  .DBInstances[0].{DBInstanceStatus,DBInstanceClass,PromotionTier,IsClusterWriter,Endpoint}
# Snapshots: .DBClusterSnapshots[0].{Status,SnapshotCreateTime,Engine}
# Global:    .GlobalClusters[0].{GlobalClusterIdentifier,GlobalClusterMembers,Status}
# Failover:  .DBCluster.{Status,Endpoint}
```

## Trigger & Scope

### SHOULD Use When
- User mentions "Aurora", "Aurora MySQL", "Aurora PostgreSQL", "Aurora cluster"
- Task involves **DB clusters** (writer + readers), not standalone RDS instances
- Keywords: aurora, cluster, reader, writer, failover, global database, serverless v2, backtrack, replica lag
- Aurora Serverless v2 scaling, custom cluster endpoints, or Data API (HTTP endpoint)
- Cluster snapshot create/restore/PITR, cluster parameter groups
- **(AIOps)** Replica lag, connection saturation (incl. RDS Proxy path), slow queries on cluster writer
- **(AIOps)** Serverless v2 ACU at ceiling, Global DB replication lag, backup compliance scan
- **(AIOps)** FinOps: idle readers, over-provisioned Serverless MaxCapacity

### SHOULD NOT Use When
- Standalone RDS (MySQL/PostgreSQL/MariaDB/Oracle/SQL Server, non-Aurora) → `aws-rds-ops`
- DynamoDB → `aws-dynamodb-ops` | ElastiCache → `aws-elasticache-ops`
- DocumentDB / Neptune → not Aurora (different engines)

### Delegation
- Security groups → `aws-ec2-ops` | IAM / IAM DB auth → `aws-iam-ops` | KMS → `aws-kms-ops`
- CloudWatch alarms / PI → `aws-cloudwatch-ops` | Secrets → `aws-secretsmanager-ops`
- VPC subnet groups → `aws-vpc-ops` | Full-chain patrol → `aws-aiops-cruise`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.DBClusterIdentifier}}` | User input | Ask once; reuse |
| `{{user.DBInstanceIdentifier}}` | User input | Writer or member instance id |
| `{{user.DBEngine}}` | User input | `aurora-mysql` or `aurora-postgresql` |
| `{{user.replica_lag_threshold_ms}}` | User input | Default: 1000 |
| `{{user.serverless_max_cap_ceiling}}` | User input | AUTO_HEAL cap for MaxCapacity (default: 64) |
| `{{output.ClusterEndpoint}}` | Last API response | `.DBClusters[0].Endpoint` |
| `{{output.ReaderEndpoint}}` | Last API response | `.DBClusters[0].ReaderEndpoint` |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity --output json`. Verify engine via `describe-db-engine-versions --engine {{user.DBEngine}}`.

**Execute (CLI primary)**: [references/aws-cli-usage.md](references/aws-cli-usage.md)

**Execute (boto3 fallback)**: After 3 CLI failures — [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md)

**Validate**: Poll `describe-db-clusters` until `Status=available` (max 30 min) or deleted (max 20 min). `aws rds wait db-cluster-available`.

**Recover**:
| Error | Action |
|-------|--------|
| DBClusterAlreadyExists / InvalidDBClusterState | HALT |
| InvalidDBClusterStateFault (failover) | Wait for `available`; retry once |
| Throttling (429) | Backoff, max 3 retries |
| 5xx Internal | Retry 3x; HALT |

## Scope

| Operation / Scenario | Safety Gate | AIOps tier |
|---------------------|-------------|------------|
| Create cluster + instances | Engine/subnet/SG validation | — |
| Add/modify reader or writer | Brief outage possible | AI_ASSIST |
| Enable Performance Insights (writer) | Reboot may be required | AUTO_HEAL |
| Raise Serverless v2 MaxCapacity | Cap ≤ `{{user.serverless_max_cap_ceiling}}` | AUTO_HEAL |
| Replica lag remediation (add reader) | None | AI_ASSIST |
| Failover cluster | **Human confirm** | MANUAL |
| Stop/start cluster | Stop: **Human confirm** | MANUAL |
| Delete cluster | **Human confirm + final snapshot** | MANUAL |
| Backtrack (MySQL) | **Human confirm** | MANUAL |
| Global DB detach / delete | **Human confirm** | MANUAL |
| Backup compliance scan | Read-only | MANUAL report |

## Safety Gates

**Delete cluster** — before `delete-db-cluster`:
1. Display: "Deleting {{user.DBClusterIdentifier}} removes writer and all readers"
2. Default: `--final-db-snapshot-identifier`; `--skip-final-snapshot` only with `DELETE_NO_SNAPSHOT {{user.DBClusterIdentifier}}`
3. Confirm: `DELETE {{user.DBClusterIdentifier}}`

**Failover** — confirm: `FAILOVER {{user.DBClusterIdentifier}}`

**Backtrack** — confirm: `BACKTRACK {{user.DBClusterIdentifier}} to {{user.BacktrackTime}}`

## Cross-Skill Orchestration

| Scenario | Chain |
|----------|-------|
| Aurora slow query (writer) | aurora(PI) → cloudwatch → aurora(params) — PI detail: `aws-rds-ops` §SQL Slow Query |
| Replica lag RCA | aurora(metrics) → aurora(describe members) → aurora(add reader) |
| Connection storm + Proxy | aurora(proxy+cluster) → secretsmanager → vpc |
| API latency (suspect DB) | elb → ec2 → aurora |
| Global DB DR | aurora(global) → route53 → cloudwatch |
| Full-chain patrol | `aws-aiops-cruise` → delegate aurora for `RDS-PROXY-AURORA-*` |

## AIOps Scenarios

See [references/prompt-examples.md](references/prompt-examples.md) (8 scenarios) and [layered-inspection-template.md](references/layered-inspection-template.md).

AIOps loop: **Collect metrics → Detect (rule ID) → RCA → Decision tier → Action → Feedback**

## Quality Gate (GCL)

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops need `confirm=<OPERATION> <resource>` in trace. AWS rules A5/A7/A8/A9/A10 per `aws-skill-generator/references/gcl-spec.md` §8.

## AIOps Delegate Contract

Orchestrator-aware. When invoked by `aws-aiops-orchestrator`, honor the delegate contract in [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md).

**Recognition**: parse `aiops_delegate:` — `request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope.resource_ids`, `trace_id`.

**Rules**:
1. **Idempotency**: writes accept `idempotency_key`; duplicate within 24h → `deduplicated: true`
2. **Confirmation**: delete/failover/backtrack/global detach require `confirmation_token`
3. **Tier**: MANUAL = read-only; AI_ASSIST = recommend (write only with token); AUTO_HEAL = non-destructive writes (Serverless MaxCapacity, enable PI) without token
4. **Trace**: propagate `trace_id` in User-Agent
5. **Output**: always append `aiops_context:` JSON block

Runbooks: [aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)

| Runbook | Trigger | Tier | Goal |
|---------|---------|------|------|
| RB-023 | FD-15, AURORA-LAG-01 | AI_ASSIST | Replica lag RCA + add reader |
| RB-024 | PD-08, AURORA-SLV2-01 | AUTO_HEAL | Raise Serverless MaxCapacity |
| RB-025 | FD-16, RDS-PROXY-AURORA-01 | MANUAL | Writer failure / controlled failover |
| RB-026 | PD-09, AURORA-GDB-01 | MANUAL | Global DB lag / DR review |
| RB-027 | PD-04, RDS-PROXY-AURORA-02 | AI_ASSIST | Proxy + Aurora connection storm |

Incident output MUST conform to [aws-aiops-cruise/references/incident-schema.md](../aws-aiops-cruise/references/incident-schema.md) (`resource_type: Aurora`, `delegate_skill: aws-aurora-ops`).

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded engine versions/ports — use `describe-db-engine-versions` / `describe-db-clusters`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Reference Files

- [Prompt Examples (AIOps)](references/prompt-examples.md)
- [Layered Inspection](references/layered-inspection-template.md)
- [AWS CLI Usage](references/aws-cli-usage.md) — includes AIOps metric collection
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md) — AIOps Metrics Map
- [Troubleshooting](references/troubleshooting.md)
- [Example Config](assets/example-config.yaml)
