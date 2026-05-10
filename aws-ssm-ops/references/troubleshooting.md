# Troubleshooting — AWS Systems Manager (SSM)

## Common Error Codes

| Error Code | HTTP | Description | Resolution |
|------------|------|-------------|------------|
| `InvalidInstanceId` | 400 | Instance not managed by SSM | Install SSM Agent, check IAM role |
| `DocumentNotFound` | 400 | Document name invalid | Use valid document from list-documents |
| `InvalidDocumentContent` | 400 | Parameter mismatch | Check document parameter schema |
| `InvalidParameters` | 400 | Malformed input | Validate JSON/parameter format |
| `ThrottlingException` | 429 | Rate limit exceeded | Exponential backoff, max 3 retries |
| `InternalServerError` | 500 | AWS service failure | Retry 3x; HALT |
| `ServiceUnavailable` | 503 | SSM endpoint down | Retry 3x; HALT |
| `AccessDenied` | 403 | IAM permission missing | Add required SSM permissions |
| `AgentNotInstalled` | N/A | SSM Agent missing on instance | Install agent manually |

---

## Diagnostic Commands

### Check SSM Agent Status

**CLI — Instance-side**:
```bash
# On the instance itself
sudo systemctl status amazon-ssm-agent
# or
sudo snap info amazon-ssm-agent
```

**CLI — From AWS side**:
```bash
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0" \
  --output json

# Check .PingStatus field
# "Online" = Agent running
# "Offline" = Agent not running
```

### Check Agent Version

```bash
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0" \
  --output json \
  --query 'InstanceInformationList[0].AgentVersion'
```

### Check Command Execution History

```bash
aws ssm list-commands \
  --instance-id "i-1234567890abcdef0" \
  --max-items 10 \
  --output json
```

---

## Agent Issues

### Agent Offline (PingStatus = Offline)

**Causes**:
1. SSM Agent not installed
2. SSM Agent process stopped
3. Network connectivity blocked
4. IAM role missing

**Diagnosis**:
```bash
# On instance
sudo systemctl status amazon-ssm-agent

# Check logs
sudo tail -f /var/log/amazon/ssm/amazon-ssm-agent.log
```

**Resolution**:
```bash
# Restart agent
sudo systemctl restart amazon-ssm-agent

# Install if missing
sudo yum install -y amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
```

### Agent Version Outdated

**Check**:
```bash
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-12345" \
  --output json \
  --query 'InstanceInformationList[0].[AgentVersion,IsLatestVersion]'
```

**Update via SSM**:
```bash
aws ssm send-command \
  --instance-ids "i-12345" \
  --document-name "AWS-UpdateSSMAgent" \
  --output json
```

---

## Network Connectivity Issues

### Cannot Reach SSM Endpoints

**Symptoms**: Agent offline, commands timeout

**Causes**:
1. Instance in private subnet without VPC endpoints
2. Security group blocks outbound HTTPS
3. SSM endpoints unreachable

**Diagnosis**:
```bash
# Test connectivity from instance
curl -v https://ssm.us-east-1.amazonaws.com
curl -v https://ec2messages.us-east-1.amazonaws.com
```

**Resolution Options**:

| Option | Steps |
|--------|-------|
| VPC Endpoints | Create `ssm`, `ec2messages`, `ssmmessages` endpoints |
| NAT Gateway | Add NAT gateway to private subnet |
| Security Group | Allow outbound HTTPS (443) to SSM endpoints |

---

## IAM Permission Issues

### AccessDenied on send-command

**Error**: `"User is not authorized to perform: ssm:SendCommand"`

**Resolution**:
- Add `ssm:SendCommand` to user IAM policy
- Ensure instance IAM role has `ssm:*` permissions

### Instance Role Missing

**Symptoms**: Agent shows `Offline`, describe-instance-information returns empty

**Resolution**:
1. Attach IAM role to instance with SSM permissions
2. Use `AmazonEC2RoleForSSM` managed role (deprecated)
3. Use `AmazonSSMManagedInstanceCore` managed role (recommended)

---

## Command Execution Issues

### Command Stuck in Pending

**Causes**:
1. Agent offline
2. Instance unreachable
3. Invalid instance ID

**Diagnosis**:
```bash
aws ssm list-command-invocations \
  --command-id "cmd-12345" \
  --details \
  --output json
```

**Resolution**: Verify instance managed status first.

### Command Failed with Non-Zero Exit Code

**Diagnosis**:
```bash
aws ssm get-command-invocation \
  --command-id "cmd-12345" \
  --instance-id "i-12345" \
  --output json \
  --query '[Status,ResponseCode,StandardErrorContent]'
```

**Common Causes**:
| Exit Code | Cause |
|-----------|-------|
| 1 | General error (check stderr) |
| 127 | Command not found |
| 126 | Permission denied |
| 2 | Script syntax error |

### Command Timed Out

**Causes**: Execution exceeded `TimeoutSeconds` or `executionTimeout`

**Resolution**: Increase timeout in send-command:
```bash
aws ssm send-command \
  --timeout-seconds 7200 \
  --parameters executionTimeout=7200 \
  ...
```

---

## Session Manager Issues

### Session Start Fails

**Error**: `"Target instance is not configured for Session Manager"`

**Causes**:
1. SSM Agent version too old (< 2.3.0)
2. Instance IAM role missing Session Manager permissions
3. `ssmmessages` endpoint unreachable

**Resolution**:
```bash
# Update agent
aws ssm send-command \
  --instance-ids "i-12345" \
  --document-name "AWS-UpdateSSMAgent"

# Check IAM role has:
# ssm:StartSession, ssm:ResumeSession, ssm:TerminateSession
```

### Session Manager Plugin Missing

**Symptoms**: `start-session` command returns error about plugin

**Resolution**:
```bash
# macOS
brew install session-manager-plugin

# Ubuntu/Debian
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin" -o session-manager-plugin
sudo dpkg -i session-manager-plugin

# Amazon Linux
sudo yum install -y https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm
```

---

## Throttling and Retry Strategy

### ThrottlingException

**Symptoms**: `"Rate exceeded"` or HTTP 429

**Retry Strategy**:
```python
# Exponential backoff
attempts = 0
max_retries = 3
while attempts < max_retries:
    try:
        response = ssm.send_command(...)
        break
    except ClientError as e:
        if e.response['Error']['Code'] == 'ThrottlingException':
            wait = 2 ** attempts + random.uniform(0, 1)
            time.sleep(wait)
            attempts += 1
        else:
            raise
```

---

## Recovery Matrix

| Issue | Detection | Recovery Action |
|-------|-----------|-----------------|
| Agent offline | describe-instance-information → PingStatus=Offline | Restart/install agent |
| IAM missing | AccessDenied error | Add IAM permissions |
| Network blocked | Agent offline + curl test fails | Create VPC endpoints |
| Command failed | ResponseCode ≠ 0 | Check stderr, fix script |
| Throttling | ThrottlingException | Exponential backoff (max 3) |
| Timeout | Status=TimedOut | Increase timeout value |
| Document invalid | DocumentNotFound | Use valid document name |