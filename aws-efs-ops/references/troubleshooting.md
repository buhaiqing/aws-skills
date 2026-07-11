# AWS EFS — Troubleshooting

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `FileSystemNotFoundException` | FS ID does not exist | Verify FS ID; check region |
| `FileSystemAlreadyExists` | Creation token reused | Idempotent; use different token |
| `FileSystemInUse` | FS has mount targets/APs | List and delete them first |
| `BadRequest` | Invalid state or parameters | Check FS state (`describe-file-systems`) |
| `MountTargetConflict` | MT already exists in subnet | Use existing mount target |
| `SecurityGroupNotFound` | SG ID invalid | Verify SG exists in VPC |
| `SubnetNotFoundException` | Subnet ID invalid | Verify subnet exists |
| `AccessPointNotFoundException` | AP ID invalid | Verify AP ID |
| `InsufficientThroughputCapacity` | Burst credit balance exhausted | Switch to Provisioned mode |
| `ThroughputLimitExceeded` | Provisioned limit too high | Reduce provisioned MiB/s |
| `DependencyTimeout` | Underlying network issue | Retry; check VPC/subnet connectivity |

## Mount Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `mount.nfs4: Connection refused` | Mount target not in subnet | Verify MT is `available` |
| `mount.nfs4: Operation timed out` | Security group blocks NFS | Open port 2049 (NFS) in SG |
| `mount.nfs4: access denied` | No Posix user / SG rule | Check SG egress; check IAM |
| `nfs: server <fs>.efs.<region>.amazonaws.com not responding` | Network path issue | Use IP address; check NACL |
| `mount: /mnt/efs: wrong fs type, bad option` | nfs-utils not installed | `yum install -y nfs-utils` or `apt install nfs-common` |
| `mount error: Protocol not supported` | NFSv4.1 not configured | Use `nfsvers=4.1` explicitly |

## Performance Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| High latency | General Purpose mode for parallel workload | Consider Max I/O mode |
| Throughput bottleneck | Burst credits exhausted | Enable Provisioned throughput |
| Slow `ls` on large directory | Directory tree too large | Restructure dirs; use access points |
| Stale file handle | NFS lock issue | `umount` then `mount` again |
| `TooManyRequests` | API throttling | Backoff; implement jitter |
