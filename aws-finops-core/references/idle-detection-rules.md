# Idle Detection Rules

Detect idle resources across 5 types. All queries are read-only.

## Common JSON Paths

```python
# CloudWatch get-metric-statistics
$.Datapoints[].Timestamp
$.Datapoints[].Average

# ELB describe-load-balancers
$.LoadBalancers[].LoadBalancerName
$.LoadBalancers[].State.Code

# EC2 describe-volumes / describe-snapshots
$.Volumes[].VolumeId
$.Volumes[].State
$.Snapshots[].SnapshotId
$.Snapshots[].VolumeId

# Lambda list-functions
$.Functions[].FunctionName
$.Functions[].LastModified

# RDS describe-db-instances
$.DBInstances[].DBInstanceIdentifier
$.DBInstances[].DBInstanceStatus
```

## ALB/NLB Idle Detection

**Idle definition**: CloudWatch `RequestCount=0` for ≥ N consecutive days.

```bash
# List all LBs
aws elbv2 describe-load-balancers --output json

# Query RequestCount per LB
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=<LB_ARN> \
  --start-time $(date -u -d "{{user.idle_days}} days ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --output json
```

**Decision logic**: If `Sum(RequestCount) == 0` for all days in period → IDLE.

## EBS Volume Idle Detection

**Idle definition**: `Status=available` (not attached) for ≥ 30 days.

```bash
# Find unattached volumes
aws ec2 describe-volumes \
  --filters Name=status,Values=available \
  --query 'Volumes[*].{VolumeId:VolumeId,CreateTime:CreateTime,Size:Size,Tags:Tags}' \
  --output json
```

**Decision logic**: Filter `CreateTime` older than 30 days. Delegate to `aws-ec2-ops` for snapshot-and-delete workflow.

## EBS Snapshot Orphan Detection

**Idle definition**: Snapshot with no associated attached volume (volume deleted).

```bash
aws ec2 describe-snapshots \
  --owner-ids self \
  --query 'Snapshots[?!contains(to_string(Tags), `aws:ec2volume`)].{SnapshotId:SnapshotId,VolumeId:VolumeId,StartTime:StartTime,State:SnapshotState}' \
  --output json
```

**Decision logic**: If `VolumeId` is `None` or the volume no longer exists → orphaned.

## Lambda Idle Detection

**Idle definition**: CloudWatch `Invocations=0` for ≥ 30 consecutive days.

```bash
# List all functions
aws lambda list-functions --output json

# Query Invocations metric
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=<FUNCTION_NAME> \
  --start-time $(date -u -d "30 days ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --output json
```

**Decision logic**: If `Sum(Invocations) == 0` for all 30 days → IDLE.

## RDS Instance Idle Detection

**Idle definition**: CloudWatch `DatabaseConnections=0` for ≥ N days.

```bash
# List RDS instances
aws rds describe-db-instances \
  --query 'DBInstances[*].{DBInstanceIdentifier:DBInstanceIdentifier,DBInstanceClass:DBInstanceClass,Engine:Engine}' \
  --output json

# Query connections metric
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=<DB_INSTANCE_ID> \
  --start-time $(date -u -d "{{user.idle_days}} days ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --output json
```

**Decision logic**: If `Sum(DatabaseConnections) == 0` for all days → IDLE. Delegate to `aws-rds-ops` for retention policy review.
