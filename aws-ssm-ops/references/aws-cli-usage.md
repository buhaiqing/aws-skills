# AWS CLI Usage — Systems Manager (SSM)

## Common JSON Paths (Centralized)

```
# Send Command:              .Command.CommandId
# Get Invocation:            .{Status,ResponseCode,StandardOutputContent,StandardErrorContent}
# List Invocations:          .CommandInvocations[].{InstanceId,Status}
# Describe Instances:        .InstanceInformationList[].{InstanceId,PingStatus,PlatformType}
# Start Session:             .SessionId
# Cancel Command:            Empty (success)
```

## Command Overview

| Command | Purpose | Primary Use |
|---------|---------|-------------|
| `send-command` | Execute remote command | Batch script execution |
| `get-command-invocation` | Get execution result | Check stdout/stderr |
| `list-command-invocations` | List all invocations | Aggregate status |
| `cancel-command` | Cancel running command | Stop execution |
| `describe-instance-information` | List managed instances | Verify SSM Agent |
| `start-session` | Start interactive session | Terminal access |
| `list-documents` | List available documents | Find templates |
| `get-document` | Get document details | Inspect parameters |

---

## send-command

Execute shell scripts or commands on managed instances.

```bash
aws ssm send-command \
  --instance-ids "i-1234567890abcdef0,i-0987654321fedcba0" \
  --document-name "AWS-RunShellScript" \
  --parameters '{"commands": ["df -h", "uptime", "systemctl status nginx"]}' \
  --region "us-east-1" \
  --output json
```

---

## get-command-invocation

Retrieve execution output for a specific instance.

```bash
aws ssm get-command-invocation \
  --command-id "cmd-1234567890abcdef0" \
  --instance-id "i-1234567890abcdef0" \
  --output json
```

---

## list-command-invocations

List all invocations for a command (aggregate view).

```bash
aws ssm list-command-invocations \
  --command-id "cmd-1234567890abcdef0" \
  --details \
  --output json
```

---

## describe-instance-information

List instances with SSM Agent registered.

```bash
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0" \
  --output json
```

---

## start-session (Session Manager)

Start interactive terminal session.

```bash
aws ssm start-session \
  --target "i-1234567890abcdef0" \
  --document-name "AWS-StartInteractiveSession" \
  --output json
```

**Note**: Requires `session-manager-plugin` installed locally for interactive terminal.

---

## cancel-command

Cancel a running command.

```bash
aws ssm cancel-command \
  --command-id "cmd-1234567890abcdef0" \
  --output json
```

---

## list-documents

Find available command documents.

```bash
aws ssm list-documents \
  --document-filter-list "key=Owner,value=Amazon" \
  --filters "Key=DocumentType,Values=Command" \
  --output json
```

---

## Common Document Names

| Document | Description |
|----------|-------------|
| `AWS-RunShellScript` | Run Linux shell commands |
| `AWS-RunPowerShellScript` | Run Windows PowerShell |
| `AWS-UpdateSSMAgent` | Update SSM Agent |
| `AWS-InstallApplication` | Install applications |
| `AWS-ConfigurePackage` | Configure software packages |
| `AWS-RunDockerAction` | Docker container operations |

---

## Pagination

SSM CLI auto-paginates. For explicit control:

```bash
aws ssm describe-instance-information \
  --max-items 50 \
  --starting-token NEXT_TOKEN \
  --output json
```

---

## Error Handling

| Error Code | CLI Exit Code | Action |
|------------|---------------|--------|
| `InvalidInstanceId` | 254 | Verify instance managed by SSM |
| `DocumentNotFound` | 254 | Check document name |
| `ThrottlingException` | 429 | Backoff 10s; retry |
| `InternalServerError` | 500 | Retry 3x; HALT |