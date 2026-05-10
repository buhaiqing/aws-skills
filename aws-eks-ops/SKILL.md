---
name: aws-eks-ops
description: >-
  Use when operating AWS EKS (Elastic Kubernetes Service) resources via AWS CLI
  or boto3 SDK; user mentions EKS, Kubernetes, k8s, cluster, nodegroup, or fargate.
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
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; configure env |
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
2. Delete all node groups
3. Wait for all deletions complete
4. Delete cluster

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
| 1.28 | Stable | Supported |
| 1.27 | Standard | Extended support available |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Example Configurations](assets/example-config.yaml)