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
  last_updated: "2026-05-10"
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
---
# AWS EKS Operations Skill

## Common JSON Paths (Centralized)

```
# Create Cluster:        .cluster.{arn,name,status,endpoint,version}
# Describe Cluster:      .cluster.{status,endpoint,certificateAuthority,version,arn}
# List Clusters:         .clusters[]
# Create Nodegroup:      .nodegroup.{nodegroupArn,status}
# Describe Nodegroup:    .nodegroup.{status,scalingConfig,instanceTypes}
# Create Fargate:        .fargateProfile.{fargateProfileArn,status}
# Create Addon:          .addon.{addonArn,status}
# Update Cluster:        .update.{id,status}
```

## Overview

AWS EKS (Elastic Kubernetes Service) is a managed Kubernetes service. This skill covers cluster, nodegroup, and Fargate profile operations.

## Trigger & Scope

### SHOULD Use When
- User mentions "EKS", "Kubernetes", "k8s", or "container orchestration"
- Task involves CRUD on **EKS Clusters** or **Node Groups**
- Keywords: cluster, nodegroup, fargate, pod, deployment, service, kubectl

### SHOULD NOT Use When
- EC2 instances → delegate to: `aws-ec2-ops`
- VPC/subnets → delegate to: `aws-vpc-ops`
- IAM roles for pods → delegate to: `aws-iam-ops`
- Load Balancer for services → delegate to: `aws-elb-ops`
- S3 for storage → delegate to: `aws-s3-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.cluster_name}}` | User input | Ask once; reuse |
| `{{user.version}}` | User input | Kubernetes version (e.g., 1.30) |
| `{{user.vpc_id}}` | User input | Ask once; reuse |
| `{{user.subnet_ids}}` | User input | Comma-separated subnet IDs |
| `{{output.cluster_arn}}` | Last API response | Parse `.cluster.arn` |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify VPC/exists, IAM role exists. Check kubectl available for kubeconfig operations.

**CLI (primary)**: `aws eks [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Poll `.cluster.status`==ACTIVE (create, max 15 min), `.nodegroup.status`==ACTIVE (max 10 min), `.fargateProfile.status`==ACTIVE (max 5 min).

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidParameterException | Fix args; retry once |
| ResourceInUseException | HALT — cluster name exists |
| ResourceLimitExceededException | HALT — quota exceeded |
| ResourceNotFoundException | HALT — verify resource exists |
| ThrottlingException | Backoff, retry 3x |

## Safety Gates

### Delete Cluster (Pre-delete Sequence Required)
```
⚠️ Cluster deletion requires cleanup in order:
1. Delete all Fargate profiles
2. Delete all addons
3. Delete all node groups
4. Wait for all deletions complete
5. Delete cluster
Confirm before proceeding.
```

### Delete Node Group
```
⚠️ Deleting nodegroup will terminate all EC2 instances in the nodegroup.
Confirm: Type DELETE {{user.nodegroup_name}} to proceed.
```

## Kubernetes Versions

| Version | Status |
|---------|--------|
| 1.31 | Latest |
| 1.30 | Stable (recommended) |
| 1.29 | Supported |
| 1.28 | Supported |

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded Kubernetes versions/AMI types — use `describe-addon-versions` / `list-clusters`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-eks-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-cluster` — IRREVERSIBLE; requires sequenced pre-cleanup: list & delete all Fargate profiles → addons → node groups → cluster; confirm `DELETE_CLUSTER <name>`
- `delete-nodegroup` — terminates all EC2 instances in the nodegroup; confirm `DELETE_NODEGROUP <name>`
- `update-cluster-version` — version upgrade; confirm with user; only one minor version jump at a time

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (cluster name echoed from `describe-cluster`), A9 (kubeconfig/certificate data masked), A10 (sts first command).

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric
- `references/prompt-templates.md` — G/C/O skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## Reference Files

### Quick Start
- [Quick Start Guide](references/quick-start.md)

### Core
- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)

### Advanced
- [EKS 2024 Features](references/eks-2024-features.md)
- [Cluster Autoscaler](references/cluster-autoscaler.md)
- [Monitoring & Logging](references/monitoring-logging.md)
- [Security Best Practices](references/security-best-practices.md)
- [Cost Optimization](references/cost-optimization.md)
- [Multi-Region HA](references/multi-region-ha.md)
- [Performance Optimization](references/performance-optimization.md)
- [Backup & Recovery](references/backup-recovery.md)
- [FAQ](references/faq.md)