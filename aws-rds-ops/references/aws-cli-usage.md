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

## SQL Slow Query Analysis

### Enable Performance Insights (on existing instance)
```bash
aws rds modify-db-instance \
  --db-instance-identifier {{id}} \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --apply-immediately
```

### Enable Slow Query Log Publish to CloudWatch
```bash
# MySQL / Aurora MySQL
aws rds modify-db-instance \
  --db-instance-identifier {{id}} \
  --cloudwatch-logs-export-configuration '{"EnableLogTypes":["slowquery"]}' \
  --apply-immediately

# PostgreSQL / Aurora PostgreSQL
aws rds modify-db-instance \
  --db-instance-identifier {{id}} \
  --cloudwatch-logs-export-configuration '{"EnableLogTypes":["postgresql"]}' \
  --apply-immediately
```

### Get DbiResourceId (required for Performance Insights API)
```bash
aws rds describe-db-instances \
  --db-instance-identifier {{id}} \
  --query 'DBInstances[0].DbiResourceId' \
  --output json
```

### Performance Insights — Top SQL by DB Load
```bash
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier {{dbi_resource_id}} \
  --start-time $(date -u -d '-1 hour' +%s) \
  --end-time $(date -u +%s) \
  --period-in-seconds 60 \
  --metric-queries '[{"Metric": "db.sproc_execution_time", "GroupBy": {"Group": "db.sql_tokenized", "Limit": 10}}]' \
  --region {{region}} \
  --output json
```

### Performance Insights — Wait Event Breakdown
```bash
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier {{dbi_resource_id}} \
  --start-time $(date -u -d '-1 hour' +%s) \
  --end-time $(date -u +%s) \
  --period-in-seconds 60 \
  --metric-queries '[{"Metric": "db.sproc_execution_time", "GroupBy": {"Group": "db.wait_event", "Limit": 10}}]' \
  --region {{region}} \
  --output json
```

### Performance Insights — Multi-Metric Over Time
```bash
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier {{dbi_resource_id}} \
  --start-time $(date -u -d '-6 hours' +%s) \
  --end-time $(date -u +%s) \
  --period-in-seconds 300 \
  --metric-queries '[
    {"Metric": "db.sproc_execution_time"},
    {"Metric": "db.cpu"},
    {"Metric": "db.io"},
    {"Metric": "db.dbload"}
  ]' \
  --region {{region}} \
  --output json
```

### List Available PI Dimensions
```bash
aws pi list-available-resource-dimensions \
  --service-type RDS \
  --identifier {{dbi_resource_id}} \
  --region {{region}} \
  --output json
```

### Query Slow Query Log from CloudWatch (MySQL)
```bash
LOG_GROUP="/aws/rds/instance/{{id}}/slowquery"
aws logs start-query \
  --log-group-name "$LOG_GROUP" \
  --start-time $(date -u -d '-1 hour' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message
    | filter @message like /(?i)(Query_time|# User@Host)/
    | parse @message /Query_time: (?<query_time>\S+).*Lock_time: (?<lock_time>\S+).*Rows_sent: (?<rows_sent>\d+).*Rows_examined: (?<rows_examined>\d+)/
    | sort query_time desc
    | limit 50' \
  --region {{region}} \
  --output json
```

### Query Slow Query Log from CloudWatch (PostgreSQL)
```bash
LOG_GROUP="/aws/rds/instance/{{id}}/postgresql"
aws logs start-query \
  --log-group-name "$LOG_GROUP" \
  --start-time $(date -u -d '-1 hour' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message
    | filter @message like /duration:/
    | parse @message /duration: (?<duration_ms>[\d.]+) ms/
    | sort duration_ms desc
    | limit 50' \
  --region {{region}} \
  --output json
```

### Slow Query Log Parameter Configuration (MySQL)
```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name {{param_group}} \
  --parameters '[
    {"ParameterName":"slow_query_log","ParameterValue":"1","ApplyMethod":"immediate"},
    {"ParameterName":"long_query_time","ParameterValue":"5","ApplyMethod":"immediate"},
    {"ParameterName":"log_queries_not_using_indexes","ParameterValue":"1","ApplyMethod":"immediate"}
  ]'
```

### Slow Query Log Parameter Configuration (PostgreSQL)
```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name {{param_group}} \
  --parameters '[
    {"ParameterName":"log_min_duration_statement","ParameterValue":"5000","ApplyMethod":"immediate"},
    {"ParameterName":"log_connections","ParameterValue":"1","ApplyMethod":"immediate"}
  ]'
```

## Common Option Flags
```
--backup-retention-period 7 | --multi-az | --storage-encrypted | --kms-key-id {{key}}
--enable-performance-insights --performance-insights-retention-period 7
--deletion-protection | --publicly-accessible (avoid prod) | --auto-minor-version-upgrade
--monitoring-interval 60 --monitoring-role-arn {{arn}}
```