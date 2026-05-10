# AWS CLI Usage — Systems Manager (SSM)

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

**Response Structure**:
```json
{
  "Command": {
    "CommandId": "cmd-1234567890abcdef0",
    "DocumentName": "AWS-RunShellScript",
    "InstanceIds": ["i-1234567890abcdef0"],
    "Status": "Pending",
    "RequestedDateTime": "2026-05-10T12:00:00Z"
  }
}
```

**JSON Path**: `.Command.CommandId`

---

## get-command-invocation

Retrieve execution output for a specific instance.

```bash
aws ssm get-command-invocation \
  --command-id "cmd-1234567890abcdef0" \
  --instance-id "i-1234567890abcdef0" \
  --output json
```

**Response Structure**:
```json
{
  "CommandId": "cmd-1234567890abcdef0",
  "InstanceId": "i-1234567890abcdef0",
  "Status": "Success",
  "ResponseCode": 0,
  "StandardOutputContent": "Filesystem      Size  Used Avail Use% Mounted on...",
  "StandardErrorContent": "",
  "ExecutionEndDate": "2026-05-10T12:01:00Z"
}
```

**JSON Paths**:
- `.Status` — Execution status (Success/Failed/TimedOut)
- `.ResponseCode` — Exit code (0 = success)
- `.StandardOutputContent` — STDOUT
- `.StandardErrorContent` — STDERR

---

## list-command-invocations

List all invocations for a command (aggregate view).

```bash
aws ssm list-command-invocations \
  --command-id "cmd-1234567890abcdef0" \
  --details \
  --output json
```

**Response Structure**:
```json
{
  "CommandInvocations": [
    {
      "CommandId": "cmd-1234567890abcdef0",
      "InstanceId": "i-1234567890abcdef0",
      "InstanceName": "web-server-01",
      "Status": "Success",
      "InvocationType": "Command"
    }
  ]
}
```

---

## describe-instance-information

List instances with SSM Agent registered.

```bash
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0" \
  --output json
```

**Response Structure**:
```json
{
  "InstanceInformationList": [
    {
      "InstanceId": "i-1234567890abcdef0",
      "PingStatus": "Online",
      "PlatformType": "Linux",
      "PlatformName": "Amazon Linux",
      "AgentVersion": "3.2.1234.0",
      "IsLatestVersion": true
    }
  ]
}
```

**JSON Paths**:
- `.PingStatus` — Agent status (Online/Offline/ConnectionLost)
- `.AgentVersion` — Installed agent version

---

## start-session (Session Manager)

Start interactive terminal session.

```bash
aws ssm start-session \
  --target "i-1234567890abcdef0" \
  --document-name "AWS-StartInteractiveSession" \
  --output json
```

**Response Structure**:
```json
{
  "SessionId": "session-1234567890abcdef0",
  "Url": "https://streaming.session-manager..."
}
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