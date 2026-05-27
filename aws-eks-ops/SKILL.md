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
---
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
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

# AWS EKS Operations Skill

## Overview

AWS EKS (Elastic Kubernetes Service) is a managed Kubernetes service that makes it easy to run Kubernetes on AWS. This skill covers cluster, nodegroup, and Fargate profile operations.

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

## EKS Components

| Component | Description | Managed By |
|-----------|-------------|------------|
| Control Plane | Kubernetes API, etcd | AWS (managed) |
| Data Plane | Worker nodes | Customer (managed nodegroups) or AWS (Fargate) |
| Node Group | EC2 worker nodes | Customer configured |
| Fargate Profile | Serverless pods | AWS (serverless) |
| Add-ons | CoreDNS, kube-proxy, vpc-cni | AWS managed |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.cluster_name}}` | User input | Ask once; reuse |
| `{{user.version}}` | User input | Kubernetes version (e.g., 1.28) |
| `{{user.vpc_id}}` | User input | Ask once; reuse |
| `{{output.cluster_arn}}` | Last API response | Parse `.cluster.arn` |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create EKS Cluster

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install AWS CLI v2: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/troubleshooting.md → Diagnostic Order for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide user to troubleshooting.md |
| VPC exists | `aws ec2 describe-vpcs --vpc-ids {{user.vpc_id}}` | HALT; verify VPC |
| Subnets exist | `aws ec2 describe-subnets` | HALT; verify subnets |
| IAM role exists | `aws iam get-role --role-name {{user.iam_role}}` | HALT; create role first |

#### Execute — CLI (Primary)
```bash
aws eks create-cluster \
  --name "{{user.cluster_name}}" \
  --version "{{user.version}}" \
  --role-arn "{{user.iam_role_arn}}" \
  --resources-vpc-config subnetIds={{user.subnet_ids}},securityGroupIds={{user.sg_ids}} \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('eks', region_name='{{user.region}}')
response = client.create_cluster(
    name='{{user.cluster_name}}',
    version='{{user.version}}',
    roleArn='{{user.iam_role_arn}}',
    resourcesVpcConfig={
        'subnetIds': ['subnet-1', 'subnet-2'],
        'securityGroupIds': ['sg-1']
    }
)
```

#### Validate
Poll until `.cluster.status` == "ACTIVE" (max wait: 15 min).

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterException | Fix args; retry once |
| ResourceInUseException | HALT; cluster name exists |
| ResourceLimitExceededException | HALT; quota exceeded |
| ThrottlingException | Backoff, retry 3x |

### Operation: Create Managed Node Group

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| Cluster active | `aws eks describe-cluster --name {{user.cluster_name}}` | HALT; wait for cluster |
| IAM role exists | `aws iam get-role` | HALT; create node IAM role |

#### Execute — CLI (Primary)
```bash
aws eks create-nodegroup \
  --cluster-name "{{user.cluster_name}}" \
  --nodegroup-name "{{user.nodegroup_name}}" \
  --node-role "{{user.node_role_arn}}" \
  --subnets "{{user.subnet_ids}}" \
  --scaling-config minSize={{user.min_size}},maxSize={{user.max_size}},desiredSize={{user.desired_size}} \
  --instance-types "{{user.instance_types}}" \
  --ami-type AL2_x86_64 \
  --output json
```

#### Validate
Poll until `.nodegroup.status` == "ACTIVE" (max wait: 10 min).

### Operation: Create Fargate Profile

#### Execute — CLI (Primary)
```bash
aws eks create-fargate-profile \
  --cluster-name "{{user.cluster_name}}" \
  --fargate-profile-name "{{user.profile_name}}" \
  --pod-execution-role-arn "{{user.pod_role_arn}}" \
  --selectors namespace={{user.namespace}},labels={{user.labels}} \
  --subnets "{{user.subnet_ids}}" \
  --output json
```

#### Validate
Poll until `.fargateProfile.status` == "ACTIVE" (max wait: 5 min).

### Operation: Update Cluster Version

#### Execute — CLI (Primary)
```bash
aws eks update-cluster-version \
  --name "{{user.cluster_name}}" \
  --version "{{user.target_version}}" \
  --output json
```

#### Validate
Poll until update complete, then verify version.

### Operation: Delete Node Group

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Execute — CLI (Primary)
```bash
aws eks delete-nodegroup \
  --cluster-name "{{user.cluster_name}}" \
  --nodegroup-name "{{user.nodegroup_name}}" \
  --output json
```

#### Validate
Poll until nodegroup deleted (max wait: 15 min).

### Operation: Delete Cluster

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

**Pre-delete Sequence**:
1. Delete all Fargate profiles
2. Delete all addons
3. Delete all node groups
4. Wait for all deletions complete
5. Delete cluster

#### Execute — CLI (Primary)
```bash
aws eks delete-cluster \
  --name "{{user.cluster_name}}" \
  --output json
```

#### Validate
Poll until cluster deleted (max wait: 15 min).

### Operation: Describe Cluster

#### Execute — CLI
```bash
aws eks describe-cluster --name "{{user.cluster_name}}" --output json
# JSON path: .cluster.{status,endpoint,certificateAuthority}
```

### Operation: List Clusters

#### Execute — CLI
```bash
aws eks list-clusters --output json
# JSON path: .clusters[]
```

### Operation: Update kubeconfig

After cluster creation, update local kubeconfig for kubectl access:

```bash
aws eks update-kubeconfig --name "{{user.cluster_name}}" --region "{{user.region}}"
```

## Kubernetes Versions Supported

| Version | Status | Notes |
|---------|--------|-------|
| 1.31 | Latest | New features |
| 1.30 | Stable | Recommended |
| 1.29 | Stable | Supported |
| 1.28 | Standard | Supported |
| 1.27 | Extended Support | Extended support available |
| 1.26 | Extended Support | Extended support available |
| 1.25 | Extended Support | Extended support available |

**Note**: EKS provides extended support for older versions at additional cost.

## Reference Files

### Quick Start
- [Quick Start Guide](references/quick-start.md) - Get started in 10 minutes

### Core Documentation
- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md) - Updated with new features
- [Troubleshooting](references/troubleshooting.md) - Enhanced with new feature issues

### Advanced Features
- [EKS 2024 Features](references/eks-2024-features.md) - Access Entries, Pod Identity, Bottlerocket
- [Cluster Autoscaler](references/cluster-autoscaler.md) - Auto-scaling configuration
- [Monitoring & Logging](references/monitoring-logging.md) - CloudWatch, Prometheus, X-Ray
- [Security Best Practices](references/security-best-practices.md) - Access control, encryption, networking

### Optimization & Best Practices
- [Cost Optimization](references/cost-optimization.md) - Spot instances, Graviton, right-sizing
- [Multi-Region HA](references/multi-region-ha.md) - Disaster recovery, failover strategies
- [Performance Optimization](references/performance-optimization.md) - Node, network, storage, application optimization
- [Backup & Recovery](references/backup-recovery.md) - Data backup, disaster recovery
- [FAQ](references/faq.md) - Common questions and answers

### Assets
- [Example Configurations](assets/example-config.yaml) - Updated with 2024 features and optimizations