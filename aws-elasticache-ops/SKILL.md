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
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact', 'capacity-forecast']
    produces_facts: ['metric', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

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

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded instance types/limits — use `describe-cache-clusters` / `describe-replication-groups`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)

## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse and return
   `aiops_context.status: "failed"` with summary
   `"confirmation_token required for destructive op"`.
3. **Decision tier respect**:
   - `decision_tier: MANUAL` — never execute writes; recommendations only.
   - `decision_tier: AI_ASSIST` — recommendations; execute only if
     `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` — execute non-destructive writes
     directly; destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` JSON
   block in the response, even on failure.

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.

