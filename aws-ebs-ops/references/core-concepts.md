# EBS Core Concepts

## Volume Types

| Type | Max IOPS | Max Throughput | Use Case |
|------|----------|---------------|----------|
| **gp3** | 16,000 | 1,000 MB/s | General purpose SSD (default) |
| **gp2** | 16,000 | 250 MB/s | Legacy general purpose |
| **io1** | 64,000 | 1,000 MB/s | High-performance: databases (legacy) |
| **io2 Block Express** | 256,000 | 4,000 MB/s | Mission-critical: SAP, Oracle |
| **st1** | 500 | 500 MB/s | Throughput-optimized HDD: logs, big data |
| **sc1** | 250 | 250 MB/s | Cold HDD: infrequent access |

## Key Concepts

- **Encryption**: EBS volumes can be encrypted at rest using KMS. Enforced via `--encrypted` flag or account-level setting.
- **Snapshots**: Incremental backup to S3. First snapshot is full; subsequent are incremental.
- **Multi-Attach** (io1/io2 only): Attach same volume to multiple Nitro-based instances (read/write from any).
- **Delete on Termination**: Auto-delete volume when EC2 instance is terminated (default for root volumes).
- **Modification**: Resize, IOPS, and throughput changes live — no downtime. Only increase size; no shrink.

## Snapshot Lifecycle

```
Create → Pending → In Progress → Completed
                                ↓
                         [Incremental backup]
                                ↓
                         Available for new volumes
```

## Limits

| Resource | Default |
|----------|---------|
| Volume size (gp3/io2) | 1-16,384 GiB |
| Volume size (st1/sc1) | 125-16,384 GiB |
| Snapshots per account | 100,000 |
| Total snapshot storage | Unlimited (charged per GiB-month) |
| Max attachments per volume | 1 (standard) / 16 (multi-attach io1/io2) |