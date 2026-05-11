---
name: aws-ec2-ops
description: >-
  Use when operating AWS EC2 instances via AWS CLI or boto3 SDK; user mentions
  EC2, Elastic Compute Cloud, instance, VM, or Amazon Machine Image (AMI).
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to EC2 endpoints.
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

# AWS EC2 Operations Skill

## Overview

Amazon EC2 (Elastic Compute Cloud) provides scalable virtual servers in AWS. This skill is an **operational runbook** with explicit scope, credential rules, pre-flight checks, dual-path execution (AWS CLI + boto3 SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "EC2", "Elastic Compute Cloud", "instance", "VM"
- Task involves CRUD on **EC2 instances** (run, stop, start, terminate, describe)
- Keywords: instance, ami, volume, keypair, security-group, launch

### SHOULD NOT Use When
- Billing only → delegate to: `aws-cost-ops`
- IAM only → delegate to: `aws-iam-ops`
- VPC/Subnet → delegate to: `aws-vpc-ops`
- Load Balancer → delegate to: `aws-elb-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default `us-east-1` if unset |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.instance_name}}` | User input | Ask once; reuse |
| `{{output.instance_id}}` | Last API response | Parse: `.Instances[0].InstanceId` |

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**

```
Pre-flight → Execute (CLI/SDK) → Validate (Poll) → Recover (On Error)
```

### Operation: Run Instance (Launch)

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
| AMI exists | `aws ec2 describe-images --image-ids {{user.ami_id}}` | Suggest valid AMI |
| KeyPair exists | `aws ec2 describe-key-pairs --key-names {{user.key_name}}` | Create or suggest |
| Security Group | `aws ec2 describe-security-groups --group-ids {{user.sg_id}}` | Verify or create |

#### Execute — CLI (Primary)
```bash
aws ec2 run-instances \
  --image-id "{{user.ami_id}}" \
  --instance-type "{{user.instance_type}}" \
  --key-name "{{user.key_name}}" \
  --security-group-ids "{{user.sg_id}}" \
  --region "{{user.region}}" \
  --tag-specifications "[{\"ResourceType\":\"instance\",\"Tags\":[{\"Key\":\"Name\",\"Value\":\"{{user.instance_name}}\"}]}]" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('ec2', region_name='{{user.region}}')
response = client.run_instances(
    ImageId='{{user.ami_id}}',
    InstanceType='{{user.instance_type}}',
    KeyName='{{user.key_name}}',
    SecurityGroupIds=['{{user.sg_id}}'],
    TagSpecifications=[
        {'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': '{{user.instance_name}}'}]}
    ],
    MinCount=1, MaxCount=1
)
instance_id = response['Instances'][0]['InstanceId']
```

#### Validate
Poll until `running` state (max 120s, interval 5s):
```bash
for i in $(seq 1 24); do
  STATUS=$(aws ec2 describe-instances --instance-ids "{{output.instance_id}}" --region "{{user.region}}" --output json | jq -r '.Reservations[0].Instances[0].State.Name')
  [ "$STATUS" = "running" ] && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidAMIID.NotFound | HALT; suggest valid AMI |
| InvalidKeyPair.NotFound | Create keypair or suggest existing |
| InvalidSecurityGroupID.NotFound | Verify SG in correct VPC |
| InstanceLimitExceeded | HALT; request quota increase |
| InsufficientInstanceCapacity | Try different AZ or instance type |

### Operation: Stop Instance

#### Pre-flight (Safety Gate)
- Verify instance exists and is `running` state
- **MUST** confirm: "Stop instance {{user.instance_id}}?"

#### Execute — CLI
```bash
aws ec2 stop-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json
```

#### Validate
Poll until `stopped` state (max 120s).

### Operation: Start Instance

#### Execute — CLI
```bash
aws ec2 start-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json
```

#### Validate
Poll until `running` state (max 120s).

### Operation: Terminate Instance (Destructive)

#### Safety Gate (Mandatory)
**MUST** obtain explicit confirmation:
> "Terminate {{user.instance_id}}? This action is IRREVERSIBLE. Confirm with exact instance ID."

#### Execute — CLI
```bash
aws ec2 terminate-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json
```

#### Validate
Poll until `terminated` state (max 60s).

### Operation: Describe Instance

#### Execute — CLI
```bash
aws ec2 describe-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json
```

#### Present to User
| Field | JSON Path | Notes |
|-------|-----------|-------|
| Instance ID | `.Reservations[0].Instances[0].InstanceId` | Primary identifier |
| State | `.Reservations[0].Instances[0].State.Name` | running/stopped/terminated |
| Instance Type | `.Reservations[0].Instances[0].InstanceType` | e.g., t3.micro |
| Private IP | `.Reservations[0].Instances[0].PrivateIpAddress` | Internal IP |
| Public IP | `.Reservations[0].Instances[0].PublicIpAddress` | External IP (if assigned) |
| Launch Time | `.Reservations[0].Instances[0].LaunchTime` | ISO 8601 |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)