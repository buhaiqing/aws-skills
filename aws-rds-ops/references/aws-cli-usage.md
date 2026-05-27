# AWS CLI Usage - RDS

AWS CLI commands for RDS operations. All commands use `--output json`.

## Common JSON Paths (Reusable)
```
# Describe: .DBInstances[0].{DBInstanceStatus,Endpoint.Address,Endpoint.Port,DBInstanceClass,Engine,EngineVersion,AllocatedStorage,StorageType,MultiAZ,DBInstanceArn}
# Snapshots: .DBSnapshots[0].{Status,SnapshotCreateTime,AllocatedStorage}
# Clusters:  .DBClusters[0].{Status,Endpoint,ReaderEndpoint,DBClusterMembers}
# Versions:  .DBEngineVersions[0].{Engine,EngineVersion,DBParameterGroupFamily}
```

## DB Instance Operations

### Create DB Instance
```bash
aws rds create-db-instance \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --db-instance-class {{user.DBInstanceClass}} \
  --engine {{user.DBEngine}} --engine-version {{user.EngineVersion}} \
  --master-username {{user.MasterUsername}} --master-user-password {{user.MasterUserPassword}} \
  --allocated-storage {{user.AllocatedStorage}} --storage-type gp3 \
  --vpc-security-group-ids {{user.SecurityGroupIds}} \
  --db-subnet-group-name {{user.DBSubnetGroupName}} --multi-az \
  --backup-retention-period 7 --enable-performance-insights --deletion-protection
```

### Describe / Modify / Delete
```bash
# Describe (single/all/by-engine)
aws rds describe-db-instances --db-instance-identifier {{id}}
aws rds describe-db-instances --filters Name=engine,Values=mysql

# Modify (use --apply-immediately or defer to maintenance window)
aws rds modify-db-instance --db-instance-identifier {{id}} --db-instance-class {{new_class}} --apply-immediately

# Delete (recommend --final-db-snapshot-identifier)
aws rds delete-db-instance --db-instance-identifier {{id}} --final-db-snapshot-identifier {{snap}}
aws rds delete-db-instance --db-instance-identifier {{id}} --skip-final-snapshot  # DANGER: data loss
```

## Snapshot Operations
```bash
aws rds create-db-snapshot --db-snapshot-identifier {{snap}} --db-instance-identifier {{id}}
aws rds describe-db-snapshots --db-instance-identifier {{id}}
aws rds describe-db-snapshots --snapshot-type manual
aws rds restore-db-instance-from-db-snapshot --db-instance-identifier {{new_id}} --db-snapshot-identifier {{snap}}
aws rds delete-db-snapshot --db-snapshot-identifier {{snap}}  # Safety gate: confirm
```

## Read Replica Operations
```bash
aws rds create-db-instance-read-replica --db-instance-identifier {{rep_id}} --source-db-instance-identifier {{source_id}}
aws rds promote-read-replica --db-instance-identifier {{rep_id}}
```

## Parameter Group Operations
```bash
aws rds create-db-parameter-group --db-parameter-group-name {{name}} --db-parameter-group-family {{family}} --description "{{desc}}"
aws rds modify-db-parameter-group --db-parameter-group-name {{name}} \
  --parameters "ParameterName=max_connections,ParameterValue=500,ApplyMethod=immediate"
aws rds delete-db-parameter-group --db-parameter-group-name {{name}}  # Pre: no instances using it
```

## Aurora Cluster Operations
```bash
aws rds create-db-cluster --db-cluster-identifier {{cluster}} --engine aurora-mysql \
  --master-username {{user}} --master-user-password {{pass}} --backup-retention-period 7
aws rds create-db-instance --db-instance-identifier {{inst}} --db-cluster-identifier {{cluster}} --db-instance-class db.r6g.large --engine aurora-mysql
aws rds describe-db-clusters --db-cluster-identifier {{cluster}}
aws rds delete-db-cluster --db-cluster-identifier {{cluster}} --final-db-snapshot-identifier {{snap}}  # Delete instances first
# Failover
aws rds failover-db-cluster --db-cluster-identifier {{cluster}} --target-db-instance-identifier {{target}}
```

## Engine & Version Discovery
```bash
aws rds describe-db-engine-versions --engine mysql
aws rds describe-orderable-db-instance-options --engine mysql --engine-version 8.0.35
```

## Waiters
```bash
aws rds wait db-instance-available --db-instance-identifier {{id}}
aws rds wait db-instance-deleted --db-instance-identifier {{id}}
aws rds wait db-snapshot-available --db-snapshot-identifier {{snap}}  # For restore operations
```

## Common Option Flags
```
--backup-retention-period 7 | --multi-az | --storage-encrypted | --kms-key-id {{key}}
--enable-performance-insights --performance-insights-retention-period 7
--deletion-protection | --publicly-accessible (avoid prod) | --auto-minor-version-upgrade
--monitoring-interval 60 --monitoring-role-arn {{arn}}
```