---
name: aws-rds-ops
description: >-
  Use when the user needs to create, manage, or delete managed relational
  databases in AWS (RDS); configure MySQL, PostgreSQL, MariaDB, Oracle, or
  Aurora clusters; set up Multi-AZ deployments for high availability; create
  or restore database snapshots; manage read replicas; configure parameter
  groups and option groups; set up automated backups; or perform database
  recovery operations, even if they don't say "RDS" and instead say "set up
  a managed database", "create a MySQL instance on AWS", "configure Aurora
  cluster", "manage database snapshots", "set up read replicas for my database",
  or "configure database failover".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to RDS endpoints.
metadata:
  author: aws
  version: "1.2.0"
  last_updated: "2026-07-31"
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
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  cross_skill_deps:
    - aws-ec2-ops
    - aws-ebs-ops
    - aws-vpc-ops
    - aws-cloudwatch-ops
    - aws-iam-ops
    - aws-cloudtrail-ops
    - aws-s3-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS RDS Operations Skill

Use for managed RDS/Aurora-adjacent relational databases, instances, clusters, snapshots, parameter/subnet groups, events, failover, backups, and slow-query diagnosis. Detailed CLI/SDK patterns remain in references.

## Common JSON Paths

Instance: .DBInstances[0].{DBInstanceIdentifier,DBInstanceStatus,DBInstanceClass,Engine,Endpoint,DBInstanceArn}
Cluster: .DBClusters[0].{DBClusterIdentifier,Status,Endpoint,ReaderEndpoint,Engine}
Snapshot: .DBSnapshots[0].{DBSnapshotIdentifier,Status,Engine,SnapshotCreateTime}
ParameterGroups: .DBParameterGroups[].{DBParameterGroupName,DBParameterGroupFamily,Description}

## Trigger & Scope

### SHOULD Use When
RDS instances/clusters, engines, snapshots, parameter/subnet groups, failover, backups, events, connections, or SQL performance.

### SHOULD NOT Use When
Aurora-specific orchestration → `aws-aurora-ops`; DynamoDB → `aws-dynamodb-ops`; ElastiCache → `aws-elasticache-ops`; IAM/KMS/secrets → respective skills.

### Delegation
Metrics/PI → `aws-cloudwatch-ops`; network → `aws-vpc-ops`; credentials → `aws-secretsmanager-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.DBInstanceIdentifier}}`, `{{user.DBClusterIdentifier}}` | User input | Resource IDs |
| `{{user.Engine}}`, `{{user.DBInstanceClass}}`, `{{user.SnapshotIdentifier}}` | User input | Operation parameters |
| `{{output.*}}` | API response | Reuse endpoints/status/ARNs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify engine, subnet/SG, parameter groups, identity, current status, and dependencies. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll available/deleted state; recover with bounded retries and halt on invalid state, quota, or ambiguous identity. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/modify instance/cluster | Validate engine, class, network, maintenance impact; read back | `confirm=` token for disruptive/reboot/storage-shrink changes |
| Failover/stop/start | Verify current state and impact; poll availability | Human confirmation |
| Delete instance (with snapshot) | Display blast radius; instance `Available`; inspect dependents | `confirm=DELETE_DB_INSTANCE <id> snapshot=<snap-id>` |
| Delete instance (skip snapshot) | Same pre-flight; irreversible data loss | `DELETE_NO_SNAPSHOT <id>` (A14 bare literal) |
| Delete snapshot/cluster snapshot | Verify existence and `Status=available` | `confirm=DELETE_DB_SNAPSHOT` / `confirm=DELETE_DB_CLUSTER_SNAPSHOT` |
| Prod delete / cross-region promote | Verify tags/state; read back from describe | `confirm=DELETE_PROD_DB` / `confirm=PROMOTE_CROSS_REGION_REPLICA` |
| Delete parameter/subnet group/event sub | Verify no resources reference it | Human confirmation |
| Slow query diagnosis | Read-only metrics/PI/engine data; mask SQL secrets | — |

Never log `MasterUserPassword`, SQL credentials, connection strings, or query secrets.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A5 (final snapshot), A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live engine/version limits, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive/failover actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

