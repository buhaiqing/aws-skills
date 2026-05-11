---
name: aws-elb-ops
description: >-
  Use when operating AWS Elastic Load Balancing (ELB) resources via AWS CLI or
  boto3 SDK; user mentions ELB, ALB, NLB, CLB, Load Balancer, or Target Group.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
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

# AWS ELB Operations Skill

## Overview

AWS Elastic Load Balancing (ELB) automatically distributes incoming application traffic across multiple targets. This skill covers **Application Load Balancer (ALB)**, **Network Load Balancer (NLB)**, and **Classic Load Balancer (CLB)** operations.

## Trigger & Scope

### SHOULD Use When
- User mentions "ELB", "Load Balancer", "ALB", "NLB", or "CLB"
- Task involves CRUD on **Load Balancers** or **Target Groups**
- Keywords: balance, distribute, health-check, listener, target-group

### SHOULD NOT Use When
- EC2 instances → delegate to: `aws-ec2-ops`
- VPC/subnets → delegate to: `aws-vpc-ops`
- SSL certificates → delegate to: `aws-acm-ops`
- Route53 DNS → delegate to: `aws-route53-ops`

## Load Balancer Types

| Type | Layer | Use Case | CLI Service |
|------|-------|----------|-------------|
| ALB | Layer 7 (HTTP/HTTPS) | Web apps, microservices | `elbv2` |
| NLB | Layer 4 (TCP/UDP) | High performance, gaming | `elbv2` |
| CLB | Layer 4/7 (legacy) | Legacy apps | `elb` |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.lb_name}}` | User input | Ask once; reuse |
| `{{user.lb_type}}` | User input | ALB, NLB, or CLB |
| `{{user.vpc_id}}` | User input | Ask once; reuse |
| `{{output.load_balancer_arn}}` | Last API response | Parse `.LoadBalancers[0].LoadBalancerArn` |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Application Load Balancer

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

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
Action: See references/integration.md → Error Messages for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide user to integration.md |
| VPC exists | `aws ec2 describe-vpcs --vpc-ids {{user.vpc_id}}` | HALT; verify VPC |
| Subnets exist | `aws ec2 describe-subnets --subnet-ids {{user.subnet_ids}}` | HALT; verify subnets |

#### Execute — CLI (Primary)
```bash
aws elbv2 create-load-balancer \
  --name "{{user.lb_name}}" \
  --type application \
  --subnets "{{user.subnet_ids}}" \
  --security-groups "{{user.security_group_ids}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('elbv2', region_name='{{user.region}}')
response = client.create_load_balancer(
    Name='{{user.lb_name}}',
    Type='application',
    Subnets=['subnet-1', 'subnet-2'],
    SecurityGroups=['sg-1']
)
```

#### Validate
```bash
aws elbv2 describe-load-balancers \
  --load-balancer-arns "{{output.load_balancer_arn}}" \
  --output json
```
Poll until `.State.Code` == "active" (max wait: 5 min).

#### Recover
| Error | Action |
|-------|--------|
| InvalidSubnet | HALT; verify subnet IDs and availability zones |
| DuplicateLoadBalancerName | Use different name |
| QuotaExceeded | HALT; request quota increase |
| Throttling (429) | Backoff, retry 3x |

### Operation: Create Target Group

#### Execute — CLI (Primary)
```bash
aws elbv2 create-target-group \
  --name "{{user.tg_name}}" \
  --protocol HTTP \
  --port 80 \
  --vpc-id "{{user.vpc_id}}" \
  --health-check-path "/health" \
  --output json
```

#### Validate
Poll until target group created (immediate).

### Operation: Register Targets

#### Execute — CLI (Primary)
```bash
aws elbv2 register-targets \
  --target-group-arn "{{output.target_group_arn}}" \
  --targets Id=i-xxx Id=i-yyy \
  --output json
```

### Operation: Create Listener

#### Execute — CLI (Primary)
```bash
aws elbv2 create-listener \
  --load-balancer-arn "{{output.load_balancer_arn}}" \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn="{{output.target_group_arn}}" \
  --output json
```

### Operation: Delete Load Balancer

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Pre-delete Checks
1. List listeners: `aws elbv2 describe-listeners --load-balancer-arn {{output.load_balancer_arn}}`
2. Delete listeners first
3. Wait for listeners deleted (poll)

#### Execute — CLI (Primary)
```bash
aws elbv2 delete-load-balancer \
  --load-balancer-arn "{{output.load_balancer_arn}}" \
  --output json
```

#### Validate
Poll until `.LoadBalancers` empty (max wait: 10 min).

### Operation: Describe Load Balancers

#### Execute — CLI
```bash
aws elbv2 describe-load-balancers --output json
# JSON path: .LoadBalancers[].{Name,LoadBalancerArn,State,VpcId,Type}
```

### Classic Load Balancer Operations

CLB uses `aws elb` commands (legacy):
- `aws elb create-load-balancer` (Classic)
- `aws elb describe-load-balancers`
- `aws elb delete-load-balancer`

## Health Check Configuration

| Parameter | ALB/NLB | CLB |
|-----------|---------|-----|
| HealthCheckPath | `/health` | TCP port or HTTP path |
| HealthCheckIntervalSeconds | 30 (default) | 30 |
| HealthCheckTimeoutSeconds | 5 | 5 |
| HealthyThresholdCount | 5 | 10 |
| UnhealthyThresholdCount | 2 | 2 |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Example Configurations](assets/example-config.yaml)