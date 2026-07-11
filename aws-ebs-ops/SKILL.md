---
name: aws-ebs-ops
description: >-
  Use when operating AWS EBS (Elastic Block Store) volumes via AWS CLI
  or boto3 SDK; user mentions EBS, volume, block storage, snapshot,
  or attached disk.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-06"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-ec2-ops            # Instance operations
    - aws-cloudwatch-ops     # EBS metrics (VolumeWriteOps, VolumeReadOps, VolumeQueueLength)
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ["health-check", "capacity-review"]
    produces_facts: ["state", "event"]
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
---

# AWS EBS Operations Skill

## Overview

AWS Elastic Block Store (EBS) provides block-level storage volumes for use with EC2 instances. This skill covers **volume lifecycle, snapshot management, modification, and attachment** operations.

## Trigger & Scope

### SHOULD Use When
- User mentions "EBS", "volume", "block storage", "snapshot", "ephemeral storage"
- Task involves CRUD on **EBS resources** (volume, snapshot)
- Keywords: ebs, volume, snapshot, block-store, gp3, io2, st1, xfs, ext4

### SHOULD NOT Use When
- EC2 instance management → delegate to: `aws-ec2-ops`
- Instance store volumes → ephemeral, not EBS
- S3 object storage → delegate to: `aws-s3-ops`
- EFS file system → delegate to AWS EFS (if a dedicated EFS skill is available)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default; allow override |
| `{{env.AWS_ACCOUNT_ID}}` | Runtime env | Required for volume ARN |
| `{{user.volume_id}}` | User input | vol-xxxxxxxx format |
| `{{user.snapshot_id}}` | User input | snap-xxxxxxxx format |
| `{{user.instance_id}}` | User input | Target instance for attachment |
| `{{output.volume_id}}` | Last API response | `.VolumeId` |
| `{{output.snapshot_id}}` | Last API response | `.SnapshotId` |
| `{{output.volume_state}}` | Last API response | `.State` (creating/available/in-use) |

## Execution Flow Pattern

**Pre-flight → Execute → Validate → Recover**

### Operation: Create Volume

#### Pre-flight

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log error |
| AZ | Confirm target AZ has capacity | Check via `aws ec2 describe-availability-zones` |
| Size | gp3: 1-16,384 GiB; io2: 4-16,384 GiB | HALT if out of range |

#### Execute — CLI
```bash
aws ec2 create-volume \
  --volume-type gp3 \
  --size {{user.size_gib}} \
  --availability-zone {{user.availability_zone}} \
  --encrypted \
  --tags Key=ManagedBy,Value=aiops \
  --output json
```

Save `{{output.volume_id}}` from `.VolumeId`.

#### Execute — boto3
```python
resp = ec2.create_volume(
    VolumeType='gp3', Size={{user.size_gib}},
    AvailabilityZone='{{user.availability_zone}}', Encrypted=True
)
volume_id = resp['VolumeId']
```

#### Validate
```bash
aws ec2 describe-volumes --volume-ids "{{user.volume_id}}" \
  --query "Volumes[0].{State:State,Size:Size,Type:VolumeType,Encrypted:Encrypted}"
```
Poll until `State == available`.

### Operation: Attach Volume

**Safety Gate**: Volume must be in `available` state. Verify device name is unused on instance.

```bash
# Pre-flight: check device not in use
aws ec2 describe-instances --instance-ids "{{user.instance_id}}" \
  --query "Reservations[0].Instances[0].BlockDeviceMappings"

# Attach
aws ec2 attach-volume \
  --volume-id "{{user.volume_id}}" \
  --instance-id "{{user.instance_id}}" \
  --device "{{user.device}}" \
  --output json
```

### Operation: Detach Volume

**Safety Gate**: MUST obtain confirmation. Check if volume is mounted (for OS-aware check, instruct user to unmount first).

```bash
# Pre-flight: check state
aws ec2 describe-volumes --volume-ids "{{user.volume_id}}" \
  --query "Volumes[0].{State:State,Attachments:Attachments}"

# Detach (force if available)
aws ec2 detach-volume \
  --volume-id "{{user.volume_id}}" \
  --instance-id "{{user.instance_id}}" \
  --device "{{user.device}}" \
  --force \
  --output json
```

```
[WARN] Detaching volume {{user.volume_id}} from {{user.instance_id}}.
Ensure the volume is unmounted from the OS first (umount command).
Type 'DETACH {{user.volume_id}}' to confirm.
```

### Operation: Delete Volume

**Safety Gate**: Volume must be `available` (not attached). MUST confirm.

```bash
# Pre-flight: verify not in-use
aws ec2 describe-volumes --volume-ids "{{user.volume_id}}" \
  --query "Volumes[0].State" --output text

# Delete
aws ec2 delete-volume --volume-id "{{user.volume_id}}" --output json
```

```
[WARN] Deleting volume {{user.volume_id}} — this is IRREVERSIBLE. Data will be lost.
Type 'DELETE {{user.volume_id}}' to confirm.
```

### Operation: Modify Volume

**Safety Gate**: Resize is irreversible (no shrink). Confirm new size is larger than current.

```bash
# Pre-flight: get current size
aws ec2 describe-volumes --volume-ids "{{user.volume_id}}" \
  --query "Volumes[0].{Size:Size,Iops:Iops,Throughput:Throughput}"

# Modify
aws ec2 modify-volume \
  --volume-id "{{user.volume_id}}" \
  --size {{user.new_size}} \
  --iops {{user.new_iops}} \
  --throughput {{user.new_throughput}} \
  --output json
```
Modifications apply gradually; poll `modifying-state` until `completed`.

### Operation: Create Snapshot

```bash
aws ec2 create-snapshot \
  --volume-id "{{user.volume_id}}" \
  --description "Snapshot via AIOps" \
  --tags Key=ManagedBy,Value=aiops \
  --output json
```

Save `{{output.snapshot_id}}` from `.SnapshotId`. Poll until `State == completed`.

### Operation: Delete Snapshot

**Safety Gate**: Confirm before deletion. Snapshots are incremental; deleting may affect dependent volumes.

```bash
# Pre-flight: check if any volumes created from this snapshot
aws ec2 describe-volumes --filters Name=snapshot-id,Values={{user.snapshot_id}} \
  --query "Volumes[].VolumeId"

# Delete
aws ec2 delete-snapshot --snapshot-id "{{user.snapshot_id}}" --output json
```

```
[WARN] Deleting snapshot {{user.snapshot_id}} removes the backup entirely.
Type 'DELETE_SNAPSHOT {{user.snapshot_id}}' to confirm.
```

## Recover

| Error | Action |
|-------|--------|
| `VolumeInUse` | Detach volume before delete |
| `InvalidVolume.ZoneMismatch` | Create volume in same AZ as instance |
| `SnapshotInProgress` | Wait and retry |
| `InvalidParameterValue` | Check size/type constraints |
| `Throttling` | Backoff, retry 3x |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)

## Token Efficiency

All 6 TE rules applied. Key points:
- TE-1: No hardcoded volume types/limits — use `describe-volumes` / `describe-account-attributes`
- TE-2: Inline comments only in boto3 code
- TE-3: Compact error tables
- TE-4: JSON paths declared inline
- TE-5: YAML anchors in `assets/example-config.yaml`
- TE-6: Flows only in SKILL.md

## Quality Gate (GCL)

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}`:
- `delete-volume` — IRREVERSIBLE data loss; confirm `DELETE_VOLUME <id>`
- `detach-volume` — disrupts running apps; confirm `DETACH_VOLUME <id>`
- `delete-snapshot` — removes backup; confirm `DELETE_SNAPSHOT <id>`

Relevant AWS rules: A7 (region), A8 (id echoed from describe), A9 (no secrets in tags/descriptions), A10 (sts first).