# AWS CLI Usage — EBS

> **Pre-condition**: `aws sts get-caller-identity` before any command.

## Common JSON Paths
- Volume: `.Volumes[0].{VolumeId,State,Size,VolumeType,Iops,Throughput,Encrypted,AvailabilityZone}`
- Snapshot: `.Snapshots[0].{SnapshotId,VolumeId,State,VolumeSize,Description,StartTime}`
- Attachments: `.Volumes[0].Attachments[].{InstanceId,Device,State,AttachTime}`

## Commands

```bash
# Volumes
aws ec2 create-volume --volume-type gp3 --size {{user.size_gib}} --availability-zone {{user.avail_zone}} --encrypted --output json
aws ec2 describe-volumes --volume-ids "{{user.volume_id}}" --output json
aws ec2 describe-volumes --filters Name=status,Values=available --output json
aws ec2 delete-volume --volume-id "{{user.volume_id}}" --output json

# Modify volume
aws ec2 modify-volume --volume-id "{{user.volume_id}}" --size {{user.new_size}} --iops {{user.new_iops}} --throughput {{user.new_throughput}} --output json
aws ec2 describe-volumes-modifications --volume-ids "{{user.volume_id}}" --output json

# Attach/Detach
aws ec2 attach-volume --volume-id "{{user.volume_id}}" --instance-id "{{user.instance_id}}" --device "{{user.device}}" --output json
aws ec2 detach-volume --volume-id "{{user.volume_id}}" --instance-id "{{user.instance_id}}" --device "{{user.device}}" --force --output json

# Snapshots
aws ec2 create-snapshot --volume-id "{{user.volume_id}}" --description "Snapshot via AIOps" --output json
aws ec2 describe-snapshots --snapshot-ids "{{user.snapshot_id}}" --output json
aws ec2 describe-snapshots --owner-ids self --query "Snapshots[?StartTime>='2026-01-01']" --output json
aws ec2 delete-snapshot --snapshot-id "{{user.snapshot_id}}" --output json

# Volume status
aws ec2 describe-volume-status --volume-ids "{{user.volume_id}}" --output json
aws ec2 describe-account-attributes --attribute-names max-instances --output json
```