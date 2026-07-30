---
name: aws-ec2-ops
description: >-
  Use when the user needs to launch, manage, stop, start, or terminate virtual
  servers (instances) in AWS; create or manage Amazon Machine Images (AMIs);
  work with Spot instances, Reserved instances, or On-Demand capacity; attach
  volumes, security groups, or key pairs to instances; or monitor instance
  state and health, even if they don't explicitly say "EC2" and instead say
  "spin up a server", "create a VM", "launch an instance", "manage my cloud
  compute resources", or "provision reserved capacity".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to EC2 endpoints.
metadata:
  author: aws
  version: "1.4.0"
  last_updated: "2026-07-30"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: true
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  cross_skill_deps:
    - aws-elb-ops             # LB target health diagnostics
    - aws-cloudwatch-ops      # EC2 metrics monitoring & FORECAST
    - aws-cloudtrail-ops      # EC2 config change audit
    - aws-ssm-ops             # SSM RunCommand for diagnostics
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS EC2 Operations Skill

Use for EC2 instances, start/stop/terminate, AMIs, key pairs, EBS attachment, snapshots, attributes, diagnostics, and load-balancer target remediation. Detailed commands remain in references.

## Common JSON Paths

Instance: .Reservations[0].Instances[0].{InstanceId,State.Name,InstanceType,Placement,PrivateIpAddress,PublicIpAddress,Tags}
Instances: .Reservations[].Instances[].{InstanceId,State.Name,InstanceType,PrivateIpAddress,Tags}
Volumes: .Volumes[].{VolumeId,State,Size,VolumeType,Attachments,Encrypted}
Snapshots: .Snapshots[].{SnapshotId,State,VolumeId,StartTime}
Images: .Images[].{ImageId,Name,State,CreationDate,BlockDeviceMappings}

## Trigger & Scope

### SHOULD Use When
EC2 instances, launch/start/stop/terminate, AMIs, key pairs, EBS attachment, snapshots, attributes, diagnostics, or target remediation.

### SHOULD NOT Use When
ASGs → `aws-autoscaling-ops`; EBS-only lifecycle → `aws-ebs-ops`; VPC → `aws-vpc-ops`; ELB → `aws-elb-ops`; EKS/ECS → respective skills.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.instance_id}}`, `{{user.image_id}}`, `{{user.instance_type}}` | User input | Instance/AMI identity |
| `{{user.volume_id}}`, `{{user.snapshot_id}}`, `{{user.key_name}}` | User input | Storage/key resources |
| `{{output.*}}` | API response | Reuse instance/volume/snapshot/image IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. First run STS identity; describe exact resources, state, tags, tenancy, termination protection, ASG/ELB membership, volumes, network, and dependencies. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll target state; recover with bounded retries and halt on incorrect state, protection, or ambiguous IDs. See references for commands.

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Launch/start instance | Validate AMI, type, IAM, network, key, quotas | — |
| Stop instance | Echo ID/state/workload and interruption impact | `confirm=STOP <instance-id>` |
| Terminate instance | Describe ID/tags; inspect protection, ASG/ELB, volumes, snapshots | `--no-dry-run` plus `confirm=TERMINATE <instance-id>` |
| Delete key pair | Show consumers and loss of access | `confirm=DELETE_KEY_PAIR <name>` |
| Attach/detach volume | Verify AZ, mapping, mount/unmount and consumers | `confirm=DETACH <volume-id>` |
| Deregister AMI | Inspect launch templates/ASGs and snapshots | `confirm=DEREGISTER_IMAGE <ami-id>` |
| Modify attributes | Diff current/requested and restart/security impact | Human confirmation |
| Forensic snapshot | Prefer read-only snapshot before destructive remediation | — |

Never log UserData, PasswordData, KeyMaterial, private keys, credentials, or sensitive tags.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A1 (`--no-dry-run` termination opt-in), A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live instance/storage state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [prompt-examples.md](references/prompt-examples.md) · [cost-tracking.md](references/cost-tracking.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for stop/terminate/storage/image actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits bounded non-destructive diagnostics/remediation; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
