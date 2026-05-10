# RDS Core Concepts

AWS Relational Database Service architecture, components, and operational concepts.

## Service Overview

**AWS RDS** - Managed relational database service that automates setup, operation, and scaling of databases.

**Key Benefits:**
- Automated provisioning and patching
- Managed backups and snapshots
- Multi-AZ high availability
- Read replicas for scaling
- Storage auto-scaling
- Performance Insights monitoring
- Security (encryption, IAM, VPC)

## Supported Database Engines

### MySQL
- **Versions**: 5.7, 8.0
- **Default Port**: 3306
- **Parameter Groups**: mysql5.7, mysql8.0
- **Storage Min**: 20 GB
- **Replication**: Read replicas, Multi-AZ

### PostgreSQL
- **Versions**: 12, 13, 14, 15, 16
- **Default Port**: 5432
- **Parameter Groups**: postgres12, postgres13, postgres14, postgres15, postgres16
- **Storage Min**: 20 GB
- **Replication**: Read replicas, Multi-AZ

### Aurora MySQL
- **Versions**: Aurora MySQL 8.0 (compatible)
- **Default Port**: 3306
- **Parameter Groups**: aurora-mysql8.0
- **Cluster Architecture**: Writer + multiple readers
- **Auto-scaling**: Aurora Serverless v2

### Aurora PostgreSQL
- **Versions**: Aurora PostgreSQL 15 (compatible)
- **Default Port**: 5432
- **Parameter Groups**: aurora-postgres15
- **Cluster Architecture**: Writer + multiple readers
- **Auto-scaling**: Aurora Serverless v2

### MariaDB
- **Versions**: 10.4, 10.5, 10.6
- **Default Port**: 3306
- **Parameter Groups**: mariadb10.4, mariadb10.5
- **Storage Min**: 20 GB

### Oracle
- **Versions**: 19c, 21c
- **Default Port**: 1521
- **License**: BYOL or License Included
- **Storage Min**: 20 GB

### Microsoft SQL Server
- **Versions**: 2016, 2017, 2019, 2022
- **Default Port**: 1433
- **License**: License Included
- **Storage Min**: 20 GB

## DB Instance Components

### DB Instance Identifier
- Unique name within AWS account
- 1-63 alphanumeric characters
- First character must be letter
- Cannot be changed after creation

### DB Instance Class
- Defines compute and memory capacity
- Prefixes: db.t (burstable), db.r (memory optimized), db.m (general), db.x (extreme memory)
- Graviton2: db.t4g, db.r6g (ARM, cost-effective)
- Standard: db.t3, db.r5, db.m5

### Storage Types

| Type | Description | IOPS | Use Case |
|------|-------------|------|----------|
| **gp2** | General Purpose SSD | Baseline 3 IOPS/GB, burst to 3000 | Dev/test, low workload |
| **gp3** | General Purpose SSD (new) | 3000 baseline, provisionable up to 16000 | Cost-effective, flexible |
| **io1** | Provisioned IOPS SSD | Up to 50000 provisioned | High performance OLTP |
| **io2** | Provisioned IOPS SSD (new) | Up to 50000, higher durability | Mission-critical |

### Storage Auto-Scaling
- Automatically grows storage when threshold reached
- Max limit: 1000 GB or configured maximum
- Threshold: Free storage < 10% or < 5 GB

## High Availability

### Multi-AZ Deployment
- Primary in one AZ, standby in another AZ
- Automatic failover to standby if primary fails
- Synchronous replication (minimal data loss)
- Typically used for production
- Costs: ~2x instance cost (standby instance)

### Multi-AZ DB Cluster (Aurora-style)
- One writer, two readers in different AZs
- Faster failover than traditional Multi-AZ
- Readers can serve read traffic
- Supported: MySQL, PostgreSQL

## Read Replicas

### Cross-AZ Read Replicas
- Asynchronous replication
- Serve read traffic, reduce primary load
- Can be promoted to standalone
- Same region, different AZ

### Cross-Region Read Replicas
- Asynchronous replication across regions
- Disaster recovery, global read scaling
- Latency varies by region distance
- Can be promoted to standalone

### Read Replica Limits
- MySQL: Up to 5 read replicas per source
- PostgreSQL: Up to 5 read replicas per source
- Aurora: Up to 15 readers per cluster

## Backup & Recovery

### Automated Backups
- Daily full backup during backup window
- Transaction logs backed up every 5 minutes
- Retention: 1-35 days (default 7)
- Point-in-time recovery (PITR) within retention
- Stored in S3 (encrypted)

### Manual Snapshots
- User-initiated, retained indefinitely
- No automatic deletion
- Manual delete required
- Can restore to new instance
- Cross-region copy supported

### Backup Retention Considerations
- Longer retention = more storage cost
- PITR within retention period only
- Restore takes time (minutes to hours)

## Aurora Clusters

### Architecture
- Storage: Distributed across 3 AZs (6 copies)
- Writer: Single writer endpoint
- Readers: Multiple reader instances
- Endpoint: Cluster endpoint (writer), reader endpoint (load balanced)

### Aurora Serverless v2
- Capacity scales instantly (0.5-128 ACU)
- Pay for capacity used
- Ideal for unpredictable workloads
- No capacity planning required

### Aurora Global Database
- Cross-region replication (<1 second lag)
- Up to 5 secondary regions
- Disaster recovery, global reads
- Each secondary can have 16 readers

## Parameter Groups

### Default Parameter Groups
- Created by AWS for each engine family
- Cannot modify default groups
- Contains engine-specific parameters

### Custom Parameter Groups
- Derived from default groups
- Modify parameters for performance tuning
- Apply to DB instances
- Static vs Dynamic parameters

### Parameter Types
- **Dynamic**: Apply immediately without reboot
  - Example: max_connections, query_cache_size
- **Static**: Require instance reboot to apply
  - Example: innodb_buffer_pool_size, shared_buffers

### Common Tuning Parameters

| Engine | Parameter | Purpose |
|--------|-----------|---------|
| MySQL | max_connections | Max concurrent connections |
| MySQL | innodb_buffer_pool_size | InnoDB cache (50-80% of memory) |
| PostgreSQL | max_connections | Max concurrent connections |
| PostgreSQL | shared_buffers | PostgreSQL cache (25% of memory) |
| Aurora | aurora_disable_backtracking | Disable backtracking feature |

## Option Groups

### Purpose
- Add optional features to DB instance
- Engine-specific options

### Examples
- **Oracle**: OEM, APEX
- **SQL Server**: SQL Server Agent
- **MySQL**: Memcached plugin (deprecated)

## Security

### VPC Security Groups
- Control network access to DB
- Inbound: Port 3306/5432 from application IPs
- Outbound: Usually unrestricted

### IAM Authentication
- Temporary credentials via IAM
- No password management
- Supported: MySQL, PostgreSQL, Aurora

### Storage Encryption
- Encrypt data at rest
- Use AWS KMS key
- Cannot disable after creation
- Transparent to applications

### SSL/TLS
- Encrypt connections in transit
- rds-ca-* certificates
- Force SSL via parameter group

### Deletion Protection
- Prevent accidental deletion
- Must disable before delete
- Applied at instance level

## Monitoring

### Performance Insights
- Real-time database load analysis
- Wait events, SQL queries, users
- 7 days free, longer retention costs extra

### Enhanced Monitoring
- OS-level metrics (CPU, memory, disk)
- 1-second granularity
- Requires IAM role

### CloudWatch Metrics
- CPUUtilization, FreeStorageSpace
- DatabaseConnections, ReadIOPS, WriteIOPS
- FreeableMemory, SwapUsage

## Quotas (Service Limits)

| Quota | Default Limit |
|-------|---------------|
| DB Instances | 40 per region |
| DB Snapshots | 100 per region |
| Total Storage | 100 TB per region |
| Read Replicas per source | 5 |
| DB Parameter Groups | 50 |
| DB Subnet Groups | 50 |

**Quota Increase**: Request via AWS Service Quotas console.

## Pricing Components

### Instance Pricing
- Per-hour charge based on instance class
- Graviton2 instances: Lower cost
- Multi-AZ: Double instance cost

### Storage Pricing
- Per GB per month
- gp3: Base cost + provisioned IOPS
- io1/io2: Base + provisioned IOPS

### Backup Storage
- Automated backup: Free up to instance size
- Additional backup storage: Per GB
- Manual snapshots: Per GB indefinitely

### Data Transfer
- Inter-AZ: $0.01/GB (Multi-AZ replication)
- Cross-region: Standard data transfer rates
- Within same AZ: Free

### Additional Features
- Performance Insights: 7 days free, $0.02/vCPU-hour beyond
- Enhanced Monitoring: Free
- Storage Auto-scaling: Free feature

## DB Subnet Groups

### Purpose
- Define VPC subnets for DB instances
- Multi-AZ requires subnets in multiple AZs

### Requirements
- At least 2 subnets in different AZs for Multi-AZ
- Subnets must have IP addresses available
- Route to internet (for public access) or private only

## Maintenance

### Maintenance Window
- Weekly window for patching, minor upgrades
- Auto-minor-version-upgrade enabled by default
- Can disable or schedule specific window

### Major Version Upgrades
- Manual upgrade process
- Requires careful planning
- Backup before upgrade

### Instance Modification
- Scale compute: Instance class change
- Scale storage: Increase allocated storage
- Storage reduction: Not supported (scale up only)

## Common DB Instance States

| State | Description |
|-------|-------------|
| available | Normal operation |
| creating | Initial creation |
| modifying | Configuration change |
| deleting | Being deleted |
| stopped | Paused (storage cost continues) |
| backing-up | Creating backup |
| restoring | Restoring from snapshot |
| upgrading | Engine version upgrade |
| maintenance | Applying maintenance |
| failed | Creation failed |

## Operational Best Practices

### Production Checklist
- Multi-AZ deployment
- Storage encryption enabled
- Deletion protection enabled
- Backup retention >= 7 days
- Private subnet (no public access)
- Security group minimal access
- Performance Insights enabled
- Enhanced monitoring enabled
- Parameter group tuned for workload

### Dev/Test Considerations
- Single AZ (cost savings)
- Smaller instance class
- Shorter backup retention
- Can use public access (with caution)
- Consider stop/start for cost savings

### Security Best Practices
- Never use public access for production
- Limit security group inbound to specific IPs
- Enable storage encryption
- Use IAM authentication where possible
- Rotate master password regularly
- Use Secrets Manager for credentials