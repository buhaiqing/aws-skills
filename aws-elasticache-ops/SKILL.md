---
name: aws-elasticache-ops
description: >-
  Use when the user needs to set up, configure, or manage in-memory caching
  clusters using Redis or Memcached; create replication groups for high
  availability; manage cache nodes, snapshots, or subnet groups; or optimize
  application performance with caching, even if they don't say "ElastiCache"
  and instead say "set up Redis", "configure a cache cluster", "improve
  database performance with caching", or "manage session storage".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-vpc-ops
    - aws-cloudwatch-ops
    - aws-ec2-ops
    - aws-cloudtrail-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact', 'capacity-forecast']
    produces_facts: ['metric', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS ElastiCache Operations Skill

Use for Redis/Valkey or Memcached replication groups, clusters, nodes, subnet groups, snapshots, scaling, failover, and cache performance. Detailed commands remain in references.

## Common JSON Paths

ReplicationGroup: .ReplicationGroup.{ARN,Status,PrimaryEndpoint}
ReplicationGroups: .ReplicationGroups[].{Status,MemberClusters,PrimaryEndpoint}
CacheCluster: .CacheCluster.{ARN,Status,CacheNodes}
CacheClusters: .CacheClusters[].{CacheClusterStatus,CacheNodes,CacheNodeType}
Snapshot: .Snapshot.{ARN,Status}
SubnetGroup: .CacheSubnetGroup.{ARN}
ModifyStatus: .ReplicationGroup.Status

## Trigger & Scope

### SHOULD Use When
ElastiCache, Redis/Valkey, Memcached, replication groups, cache nodes, subnet groups, snapshots, or capacity/performance changes.

### SHOULD NOT Use When
EC2 → `aws-ec2-ops`; VPC/security groups → `aws-vpc-ops`; S3 → `aws-s3-ops`; databases → `aws-rds-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.group_id}}`, `{{user.cluster_id}}` | User input | Resource IDs |
| `{{user.engine}}`, `{{user.node_type}}`, `{{user.subnet_group}}` | User input | Runtime configuration |
| `{{user.snapshot_name}}`, `{{user.snapshot_id}}` | User input | Backup identifiers |
| `{{output.*}}` | API response | Reuse ARN/status/endpoints |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify subnet/security groups, engine support, capacity, identifiers, and current status. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll cluster/replication/snapshot status; recover with bounded throttling retries and halt on missing resources or insufficient capacity. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create Redis/Valkey group | Verify engine, subnet, SG, node type; poll available | — |
| Create Memcached cluster | Verify topology and subnet; poll available | — |
| Modify/scale | Describe current config and failover impact; read back | Token when `--apply-immediately` may fail over |
| Create snapshot | Verify source and unique name; poll available | — |
| Delete snapshot | Inspect dependencies and retention need | Human confirmation |
| Delete replication group | Display members/endpoints; default final snapshot; validate absent | `confirm=DELETE_RG <group-id>` |
| Delete cache cluster | Display nodes/endpoints; default final snapshot; validate absent | `confirm=DELETE_CLUSTER <cluster-id>` |

Never hardcode engine versions or node types; query live support. Mask auth tokens and sensitive endpoint data in traces.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live engine/node support, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [integration.md](../aws-skill-generator/references/integration.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive or failover actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
