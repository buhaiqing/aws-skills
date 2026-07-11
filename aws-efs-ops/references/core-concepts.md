# AWS EFS — Core Concepts

## Service Architecture

| Concept | Description |
|---------|-------------|
| **File System** | Regional NFSv4.1-compatible storage; accessible across AZs via mount targets |
| **Mount Target** | Network endpoint (ENI) per subnet; provides NFS access point for EC2/Lambda |
| **Access Point** | Application-specific entry point with POSIX user + root directory restriction |
| **Lifecycle Management** | Auto-transition files to Infrequent Access (IA) tier after N days |
| **Throughput Mode** | Bursting (baseline + credits) or Provisioned (fixed MiB/s) |

## Performance Modes

| Mode | Use Case | Max Throughput |
|------|----------|---------------|
| **General Purpose** (default) | Latency-sensitive workloads (web, CMS, CI/CD) | 3 GB/s (burst) |
| **Max I/O** | High-throughput parallel workloads (big data, HPC) | 10+ GB/s |

## Throughput Modes

| Mode | Pricing | Best For |
|------|---------|----------|
| **Bursting** | 1 MiB/s per 1 GiB of storage | Variable workloads |
| **Provisioned** | Fixed $/MiB/s | Predictable high throughput |
| **Elastic** | Pay per MiB/s consumed | Unpredictable throughput needs |

## Key Quotas (verify at runtime)

| Resource | Default Limit | CLI Query |
|----------|--------------|-----------|
| File systems per region | 100 | `aws efs describe-file-systems \| jq '.FileSystems \| length'` |
| Mount targets per FS per AZ | 1 | `aws efs describe-mount-targets --file-system-id <fs>` |
| Security groups per mount target | 5 | `describe-mount-target-security-groups` |
| Access points per FS | 1,000 | `describe-access-points` |

## NFS Client Mount

```bash
# From EC2 (install nfs-utils first)
sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport \
  {{user.file_system_id}}.efs.{{user.region}}.amazonaws.com:/ /mnt/efs
```

## Encryption

| Type | Setting | Key |
|------|---------|-----|
| At rest (data) | `--encrypted` | AWS managed or KMS (`--kms-key-id`) |
| In transit (NFS) | AWS CLI default | TLS via mount helper |

## Lifecycle Policy Rules

| Policy | Action | Use Case |
|--------|--------|----------|
| `AFTER_14_DAYS` → IA | Move to Infrequent Access after 14 days | Standard infrequent access |
| `AFTER_30_DAYS` → IA | Move to IA after 30 days | Backup/archive data |
| `AFTER_60_DAYS` → IA | Move to IA after 60 days | Cold data |
| `AFTER_90_DAYS` → IA | Move to IA after 90 days | Long-term retention |
