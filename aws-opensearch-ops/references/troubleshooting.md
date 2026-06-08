# OpenSearch Service Troubleshooting

Common OpenSearch Service error codes, recovery procedures, and operational troubleshooting.

## Error Reference (by category)

### Domain Errors
| Error | Resolution |
|-------|-----------|
| ResourceAlreadyExistsException | HALT — use different domain name or modify existing |
| ResourceNotFoundException | Verify domain name spelling, check region, or domain was deleted |
| InvalidTypeException | List valid types: `aws opensearch list-instance-type-details` |
| ValidationException | HALT — fix parameters (e.g., invalid engine version) |
| DomainProcessingException | HALT — domain is processing; retry later |

### Storage Errors
| Error | Resolution |
|-------|-----------|
| LimitExceededException | Request quota increase or reduce cluster size |
| InsufficientStorageCapacity | Reduce volume size or change instance type |

### Snapshot Errors
| Error | Resolution |
|-------|-----------|
| SnapshotInProgressException | HALT — wait for current snapshot to complete |
| ResourceNotFoundException (snapshot) | Verify snapshot name and repository |
| BaseException | RETRY — transient error |

### Network/VPC Errors
| Error | Resolution |
|-------|-----------|
| InvalidVPCNetworkState | Verify subnet IDs, SG IDs, and VPC configuration |
| VPCAccessNotEnabled | Enable VPC access during domain creation |

### Permission Errors
| Error | Resolution |
|-------|-----------|
| AccessDeniedException | Add IAM permissions: `es:CreateDomain`, `es:DescribeDomain`, `es:DeleteDomain` |
| KMSAccessDeniedException | Add KMS permissions for encryption at rest |

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
| Timeout | Security group blocks IP | Add inbound rule for port 443 / source IP |
| Timeout | Domain in VPC without endpoint | Use VPC endpoint or bastion host |
| Auth failed | Wrong master user credentials | Verify username/password or IAM role |
| Auth failed | Fine-grained access control disabled | Enable AdvancedSecurityOptions |

**Diagnostic steps**:
```bash
aws opensearch describe-domain --domain-name {{name}} --query "DomainStatus.Endpoint"
aws opensearch describe-domain --domain-name {{name}} --query "DomainStatus.VPCOptions"
aws ec2 describe-security-groups --group-ids {{sg_id}} --query "SecurityGroups[0].IpPermissions"
```

## Cluster Health Issues
| Symptom | Diagnosis | Resolution |
|---------|-----------|-----------|
| ClusterStatus red | Missing primary shard | Restore from snapshot; check node health |
| ClusterStatus yellow | Unassigned replica shards | Add nodes or reduce replica count |
| High JVMMemoryPressure | Heap pressure > 75% | Scale up instance type; reduce shard count |
| High CPUUtilization | Heavy indexing/search | Scale instance type; add data nodes |
| FreeStorageSpace low | < 20% | Increase EBS volume; enable UltraWarm |
| High ShardCount | > 1000 per node | Shrink indices; use index rollover |
| Slow queries | Large index, no mapping | Add mapping; use index templates; tune refresh interval |

## Snapshot Issues
**Snapshot hanging**: Large domains take time. Check `SnapshotList[].Status` via `describe-snapshots`.
**Restore slow**: Large snapshot / small instance class. Use larger class for faster restore.

## Delete Operation Issues
**Blocked by snapshot in progress**:
```bash
aws opensearch describe-snapshots --domain-name {{name}} --repository-name cs-automated
# Wait for Status=completed, then retry delete
```
**Domain in Processing state**:
```bash
aws opensearch describe-domain --domain-name {{name}} --query "DomainStatus.Processing"
# Wait for false before delete or modify
```

## Upgrade Issues
**Incompatible upgrade**: Check `get-compatible-versions` first.
**Upgrade failed**: Domain rolls back automatically. Check `UpgradeHistory` for errors.

## Monitoring Alerts
| Alert | Threshold | Action |
|-------|-----------|--------|
| ClusterStatus red | Any | Immediate investigation; restore from snapshot if needed |
| JVMMemoryPressure | > 85% | Scale up or reduce shards |
| FreeStorageSpace | < 20% | Increase volume or enable UltraWarm |
| CPUUtilization | > 80% sustained | Scale instance type or add nodes |

## Recovery Procedures
**Domain**: Identify error → check state → apply fix (retry once) → HALT if persistent, backoff for throttling (max 3).
**Connection**: Check state → verify endpoint → test TCP → check SG → verify creds → apply fix.
**Snapshot**: Wait `completed` → restore → validate → update app endpoints → monitor.
