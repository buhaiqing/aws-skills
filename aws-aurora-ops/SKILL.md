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
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: [health-check, rca, self-heal, change-impact, compliance-scan, capacity-forecast]
    produces_facts: [metric, state, event, finding]
    idempotency_ttl: PT24H
    destructive_ops_require_confirm: true
---

# AWS Aurora Operations Skill

Use for Aurora MySQL/PostgreSQL clusters, readers, failover, Serverless v2, Global Database, snapshots, parameter groups, Data API, and AIOps diagnosis. Detailed CLI/SDK commands remain in references.

## Common JSON Paths

Cluster: .DBClusters[0].{Status,Endpoint,ReaderEndpoint,DBClusterMembers,Engine,EngineVersion}
Instance: .DBInstances[0].{DBInstanceStatus,DBInstanceClass,PromotionTier,IsClusterWriter,Endpoint}
Snapshot: .DBClusterSnapshots[0].{Status,SnapshotCreateTime,Engine}
Global: .GlobalClusters[0].{GlobalClusterIdentifier,GlobalClusterMembers,Status}
Failover: .DBCluster.{Status,Endpoint}

## Trigger & Scope

### SHOULD Use When
Aurora clusters/readers/writers, failover, Global DB, Serverless v2, snapshots, backtrack, Data API, replica lag, connection storms, slow writer queries, capacity, or backup compliance.

### SHOULD NOT Use When
Standalone RDS → `aws-rds-ops`; DynamoDB → `aws-dynamodb-ops`; ElastiCache → `aws-elasticache-ops`; DocumentDB/Neptune are different engines.

### Delegation
Security groups → `aws-ec2-ops`; IAM → `aws-iam-ops`; KMS → `aws-kms-ops`; metrics → `aws-cloudwatch-ops`; secrets → `aws-secretsmanager-ops`; subnet groups → `aws-vpc-ops`; patrol → `aws-aiops-cruise`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.DBClusterIdentifier}}`, `{{user.DBInstanceIdentifier}}` | User input | Cluster/member IDs |
| `{{user.DBEngine}}`, `{{user.replica_lag_threshold_ms}}` | User input | Engine and detection threshold |
| `{{user.serverless_max_cap_ceiling}}` | User input | AUTO_HEAL ceiling |
| `{{output.*}}` | API response | Reuse cluster and reader endpoints |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json` first; verify engine, subnet, SG, and identifiers. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll `describe-db-clusters` until `available` or deleted. Recover with bounded backoff on throttling; halt on invalid state or ambiguous identity. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create cluster/instances | Validate engine, subnet, SG; poll available | — |
| Add/modify reader | Inspect members and outage impact; validate status | AI_ASSIST token when needed |
| Failover | Verify available and target writer; validate endpoint | `confirm=FAILOVER_CLUSTER {{user.DBClusterIdentifier}}` |
| Stop/start | Check cluster state; validate availability | Human confirmation |
| Delete cluster | Display blast radius; default final snapshot; validate deletion | `confirm=DELETE_DB_CLUSTER {{user.DBClusterIdentifier}}`; skip-snapshot additionally `DELETE_NO_SNAPSHOT {{user.DBClusterIdentifier}}`; prod tag additionally `confirm=DELETE_PROD_CLUSTER {{user.DBClusterIdentifier}}` |
| Backtrack | Verify MySQL and target time; validate recovery | `confirm=BACKTRACK {{user.DBClusterIdentifier}} to {{user.BacktrackTime}}` |
| Global detach/delete | Inspect members and DR impact | Human confirmation |
| AIOps remediation | Collect metrics, detect rule, RCA, choose tier, act, feedback | Tier/token rules below |

## AIOps Delegate Contract

Parse `aiops_delegate` (`request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope.resource_ids`, `trace_id`); deduplicate writes by `idempotency_key` for 24h; `MANUAL` is read-only, `AI_ASSIST` writes only with `confirmation_token`, `AUTO_HEAL` permits non-destructive writes; destructive delete/failover/backtrack/global operations always require a token. Propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks RB-023–RB-027 and incident schema: [prompt-examples.md](references/prompt-examples.md), [incident-schema.md](../aws-aiops-cruise/references/incident-schema.md).

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A14, A7, A8, A9, A10 from `gcl-spec.md` §8; mask credentials and require confirmation tokens in traces.

## Token Efficiency

TE-1…TE-6 apply; query live engine/cluster data, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [prompt-examples.md](references/prompt-examples.md) · [layered-inspection-template.md](references/layered-inspection-template.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)
