# AWS CLI Usage - RDS

AWS CLI commands for RDS operations. All commands use `--output json`.

## DB Instance Operations

### Create DB Instance
```bash
aws rds create-db-instance \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --db-instance-class {{user.DBInstanceClass}} \
  --engine {{user.DBEngine}} \
  --engine-version {{user.EngineVersion}} \
  --master-username {{user.MasterUsername}} \
  --master-user-password {{user.MasterUserPassword}} \
  --allocated-storage {{user.AllocatedStorage}} \
  --storage-type gp3 \
  --vpc-security-group-ids {{user.SecurityGroupIds}} \
  --db-subnet-group-name {{user.DBSubnetGroupName}} \
  --availability-zone {{user.AvailabilityZone}} \
  --multi-az \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --deletion-protection \
  --output json
```

**JSON paths:**
- `.DBInstance.DBInstanceIdentifier`
- `.DBInstance.DBInstanceStatus` → "creating"
- `.DBInstance.Endpoint.Address` (null during creation)

### Describe DB Instances
```bash
# Single instance
aws rds describe-db-instances \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --output json

# All instances
aws rds describe-db-instances --output json

# Filter by engine
aws rds describe-db-instances \
  --filters Name=engine,Values=mysql \
  --output json
```

**JSON paths:**
- `.DBInstances[0].DBInstanceStatus` → "available", "creating", "modifying", "deleting"
- `.DBInstances[0].Endpoint.Address` → connection host
- `.DBInstances[0].Endpoint.Port` → connection port (default: 3306 MySQL, 5432 PostgreSQL)
- `.DBInstances[0].DBInstanceClass` → instance type
- `.DBInstances[0].Engine` → database engine
- `.DBInstances[0].EngineVersion` → version string
- `.DBInstances[0].AllocatedStorage` → storage GB
- `.DBInstances[0].StorageType` → gp2, gp3, io1
- `.DBInstances[0].MultiAZ` → boolean
- `.DBInstances[0].DBInstanceArn`

### Modify DB Instance
```bash
aws rds modify-db-instance \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --db-instance-class {{user.NewDBInstanceClass}} \
  --allocated-storage {{user.NewAllocatedStorage}} \
  --apply-immediately \
  --output json
```

**Note:** Without `--apply-immediately`, changes apply during next maintenance window.

**JSON paths:**
- `.DBInstance.DBInstanceStatus` → "modifying"

### Delete DB Instance
```bash
# With final snapshot (recommended)
aws rds delete-db-instance \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --final-db-snapshot-identifier {{user.FinalSnapshotIdentifier}} \
  --output json

# Without final snapshot (SKIP final snapshot - data loss)
aws rds delete-db-instance \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --skip-final-snapshot \
  --output json
```

**Safety Gate:** Human confirmation required before deletion.

## Snapshot Operations

### Create Manual Snapshot
```bash
aws rds create-db-snapshot \
  --db-snapshot-identifier {{user.SnapshotIdentifier}} \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --output json
```

**JSON paths:**
- `.DBSnapshot.DBSnapshotIdentifier`
- `.DBSnapshot.Status` → "creating", "available"

### Describe Snapshots
```bash
# Single snapshot
aws rds describe-db-snapshots \
  --db-snapshot-identifier {{user.SnapshotIdentifier}} \
  --output json

# All snapshots for an instance
aws rds describe-db-snapshots \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --output json

# All manual snapshots
aws rds describe-db-snapshots \
  --snapshot-type manual \
  --output json
```

**JSON paths:**
- `.DBSnapshots[0].Status` → "available", "creating"
- `.DBSnapshots[0].SnapshotCreateTime`
- `.DBSnapshots[0].AllocatedStorage`

### Restore from Snapshot
```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier {{user.NewDBInstanceIdentifier}} \
  --db-snapshot-identifier {{user.SnapshotIdentifier}} \
  --db-instance-class {{user.DBInstanceClass}} \
  --output json
```

### Delete Snapshot
```bash
aws rds delete-db-snapshot \
  --db-snapshot-identifier {{user.SnapshotIdentifier}} \
  --output json
```

**Safety Gate:** Human confirmation required.

## Read Replica Operations

### Create Read Replica
```bash
aws rds create-db-instance-read-replica \
  --db-instance-identifier {{user.ReplicaIdentifier}} \
  --source-db-instance-identifier {{user.SourceDBInstanceIdentifier}} \
  --db-instance-class {{user.ReplicaInstanceClass}} \
  --output json
```

### Promote Read Replica
```bash
aws rds promote-read-replica \
  --db-instance-identifier {{user.ReplicaIdentifier}} \
  --output json
```

## Parameter Group Operations

### Create Parameter Group
```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name {{user.ParameterGroupName}} \
  --db-parameter-group-family {{user.ParameterGroupFamily}} \
  --description "{{user.Description}}" \
  --output json
```

**Parameter group families:**
- MySQL 8.0: `mysql8.0`
- MySQL 5.7: `mysql5.7`
- PostgreSQL 15: `postgres15`
- PostgreSQL 14: `postgres14`
- Aurora MySQL 8.0: `aurora-mysql8.0`
- Aurora PostgreSQL 15: `aurora-postgres15`

### Describe Parameter Groups
```bash
aws rds describe-db-parameter-groups \
  --db-parameter-group-name {{user.ParameterGroupName}} \
  --output json
```

### Modify Parameter Group
```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name {{user.ParameterGroupName}} \
  --parameters "ParameterName=max_connections,ParameterValue=500,ApplyMethod=immediate" \
  --parameters "ParameterName=innodb_buffer_pool_size,ParameterValue={{{user.BufferPoolSize}}},ApplyMethod=pending-reboot" \
  --output json
```

**Apply methods:**
- `immediate` - Dynamic parameters, apply immediately
- `pending-reboot` - Static parameters, require instance reboot

### Delete Parameter Group
```bash
aws rds delete-db-parameter-group \
  --db-parameter-group-name {{user.ParameterGroupName}} \
  --output json
```

**Precondition:** No DB instances must be using this parameter group.

## Aurora Cluster Operations

### Create Aurora Cluster
```bash
aws rds create-db-cluster \
  --db-cluster-identifier {{user.ClusterIdentifier}} \
  --engine aurora-mysql \
  --engine-version {{user.EngineVersion}} \
  --master-username {{user.MasterUsername}} \
  --master-user-password {{user.MasterUserPassword}} \
  --vpc-security-group-ids {{user.SecurityGroupIds}} \
  --db-subnet-group-name {{user.DBSubnetGroupName}} \
  --backup-retention-period 7 \
  --output json
```

### Create Aurora Instance (add to cluster)
```bash
aws rds create-db-instance \
  --db-instance-identifier {{user.InstanceIdentifier}} \
  --db-instance-class db.r6g.large \
  --engine aurora-mysql \
  --db-cluster-identifier {{user.ClusterIdentifier}} \
  --output json
```

### Describe Aurora Cluster
```bash
aws rds describe-db-clusters \
  --db-cluster-identifier {{user.ClusterIdentifier}} \
  --output json
```

**JSON paths:**
- `.DBClusters[0].Status` → "available", "creating"
- `.DBClusters[0].Endpoint` → writer endpoint
- `.DBClusters[0].ReaderEndpoint` → reader endpoint
- `.DBClusters[0].DBClusterMembers` → instances in cluster

### Delete Aurora Cluster
```bash
# With final snapshot
aws rds delete-db-cluster \
  --db-cluster-identifier {{user.ClusterIdentifier}} \
  --final-db-snapshot-identifier {{user.FinalSnapshotIdentifier}} \
  --output json

# Skip final snapshot
aws rds delete-db-cluster \
  --db-cluster-identifier {{user.ClusterIdentifier}} \
  --skip-final-snapshot \
  --output json
```

## Engine & Version Discovery

### Describe Available Engines
```bash
aws rds describe-db-engine-versions \
  --engine mysql \
  --output json
```

**JSON paths:**
- `.DBEngineVersions[0].Engine`
- `.DBEngineVersions[0].EngineVersion`
- `.DBEngineVersions[0].DBParameterGroupFamily`

### Describe Orderable Instance Classes
```bash
aws rds describe-orderable-db-instance-options \
  --engine mysql \
  --engine-version 8.0.35 \
  --output json
```

## Wait Operations

```bash
# Wait for instance available
aws rds wait db-instance-available \
  --db-instance-identifier {{user.DBInstanceIdentifier}}

# Wait for instance deleted
aws rds wait db-instance-deleted \
  --db-instance-identifier {{user.DBInstanceIdentifier}}
```

## DB Instance Classes (Common)

| Class | Use Case |
|-------|----------|
| `db.t3.micro` | Dev/test, minimal |
| `db.t3.small` | Dev/test, small |
| `db.t3.medium` | Dev/test, moderate |
| `db.t4g.micro` | Dev/test, Graviton2 |
| `db.r6g.large` | Production, Graviton2 |
| `db.r6g.xlarge` | Production, larger |
| `db.r5.large` | Production, standard |
| `db.r5.xlarge` | Production, larger |
| `db.m5.large` | General purpose |
| `db.x1.16xlarge` | High memory |

## Storage Types

| Type | IOPS | Use Case |
|------|------|----------|
| `gp2` | Baseline 3 IOPS/GB | General purpose |
| `gp3` | 3000 baseline, max 16000 | Cost-effective, provisionable |
| `io1` | Provisioned, max 50000 | High performance |
| `io2` | Provisioned, max 50000 | High durability |

## Common Options

```bash
--backup-retention-period 7          # Days to retain backups
--multi-az                           # Multi-AZ deployment
--storage-encrypted                  # Enable encryption
--kms-key-id {{user.KmsKeyId}}       # Custom KMS key
--enable-performance-insights        # Performance monitoring
--deletion-protection                # Prevent accidental deletion
--publicly-accessible                # Public IP (avoid for production)
--auto-minor-version-upgrade         # Auto upgrade minor versions
--monitoring-interval 60             # Enhanced monitoring
--monitoring-role-arn {{user.RoleArn}} # IAM role for monitoring
```