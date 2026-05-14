---
name: aws-elasticache-ops
description: >-
  Use when the user needs to set up, configure, or manage in-memory caching
  clusters using Redis or Memcached; create replication groups for high
  availability; manage cache nodes, snapshots, or subnet groups; or optimize
  application performance with caching, even if they don't say "ElastiCache"
  and instead say "set up Redis", "configure a cache cluster", "improve
  database performance with caching", or "manage session storage".
---
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

# AWS ElastiCache Operations Skill

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

## ElastiCache Engines

| Engine | Description | Features |
|--------|-------------|----------|
| Redis | Key-value store | Replication, clustering, persistence, Pub/Sub |
| Memcached | Key-value store | Multi-thread, simple caching, no persistence |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.cluster_name}}` | User input | Ask once; reuse |
| `{{user.engine}}` | User input | Redis or Memcached |
| `{{user.node_type}}` | User input | Cache node type (e.g., cache.t3.micro) |
| `{{output.cluster_arn}}` | Last API response | Parse `.CacheCluster.ARN` |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Redis Replication Group

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide user to integration.md |
| Subnet group exists | `aws elasticache describe-cache-subnet-groups` | HALT; create subnet group first |
| Security group exists | `aws ec2 describe-security-groups` | HALT; verify SG |

#### Execute — CLI (Primary)
```bash
aws elasticache create-replication-group \
  --replication-group-id "{{user.group_id}}" \
  --replication-group-description "{{user.description}}" \
  --engine redis \
  --cache-node-type "{{user.node_type}}" \
  --num-cache-clusters {{user.num_clusters}} \
  --cache-subnet-group-name "{{user.subnet_group}}" \
  --security-group-ids "{{user.sg_ids}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('elasticache', region_name='{{user.region}}')
response = client.create_replication_group(
    ReplicationGroupId='{{user.group_id}}',
    ReplicationGroupDescription='{{user.description}}',
    Engine='redis',
    CacheNodeType='{{user.node_type}}',
    NumCacheClusters=3,
    CacheSubnetGroupName='{{user.subnet_group}}',
    SecurityGroupIds=['sg-xxx']
)
```

#### Validate
Poll until `.ReplicationGroup.Status` == "available" (max wait: 15 min).

### Operation: Create Memcached Cluster

#### Execute — CLI (Primary)
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id "{{user.cluster_id}}" \
  --engine memcached \
  --cache-node-type "{{user.node_type}}" \
  --num-cache-nodes {{user.num_nodes}} \
  --cache-subnet-group-name "{{user.subnet_group}}" \
  --security-group-ids "{{user.sg_ids}}" \
  --output json
```

#### Validate
Poll until `.CacheCluster.CacheClusterStatus` == "available".

### Operation: Create Cache Subnet Group

#### Execute — CLI (Primary)
```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name "{{user.subnet_group_name}}" \
  --cache-subnet-group-description "{{user.description}}" \
  --subnet-ids "{{user.subnet_ids}}" \
  --output json
```

### Operation: Describe Replication Group

#### Execute — CLI
```bash
aws elasticache describe-replication-groups \
  --replication-group-id "{{user.group_id}}" \
  --output json
# JSON path: .ReplicationGroups[].{Status,PrimaryEndpoint,MemberClusters}
```

### Operation: Describe Cache Cluster

#### Execute — CLI
```bash
aws elasticache describe-cache-clusters \
  --cache-cluster-id "{{user.cluster_id}}" \
  --show-cache-node-info \
  --output json
```

### Operation: Add Read Replica (Redis)

#### Execute — CLI (Primary)
```bash
aws elasticache increase-replica-count \
  --replication-group-id "{{user.group_id}}" \
  --new-replica-count {{user.new_count}} \
  --apply-immediately \
  --output json
```

### Operation: Modify Replication Group

#### Execute — CLI (Primary)
```bash
aws elasticache modify-replication-group \
  --replication-group-id "{{user.group_id}}" \
  --cache-node-type "{{user.new_node_type}}" \
  --apply-immediately \
  --output json
```

### Operation: Delete Replication Group

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Execute — CLI (Primary)
```bash
aws elasticache delete-replication-group \
  --replication-group-id "{{user.group_id}}" \
  --final-snapshot-identifier "{{user.snapshot_id}}" \
  --output json
```

#### Validate
Poll until replication group deleted (max wait: 15 min).

### Operation: Delete Cache Cluster

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Execute — CLI (Primary)
```bash
aws elasticache delete-cache-cluster \
  --cache-cluster-id "{{user.cluster_id}}" \
  --final-snapshot-identifier "{{user.snapshot_id}}" \
  --output json
```

### Operation: Create Snapshot

#### Execute — CLI (Primary)
```bash
aws elasticache create-snapshot \
  --snapshot-name "{{user.snapshot_name}}" \
  --replication-group-id "{{user.group_id}}" \
  --output json
```

### Operation: List Snapshots

#### Execute — CLI
```bash
aws elasticache describe-snapshots --output json
```

## Redis vs Memcached Comparison

| Feature | Redis | Memcached |
|---------|-------|-----------|
| Data Structures | Strings, Lists, Sets, Hashes, Sorted Sets | Strings only |
| Persistence | Yes (AOF, RDB) | No |
| Replication | Yes (Primary/Read Replicas) | No |
| Clustering | Yes (Sharding) | No (distributed hash) |
| Multi-thread | No (single-thread) | Yes |
| Transactions | Yes | No |
| Pub/Sub | Yes | No |

## Cache Node Types

| Node Type | vCPU | Memory | Use Case |
|-----------|------|--------|----------|
| cache.t3.micro | 1 | 0.5 GB | Dev/Test |
| cache.t3.small | 1 | 1.4 GB | Dev/Test |
| cache.t3.medium | 2 | 3.1 GB | Small prod |
| cache.m5.large | 2 | 6.4 GB | Production |
| cache.m5.xlarge | 4 | 13 GB | Production |
| cache.r5.large | 2 | 13 GB | Large data |
| cache.r5.xlarge | 4 | 27 GB | Large data |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Example Configurations](assets/example-config.yaml)