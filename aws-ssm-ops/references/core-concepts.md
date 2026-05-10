# Core Concepts — AWS Systems Manager (SSM)

## Service Architecture

AWS Systems Manager is a **management service** that provides:

1. **Run Command** — Remote command execution (batch, non-interactive)
2. **Session Manager** — Interactive shell access (no SSH required)
3. **Documents** — Reusable command templates
4. **Parameter Store** — Configuration/secrets management
5. **Patch Manager** — OS patching automation

This skill focuses on **Run Command** and **Session Manager** for remote execution.

---

## SSM Agent

### What It Is

SSM Agent is a **software agent** installed on EC2 instances that:
- Communicates with SSM service endpoints
- Receives and executes commands from Run Command
- Provides interactive shell for Session Manager
- Reports instance status and inventory

### Agent Status

| Status | Meaning |
|--------|---------|
| `Online` | Agent connected, ready to receive commands |
| `Offline` | Agent not running or network issue |
| `ConnectionLost` | Agent was online, now disconnected |

### Pre-installed on

| AMI Type | SSM Agent Status |
|----------|------------------|
| Amazon Linux 2 | Pre-installed, auto-started |
| Amazon Linux 2023 | Pre-installed, auto-started |
| Ubuntu 18.04+ | Pre-installed (cloud-init) |
| Windows Server | Pre-installed |
| Custom AMIs | Manual installation required |

### Manual Installation

**Amazon Linux / RHEL / CentOS**:
```bash
sudo yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
```

**Ubuntu / Debian**:
```bash
sudo snap install amazon-ssm-agent --classic
sudo systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
sudo systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service
```

---

## SSM Documents

### What They Are

Documents are **JSON templates** that define:
- Command type (Shell, PowerShell, etc.)
- Input parameters
- Execution steps
- Output handling

### Key Document Types

| Type | Purpose | Example |
|------|---------|---------|
| `Command` | Execute scripts | AWS-RunShellScript |
| `Session` | Interactive access | AWS-StartInteractiveSession |
| `Automation` | Multi-step workflows | AWS-UpdateSSMAgent |
| `Package` | Software deployment | AWS-ConfigurePackage |

### Common Documents

| Document Name | Platform | Use Case |
|--------------|----------|---------|
| `AWS-RunShellScript` | Linux | Execute shell commands |
| `AWS-RunPowerShellScript` | Windows | Execute PowerShell |
| `AWS-UpdateSSMAgent` | All | Update agent version |
| `AWS-InstallApplication` | All | Install software packages |
| `AWS-ConfigurePackage` | All | Configure applications |
| `AWS-RunDockerAction` | Linux | Docker operations |
| `AWS-StartInteractiveSession` | All | Session Manager entry |

---

## Run Command

### Execution Model

```
┌─────────┐     ┌─────────────┐     ┌───────────┐     ┌────────────┐
│  User   │ →   │ SSM Service │ →   │ SSM Agent │ →   │  Instance  │
│ Command │     │ (Regional)  │     │ (Local)   │     │ Execution  │
└─────────┘     └─────────────┘     └───────────┘     └────────────┘
      │                │                   │                  │
      │                │                   │                  │
      └────────────────┴───────────────────┴──────────────────┘
                    Results returned via SSM Service
```

### Execution Status

| Status | Meaning |
|--------|---------|
| `Pending` | Command queued, not yet delivered |
| `InProgress` | Agent executing command |
| `Success` | Command completed (exit code 0) |
| `Failed` | Command failed (exit code ≠ 0) |
| `Cancelled` | User cancelled |
| `TimedOut` | Execution exceeded timeout |

### Timeout Configuration

| Parameter | Default | Max |
|-----------|---------|-----|
| `TimeoutSeconds` (send-command) | 3600 | 172800 (48h) |
| `executionTimeout` (document) | 3600 | Depends on document |

---

## Session Manager

### What It Is

Interactive shell access to EC2 instances:
- No SSH port 22 required
- No bastion host needed
- Works through SSM endpoints
- Audit logging available

### How It Works

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ Local Client │ →   │ SSM Service │ →   │ SSM Agent    │
│ (Plugin)     │     │ WebSocket   │     │ Shell Proxy  │
└──────────────┘     └─────────────┘     └──────────────┘
         ↑                   ↑                   ↑
         └───────────────────┴───────────────────┘
                    Bi-directional terminal stream
```

### Requirements

1. **Session Manager Plugin** installed locally
2. **IAM role** on instance with `ssm:StartSession` permission
3. **SSM Agent** running on target instance
4. Network access to SSM endpoints

---

## IAM Permissions

### Required Instance Role

```json
{
  "Effect": "Allow",
  "Action": [
    "ssm:UpdateInstanceInformation",
    "ssm:ListInstanceAssociations",
    "ssm:DescribeInstanceProperties",
    "ssm:SendCommand",
    "ssm:GetCommandInvocation"
  ],
  "Resource": "*"
}
```

### Session Manager Additional Permissions

```json
{
  "Effect": "Allow",
  "Action": [
    "ssm:StartSession",
    "ssm:TerminateSession",
    "ssm:ResumeSession"
  ],
  "Resource": [
    "arn:aws:ec2:*:*:instance/*",
    "arn:aws:ssm:*:*:document/AWS-StartInteractiveSession"
  ]
}
```

---

## Network Requirements

### SSM Endpoints

| Endpoint | Service |
|----------|---------|
| `ssm.{region}.amazonaws.com` | Run Command, Session Manager |
| `ssmmessages.{region}.amazonaws.com` | Session Manager data channel |
| `ec2messages.{region}.amazonaws.com` | Run Command data channel |

### Connectivity Options

| Option | Use Case |
|--------|---------|
| Public internet | Instances with public IP |
| VPC endpoints | Private instances (no internet) |
| NAT Gateway | Private instances via NAT |

---

## Service Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Commands per region | 1000/minute | Yes |
| Concurrent sessions per instance | 1 | No |
| Command history retention | 30 days | No |
| Max targets per command | 50 (EC2), 500 (Tags) | Yes |

---

## Comparison: Run Command vs Session Manager

| Feature | Run Command | Session Manager |
|---------|-------------|-----------------|
| Type | Batch execution | Interactive terminal |
| Output | Retrieved after completion | Real-time streaming |
| Timeout | Configurable | Session timeout (default 30min) |
| Use case | Scripts, diagnostics | Debugging, troubleshooting |
| Parallel | Multiple instances | Single instance |