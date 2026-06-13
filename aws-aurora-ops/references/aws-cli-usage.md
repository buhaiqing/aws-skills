# AWS CLI Usage — Aurora (RDS API)

All commands use `aws rds ... --output json`. Aurora shares the RDS CLI namespace.

## Common JSON Paths (Reusable)

```
# Cluster:   .DBClusters[0].{Status,Endpoint,ReaderEndpoint,DBClusterMembers,Engine,EngineVersion,DeletionProtection}
# Instance:  .DBInstances[0].{DBInstanceStatus,DBInstanceClass,PromotionTier,IsClusterWriter,Endpoint}
# Snapshots: .DBClusterSnapshots[0].{Status,SnapshotCreateTime,Engine,AllocatedStorage}
# Global:    .GlobalClusters[0].{GlobalClusterIdentifier,GlobalClusterMembers,Status}
# Versions:  .DBEngineVersions[0].{Engine,EngineVersion,DBParameterGroupFamily}
```

## Engine Discovery

```bash
aws rds describe-db-engine-versions --engine aurora-mysql --region {{user.region}} --output json
aws rds describe-db-engine-versions --engine aurora-postgresql --region {{user.region}} --output json
aws rds describe-orderable-db-instance-options \
  --engine aurora-mysql --engine-version {{user.EngineVersion}} \
  --region {{user.region}} --output json
```

## Create Aurora Cluster

```bash
aws rds create-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --engine {{user.DBEngine}} \
  --engine-version {{user.EngineVersion}} \
  --master-username {{user.MasterUsername}} \
  --master-user-password {{user.password_secrets_manager_arn}} \
  --db-subnet-group-name {{user.DBSubnetGroupName}} \
  --vpc-security-group-ids {{user.SecurityGroupIds}} \
  --backup-retention-period 7 \
  --storage-encrypted \
  --deletion-protection \
  --region {{user.region}} --output json
```

## Add Cluster Instances (Writer / Reader)

```bash
# Writer (first instance or explicit promotion tier 0–1)
aws rds create-db-instance \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --db-instance-class {{user.DBInstanceClass}} \
  --engine {{user.DBEngine}} \
  --promotion-tier 1 \
  --region {{user.region}} --output json

# Reader
aws rds create-db-instance \
  --db-instance-identifier {{user.ReaderInstanceIdentifier}} \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --db-instance-class {{user.DBInstanceClass}} \
  --engine {{user.DBEngine}} \
  --promotion-tier 2 \
  --region {{user.region}} --output json
```

## Serverless v2

Set scaling on create or modify:

```bash
aws rds create-db-instance \
  --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --db-instance-class db.serverless \
  --engine {{user.DBEngine}} \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16 \
  --region {{user.region}} --output json

aws rds modify-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --serverless-v2-scaling-configuration MinCapacity=1,MaxCapacity=32 \
  --apply-immediately \
  --region {{user.region}} --output json
```

## Describe / Modify / Delete Cluster

```bash
aws rds describe-db-clusters --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --region {{user.region}} --output json

aws rds modify-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --backup-retention-period 14 \
  --apply-immediately \
  --region {{user.region}} --output json

# Delete — default path uses final snapshot
aws rds delete-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --final-db-snapshot-identifier {{user.FinalSnapshotId}} \
  --region {{user.region}} --output json
```

## Failover

```bash
aws rds failover-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --target-db-instance-identifier {{user.TargetInstanceId}} \
  --region {{user.region}} --output json
```

## Stop / Start Cluster

```bash
aws rds stop-db-cluster --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --region {{user.region}} --output json
aws rds start-db-cluster --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --region {{user.region}} --output json
```

## Cluster Snapshots

```bash
aws rds create-db-cluster-snapshot \
  --db-cluster-snapshot-identifier {{user.SnapshotId}} \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --region {{user.region}} --output json

aws rds describe-db-cluster-snapshots --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --region {{user.region}} --output json

aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier {{user.NewClusterId}} \
  --snapshot-identifier {{user.SnapshotId}} \
  --engine {{user.DBEngine}} \
  --region {{user.region}} --output json

aws rds restore-db-cluster-to-point-in-time \
  --db-cluster-identifier {{user.NewClusterId}} \
  --source-db-cluster-identifier {{user.DBClusterIdentifier}} \
  --restore-to-time {{user.RestoreTime}} \
  --region {{user.region}} --output json

aws rds delete-db-cluster-snapshot \
  --db-cluster-snapshot-identifier {{user.SnapshotId}} \
  --region {{user.region}} --output json
```

## Cluster Parameter Groups

```bash
aws rds create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name {{user.ParamGroupName}} \
  --db-parameter-group-family {{user.Family}} \
  --description "{{user.Description}}" \
  --region {{user.region}} --output json

aws rds modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name {{user.ParamGroupName}} \
  --parameters "ParameterName=max_connections,ParameterValue=2000,ApplyMethod=immediate" \
  --region {{user.region}} --output json

aws rds modify-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --db-cluster-parameter-group-name {{user.ParamGroupName}} \
  --apply-immediately \
  --region {{user.region}} --output json

aws rds delete-db-cluster-parameter-group \
  --db-cluster-parameter-group-name {{user.ParamGroupName}} \
  --region {{user.region}} --output json
```

## Global Database

```bash
aws rds create-global-cluster \
  --global-cluster-identifier {{user.GlobalClusterId}} \
  --engine {{user.DBEngine}} \
  --region {{user.region}} --output json

aws rds create-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --global-cluster-identifier {{user.GlobalClusterId}} \
  --engine {{user.DBEngine}} \
  --region {{user.region}} --output json

aws rds describe-global-clusters --global-cluster-identifier {{user.GlobalClusterId}} \
  --region {{user.region}} --output json

aws rds remove-from-global-cluster \
  --global-cluster-identifier {{user.GlobalClusterId}} \
  --db-cluster-identifier {{user.SecondaryClusterArn}} \
  --region {{user.region}} --output json

aws rds delete-global-cluster \
  --global-cluster-identifier {{user.GlobalClusterId}} \
  --region {{user.region}} --output json
```

## Backtrack (Aurora MySQL)

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --backtrack-window 86400 \
  --region {{user.region}} --output json

aws rds backtrack-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --backtrack-to {{user.BacktrackTime}} \
  --region {{user.region}} --output json
```

## Custom Endpoints & Data API

```bash
aws rds create-db-cluster-endpoint \
  --db-cluster-endpoint-identifier {{user.EndpointId}} \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --static-members {{user.ReaderInstanceIds}} \
  --region {{user.region}} --output json

aws rds delete-db-cluster-endpoint \
  --db-cluster-endpoint-identifier {{user.EndpointId}} \
  --region {{user.region}} --output json

aws rds start-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --region {{user.region}} --output json
# Data API: enable via modify-db-cluster --enable-http-endpoint (Aurora Serverless / compatible)
aws rds modify-db-cluster \
  --db-cluster-identifier {{user.DBClusterIdentifier}} \
  --enable-http-endpoint \
  --region {{user.region}} --output json
```

## Waiters

```bash
aws rds wait db-cluster-available --db-cluster-identifier {{user.DBClusterIdentifier}}
aws rds wait db-cluster-deleted --db-cluster-identifier {{user.DBClusterIdentifier}}
aws rds wait db-cluster-snapshot-available --db-cluster-snapshot-identifier {{user.SnapshotId}}
```

## AIOps — Metric Collection

Use `DBClusterIdentifier` dimension for cluster-level metrics; use `DBInstanceIdentifier` for per-instance.

```bash
# Replica lag (cluster)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name AuroraReplicaLag \
  --dimensions Name=DBClusterIdentifier,Value={{user.DBClusterIdentifier}} \
  --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average,Maximum \
  --region {{user.region}} --output json

# Cluster connections
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name DatabaseConnections \
  --dimensions Name=DBClusterIdentifier,Value={{user.DBClusterIdentifier}} \
  --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum \
  --region {{user.region}} --output json

# Serverless v2 capacity (per serverless instance)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name ServerlessDatabaseCapacity \
  --dimensions Name=DBInstanceIdentifier,Value={{user.DBInstanceIdentifier}} \
  --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average,Maximum \
  --region {{user.region}} --output json

# Global Database replication lag (primary region)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name AuroraGlobalDBReplicationLag \
  --dimensions Name=DBClusterIdentifier,Value={{user.DBClusterIdentifier}} \
  --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum \
  --region {{user.region}} --output json

# Writer CPU + buffer cache
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value={{user.DBInstanceIdentifier}} \
  --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average \
  --region {{user.region}} --output json
```

### RDS Proxy path (when proxy in front of Aurora)

```bash
aws rds describe-db-proxies --region {{user.region}} --output json
aws rds describe-db-proxy-targets --db-proxy-name {{user.ProxyName}} \
  --region {{user.region}} --output json
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name ClientConnections \
  --dimensions Name=ProxyName,Value={{user.ProxyName}} \
  --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum \
  --region {{user.region}} --output json
```

### Performance Insights (writer instance)

```bash
# DbiResourceId from writer member
aws rds describe-db-instances --db-instance-identifier {{user.DBInstanceIdentifier}} \
  --query 'DBInstances[0].DbiResourceId' --output json

aws pi get-resource-metrics \
  --service-type RDS --identifier {{output.dbi_resource_id}} \
  --start-time $(date -u -d '-1 hour' +%s) --end-time $(date -u +%s) \
  --period-in-seconds 60 \
  --metric-queries '[{"Metric":"db.load.avg","GroupBy":{"Group":"db.wait_event","Limit":10}}]' \
  --region {{user.region}} --output json
```
