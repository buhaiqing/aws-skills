# Integration Setup — AWS Systems Manager (SSM)

## Prerequisites

### Required Components

| Component | Requirement |
|-----------|-------------|
| AWS CLI | v2.0+ installed |
| boto3 | Python 3.10+ with boto3 package |
| AWS Credentials | Access key + secret key configured |
| Region | Valid AWS region with SSM support |
| SSM Agent | Installed on target instances |
| IAM Role | Instance role with SSM permissions |

---

## AWS CLI Installation

### macOS
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
aws --version
```

### Linux (Amazon Linux / RHEL / CentOS)
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

### Linux (Ubuntu / Debian)
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

---

## Credential Configuration

### Option 1: Environment Variables

```bash
export AWS_ACCESS_KEY_ID="{{env.AWS_ACCESS_KEY_ID}}"
export AWS_SECRET_ACCESS_KEY="{{env.AWS_SECRET_ACCESS_KEY}}"
export AWS_DEFAULT_REGION="us-east-1"
```

**Agent Rule**: NEVER ask user for credentials; fail if unset.

### Option 2: AWS Credentials File

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region, Output format
```

**File location**: `~/.aws/credentials`
```
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

### Option 3: IAM Role (EC2 Instance)

Instance profile with SSM permissions attached to EC2.

---

## boto3 Installation

### Using pip
```bash
pip install boto3
```

### Using uv (Recommended)
```bash
uv pip install boto3
```

### Verification
```python
import boto3
ssm = boto3.client('ssm', region_name='us-east-1')
print(ssm.describe_instance_information())
```

---

## SSM Agent Installation on EC2

### Amazon Linux 2 / 2023
```bash
# Pre-installed; verify
sudo systemctl status amazon-ssm-agent

# If missing
sudo yum install -y amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
```

### Ubuntu 18.04 / 20.04 / 22.04
```bash
# Using snap (pre-installed on newer AMIs)
sudo snap install amazon-ssm-agent --classic
sudo systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
sudo systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service
```

### RHEL / CentOS
```bash
sudo yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
```

### Windows Server
```powershell
# Download and install
Invoke-WebRequest -Uri "https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/windows/amd64/amazon-ssm-agent.msi" -OutFile "amazon-ssm-agent.msi"
msiexec /i amazon-ssm-agent.msi
```

---

## IAM Role Setup

### Create Instance Role

**CLI**:
```bash
# Create role
aws iam create-role \
  --role-name "SSMManagedInstanceRole" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach managed policy
aws iam attach-role-policy \
  --role-name "SSMManagedInstanceRole" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name "SSMManagedInstanceProfile"

# Add role to profile
aws iam add-role-to-instance-profile \
  --instance-profile-name "SSMManagedInstanceProfile" \
  --role-name "SSMManagedInstanceRole"
```

### Attach Role to Instance

```bash
aws ec2 associate-iam-instance-profile \
  --instance-id "i-1234567890abcdef0" \
  --iam-instance-profile Name=SSMManagedInstanceProfile
```

---

## VPC Endpoints (Private Instances)

### Required Endpoints

For private instances without internet access:

| Endpoint Service | Purpose |
|-----------------|---------|
| `com.amazonaws.{region}.ssm` | Run Command, Session Manager |
| `com.amazonaws.{region}.ec2messages` | Command delivery |
| `com.amazonaws.{region}.ssmmessages` | Session Manager data |

### Create VPC Endpoints

```bash
# Get VPC ID
VPC_ID="vpc-12345"

# Create SSM endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name "com.amazonaws.us-east-1.ssm" \
  --vpc-endpoint-type Interface \
  --subnet-ids "subnet-12345" "subnet-67890"

# Create ec2messages endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name "com.amazonaws.us-east-1.ec2messages" \
  --vpc-endpoint-type Interface

# Create ssmmessages endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name "com.amazonaws.us-east-1.ssmmessages" \
  --vpc-endpoint-type Interface
```

---

## Session Manager Plugin Installation

Required for interactive sessions (`start-session`).

### macOS
```bash
brew install session-manager-plugin
```

### Ubuntu / Debian
```bash
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin" -o "session-manager-plugin.deb"
sudo dpkg -i session-manager-plugin.deb
```

### Amazon Linux / RHEL / CentOS
```bash
sudo yum install -y https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm
```

### Windows
Download from: https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe

---

## Verification Checklist

### Pre-flight Verification

```bash
# 1. Check AWS CLI
aws --version

# 2. Check credentials
aws sts get-caller-identity

# 3. Check region
aws configure get region

# 4. List managed instances
aws ssm describe-instance-information --output json

# 5. List available documents
aws ssm list-documents --document-filter-list key=Owner,value=Amazon --output json
```

### Instance-side Verification

```bash
# On target instance
sudo systemctl status amazon-ssm-agent

# Check connectivity
curl -v https://ssm.us-east-1.amazonaws.com
curl -v https://ec2messages.us-east-1.amazonaws.com
```

---

## Quick Start Test

### Execute First Command

```bash
# Send test command
aws ssm send-command \
  --instance-ids "i-1234567890abcdef0" \
  --document-name "AWS-RunShellScript" \
  --parameters '{"commands": ["echo Hello from SSM", "whoami", "date"]}' \
  --output json

# Get command ID from response
COMMAND_ID="cmd-..."

# Check results after 30 seconds
sleep 30
aws ssm get-command-invocation \
  --command-id $COMMAND_ID \
  --instance-id "i-1234567890abcdef0" \
  --output json
```

---

## Troubleshooting Integration Issues

| Issue | Check | Resolution |
|-------|-------|------------|
| Credentials not found | `aws sts get-caller-identity` | Set env vars or run `aws configure` |
| Instance not managed | `describe-instance-information` | Install SSM Agent |
| AccessDenied | Check IAM role | Add `AmazonSSMManagedInstanceCore` policy |
| Agent offline | Check agent status on instance | Restart agent service |
| Network blocked | Test endpoint connectivity | Create VPC endpoints |