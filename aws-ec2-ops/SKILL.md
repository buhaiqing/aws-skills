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
  last_updated: "2026-06-26"
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
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS EC2 Operations Skill

## Common JSON Paths (Centralized)

```
# Run/Describe Instance: .Instances[0].{InstanceId,State.Name,InstanceType,PrivateIpAddress,LaunchTime}
# Describe (list):       .Reservations[].Instances[].{InstanceId,State.Name,InstanceType,Tags}
# Create Volume:         .VolumeId
# Describe Volume:       .Volumes[0].{VolumeId,Size,VolumeType,State,Attachments[0].InstanceId}
# Create Snapshot:       .Snapshots[0].SnapshotId
# Create Image:          .ImageId
# Create KeyPair:        .KeyMaterial
```

## Overview

Amazon EC2 (Elastic Compute Cloud) provides scalable virtual servers in AWS. This skill is an **operational runbook** with explicit scope, credential rules, pre-flight checks, dual-path execution (AWS CLI + boto3 SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "EC2", "Elastic Compute Cloud", "instance", "VM"
- Task involves CRUD on **EC2 instances** (run, stop, start, terminate, describe)
- **(AIOps)** EC2 instance behind a load balancer is unhealthy
- **(AIOps)** LB health check failure root cause
- **(AIOps)** Auto-recover EC2 instance for LB target group
- **(AIOps)** EC2 capacity for LB scaling
- **(AIOps)** Instance status check failed — LB not receiving traffic
- Keywords: balance, distribute, health-check, listener, target-group, unhealthy-instance, ec2-lb-diagnostics

### SHOULD NOT Use When
- Billing/cost analysis → out of scope; use AWS Cost Explorer directly
- IAM only → delegate to: `aws-iam-ops`
- VPC/Subnet → delegate to: `aws-vpc-ops`
- Load Balancer → delegate to: `aws-elb-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default `us-east-1` if unset |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile (SSO / AssumeRole); overrides explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.instance_name}}` | User input | Ask once; reuse |
| `{{user.ami_id}}` | User input | Ask once; reuse |
| `{{user.instance_type}}` | User input | Ask once; reuse |
| `{{user.key_name}}` | User input | Ask once; reuse |
| `{{user.sg_id}}` | User input | Ask once; reuse |
| `{{user.instance_id}}` | User input / output | Resolve by name/tag, then reuse |
| `{{user.volume_id}}` | User input / output | Resolve by instance or list, then reuse |
| `{{user.volume_size}}` | User input | Default `10` GB |
| `{{user.volume_type}}` | User input | Default `gp3` |
| `{{user.snapshot_id}}` | User input / output | Resolve or create, then reuse |
| `{{user.image_id}}` | User input / output | Describe AMI, then reuse |
| `{{user.image_name}}` | User input | AMI name; ask once |
| `{{user.device}}` | User input | Default `/dev/sdf` |
| `{{user.new_instance_type}}` | User input | Target type for modify |
| `{{output.instance_id}}` | API response | Parse: `.Instances[0].InstanceId` after Run |
| `{{output.volume_id}}` | API response | Parse: `.Volumes[0].VolumeId` after Create |
| `{{output.snapshot_id}}` | API response | Parse: `.Snapshots[0].SnapshotId` after Create |
| `{{output.image_id}}` | API response | Parse: `.ImageId` after CreateImage |
| `{{output.key_material}}` | API response | Parse: `.KeyMaterial` (private key, save once) |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{env.AWS_ACCOUNT_ID}}` | `.env` or runtime env | Substitute before use |
| `{{user.instance_id}}` | User input | Ask once; substitute |
| `{{user.instance_type}}` | User input | Ask once; substitute |

Before using `example-config.yaml`:
1. Load `.env` from project root (if present)
2. Substitute `{{env.*}}` placeholders with loaded values
3. Collect `{{user.*}}` values from user input
4. Use rendered config for CLI/SDK commands

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Common Pre-flight Steps (all ops)

#### Step 1: Check CLI
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: pip install awscli`

#### Step 2: Load & Verify Credentials
```bash
aws sts get-caller-identity --output json
```
Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from env)
[OK]   AWS_ACCESS_KEY_ID=**** (masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```
On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/troubleshooting.md for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide to troubleshooting.md |
| Region valid | `aws ec2 describe-instances --region {{user.region}}` | Suggest valid region |

### Operation: Run Instance (Launch)

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| AMI exists | `aws ec2 describe-images --image-ids {{user.ami_id}}` | Suggest valid AMI |
| KeyPair exists | `aws ec2 describe-key-pairs --key-names {{user.key_name}}` | Create or suggest |
| Security Group | `aws ec2 describe-security-groups --group-ids {{user.sg_id}}` | Verify or create |

#### Execute — CLI (Primary)
```bash
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "{{user.ami_id}}" \
  --instance-type "{{user.instance_type}}" \
  --key-name "{{user.key_name}}" \
  --security-group-ids "{{user.sg_id}}" \
  --region "{{user.region}}" \
  --tag-specifications "[{\"ResourceType\":\"instance\",\"Tags\":[{\"Key\":\"Name\",\"Value\":\"{{user.instance_name}}\"}]}]" \
  --output json | jq -r '.Instances[0].InstanceId')
```
Log: `[OK] Instance launched: $INSTANCE_ID`
Set `{{output.instance_id}}` = `$INSTANCE_ID`

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

#### Pre-flight
- Describe instance to verify it exists and is `running` state
- **Safety Gate**: MUST obtain confirmation: "Stop instance {{user.instance_id}}? This will shut down the instance. Confirm with exact instance ID."

#### Execute — CLI (Primary)
```bash
aws ec2 stop-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.stop_instances(InstanceIds=['{{user.instance_id}}'])
print(f"Stopping: {response['StoppingInstances'][0]['InstanceId']}")
```

#### Validate
Poll until `stopped` state (max 120s, interval 5s):
```bash
for i in $(seq 1 24); do
  STATUS=$(aws ec2 describe-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json | jq -r '.Reservations[0].Instances[0].State.Name')
  [ "$STATUS" = "stopped" ] && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| IncorrectInstanceState | HALT — instance must be running |
| InvalidInstanceID.NotFound | HALT — verify instance ID |
| ThrottlingException | Backoff; retry 3x |

### Operation: Start Instance

#### Pre-flight
- Describe instance to verify it exists and is `stopped` state
- If already `running`: inform user that instance is already running; no action needed

#### Execute — CLI (Primary)
```bash
aws ec2 start-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.start_instances(InstanceIds=['{{user.instance_id}}'])
print(f"Starting: {response['StartingInstances'][0]['InstanceId']}")
```

#### Validate
Poll until `running` state (max 120s, interval 5s):
```bash
for i in $(seq 1 24); do
  STATUS=$(aws ec2 describe-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json | jq -r '.Reservations[0].Instances[0].State.Name')
  [ "$STATUS" = "running" ] && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| IncorrectInstanceState | HALT — instance must be stopped |
| InvalidInstanceID.NotFound | HALT — verify instance ID |
| ThrottlingException | Backoff; retry 3x |

### Operation: Terminate Instance (Destructive)

#### Safety Gate (Mandatory)
- Describe instance to verify it exists
- **MUST** obtain explicit confirmation:
> "Terminate {{user.instance_id}}? This action is IRREVERSIBLE — all associated data will be lost. Confirm with exact instance ID."

#### Execute — CLI (Primary)
```bash
aws ec2 terminate-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.terminate_instances(InstanceIds=['{{user.instance_id}}'])
print(f"Terminating: {response['TerminatingInstances'][0]['InstanceId']}")
```

#### Validate
Poll until `terminated` state (max 60s, interval 5s):
```bash
for i in $(seq 1 12); do
  STATUS=$(aws ec2 describe-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json | jq -r '.Reservations[0].Instances[0].State.Name')
  [ "$STATUS" = "terminated" ] && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| IncorrectInstanceState | HALT — instance already terminating/terminated |
| InvalidInstanceID.NotFound | HALT — verify instance ID |
| ThrottlingException | Backoff; retry 3x |

### Operation: Describe Instance

#### Execute — CLI (Primary)
```bash
aws ec2 describe-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.describe_instances(InstanceIds=['{{user.instance_id}}'])
instance = response['Reservations'][0]['Instances'][0]
print(f"{instance['InstanceId']}: {instance['State']['Name']} ({instance['InstanceType']})")
```

#### Validate
Verify response contains the requested instance.

#### Recover
| Error | Action |
|-------|--------|
| InvalidInstanceID.NotFound | HALT — verify instance ID |
| ThrottlingException | Backoff; retry 3x |

### Operation: Describe Instances (List/Filter)

#### Execute — CLI (Primary)
```bash
# All instances
aws ec2 describe-instances --region "{{user.region}}" --output json

# Filter by state
aws ec2 describe-instances --region "{{user.region}}" --filters Name=instance-state-name,Values=running --output json

# Filter by tag
aws ec2 describe-instances --region "{{user.region}}" --filters Name=tag:Name,Values="{{user.instance_name}}" --output json
```

#### Execute — boto3 (Fallback)
```python
paginator = client.get_paginator('describe_instances')
filters = [{'Name': 'tag:Name', 'Values': ['{{user.instance_name}}']}]
for page in paginator.paginate(Filters=filters):
    for r in page['Reservations']:
        for i in r['Instances']:
            print(f"{i['InstanceId']}: {i['State']['Name']} ({i['InstanceType']})")
```

#### Validate
Verify response returns expected instances.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix filter expression; retry once |
| ThrottlingException | Backoff; retry 3x |

### Operation: Create KeyPair

#### Pre-flight
Check if key name already exists:
```bash
aws ec2 describe-key-pairs --key-names "{{user.key_name}}" --region "{{user.region}}" --output json || echo "KeyPair does not exist"
```

#### Execute — CLI (Primary)
```bash
RESULT=$(aws ec2 create-key-pair --key-name "{{user.key_name}}" --key-type ed25519 --region "{{user.region}}" --output json)
PRIVATE_KEY=$(echo "$RESULT" | jq -r '.KeyMaterial')
```
**CRITICAL**: Save private key immediately — AWS will NOT return it again.
Set `{{output.key_material}}` = `$PRIVATE_KEY`

#### Execute — boto3 (Fallback)
```python
response = client.create_key_pair(KeyName='{{user.key_name}}', KeyType='ed25519')
print(f"KeyPair: {response['KeyName']}")
print(f"Private key:\n{response['KeyMaterial']}")
```

#### Validate
```bash
aws ec2 describe-key-pairs --key-names "{{user.key_name}}" --region "{{user.region}}" --output json
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidKeyPair.Duplicate | HALT — name already exists; suggest different name |
| ThrottlingException | Backoff; retry 3x |

### Operation: Delete KeyPair

#### Safety Gate (Destructive)
- **MUST** confirm: "Delete key pair {{user.key_name}}? Instances using this key will lose SSH access for new connections."
- Verify keypair exists first

#### Execute — CLI (Primary)
```bash
aws ec2 delete-key-pair --key-name "{{user.key_name}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_key_pair(KeyName='{{user.key_name}}')
```

#### Validate
`aws ec2 describe-key-pairs --key-names "{{user.key_name}}"` → key pair not found.

#### Recover
| Error | Action |
|-------|--------|
| InvalidKeyPair.NotFound | HALT — key pair does not exist |
| ThrottlingException | Backoff; retry 3x |

### Operation: Create Volume (EBS)

#### Pre-flight
- Verify availability zone: `{{user.region}}a` (or user-specified AZ)

#### Execute — CLI (Primary)
```bash
VOLUME_ID=$(aws ec2 create-volume \
  --availability-zone "{{user.region}}a" \
  --size "{{user.volume_size:10}}" \
  --volume-type "{{user.volume_type:gp3}}" \
  --region "{{user.region}}" \
  --output json | jq -r '.VolumeId')
```
Log: `[OK] Volume created: $VOLUME_ID`
Set `{{output.volume_id}}` = `$VOLUME_ID`

#### Execute — boto3 (Fallback)
```python
response = client.create_volume(
    AvailabilityZone='{{user.region}}a',
    Size={{user.volume_size:10}},
    VolumeType='{{user.volume_type:gp3}}'
)
volume_id = response['VolumeId']
```

#### Validate
Wait until `available` state (max 30s, interval 5s):
```bash
for i in $(seq 1 6); do
  STATUS=$(aws ec2 describe-volumes --volume-ids "{{output.volume_id}}" --region "{{user.region}}" --output json | jq -r '.Volumes[0].State')
  [ "$STATUS" = "available" ] && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| VolumeLimitExceeded | HALT — request quota increase |
| InsufficientFreeAddressesInSubnet | HALT — choose different AZ |
| ThrottlingException | Backoff; retry 3x |

### Operation: Attach Volume

#### Pre-flight
- Verify volume exists and state is `available`
- Verify instance exists and state is `running`

#### Execute — CLI (Primary)
```bash
aws ec2 attach-volume \
  --volume-id "{{user.volume_id|output.volume_id}}" \
  --instance-id "{{user.instance_id}}" \
  --device "{{user.device:/dev/sdf}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.attach_volume(
    VolumeId='{{user.volume_id|output.volume_id}}',
    InstanceId='{{user.instance_id}}',
    Device='{{user.device:/dev/sdf}}'
)
```

#### Validate
Wait until volume state is `in-use` (max 30s, interval 5s):
```bash
for i in $(seq 1 6); do
  STATUS=$(aws ec2 describe-volumes --volume-ids "{{user.volume_id|output.volume_id}}" --region "{{user.region}}" --output json | jq -r '.Volumes[0].State')
  [ "$STATUS" = "in-use" ] && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidVolume.NotFound | HALT — volume does not exist |
| InvalidInstanceID.NotFound | HALT — instance does not exist |
| IncorrectState | HALT — volume must be `available` |
| ThrottlingException | Backoff; retry 3x |

### Operation: Detach Volume

#### Safety Gate
- Verify volume is attached to instance
- **MUST** confirm: "Detach volume {{user.volume_id}} from instance {{user.instance_id}}?"

#### Execute — CLI (Primary)
```bash
aws ec2 detach-volume --volume-id "{{user.volume_id}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.detach_volume(VolumeId='{{user.volume_id}}')
```

#### Validate
Wait until volume state is `available` (max 60s, interval 5s):
```bash
for i in $(seq 1 12); do
  STATUS=$(aws ec2 describe-volumes --volume-ids "{{user.volume_id}}" --region "{{user.region}}" --output json | jq -r '.Volumes[0].State')
  [ "$STATUS" = "available" ] && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidVolume.NotFound | HALT — volume does not exist |
| IncorrectState | HALT — volume must be `in-use` |
| ThrottlingException | Backoff; retry 3x |

### Operation: Describe Volumes

#### Execute — CLI (Primary)
```bash
# All volumes
aws ec2 describe-volumes --region "{{user.region}}" --output json

# Filter by instance attachment
aws ec2 describe-volumes --region "{{user.region}}" --filters Name=attachment.instance-id,Values="{{user.instance_id}}" --output json

# Single volume
aws ec2 describe-volumes --volume-ids "{{user.volume_id}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.describe_volumes(
    Filters=[{'Name': 'attachment.instance-id', 'Values': ['{{user.instance_id}}']}]
)
for v in response['Volumes']:
    print(f"{v['VolumeId']}: {v['Size']}GB {v['VolumeType']} ({v['State']})")
```

#### Validate
Verify response contains volumes matching the filter.

#### Recover
| Error | Action |
|-------|--------|
| InvalidVolume.NotFound | HALT — volume does not exist |
| ThrottlingException | Backoff; retry 3x |

### Operation: Create Snapshot

#### Pre-flight
- Verify volume exists (describe volume)

#### Execute — CLI (Primary)
```bash
SNAPSHOT_ID=$(aws ec2 create-snapshot \
  --volume-id "{{user.volume_id}}" \
  --description "{{user.snapshot_description:Snapshot of {{user.volume_id}}}}" \
  --region "{{user.region}}" \
  --output json | jq -r '.SnapshotId')
```
Set `{{output.snapshot_id}}` = `$SNAPSHOT_ID`

#### Execute — boto3 (Fallback)
```python
response = client.create_snapshot(
    VolumeId='{{user.volume_id}}',
    Description='{{user.snapshot_description:Snapshot of volume}}'
)
snapshot_id = response['SnapshotId']
```

#### Validate
Poll until `completed` state (max 300s, interval 10s):
```bash
for i in $(seq 1 30); do
  STATUS=$(aws ec2 describe-snapshots --snapshot-ids "{{output.snapshot_id}}" --region "{{user.region}}" --output json | jq -r '.Snapshots[0].State')
  [ "$STATUS" = "completed" ] && break
  sleep 10
done
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidVolume.NotFound | HALT — volume does not exist |
| SnapshotCreationPerVolumeRateExceeded | HALT — too many concurrent snapshots |
| ThrottlingException | Backoff; retry 3x |

### Operation: Create Image (AMI)

#### Pre-flight
- Verify instance exists
- **Recommend** stopping instance first for data consistency: "Stop instance {{user.instance_id}} first? (Recommended for consistent AMI)"

#### Execute — CLI (Primary)
```bash
IMAGE_ID=$(aws ec2 create-image \
  --instance-id "{{user.instance_id}}" \
  --name "{{user.image_name}}" \
  --description "{{user.image_description:AMI of {{user.instance_id}}}}" \
  --region "{{user.region}}" \
  --output json | jq -r '.ImageId')
```
Set `{{output.image_id}}` = `$IMAGE_ID`

#### Execute — boto3 (Fallback)
```python
response = client.create_image(
    InstanceId='{{user.instance_id}}',
    Name='{{user.image_name}}',
    Description='{{user.image_description:AMI}}',
    NoReboot=False
)
image_id = response['ImageId']
```

#### Validate
Poll until `available` state (max 600s, interval 30s):
```bash
for i in $(seq 1 20); do
  STATUS=$(aws ec2 describe-images --image-ids "{{output.image_id}}" --region "{{user.region}}" --output json | jq -r '.Images[0].State')
  [ "$STATUS" = "available" ] && break
  sleep 30
done
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidInstanceID.NotFound | HALT — instance does not exist |
| IncorrectInstanceState | HALT — stop instance first for consistent AMI |
| ThrottlingException | Backoff; retry 3x |

### Operation: Deregister Image (AMI)

#### Safety Gate (Destructive)
- **MUST** confirm: "Deregister AMI {{user.image_id}}? This removes the AMI. Existing instances continue running, but new instances cannot be launched from this AMI."

#### Execute — CLI (Primary)
```bash
aws ec2 deregister-image --image-id "{{user.image_id}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
client.deregister_image(ImageId='{{user.image_id}}')
```

#### Validate
`aws ec2 describe-images --image-ids "{{user.image_id}}"` → image not found (error expected).

#### Recover
| Error | Action |
|-------|--------|
| InvalidAMIID.NotFound | HALT — AMI does not exist |
| AMIWithSnapshotsInUse | HALT — AMI has dependent snapshots in use |
| ThrottlingException | Backoff; retry 3x |

### Operation: Modify Instance Attribute

#### Pre-flight
- For instance type change: instance **must** be `stopped`
- Verify the target attribute is valid

#### Execute — CLI (Primary) — Change Instance Type
```bash
aws ec2 modify-instance-attribute \
  --instance-id "{{user.instance_id}}" \
  --instance-type "{\"Value\":\"{{user.new_instance_type}}\"}" \
  --region "{{user.region}}" --output json
```

#### Execute — CLI (Primary) — Change Security Groups
```bash
aws ec2 modify-instance-attribute \
  --instance-id "{{user.instance_id}}" \
  --groups "{{user.new_sg_id}}" \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
client.modify_instance_attribute(
    InstanceId='{{user.instance_id}}',
    InstanceType={'Value': '{{user.new_instance_type}}'}
)
```

#### Validate
```bash
aws ec2 describe-instances --instance-ids "{{user.instance_id}}" --region "{{user.region}}" --output json | jq '.Reservations[0].Instances[0].InstanceType'
```

#### Recover
| Error | Action |
|-------|--------|
| IncorrectInstanceState | HALT — instance must be stopped for type change |
| InvalidParameterValue | Fix attribute value; retry once |
| ThrottlingException | Backoff; retry 3x |

## Token Efficiency Guidelines (P0)

The following 6 rules minimize Token consumption:

### TE-1: API Query > Static Tables
Use API commands instead of hardcoding instance type or AMI tables.
```markdown
# DO: describe-instance-types to discover
aws ec2 describe-instance-types --filters "Name=current-generation,Values=true" --query "InstanceTypes[].InstanceType"
```
### TE-2: No docstrings in boto3 SDK
```python
# DO: inline comments only
def run_instance(client, ami, type):
    try: return client.run_instances(ImageId=ami, InstanceType=type)
    except ClientError as e: handle_error(e)
```
### TE-3: Compact error tables
```markdown
| Error | Resolution |
|-------|-----------|
| InvalidAMIID.NotFound | HALT — suggest valid AMI |
```
### TE-4: Centralized JSON paths
File-top `## Common JSON Paths` block; one path per resource type.
### TE-5: YAML anchors in example-config.yaml
Use `&defaults` anchors in `assets/example-config.yaml`.
### TE-6: Eliminate cross-file duplicate flows
SKILL.md already has full flow → no Complete Workflow in reference files.

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)
- [Example Configuration](assets/example-config.yaml)

---

## AIOps: EC2 as Load Balancer Target — Diagnostics & Auto-Healing

### AIOps Data Collection: EC2 Health Metrics for LB RCA

| Metric | Namespace | AIOps Use |
|--------|-----------|-----------|
| `CPUUtilization` | AWS/EC2 | Backend overload detection for latency/502 RCA |
| `StatusCheckFailed` | AWS/EC2 | Aggregate instance-level health (system + application) |
| `StatusCheckFailed_System` | AWS/EC2 | AWS infrastructure issue affecting LB target |
| `StatusCheckFailed_Instance` | AWS/EC2 | OS/application issue — possible health check failure |
| `NetworkIn` / `NetworkOut` | AWS/EC2 | Bandwidth saturation detection |
| `DiskReadOps` / `DiskWriteOps` | AWS/EC2 | I/O bottleneck detection |
| `MemoryUtilization` | CWAgent (custom) | Memory pressure causing slow responses |

### AIOps Diagnostic Flows (Cross-Skill with ELB)

```
EC2 ↔ ELB Diagnostic Integration:
  When ELB detects unhealthy targets:
  1. [aws-elb-ops] Identifies unhealthy targets → instance IDs
  2. [aws-ec2-ops] Diagnoses each instance:
     a. Check StatusCheck: System + Instance health
     b. Check CPUUtilization trend (last 30 min)
     c. Check NetworkIn/Out for anomalies
     d. Check CloudTrail for recent config changes (stop, modify, SG change)
  3. [aws-ec2-ops] Determines root cause:
     - StatusCheckFailed_System → AWS infrastructure issue (stop & start to migrate)
     - StatusCheckFailed_Instance → OS crash/hang → reboot via AH-EC2-01
     - CPU > 90% → Capacity saturation → resize via AH-EC2-02
     - Network high → Bandwidth limit (check NetworkBurstLimit)
  4. Returns diagnosis to aws-elb-ops for auto-remediation decision
```

### Self-Healing Actions

#### AH-EC2-01: Reboot Unhealthy Instance [AUTO_HEAL]

Trigger: StatusCheckFailed_Instance = true AND ELB reports unhealthy target.

```
Decision: [AUTO_HEAL] (reversible, low risk)
```

```bash
# Auto-reboot command sequence
aws ec2 reboot-instances --instance-ids "{{user.instance_id}}"

# Verify status check recovery (max 2 min)
for i in $(seq 1 24); do
  STATUS=$(aws ec2 describe-instance-status \
    --instance-ids "{{user.instance_id}}" \
    --query "InstanceStatuses[0].{System: SystemStatus.Status, Instance: InstanceStatus.Status}" \
    --output json)
  SYS=$(echo "$STATUS" | jq -r '.System')
  INS=$(echo "$STATUS" | jq -r '.Instance')
  if [ "$SYS" = "ok" ] && [ "$INS" = "ok" ]; then
    echo "[OK] Health check passed after $((i * 5))s"
    break
  fi
  sleep 5
done
```
**Fallback**: 2 failures → downgrade to `[AI_ASSIST]`.

#### AH-EC2-02: Instance Resize for Capacity [AI_ASSIST]

Trigger: CPU > 90% for 15+ min AND ELB latency high.

```
Decision: [AI_ASSIST] (cost impact — user must confirm)
```

```bash
# Resize command sequence (after user confirms)
aws ec2 stop-instances --instance-ids "{{user.instance_id}}"
# Wait for stopped state, then:
aws ec2 modify-instance-attribute \
  --instance-id "{{user.instance_id}}" \
  --instance-type "{\"Value\":\"{{user.new_instance_type}}\"}"
aws ec2 start-instances --instance-ids "{{user.instance_id}}"
```

#### AH-EC2-03: SSM RunCommand Health Check [AI_ASSIST]

Trigger: Instance routing to LB but application-level unhealthy (port not listening).

```
Decision: [AI_ASSIST] (diagnostic only)
```

```bash
# Run SSM Diagnostic
aws ssm send-command \
  --instance-ids "{{user.instance_id}}" \
  --document-name "AWS-RunShellScript" \
  --parameters '{"commands":[
    "echo '=== Disk ===", "df -h",
    "echo '=== Memory ===", "free -m",
    "echo '=== Port Listeners ===", "ss -tlnp",
    "echo '=== Service Status ===", "systemctl list-units --type=service --state=running"
  ]}'
```

#### AH-EC2-04: Capacity Pre-Warning [Predictive]

```
Trigger: CPUUtilization steadily increasing over 7 days
  Current: 72% (average)
  FORECAST 7-day: 88% → exceeds 80% safe threshold
  Action: [AI_ASSIST] Recommend proactive resize before SLA impact
```

### Cross-Module Integration

| Condition | Delegate To |
|-----------|-------------|
| LB-health check EC2 diagnosis | `aws-elb-ops` (RCA coordination) |
| EC2 metrics for LB capacity | `aws-cloudwatch-ops` (FORECAST) |
| EC2 config change audit | `aws-cloudtrail-ops` (CloudTrail) |
| SSM RunCommand for diagnostics | `aws-ssm-ops` (SSM RunCommand) |
## Quality Gate (GCL)

> This skill is the **Phase 1 GCL pilot** (2026-06-04). Every execution of
> `aws-ec2-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value | Source |
|---|---|---|
| Class | `required` | `gcl-spec.md` §10 (pilot) |
| `max_iterations` | `2` | `gcl-spec.md` §10 (Phase 1 default) |
| Rubric | `references/rubric.md` (v1) | this skill |
| Prompts | `references/prompt-templates.md` (v1) | this skill |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |

### Per-operation gating

The Orchestrator applies GCL on every execution. The following operations
are **destructive** and require `{{user.safety_confirm}}` in the trace
(exact format `confirm=<OPERATION> <resource-id>`):

- `terminate-instances`
- `delete-key-pair`
- `deregister-image`
- `detach-volume` (when `--force` is used)
- `modify-instance-attribute` (when changing `InstanceType` or `DisableApiStop` on a running instance)

Non-destructive operations (`describe-instances`, `start-instances`,
`run-instances` with idempotency token) still flow through GCL but with
`Safety` dim scored against routine guard rules only.

### AWS-specific rules in force

This skill's rubric instantiates the repo-wide AWS rules from
`gcl-spec.md` §8. The ones most relevant to EC2:

- **A1** — `terminate-instances` requires `--no-dry-run` confirmation in trace
- **A7** — `--region` must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
- **A8** — Resource id in request must be echoed from a `describe-instances` lookup
- **A9** — `KeyMaterial` / `UserData` credentials MUST NOT appear in trace
- **A10** — `aws sts get-caller-identity` MUST be the first command in trace

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric + safety special cases
- `references/prompt-templates.md` — Generator / Critic / Orchestrator skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse and return
   `aiops_context.status: "failed"` with summary
   `"confirmation_token required for destructive op"`.
3. **Decision tier respect**:
   - `decision_tier: MANUAL` — never execute writes; recommendations only.
   - `decision_tier: AI_ASSIST` — recommendations; execute only if
     `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` — execute non-destructive writes
     directly; destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` JSON
   block in the response, even on failure.

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.