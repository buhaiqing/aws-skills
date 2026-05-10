# Core Concepts — ElastiCache

## What is AWS ElastiCache

- **Purpose**: Managed in-memory caching service for Redis and Memcached
- **Category**: Database & Caching
- **Console**: https://console.aws.amazon.com/elasticache/home
- **Docs**: https://docs.aws.amazon.com/AmazonElastiCache/

## Engine Comparison

| Feature | Redis | Memcached |
|---------|-------|-----------|
| Data Structures | Strings, Lists, Sets, Hashes, Sorted Sets | Strings only |
| Persistence | Yes (RDB, AOF) | No |
| Replication | Yes (Primary + Replicas) | No |
| Clustering/Sharding | Yes (Cluster Mode) | No |
| Multi-thread | No (single-threaded) | Yes (multi-threaded) |
| Transactions | Yes (MULTI/EXEC) | No |
| Pub/Sub | Yes | No |
| Lua Scripts | Yes | No |
| Sorted Sets | Yes | No |
| TTL | Per-key | Per-item (slabs) |
| Auth | Yes (AUTH token) | No |

## Architecture

### Redis Architecture

| Mode | Description | Use Case |
|------|-------------|----------|
| Single Node | One Redis instance | Dev/Test, small cache |
| Cluster Mode Disabled | Primary + Read Replicas | High read throughput |
| Cluster Mode Enabled | Sharded across node groups | Large datasets, high throughput |

### Memcached Architecture

| Mode | Description |
|------|-------------|
| Single Node | One Memcached instance |
| Multi-Node | Multiple nodes with distributed hashing |

## Replication Group Components (Redis)

| Component | Description |
|-----------|-------------|
| Primary Cluster | Write endpoint, leader |
| Read Replicas | Read-only copies, followers |
| Node Group | Shard (Cluster Mode enabled) |
| Primary Endpoint | Write endpoint address |
| Reader Endpoint | Read endpoint address |

## Cache Cluster Components

| Component | Description |
|-----------|-------------|
| Cache Node | Individual instance |
| Cache Cluster | Collection of nodes (Memcached) |
| Endpoint | Connection address |
| Port | Redis: 6379, Memcached: 11211 |

## Cache Node Types

### General Purpose (M5/M6G)
| Node Type | vCPU | Memory | Network |
|-----------|------|--------|---------|
| cache.m5.large | 2 | 6.4 GB | Up to 5 Gbps |
| cache.m5.xlarge | 4 | 13 GB | Up to 10 Gbps |
| cache.m5.2xlarge | 8 | 26 GB | Up to 10 Gbps |
| cache.m5.4xlarge | 16 | 52 GB | Up to 10 Gbps |
| cache.m6g.large | 2 | 6.4 GB | Up to 5 Gbps (Graviton) |
| cache.m6g.xlarge | 4 | 13 GB | Up to 10 Gbps |

### Memory Optimized (R5/R6G)
| Node Type | vCPU | Memory | Network |
|-----------|------|--------|---------|
| cache.r5.large | 2 | 13 GB | Up to 5 Gbps |
| cache.r5.xlarge | 4 | 27 GB | Up to 10 Gbps |
| cache.r5.2xlarge | 8 | 54 GB | Up to 10 Gbps |
| cache.r5.4xlarge | 16 | 108 GB | Up to 10 Gbps |
| cache.r6g.large | 2 | 13 GB | Up to 5 Gbps (Graviton) |
| cache.r6g.xlarge | 4 | 27 GB | Up to 10 Gbps |

### Burstable (T3/T4G)
| Node Type | vCPU | Memory | Use Case |
|-----------|------|--------|----------|
| cache.t3.micro | 1 | 0.5 GB | Dev/Test |
| cache.t3.small | 1 | 1.4 GB | Dev/Test |
| cache.t3.medium | 2 | 3.1 GB | Small prod |
| cache.t4g.micro | 1 | 0.5 GB | Dev/Test (Graviton) |

## Cluster Mode Enabled (Redis Sharding)

| Parameter | Description |
|-----------|-------------|
| NumNodeGroups | Number of shards (1-500) |
| ReplicasPerNodeGroup | Replicas per shard (0-5) |
| Slot Allocation | 16384 hash slots distributed |
| Each Node Group | Primary + replicas |

Example: 3 shards × 2 replicas = 9 nodes total

## Automatic Failover (Redis)

| Feature | Description |
|---------|-------------|
| Multi-AZ | Replicas in different AZs |
| Automatic Failover | Replica promoted on primary failure |
| Detection Time | 30-60 seconds |
| Failover Time | 1-2 minutes |

## Encryption & Security

| Feature | Redis | Memcached |
|---------|-------|-----------|
| At-Rest Encryption | Yes (optional) | No |
| Transit Encryption | Yes (TLS) | No |
| Auth Token | Yes (Redis AUTH) | No |
| IAM Authentication | Yes (optional) | No |

## Persistence (Redis Only)

| Type | Description | Trade-off |
|------|-------------|-----------|
| RDB (Snapshot) | Point-in-time snapshots | Good for backup, may lose recent data |
| AOF (Append Only) | Log every write | More durable, larger files |
| Both | RDB + AOF | Best durability |

## Cache Parameter Groups

| Parameter Family | Engine |
|------------------|--------|
| redis7 | Redis 7.x |
| redis6x | Redis 6.x |
| memcached1.6 | Memcached 1.6.x |

### Common Redis Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| maxmemory-policy | volatile-lru | Eviction policy |
| timeout | 0 | Client timeout (seconds) |
| tcp-keepalive | 300 | TCP keepalive |
| cluster-enabled | yes | Cluster mode |
| appendonly | no | AOF persistence |

## Subnet Groups

| Component | Requirement |
|-----------|-------------|
| Subnets | At least 2 AZs recommended |
| CIDR | Enough IPs for all nodes |
| VPC | Same VPC for all subnets |

## Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Clusters per Region | 100 | Yes |
| Nodes per Cluster (Memcached) | 20 | Yes |
| Nodes per Region | 500 | Yes |
| Replication Groups per Region | 50 | Yes |
| Node Groups per Cluster | 500 | No |
| Replicas per Node Group | 5 | No |
| Parameter Groups | 50 | Yes |
| Subnet Groups | 50 | Yes |
| Snapshots | 100 per cluster | No |

## Best Practices

### Redis
- Use Multi-AZ for production
- Enable automatic failover
- Use Cluster Mode for large datasets
- Enable encryption for sensitive data
- Set appropriate maxmemory-policy
- Monitor replication lag

### Memcached
- Use multiple nodes for throughput
- Distribute across AZs
- Monitor connection count
- Set appropriate slab sizes

### General
- Deploy in private subnets
- Use security groups to restrict access
- Monitor cache hit rate
- Set appropriate TTL values
- Scale based on memory usage

## Pricing

| Component | Cost |
|-----------|------|
| Cache Nodes | Per-node hourly rate |
| Data Transfer | VPC data transfer rates |
| Snapshots | Backup storage charges |
| Reserved Nodes | Discounted rate (1-3 year) |

Example pricing (us-east-1):
- cache.t3.micro: ~$0.026/hour
- cache.m5.large: ~$0.125/hour
- cache.r5.large: ~$0.175/hour

## Monitoring Metrics

| Metric | Redis | Memcached |
|--------|-------|-----------|
| CacheHits | Yes | Yes |
| CacheMisses | Yes | Yes |
| Evictions | Yes | Yes |
| BytesUsedForCache | Yes | Yes |
| CPUUtilization | Yes | Yes |
| SwapUsage | Yes | Yes |
| CurrentConnections | Yes | Yes |
| NewConnections | Yes | Yes |
| Get/Set Commands | Yes | No |
| ReplicationLag | Yes | No |

## Related Services

| Service | Integration |
|---------|-------------|
| EC2 | Application instances |
| VPC | Network, subnets, SG |
| CloudWatch | Monitoring |
| Lambda | Event-driven scaling |
| Route 53 | DNS endpoints |
| S3 | Backup storage (manual) |
| IAM | Authentication (Redis) |