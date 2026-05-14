---
name: aws-ssm-ops
description: >-
  Use this skill when managing AWS SSM resources, executing remote commands via
  Run Command, starting interactive sessions via Session Manager, managing SSM
  documents, or checking command execution status; even if the user doesn't
  explicitly mention "SSM" but needs remote EC2 management without SSH access.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, SSM Agent
  installed on target instances, network access to SSM endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-15"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

# AWS Systems Manager (SSM) Operations Skill

## Overview

AWS Systems Manager (SSM) provides **remote command execution** and **session management** for EC2 instances without SSH access. This skill covers Run Command (batch execution), Session Manager (interactive shell), and Document management.

## Trigger & Scope

### SHOULD Use When
- User mentions "AWS SSM", "Systems Manager", "Run Command", "Session Manager"
- Task involves remote execution on EC2 instances without SSH
- Keywords: `send-command`, `run shell script`, `remote execute`, `interactive session`
- Managing SSM Documents (AWS-RunShellScript, AWS-RunPowerShellScript)
- Checking command execution status or invocation results

### SHOULD NOT Use When
- Billing/cost analysis → delegate to: `aws-cost-ops`
- IAM role creation for SSM → delegate to: `aws-iam-ops`
- EC2 instance lifecycle (start/stop/terminate) → delegate to: `aws-ec2-ops`
- VPC endpoint creation → delegate to: `aws-vpc-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.instance_ids}}` | User input | Ask once; comma-separated list |
| `{{user.commands}}` | User input | Ask once; array of shell commands |
| `{{user.document_name}}` | User input | Default: `AWS-RunShellScript` |
| `{{output.command_id}}` | Last API response | Parse `.Command.CommandId` |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Operation: Send Command (Remote Execution)

### Pre-flight

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
| SSM Agent installed | Check instance tags or describe-instance-information | WARN; may fail on target |
| Instance reachable | `aws ssm describe-instance-information` | HALT; no managed instances |
| Document exists | `aws ssm list-documents --document-filter key=Name,value={{user.document_name}}` | HALT; use valid document |

### Execute — CLI (Primary)

```bash
aws ssm send-command \
  --instance-ids "{{user.instance_ids}}" \
  --document-name "{{user.document_name}}" \
  --parameters commands="{{user.commands}}" \
  --region "{{env.AWS_DEFAULT_REGION}}" \
  --output json
```

**JSON Path for CommandId**: `.Command.CommandId`

### Execute — boto3 (Fallback)

```python
import boto3

ssm = boto3.client('ssm', region_name='{{env.AWS_DEFAULT_REGION}}')
response = ssm.send_command(
    InstanceIds=['{{user.instance_ids}}'.split(',')],
    DocumentName='{{user.document_name}}',
    Parameters={'commands': ['{{user.commands}}'.split(',')]}
)
command_id = response['Command']['CommandId']
```

### Validate

Poll command status until terminal state (Success/Failed/TimedOut):

```bash
# Check overall command status
aws ssm list-command-invocations \
  --command-id "{{output.command_id}}" \
  --details \
  --output json

# JSON path: `.CommandInvocations[].Status`
```

**Terminal States**: `Success`, `Failed`, `Cancelled`, `TimedOut`

**Polling**: Interval 5s, max wait 300s (5 min)

### Recover

| Error | Action |
|-------|--------|
| InvalidInstanceId | Verify instance ID; check SSM Agent status |
| DocumentNotFound | Use valid document name; list with `aws ssm list-documents` |
| ThrottlingException | Backoff 10s; retry 3x |
| InternalServerError | Retry 3x; then HALT |
| AgentNotInstalled | WARN; install SSM Agent manually |

---

## Operation: Get Command Invocation Result

### Execute — CLI

```bash
aws ssm get-command-invocation \
  --command-id "{{output.command_id}}" \
  --instance-id "{{user.instance_id}}" \
  --output json
```

**JSON Paths**:
- `.Status` — Execution status
- `.StandardOutputContent` — STDOUT
- `.StandardErrorContent` — STDERR
- `.ResponseCode` — Exit code

---

## Operation: List Managed Instances

### Execute — CLI

```bash
aws ssm describe-instance-information \
  --filters key=InstanceIds,value="{{user.instance_ids}}" \
  --output json
```

**JSON Path**: `.InstanceInformationList[].InstanceId`, `.InstanceInformationList[].PingStatus`

---

## Operation: Start Interactive Session (Session Manager)

### Execute — CLI

```bash
aws ssm start-session \
  --target "{{user.instance_id}}" \
  --document-name "AWS-StartInteractiveSession" \
  --output json
```

**Note**: Returns session ID; actual terminal requires `session-manager-plugin` installed locally.

---

## Operation: Cancel Command

**Safety Gate**: Confirm cancellation with user.

```bash
aws ssm cancel-command \
  --command-id "{{output.command_id}}" \
  --output json
```

---

## SSM Documents Reference

| Document Name | Platform | Purpose |
|--------------|----------|---------|
| `AWS-RunShellScript` | Linux | Execute shell commands |
| `AWS-RunPowerShellScript` | Windows | Execute PowerShell |
| `AWS-UpdateSSMAgent` | All | Update SSM Agent |
| `AWS-InstallApplication` | All | Install packages |
| `AWS-ConfigurePackage` | All | Configure packages |

---

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)