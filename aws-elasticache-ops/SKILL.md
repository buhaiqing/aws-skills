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
  last_updated: "2026-06-26"
  runtime: Harness AI Agent
  cli_applicability: dual-path
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
---
# AWS ElastiCache Operations Skill

## Common JSON Paths (Centralized)

```
# Create Repl Group:    .ReplicationGroup.{ARN,Status,PrimaryEndpoint}
# Describe Repl Group:  .ReplicationGroups[].{Status,MemberClusters,PrimaryEndpoint}
# Create Cache Cluster: .CacheCluster.{ARN,Status,CacheNodes}
# Describe Cache:       .CacheClusters[].{CacheClusterStatus,CacheNodes,CacheNodeType}
# Create Snapshot:      .Snapshot.{ARN,Status}
# Create Subnet Group:  .CacheSubnetGroup.{ARN}
# Modify RG:            .ReplicationGroup.Status
```

## Overview

AWS ElastiCache is a managed in-memory caching service supporting Redis and Memcached. This skill covers cluster, replication group, and cache node operations.

## Trigger & Scope

### SHOULD Use When
- User mentions "ElastiCache", "Redis", "Memcached", or "cache cluster"
- Task involves CRUD on **Cache Clusters** or **Replication Groups**
- Keywords: cache, in-memory, replication, cluster, node, subnet group

### SHOULD NOT Use When
- EC2 instances → delegate to: `aws-ec2-ops`
- VPC/subnets → delegate to: `aws-vpc-ops`
- Security groups → delegate to: `aws-vpc-ops`
- S3 for storage → delegate to: `aws-s3-ops`
- RDS databases → delegate to: `aws-rds-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.cluster_name}}` | User input | Ask once; reuse |
| `{{user.engine}}` | User input | Redis or Memcached |
| `{{user.node_type}}` | User input | cache.t3.micro |
| `{{user.group_id}}` | User input | Replication group ID |
| `{{output.cluster_arn}}` | Last API response | Parse `.CacheCluster.ARN` |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify subnet group exists via `describe-cache-subnet-groups`, verify security group.

**CLI (primary)**: `aws elasticache [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Poll `.ReplicationGroup.Status` or `.CacheCluster.CacheClusterStatus` == "available". Max wait: 15 min (create), 15 min (delete).

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidParameterValue (400) | Fix params; retry once |
| CacheClusterNotFound | HALT — verify cluster ID |
| ReplicationGroupNotFoundFault | HALT — verify group ID |
| InsufficientCacheClusterCapacity | HALT — try different node type/region |
| Throttling (429) | Backoff, retry 3x |
| InternalError (5xx) | Retry 3x; HALT |

## Operations

### OP: Create Redis Replication Group
```bash
aws elasticache create-replication-group \
  --replication-group-id "{{user.group_id}}" \
  --replication-group-description "{{user.description}}" \
  --engine redis --cache-node-type "{{user.node_type}}" \
  --num-cache-clusters {{user.num_clusters}} \
  --cache-subnet-group-name "{{user.subnet_group}}" \
  --security-group-ids "{{user.sg_ids}}"
```
Validate: Poll until Status="available" (max 15 min). Wait: `describe-replication-groups --replication-group-id {{o.group_id}}`.

### OP: Create Memcached Cluster
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id "{{user.cluster_id}}" --engine memcached \
  --cache-node-type "{{user.node_type}}" --num-cache-nodes {{user.num_nodes}} \
  --cache-subnet-group-name "{{user.subnet_group}}" --security-group-ids "{{user.sg_ids}}"
```
Validate: Poll until CacheClusterStatus="available" (max 15 min).

### OP: Cache Subnet Group
```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name "{{user.subnet_group_name}}" \
  --cache-subnet-group-description "{{user.description}}" \
  --subnet-ids "{{user.subnet_ids}}"
```

### OP: Describe / Modify / Delete
```bash
aws elasticache describe-replication-groups --replication-group-id "{{user.group_id}}"
aws elasticache describe-cache-clusters --cache-cluster-id "{{user.cluster_id}}" --show-cache-node-info
aws elasticache modify-replication-group --replication-group-id "{{user.group_id}}" --cache-node-type "{{user.new_node_type}}" --apply-immediately
aws elasticache increase-replica-count --replication-group-id "{{user.group_id}}" --new-replica-count {{user.new_count}} --apply-immediately
```

### OP: Snapshot
```bash
aws elasticache create-snapshot --snapshot-name "{{user.snapshot_name}}" --replication-group-id "{{user.group_id}}"
aws elasticache describe-snapshots
aws elasticache delete-snapshot --snapshot-name "{{user.snapshot_name}}"
```

### OP: Delete (Destructive)
**Safety Gate**: Confirm with user before deletion.
```bash
aws elasticache delete-replication-group \
  --replication-group-id "{{user.group_id}}" \
  --final-snapshot-identifier "{{user.snapshot_id}}"

aws elasticache delete-cache-cluster \
  --cache-cluster-id "{{user.cluster_id}}" \
  --final-snapshot-identifier "{{user.snapshot_id}}"
```

## Redis vs Memcached (Key Differences)

| Feature | Redis | Memcached |
|---------|-------|-----------|
| Data Structures | Rich (Strings, Lists, Sets, Hashes, Sorted Sets) | Strings only |
| Persistence | Yes (AOF/RDB) | No |
| Replication | Yes (Primary+Replicas) | No |
| Clustering/Sharding | Yes | No |
| Use `describe-cache-engine-versions` for latest engine versions. | | |

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-elasticache-ops` MUST be wrapped by the Generator-Critic-Loop
> defined in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-replication-group` — data loss; recommend `--final-snapshot-identifier`; confirm `DELETE_RG <group-id>`
- `delete-cache-cluster` — data loss; recommend `--final-snapshot-identifier`; confirm `DELETE_CLUSTER <cluster-id>`
- `delete-snapshot` — snapshot data permanently lost; confirm with user
- `modify-replication-group` with `--apply-immediately` — can cause failover; confirm

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource ID echoed from `describe-*`), A9 (no secrets in trace), A10 (sts first command).

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric
- `references/prompt-templates.md` — G/C/O skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)