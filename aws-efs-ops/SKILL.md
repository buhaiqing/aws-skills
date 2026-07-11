---
name: aws-efs-ops
description: >-
  Use when operating AWS EFS (Elastic File System) resources via AWS CLI or
  boto3 SDK; user mentions EFS, NFS, file system, mount target, access point,
  or shared file storage.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-12"
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
    enabled: false
    class: optional
    reason: "Not yet listed in AGENTS.md §11.5 — GCL disabled by default for new skills"
  cross_skill_deps:
    - aws-ec2-ops            # EC2 mount instances
    - aws-vpc-ops            # VPC/subnet/security group for mount targets
    - aws-kms-ops            # Encryption at rest (KMS key)
    - aws-cloudwatch-ops     # EFS metric monitoring
---

# AWS EFS Operations Skill

## Overview

AWS Elastic File System (EFS) provides scalable, elastic NFS file storage for use with AWS cloud services and on-premises resources. This skill covers **file system lifecycle, mount targets, access points, and network configuration**.

## Trigger & Scope

### SHOULD Use When
- User mentions "EFS", "Elastic File System", "NFS", "shared file system", "file storage"
- Task involves CRUD on **EFS resources** (file system, mount target, access point)
- Keywords: efs, elastic-file-system, nfs, mount-target, access-point, file-system

### SHOULD NOT Use When
- Block-level storage → delegate to: `aws-ebs-ops`
- EC2 instance store → ephemeral, not EBS/EFS
- S3 object storage → delegate to: `aws-s3-ops`
- EC2 instance management → delegate to: `aws-ec2-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | Skip if AWS_PROFILE or IAM Role used |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | Skip if AWS_PROFILE or IAM Role used |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile (SSO / AssumeRole) |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.file_system_id}}` | Last API response | `describe-file-systems → .FileSystems[0].FileSystemId` |
| `{{output.file_system_id}}` | Last API response | Auto-populated from `create-file-system` |

## Config File Placeholders

EFS does not use a standard config file format. CLI parameters are provided inline. `assets/example-config.yaml` documents common parameter combinations.

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create File System

#### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
aws efs describe-file-systems --region {{user.region}} --output json
```
Log: `[OK] EFS accessible, N existing file systems`

#### Execute — CLI (Primary)
```bash
aws efs create-file-system \
  --creation-token "{{user.file_system_token}}" \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --region "{{user.region}}" \
  --output json
```
- `--creation-token`: idempotency token (use a unique value like `<name>-<timestamp>`)
- `--performance-mode`: `generalPurpose` (default) or `maxIO`
- `--throughput-mode`: `bursting` (default) or `provisioned` (requires `--provisioned-throughput-in-mibps`)
- `--encrypted`: enabled by default; use `--kms-key-id` for custom KMS key

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('efs', region_name='{{user.region}}')
response = client.create_file_system(
    CreationToken='{{user.file_system_token}}',
    PerformanceMode='generalPurpose',
    ThroughputMode='bursting',
    Encrypted=True
)
file_system_id = response['FileSystemId']
```

#### Validate
```bash
aws efs describe-file-systems \
  --file-system-id "{{output.file_system_id}}" \
  --region "{{user.region}}" \
  --query 'FileSystems[0].LifeCycleState' --output json
```
Expect: `"available"` (may take minutes after creation)

#### Recover
| Error | Action |
|-------|--------|
| `FileSystemAlreadyExists` | Creation token reused — idempotent; return existing FS |
| `InsufficientThroughputCapacity` | HALT; ask user to request throughput increase |
| `ThroughputLimitExceeded` | HALT; reduce provisioned throughput |
| `BadRequest` (invalid KMS key) | Fix KMS key ID or ARN |

---

### Operation: Delete File System

**Safety Gate**: MUST obtain explicit user confirmation (`confirm=DELETE <file_system_id>`). File system must have no mount targets and no access points.

#### Pre-flight
```bash
# Check mount targets
aws efs describe-mount-targets --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" --output json
# Check access points
aws efs describe-access-points --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" --output json
```
If mount targets or access points exist, delete them first.

#### Execute — CLI
```bash
aws efs delete-file-system \
  --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" --output json
```

#### Validate
```bash
aws efs describe-file-systems \
  --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" 2>&1 | grep -q "FileSystemNotFoundException" && echo "[DELETE OK]"
```

#### Recover
| Error | Action |
|-------|--------|
| `FileSystemInUse` | Mount targets/access points exist — list & delete first |
| `FileSystemNotFoundException` | Already deleted — idempotent |
| `BadRequest` | File system not in `available` state — wait and retry |

---

### Operation: Create Mount Target

#### Pre-flight
Verify subnet exists and security group allows NFS (port 2049).

```bash
aws ec2 describe-subnets --subnet-ids "{{user.subnet_id}}" --region "{{user.region}}" --output json
```

#### Execute — CLI
```bash
aws efs create-mount-target \
  --file-system-id "{{user.file_system_id}}" \
  --subnet-id "{{user.subnet_id}}" \
  --security-groups "{{user.security_group_id}}" \
  --region "{{user.region}}" --output json
```

#### Validate
```bash
aws efs describe-mount-targets \
  --file-system-id "{{user.file_system_id}}" \
  --region "{{user.region}}" \
  --query 'MountTargets[?SubnetId==`{{user.subnet_id}}`].LifeCycleState' \
  --output json
```
Expect: `"available"`

---

### Operation: Delete Mount Target

**Safety Gate**: User must confirm.

```bash
aws efs delete-mount-target \
  --mount-target-id "{{user.mount_target_id}}" \
  --region "{{user.region}}" --output json
```

### Operation: Create Access Point

```bash
aws efs create-access-point \
  --file-system-id "{{user.file_system_id}}" \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory Path="/data",CreationInfo='{OwnerUid=1000,OwnerGid=1000,Permissions=0755}' \
  --region "{{user.region}}" --output json
```

### Operation: Delete Access Point

**Safety Gate**: User must confirm.

```bash
aws efs delete-access-point \
  --access-point-id "{{user.access_point_id}}" \
  --region "{{user.region}}" --output json
```

## Common JSON Paths

```json
// describe-file-systems
{ "FileSystems": [{ "FileSystemId": "fs-12345678", "LifeCycleState": "available" }] }
// → .FileSystems[0].FileSystemId

// describe-mount-targets
{ "MountTargets": [{ "MountTargetId": "fsmt-12345678", "SubnetId": "subnet-xxx", "LifeCycleState": "available" }] }
// → .MountTargets[0].MountTargetId

// describe-access-points
{ "AccessPoints": [{ "AccessPointId": "fsap-12345678", "FileSystemId": "fs-xxx" }] }
// → .AccessPoints[].AccessPointId
```

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Example Config](assets/example-config.yaml)

## Token Efficiency (TE)

- **TE-1**: Use `aws efs describe-file-systems` to query limits/quotas at runtime; no static table.
- **TE-2**: boto3 code uses inline comments, no docstrings (see `references/boto3-sdk-usage.md`).
- **TE-3**: Error tables compact — common errors only; see per-operation Recover tables.
- **TE-4**: JSON paths centralized in Common JSON Paths block above.
- **TE-5**: YAML anchors in `assets/example-config.yaml` for shared fields.

## Quality Gate (GCL)

GCL is **disabled** for `aws-efs-ops` by default per `AGENTS.md` §11.5 (`Not yet listed — GCL disabled by default for new skills`). When GCL is enabled in a future rollout, a `references/rubric.md` and `references/prompt-templates.md` will be added.
