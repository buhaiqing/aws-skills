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
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ["health-check", "capacity-review"]
    produces_facts: ["state", "event"]
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
---

# AWS EBS Operations Skill
Use this skill for EBS volumes and snapshots: lifecycle, attachment, modification, and recovery. Detailed CLI/SDK patterns live in the references.

## Trigger & Scope

### SHOULD Use When
EBS, volume, block storage, snapshot, attached disk, or volume lifecycle tasks.

### SHOULD NOT Use When
EC2 instance management → `aws-ec2-ops`; instance store → out of scope; S3 → `aws-s3-ops`; EFS → `aws-efs-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.volume_id}}`, `{{user.snapshot_id}}`, `{{user.instance_id}}` | User input | Resource identifiers |
| `{{user.size_gib}}`, `{{user.availability_zone}}`, `{{user.device}}` | User input | Operation parameters |
| `{{output.*}}` | API response | Reuse `.VolumeId`, `.SnapshotId`, `.State` |

## Common JSON Paths

VolumeId: .VolumeId
SnapshotId: .SnapshotId
VolumeState: .State

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. First run `aws --version` and `aws sts get-caller-identity`; use CLI `--output json`, then boto3 after 3 CLI failures. Validate with `describe-volumes`/`describe-snapshots` and poll asynchronous state transitions. Use [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

### Create Volume

Pre-flight: verify AZ and requested parameters; Execute `create-volume`; Validate `.VolumeId` and poll `State=available`; Recover on throttling or invalid parameters with bounded backoff.

### Attach Volume

Pre-flight: volume is `available`, instance exists, and device is unused; Execute `attach-volume`; Validate attachment state and instance mapping; Recover by re-describing both resources before retry.

### Detach Volume

Pre-flight: instruct the user to unmount at OS level and inspect attachments; require `DETACH {{user.volume_id}}`; Execute `detach-volume` (force only when explicitly requested); Validate detached state; Recover by waiting for in-progress transitions.

### Delete Volume

Pre-flight: verify volume is `available` and not attached; require `DELETE {{user.volume_id}}`; Execute `delete-volume`; Validate `describe-volumes` returns not found; Recover `VolumeInUse` by halting and resolving attachment.

### Modify Volume

Pre-flight: compare current and requested size (no shrink) and inspect modification state; Execute `modify-volume`; Validate until modification completes; Recover by polling rather than issuing duplicate modifications.

### Create Snapshot

Pre-flight: verify source volume; Execute `create-snapshot`; Validate `.SnapshotId` and poll `State=completed`; Recover `SnapshotInProgress` by waiting and re-checking.

### Delete Snapshot

Pre-flight: inspect volumes created from the snapshot; require `DELETE_SNAPSHOT {{user.snapshot_id}}`; Execute `delete-snapshot`; Validate absence; Recover by halting on dependency or throttling errors.

## Safety Gates

Never detach, delete, or force-delete without explicit confirmation. Mask credentials and sensitive user data in traces. Do not proceed on `VolumeInUse`, zone mismatch, missing identity, or ambiguous resource IDs.

## Recover

`VolumeInUse` → resolve attachments; `InvalidVolume.ZoneMismatch` → use the instance AZ; `SnapshotInProgress` → wait; `InvalidParameterValue` → re-check live constraints; `Throttling` → bounded exponential backoff, then halt.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7 (region), A8 (resource echoed from describe), A9 (no secrets in tags/descriptions), and A10 (STS first command).

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive ops; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
