---
name: aws-eks-ops
description: >-
  Use when the user needs to create, configure, or manage Kubernetes clusters
  in AWS (EKS); scale node groups or Fargate profiles; update cluster versions;
  or perform Kubernetes-specific operations with kubectl, deployments, services,
  or Helm charts, even if they don't say "EKS" and instead say "set up a
  Kubernetes cluster", "manage a k8s cluster", "configure container
  orchestration on AWS", "deploy pods via kubectl", or "work with Helm charts
  in AWS".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), kubectl, valid AWS credentials, network
  access to AWS endpoints.
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
    - AWS_DEFAULT_REGION
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-ec2-ops
    - aws-vpc-ops
    - aws-iam-ops
    - aws-ecr-ops
    - aws-cloudwatch-ops
    - aws-ecs-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS EKS Operations Skill

Use for EKS clusters, managed nodegroups, Fargate profiles, addons, versions, kubeconfig, kubectl, and Helm. Detailed CLI/SDK patterns remain in references.

## Common JSON Paths

CreateCluster: .cluster.{arn,name,status,endpoint,version}
DescribeCluster: .cluster.{status,endpoint,certificateAuthority,version,arn}
ListClusters: .clusters[]
Nodegroup: .nodegroup.{nodegroupArn,status,scalingConfig,instanceTypes}
FargateProfile: .fargateProfile.{fargateProfileArn,status}
Addon: .addon.{addonArn,status}
Update: .update.{id,status}

## Trigger & Scope

### SHOULD Use When
EKS, Kubernetes/k8s clusters, managed nodegroups, Fargate, addons, kubectl, deployments, services, or Helm on AWS.

### SHOULD NOT Use When
EC2 → `aws-ec2-ops`; VPC → `aws-vpc-ops`; pod IAM → `aws-iam-ops`; load balancers → `aws-elb-ops`; S3 → `aws-s3-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.cluster_name}}`, `{{user.nodegroup_name}}` | User input | Resource names |
| `{{user.version}}`, `{{user.vpc_id}}`, `{{user.subnet_ids}}` | User input | Version and network |
| `{{output.cluster_arn}}` | API response | Reuse `.cluster.arn` |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version`, `aws sts get-caller-identity --output json`, and verify VPC, IAM, kubectl, and identifiers. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll cluster/nodegroup/Fargate status to `ACTIVE`; recover with bounded throttling backoff and halt on name conflicts, quota, or missing resources. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Delete cluster | Sequenced cleanup: Fargate profiles → addons → nodegroups → cluster | `confirm=DELETE_CLUSTER <name>` |
| Delete nodegroup | Describe nodegroup; terminates EC2 instances | `confirm=DELETE_NODEGROUP <name>` |
| Delete addon | Describe addon and cluster dependencies | `confirm=DELETE_ADDON <name>` |
| Delete Fargate profile | List profiles and pod selectors | `confirm=DELETE_FARGATE_PROFILE <name>` |
| Update cluster version | One minor version jump; compat check | Human confirmation |

Mask kubeconfig/certificate data in traces.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7 (region), A8 (cluster echoed from describe), A9 (kubeconfig/certificate masking), and A10 (STS first command).

## Token Efficiency

TE-1…TE-6 apply; query live versions and quotas, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[quick-start.md](references/quick-start.md) · [aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive ops; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
