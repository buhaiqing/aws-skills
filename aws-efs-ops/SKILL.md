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
  last_updated: "2026-07-31"
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
  cross_skill_deps:
    - aws-ec2-ops            # EC2 mount instances
    - aws-vpc-ops            # VPC/subnet/security group for mount targets
    - aws-kms-ops            # Encryption at rest (KMS key)
    - aws-cloudwatch-ops     # EFS metric monitoring
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'self-heal', 'change-impact']
    produces_facts: ['state', 'metric']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS EFS Operations Skill

Use for EFS file systems, mount targets, access points, policies, encryption, throughput, backups, and lifecycle. Detailed CLI/SDK commands remain in references.

## Common JSON Paths

FileSystem: .{FileSystemId,Name,LifeCycleState,NumberOfMountTargets,Encrypted,ThroughputMode}
MountTargets: .MountTargets[].{MountTargetId,FileSystemId,SubnetId,LifeCycleState,IpAddress}
AccessPoints: .AccessPoints[].{AccessPointId,FileSystemId,LifeCycleState,PosixUser,RootDirectory}

## Trigger & Scope

### SHOULD Use When
EFS file systems, mount targets, access points, throughput, encryption, backup, lifecycle, or NFS connectivity.

### SHOULD NOT Use When
EBS → `aws-ebs-ops`; EC2 lifecycle → `aws-ec2-ops`; S3 object storage → `aws-s3-ops`; VPC/subnets/SGs → `aws-vpc-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.file_system_id}}`, `{{user.mount_target_id}}`, `{{user.access_point_id}}` | User input | Resource IDs |
| `{{user.subnet_id}}`, `{{user.security_group_ids}}`, `{{user.region}}` | User input | Network configuration |
| `{{output.*}}` | API response | Reuse IDs/state/IPs |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify file system, AZ/subnet, SG, encryption, access points, and NFS dependencies. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll lifecycle state; recover with bounded retries and halt on missing resources, occupied dependencies, or invalid network. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create file system | Validate encryption, tags, throughput/lifecycle; poll available | — |
| Delete file system | Verify no mount targets, access points, backups, or consumers | `confirm=DELETE_FS <file-system-id>` |
| Create/delete mount target | Validate subnet/AZ and SG; delete only after consumers drain | `confirm=DELETE_MOUNT_TARGET <mount-target-id>` |
| Create/delete access point | Validate POSIX/root directory and consumers | `confirm=DELETE_ACCESS_POINT <access-point-id>` |
| Update policy/throughput | Diff access and performance impact; read back | Token for public/widened access or disruptive change |

Never log mount credentials, policy secrets, NFS client data, or sensitive tags.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live filesystem/network state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive/network-impacting actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
