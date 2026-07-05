# EBS Troubleshooting

## Error Table

| Error | Resolution |
|-------|-----------|
| `VolumeInUse` | Detach volume before delete |
| `InvalidVolume.ZoneMismatch` | Create volume in same AZ as target instance |
| `InvalidParameterValue` | Check size/type/IOPS constraints; gp3 max 16k IOPS |
| `SnapshotInProgress` | Wait for snapshot to complete before deleting |
| `VolumeModificationRateExceeded` | Wait 6 hours between modification requests |
| `IncorrectState` | Volume must be `available` or `in-use` for the operation |
| `ResourceLimitExceeded` | Account volume/snapshot limit exceeded |
| `DependencyViolation` | Volume has dependent snapshots or attachments |
| `InvalidSnapshot.InProgress` | Snapshot still in progress; cannot delete |

## Common Issues

### Volume stuck in `creating`
- Rare; wait up to 5 minutes
- If still stuck, delete and recreate

### Detach takes too long
- Force detach with `--force` flag
- Note: `--force` may risk data integrity; unmount from OS first

### Modification not taking effect
- gp3 → gp3 changes are live; io1/io2/gp2 need 6h cooldown
- Size increase only; no shrink
- File system resize required on Linux: `sudo resize2fs /dev/xvdf`

### Snapshot lifecycle
```bash
# Check snapshot progress
aws ec2 describe-snapshots --snapshot-ids "{{user.snapshot_id}}" \
  --query "Snapshots[0].{State:State,Progress:Progress,VolumeSize:VolumeSize}"
```