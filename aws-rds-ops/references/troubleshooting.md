# RDS Troubleshooting

Common RDS error codes, recovery procedures, and operational troubleshooting.

## Error Reference (by category)

### Instance Errors
| Error | Resolution |
|-------|-----------|
| DBInstanceAlreadyExists | HALT — use different identifier or modify existing |
| InvalidDBInstanceState | HALT — wait for `available` state (current: creating/modifying/deleting/stopped/upgrading) |
| DBInstanceNotFound | Verify identifier spelling, check region, or instance was deleted |
| InvalidDBInstanceClass | List valid classes: `describe-orderable-db-instance-options --engine {{engine}}` |

### Storage Errors
| Error | Resolution |
|-------|-----------|
| InsufficientStorageCapacity | Reduce size, try different AZ, use gp3 instead of io1/io2 |
| StorageTypeNotSupported | Use gp2/gp3 (supported by most engines) |
| StorageQuotaExceeded | Request quota increase, delete unused snapshots |

### Snapshot Errors
| Error | Resolution |
|-------|-----------|
| DBSnapshotAlreadyExists | Use unique name (timestamp-based: `mydb-snapshot-20260510-1200`) |
| DBSnapshotNotFound | Verify name, check region (snapshots are regional) |
| InvalidDBSnapshotState | Wait for `available` state before restore |

### Parameter Group Errors
| Error | Resolution |
|-------|-----------|
| DBParameterGroupNotFound | Create group first, or use default group |
| DBParameterGroupAlreadyExists | Use different name or modify existing |
| InvalidDBParameterGroupState | Instances using this group — modify them first |
```bash
# Check instances using a parameter group
aws rds describe-db-instances --query "DBInstances[?DBParameterGroups[?DBParameterGroupName=='{{name}}']]"
```

### Network/VPC Errors
| Error | Resolution |
|-------|-----------|
| InvalidVPCNetworkState | Verify subnet group has subnets in ≥2 AZs, check IP availability |
| DBSubnetGroupNotFound | Create subnet group or use default |
| DBSecurityGroupNotFound | Create EC2 security group first (`aws ec2 create-security-group`) |

### Permission Errors
| Error | Resolution |
|-------|-----------|
| AuthorizationNotFound | Add IAM permissions for RDS: `rds:CreateDBInstance`, `rds:DescribeDBInstances`, `rds:DeleteDBInstance` |
| KMSAccessDenied | Add KMS permissions: `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey` |

### Quota Errors
| Limit | Default | Resolution |
|-------|---------|-----------|
| DB Instances | 40/region | Request quota increase via Service Quotas console |
| DB Snapshots | 100/region | Delete unused snapshots |
| Read Replicas/source | 5 | Reduce replicas |

## Throttling (429)
Exponential backoff strategy:
```python
import time, math
def exponential_backoff(attempt, base=0.5, max_delay=60):
    time.sleep(min(base * math.pow(2, attempt), max_delay))
```

## Connection Troubleshooting
| Symptom | Cause | Solution |
|---------|-------|----------|
| Timeout | Security group blocks IP | Add inbound rule for port/source IP |
| Timeout | Instance stopped | Start instance |
| Timeout | Wrong endpoint | Use `describe` to get correct endpoint |
| Refused | Wrong port | Use correct port (3306/5432) |
| Auth failed | Wrong credentials | Verify username/password |
| Auth failed | IAM auth/SSL issue | Configure IAM/SSL properly |

**Diagnostic steps**:
```bash
aws rds describe-db-instances --db-instance-identifier {{id}} --query "DBInstances[0].Endpoint"
nc -zv {{endpoint}} {{port}}  # TCP test from app host
aws ec2 describe-security-groups --group-ids {{sg_id}} --query "SecurityGroups[0].IpPermissions"
```

## Read Replica Issues
**ReplicaLag high**: Scale source/replica, monitor via CloudWatch `ReplicaLag` metric.
**Can't promote**: Source not available / replica initializing — wait and retry.

## Aurora Cluster Issues
**Cluster unavailable**: Check `describe-db-clusters` → `.DBClusterMembers`, no writer = failover needed.
**Instance addition failed**: Cluster not available / class unsupported / AZ capacity — wait, check options, try different AZ.
```bash
aws rds failover-db-cluster --db-cluster-identifier {{cluster}} --target-db-instance-identifier {{target}}
```

## Performance Issues
| Symptom | Diagnosis | Resolution |
|---------|-----------|-----------|
| High CPU | Performance Insights → Top SQL | Scale class, tune params, optimize queries, add indexes |
| High memory (SwapUsage>0) | Connections / buffer pool | Increase buffer pool, reduce max_connections, scale class |
| IOPS saturation (ReadLatency↑) | gp2/gp3 hitting limits | Increase storage (more baseline), switch to io1/io2, scale class |
| Slow queries | Slow query log / Performance Insights | Add indexes, tune params |

## Backup/Snapshot Issues
**Snapshot hanging in `creating`**: Large DB takes time (hours). Check instance IOPS during snapshot. Multi-AZ = faster snapshots.
**Restore slow**: Large snapshot / small instance class. Use larger class for faster restore.

## Delete Operation Issues
**Blocked by read replicas**:
```bash
aws rds describe-db-instances --query "DBInstances[?ReadReplicaSourceDBInstanceIdentifier=='{{source}}']"
# Delete/promote replicas first, then delete source
```
**Blocked by deletion protection**:
```bash
aws rds modify-db-instance --db-instance-identifier {{id}} --no-deletion-protection --apply-immediately
aws rds wait db-instance-available --db-instance-identifier {{id}}
aws rds delete-db-instance --db-instance-identifier {{id}} --final-db-snapshot-identifier {{snap}}
```
**Aurora cluster**: Delete all instances in cluster first, then delete cluster.

## Parameter Group Issues
**Static param not applied**: Reboot instance — `aws rds reboot-db-instance --db-instance-identifier {{id}}`
**Invalid param value**: Check constraints with `describe-engine-default-parameters`

## Monitoring Alerts
| Alert | Threshold | Action |
|-------|-----------|--------|
| FreeStorageSpace low | < 10% | Enable auto-scaling or manually increase |
| DatabaseConnections high | > 90% max_connections | Increase max_connections, check connection leaks |
| SwapUsage > 0 | Any | Memory pressure — increase buffer pool, scale class |

## Recovery Procedures
**Instance**: Identify error → check state → apply fix (retry once) → HALT if persistent, backoff for throttling (max 3).
**Connection**: Check state → verify endpoint → test TCP → check SG → verify creds → apply fix.
**Snapshot**: Wait `available` → restore → validate → update app endpoints → monitor.