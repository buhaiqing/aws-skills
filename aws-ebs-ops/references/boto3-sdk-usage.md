# boto3 SDK Usage — EBS

```python
import boto3
ec2 = boto3.client('ec2', region_name='{{env.AWS_DEFAULT_REGION}}')

# Create volume
resp = ec2.create_volume(VolumeType='gp3', Size=100, AvailabilityZone='{{user.avail_zone}}', Encrypted=True)
vol_id = resp['VolumeId']

# List/describe volumes
vols = ec2.describe_volumes()['Volumes']
vol = ec2.describe_volumes(VolumeIds=['{{user.volume_id}}'])['Volumes'][0]

# Attach volume
ec2.attach_volume(VolumeId='{{user.volume_id}}', InstanceId='{{user.instance_id}}', Device='{{user.device}}')

# Detach volume
ec2.detach_volume(VolumeId='{{user.volume_id}}', InstanceId='{{user.instance_id}}', Device='{{user.device}}', Force=True)

# Delete volume
ec2.delete_volume(VolumeId='{{user.volume_id}}')

# Modify volume
ec2.modify_volume(VolumeId='{{user.volume_id}}', Size=200, Iops=5000, Throughput=250)

# Check modification progress
mods = ec2.describe_volumes_modifications(VolumeIds=['{{user.volume_id}}'])['VolumesModifications']
mod_state = mods[0]['ModificationState']  # modifying/completed/failed

# Create snapshot
resp = ec2.create_snapshot(VolumeId='{{user.volume_id}}', Description='Backup')
snap_id = resp['SnapshotId']

# List snapshots
snaps = ec2.describe_snapshots(OwnerIds=['self'])['Snapshots']

# Delete snapshot
ec2.delete_snapshot(SnapshotId='{{user.snapshot_id}}')

# Wait for snapshot completion
waiter = ec2.get_waiter('snapshot_completed')
waiter.wait(SnapshotIds=['{{user.snapshot_id}}'])

# Check volume status
status = ec2.describe_volume_status(VolumeIds=['{{user.volume_id}}'])
```