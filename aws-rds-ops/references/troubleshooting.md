# RDS Troubleshooting

Common RDS error codes, recovery procedures, and operational troubleshooting.

## Error Code Reference

### Instance Errors

#### DBInstanceAlreadyExists
```
Error: DB instance {{identifier}} already exists
```
**Cause**: Attempting to create instance with existing identifier.
**Resolution**: 
- Use `describe-db-instances` to check existing instance
- Use different identifier for new instance
- Modify existing instance instead of creating new one

#### InvalidDBInstanceState
```
Error: DB instance {{identifier}} is in {{state}} state
```
**Cause**: Operation not allowed in current state.
**Common States and Actions**:
| Current State | Blocked Operations | Resolution |
|---------------|-------------------|------------|
| creating | modify, delete | Wait for 'available' |
| modifying | modify, delete | Wait for 'available' |
| deleting | any operation | Wait for deletion |
| restoring | modify, delete | Wait for 'available' |
| stopped | snapshot, modify | Start instance first |
| upgrading | modify, delete | Wait for 'available' |

**Resolution**:
```bash
aws rds describe-db-instances --db-instance-identifier {{identifier}}
# Wait for state to become 'available'
```

#### DBInstanceNotFound
```
Error: DB instance {{identifier}} not found
```
**Cause**: Instance deleted or identifier incorrect.
**Resolution**:
- Verify identifier spelling
- Check different region
- Check if instance was recently deleted

#### InvalidDBInstanceClass
```
Error: DB instance class {{class}} is not supported
```
**Cause**: Instance class not available for engine or region.
**Resolution**:
- Use `describe-orderable-db-instance-options` to list valid classes
- Check region-specific availability
- Try alternative instance class

### Storage Errors

#### InsufficientStorageCapacity
```
Error: Insufficient storage capacity for requested storage size
```
**Cause**: Region or AZ cannot allocate requested storage.
**Resolution**:
- Reduce allocated storage size
- Try different availability zone
- Try different region
- Use gp3 instead of io1/io2 if not needed

#### StorageTypeNotSupported
```
Error: Storage type {{type}} not supported for engine {{engine}}
```
**Cause**: Engine or configuration doesn't support storage type.
**Resolution**:
- Use supported storage type (gp2, gp3 for most engines)
- Check engine documentation for storage options

#### StorageQuotaExceeded
```
Error: Storage quota exceeded for account
```
**Cause**: Total storage allocation exceeds regional limit.
**Resolution**:
- Request quota increase via Service Quotas
- Delete unused snapshots
- Reduce storage on existing instances

### Snapshot Errors

#### DBSnapshotAlreadyExists
```
Error: DB snapshot {{identifier}} already exists
```
**Cause**: Snapshot name already used.
**Resolution**:
- Use unique snapshot identifier
- Timestamp-based naming: `mydb-snapshot-20260510-1200`

#### DBSnapshotNotFound
```
Error: DB snapshot {{identifier}} not found
```
**Cause**: Snapshot deleted or identifier incorrect.
**Resolution**:
- Verify snapshot identifier
- Check snapshot was created successfully
- Check region (snapshots are regional)

#### InvalidDBSnapshotState
```
Error: DB snapshot {{identifier}} is not in available state
```
**Cause**: Snapshot still being created or in invalid state.
**Resolution**:
- Wait for snapshot to reach 'available' state
- Check snapshot status before restore

### Parameter Group Errors

#### DBParameterGroupNotFound
```
Error: DB parameter group {{name}} not found
```
**Cause**: Parameter group doesn't exist.
**Resolution**:
- Create parameter group first
- Use default parameter group
- Verify group name spelling

#### DBParameterGroupAlreadyExists
```
Error: DB parameter group {{name}} already exists
```
**Cause**: Attempting to create existing group.
**Resolution**:
- Use different name
- Modify existing group instead

#### InvalidDBParameterGroupState
```
Error: DB parameter group {{name}} cannot be deleted
```
**Cause**: Instances are using the parameter group.
**Resolution**:
```bash
# Check instances using the group
aws rds describe-db-instances --query "DBInstances[?DBParameterGroups[?DBParameterGroupName=='{{name}}']]"
# Modify instances to use different group before deletion
```

### Network/VPC Errors

#### InvalidVPCNetworkState
```
Error: VPC network state is invalid
```
**Cause**: Subnet group or network configuration issue.
**Resolution**:
- Verify DB subnet group has subnets in multiple AZs
- Check subnets have sufficient IP addresses
- Verify security group exists and allows required access

#### DBSubnetGroupNotFound
```
Error: DB subnet group {{name}} not found
```
**Cause**: Subnet group doesn't exist.
**Resolution**:
- Create DB subnet group first
- Use default subnet group if available

#### DBSecurityGroupNotFound
```
Error: DB security group {{id}} not found
```
**Cause**: VPC security group doesn't exist.
**Resolution**:
- Create EC2 security group first
- Use `aws ec2 create-security-group`
- Verify security group ID format

### Permission Errors

#### AuthorizationNotFound
```
Error: User does not have authorization for operation
```
**Cause**: IAM permissions missing for RDS operation.
**Resolution**:
- Add required IAM policy for RDS
- Check IAM user/role permissions
- Required permissions depend on operation:
```json
{
  "Effect": "Allow",
  "Action": [
    "rds:CreateDBInstance",
    "rds:DescribeDBInstances",
    "rds:DeleteDBInstance"
  ],
  "Resource": "*"
}
```

#### KMSAccessDenied
```
Error: Access denied to KMS key {{key_id}}
```
**Cause**: IAM permissions missing for KMS key.
**Resolution**:
- Add KMS permissions for encryption
- Verify KMS key exists and is not scheduled for deletion
```json
{
  "Effect": "Allow",
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:GenerateDataKey"
  ],
  "Resource": "{{key_arn}}"
}
```

### Quota Errors

#### QuotaExceeded
```
Error: You have reached the quota limit for {{resource}}
```
**Common Quotas**:
| Resource | Default Limit |
|----------|---------------|
| DB Instances | 40 |
| DB Snapshots | 100 |
| Read Replicas per source | 5 |

**Resolution**:
- Request quota increase via AWS Service Quotas console
- Delete unused resources
- Optimize resource usage

## Throttling Handling

### API Rate Limiting
```
Error: Request rate limit exceeded (ThrottlingException)
```
**Cause**: Too many API requests in short time.
**Resolution**:
- Implement exponential backoff
- Reduce request frequency
- Use batch operations when possible

**Backoff Strategy**:
```python
import time
import math

def exponential_backoff(attempt: int, base: float = 0.5, max_delay: float = 60):
    """Calculate delay for exponential backoff."""
    delay = min(base * math.pow(2, attempt), max_delay)
    time.sleep(delay)
```

## Connection Troubleshooting

### Cannot Connect to Database

#### Symptoms
- Connection timeout
- Connection refused
- Authentication failed

#### Common Causes and Solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| Timeout | Security group blocks IP | Add inbound rule for port/source IP |
| Timeout | Instance stopped | Start instance |
| Timeout | Wrong endpoint | Use describe to get correct endpoint |
| Refused | Wrong port | Use correct port (3306/5432) |
| Auth failed | Wrong credentials | Verify username/password |
| Auth failed | IAM auth issue | Configure IAM authentication properly |
| Auth failed | SSL required | Configure SSL in client |

#### Diagnostic Steps
```bash
# 1. Check instance status
aws rds describe-db-instances --db-instance-identifier {{identifier}}

# 2. Verify endpoint
aws rds describe-db-instances --db-instance-identifier {{identifier}} \
  --query "DBInstances[0].Endpoint"

# 3. Test TCP connectivity (from application host)
nc -zv {{endpoint}} {{port}}

# 4. Check security group rules
aws ec2 describe-security-groups --group-ids {{sg_id}} \
  --query "SecurityGroups[0].IpPermissions"
```

### Slow Connection Performance

#### Causes
- High CPU utilization
- Insufficient memory (swapping)
- Disk IOPS saturation
- Network latency
- Large connection pool

#### Diagnostics
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value={{identifier}} \
  --statistics Average \
  --period 300 \
  --start-time {{start}} \
  --end-time {{end}}

# Check Performance Insights (if enabled)
aws rds describe-performance-insights-details \
  --db-instance-identifier {{identifier}}
```

## Read Replica Issues

### Replica Lag

**Symptoms**: High replication lag, stale data.

**Causes**:
- Insufficient write capacity on source
- Network latency (cross-region)
- Large transaction volume
- Replica instance undersized

**Resolution**:
- Scale source instance
- Scale replica instance
- Monitor via CloudWatch: `ReplicaLag`

### Replica Promotion Issues

**Error**: Cannot promote read replica
**Causes**:
- Source instance not in 'available' state
- Replica still initializing
- Replication in progress

**Resolution**:
- Wait for replica status 'available'
- Check ReadReplicaSourceDBInstanceIdentifier

## Aurora Cluster Issues

### Cluster Not Available

**Symptoms**: Cluster endpoint unreachable.

**Causes**:
- No instances in cluster
- Writer instance failed
- Network issues

**Resolution**:
```bash
# Check cluster status
aws rds describe-db-clusters --db-cluster-identifier {{identifier}}

# Verify instances in cluster
aws rds describe-db-clusters --db-cluster-identifier {{identifier}} \
  --query "DBClusters[0].DBClusterMembers"
```

### Instance Addition Failed

**Error**: Cannot add instance to cluster

**Causes**:
- Cluster not in 'available' state
- Instance class not supported
- AZ capacity issue

**Resolution**:
- Wait for cluster available
- Check orderable options
- Try different AZ

## Performance Issues

### High CPU Utilization

**Diagnosis**:
- Check Performance Insights for top queries
- Review slow query logs
- Tune parameters (memory, connections)

**Resolution**:
- Scale instance class (more CPU)
- Tune database parameters
- Optimize queries
- Add indexes

### High Memory Usage

**Symptoms**: SwapUsage metric high, performance degradation.

**Causes**:
- Buffer pool too small
- Too many connections
- Memory leaks (rare)

**Resolution**:
- Increase buffer pool size (parameter group)
- Reduce max_connections
- Scale to larger instance class

### Disk IOPS Saturation

**Symptoms**: High ReadLatency, WriteLatency.

**Causes**:
- Storage insufficient for workload
- gp2/gp3 hitting IOPS limits

**Resolution**:
- Increase allocated storage (more baseline IOPS for gp2/gp3)
- Switch to provisioned IOPS (io1/io2)
- Scale instance class for more memory (reduce disk reads)

## Backup/Snapshot Issues

### Snapshot Creation Hanging

**Symptoms**: Snapshot stays in 'creating' state.

**Causes**:
- Large database size
- IOPS saturation during snapshot
- Instance in wrong state

**Resolution**:
- Wait (large DBs take hours)
- Check instance IOPS during snapshot
- Use Multi-AZ for faster snapshots

### Restore Taking Too Long

**Causes**:
- Large snapshot size
- Instance class affects restore speed
- Storage allocation overhead

**Resolution**:
- Wait for restore completion
- Use larger instance class for faster restore
- Monitor via describe-db-instances

## Delete Operation Issues

### Delete Blocked by Read Replicas

```
Error: Cannot delete DB instance because it has read replicas
```
**Resolution**:
```bash
# 1. List replicas
aws rds describe-db-instances --query "DBInstances[?ReadReplicaSourceDBInstanceIdentifier=='{{source_id}}']"

# 2. Delete replicas first or promote them
aws rds delete-db-instance --db-instance-identifier {{replica_id}} --skip-final-snapshot

# 3. Then delete source
aws rds delete-db-instance --db-instance-identifier {{source_id}} --final-db-snapshot-identifier {{final_snapshot}}
```

### Delete Blocked by Deletion Protection

```
Error: Cannot delete DB instance because deletion protection is enabled
```
**Resolution**:
```bash
# 1. Disable deletion protection
aws rds modify-db-instance \
  --db-instance-identifier {{identifier}} \
  --no-deletion-protection \
  --apply-immediately

# 2. Wait for modification
aws rds wait db-instance-available --db-instance-identifier {{identifier}}

# 3. Delete instance
aws rds delete-db-instance --db-instance-identifier {{identifier}} --final-db-snapshot-identifier {{snapshot}}
```

### Delete Blocked by Aurora Cluster

```
Error: Cannot delete Aurora cluster instance - cluster has instances
```
**Resolution**:
- Delete all instances in cluster first
- Then delete cluster

## Parameter Group Troubleshooting

### Static Parameter Not Applied

**Symptom**: Parameter value shows in group but not effective.

**Cause**: Static parameters require reboot.

**Resolution**:
```bash
# Reboot instance to apply static parameters
aws rds reboot-db-instance --db-instance-identifier {{identifier}}
```

### Invalid Parameter Value

```
Error: Invalid parameter value for {{parameter_name}}
```
**Resolution**:
- Check parameter constraints in documentation
- Verify value format (units, ranges)
- Use `describe-engine-default-parameters` for valid ranges

## Monitoring Alerts

### FreeStorageSpace Low

**Symptom**: FreeStorageSpace metric declining.

**Resolution**:
- Enable storage auto-scaling
- Increase allocated storage
- Delete old data/logs
- Monitor threshold: < 10% critical

### DatabaseConnections High

**Symptom**: Connections near max_connections limit.

**Resolution**:
- Increase max_connections in parameter group
- Review connection pool settings in application
- Check for connection leaks
- Scale instance class

### SwapUsage High

**Symptom**: SwapUsage > 0, indicates memory pressure.

**Resolution**:
- Increase buffer pool size
- Scale to larger instance class
- Reduce connection count

## Recovery Procedures

### Instance Recovery Flow
```
1. Identify error type
2. Check instance state
3. Apply immediate fix (retry with correction)
4. If HALT condition, escalate to user
5. If retry condition, apply exponential backoff
6. Max 3 retries before HALT
```

### Connection Recovery Flow
```
1. Check instance state (available)
2. Verify endpoint and port
3. Test network connectivity
4. Check security group rules
5. Verify credentials
6. Apply fix based on diagnosis
```

### Snapshot Recovery Flow
```
1. Wait for snapshot 'available' state
2. Restore to new instance
3. Validate data integrity
4. Update application endpoints
5. Monitor new instance
```