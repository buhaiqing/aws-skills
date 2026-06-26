# Core Concepts — ElastiCache

## Overview

AWS ElastiCache is a managed in-memory caching service for Redis and Memcached.

## Engine Comparison (Core Decisions Only)

| Aspect | Redis | Memcached |
|--------|-------|-----------|
| Data Structures | Rich: Strings, Lists, Sets, Sorted Sets, Hashes, Streams | Strings only |
| Persistence | Yes (RDB snapshot, AOF log) | No |
| Replication | Yes (Primary + Replicas, auto-failover) | No |
| Clustering/Sharding | Yes (Cluster Mode: up to 500 shards) | No (manual client-side sharding) |
| Auth & Encryption | AUTH token, TLS, at-rest encryption, IAM auth | No |
| Best for | Caching + durable state, pub/sub, rate limiting | Simple key-value cache, high concurrency |

Use `aws elasticache describe-cache-engine-versions --engine redis|memcached` for latest versions.

## Replication Group Architecture (Redis)

| Component | Description |
|-----------|-------------|
| Cluster Mode Disabled | Primary + up to 5 Replicas; read scaling |
| Cluster Mode Enabled | Up to 500 shards × 5 replicas each; data partitioning |
| Primary Endpoint | Write endpoint (DNS, auto-failover-aware) |
| Reader Endpoint | Round-robin read endpoint for replicas |

## Cache Cluster (Memcached / Single-Node Redis)

Simple multi-node group. Each node independent; data distributed by client hashing strategy.

## Key Operations

| Resource | Creates via | Describes via | Deletes via |
|----------|-------------|---------------|-------------|
| Replication Group | `create-replication-group` | `describe-replication-groups` | `delete-replication-group` |
| Cache Cluster | `create-cache-cluster` | `describe-cache-clusters` | `delete-cache-cluster` |
| Snapshot (Redis) | `create-snapshot` | `describe-snapshots` | `delete-snapshot` |
| Subnet Group | `create-cache-subnet-group` | `describe-cache-subnet-groups` | `delete-cache-subnet-group` |
| Parameter Group | `create-cache-parameter-group` | `describe-cache-parameters` | `delete-cache-parameter-group` |

## Node Types

- **Burstable (T3/T4g)**: Dev/test, small workloads
- **General Purpose (M5/M6g)**: Balanced compute/memory
- **Memory Optimized (R5/R6g)**: Memory-intensive workloads

Use `aws elasticache list-allowed-node-type-modifications --replication-group-id <id>` for upgrade paths.
Use `describe-reserved-cache-nodes-offerings` for pricing info.

## Networking

| Component | Requirement |
|-----------|-------------|
| Subnet group | ≥ 2 subnets across different AZs for HA |
| SG ingress | Port 6379 (Redis) or 11211 (Memcached) |
| Encryption | TLS for transit, KMS for at-rest (Redis only) |

## Security

- Redis AUTH token (set at creation)
- IAM auth for Redis (token-based, supported in redis7+)
- At-rest encryption (KMS, Redis only)
- In-transit encryption (TLS, Redis only)

## Parameter Groups

| Family | Engine |
|--------|--------|
| redis7 | Redis 7.x |
| redis6x | Redis 6.x |
| memcached1.6 | Memcached 1.6.x |

Key Redis params: `maxmemory-policy` (eviction), `timeout` (client idle), `appendonly` (persistence).
Use `aws elasticache describe-cache-parameters` to inspect.

## Service Quotas

| Resource | Default | API to check |
|----------|---------|-------------|
| Clusters per region | 100 | `describe-cache-clusters` |
| Replication groups per region | 50 | `describe-replication-groups` |
| Max replicas per RG | 5 | Fixed |
| Max shards (Cluster Mode) | 500 | Fixed |

Use `aws service-quotas get-service-quota` or AWS Console for current limits.

