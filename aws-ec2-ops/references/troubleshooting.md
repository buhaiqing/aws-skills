# Troubleshooting — EC2

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| InvalidAMIID.NotFound (400) | Use valid AMI; get latest from `describe-images` |
| InvalidAMIID.Malformed (400) | Format: `ami-xxxxxxxxxxxxxxxxx` |
| InvalidKeyPair.NotFound (400) | Create via `create-key-pair` |
| InvalidKeyPair.Duplicate (400) | Use different name |
| InvalidSecurityGroupID.NotFound (400) | Check SG ID and VPC |
| InvalidInstanceID.NotFound (400) | Verify instance ID |
| InstanceLimitExceeded (400) | Request quota increase via Service Quotas |
| InsufficientInstanceCapacity (500) | Try different instance type or AZ |
| UnauthorizedOperation (403) | Add `ec2:*` or specific permissions |
| ThrottlingException (429) | Backoff and retry (max 3x) |
| InternalError (500) | Retry 3x; contact support if persistent |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify region**: Check `AWS_DEFAULT_REGION` or pass `--region`
3. **Describe instance**: `aws ec2 describe-instances --instance-ids i-xxx`
4. **Check state**: Verify not in transition state
5. **Check dependencies**: VPC, Subnet, Security Group, KeyPair

## Common Issues

### Instance Won't Start

| Symptom | Possible Cause | Resolution |
|---------|----------------|------------|
| Stuck in pending | Capacity issue | Try different AZ or instance type |
| Fails immediately | AMI/SG/Subnet issue | Verify all dependencies |
| Authorization error | IAM permissions | Check `ec2:StartInstances` permission |

### Instance Won't Stop

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Stuck in stopping | Hypervisor issue | Force stop (API: `stop-instances --force`) |
| Takes too long | EBS write pending | Wait; check EBS volume status |

### SSH Connection Failed

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Connection refused | Not running | Start instance |
| Permission denied | Wrong key | Use correct .pem file |
| Timeout | Security Group | Allow inbound SSH (port 22) |

### AMI Not Found

```bash
# Get latest Amazon Linux 2 AMI
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
  --query "Images[-1].ImageId" \
  --output text
```

### Capacity Issues

When `InsufficientInstanceCapacity`:
1. Try different instance type (e.g., t3.small → t3.micro)
2. Try different Availability Zone
3. Try different region
4. Use Spot instances if acceptable

## CloudWatch Metrics

Key metrics for EC2:
- `CPUUtilization`
- `NetworkIn/Out`
- `DiskRead/WriteOps`
- `StatusCheckFailed`

```bash
aws cloudwatch get-metric-data \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxx \
  --output json
```

## AIOps: EC2-LB Cross-Module Diagnostic Flow

### EC2 Behind LB: Health Check Failure RCA

```
Trigger: Instance is ELB target but reported as unhealthy
┌──────────────────────────────────────────────────────────────────┐
│ Step 1 — Check EC2 Instance Status                               │
│ aws ec2 describe-instance-status --instance-ids {{instance_id}}  │
│                                                                  │
│ Step 2 — Check CloudWatch Metrics (last 30min)                   │
│ # CPUUtilization trend                                           │
│ aws cloudwatch get-metric-statistics --namespace AWS/EC2         │
│   --metric-name CPUUtilization --statistics Average              │
│   --dimensions Name=InstanceId,Value={{instance_id}}             │
│   --start-time "$(date -d '-30 minutes' -u ...)" --period 300    │
│                                                                  │
│ # StatusCheckFailed (any recent failures)                        │
│ aws cloudwatch get-metric-statistics --namespace AWS/EC2         │
│   --metric-name StatusCheckFailed --statistics Sum              │
│   --dimensions Name=InstanceId,Value={{instance_id}}             │
│                                                                  │
│ Step 3 — Check CloudTrail for Recent Changes                    │
│ aws cloudtrail lookup-events --lookup-attributes                 │
│   AttributeKey=ResourceName,AttributeValue={{instance_id}}       │
│   --start-time "{{T0-60m}}" --end-time "{{T0+5m}}"               │
│                                                                  │
│ Step 4 — Determine Root Cause                                    │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ SystemCheck failed → AWS HW issue → [AI_ASSIST] stop&start  │  │
│ │ InstanceCheck failed → OS issue → [AUTO_HEAL] reboot        │  │
│ │ CPU > 90% → Capacity → [AI_ASSIST] resize or add instances  │  │
│ │ CloudTrail "stop" → instance was recently stopped           │  │
│ └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Auto-Healing Decision Matrix for LB Targets

| Symptom | Root Cause | Decision | Action |
|---------|-----------|----------|--------|
| StatusCheckFailed_System | AWS hardware issue | `[AI_ASSIST]` | Stop and start (migrate to new host) |
| StatusCheckFailed_Instance | OS hang | `[AUTO_HEAL]` | Reboot instance |
| CPU > 90% for 15+ min | Capacity saturation | `[AI_ASSIST]` | Resize or add instances |
| App port not listening | Application crash | `[AI_ASSIST]` | SSM RunCommand restart service |
| Disk full | No free space | `[AI_ASSIST]` | Clean disk or attach new volume |
| Memory > 90% | Memory pressure | `[AI_ASSIST]` | Resize or add instances |

### Predictive Capacity Check (FORECAST)

```bash
# Predict CPU utilization for next 7 days
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization","Dimensions":[{"Name":"InstanceId","Value":"{{instance_id}}"}]},"Period":3600,"Stat":"Average"}},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)","Label":"7-Day Forecast"}
  ]' \
  --start-time "$(date -d '-14 days' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### SSM Diagnostic Commands for Application Health

```bash
# Run full diagnostic via SSM
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --targets Key=instanceids,Values="{{instance_id}}" \
  --parameters '{"commands":[
    "echo '=== Disk ===", "df -h",
    "echo '=== Memory ===", "free -m",
    "echo '=== Listeners ===", "ss -tlnp",
    "echo '=== Processes ===", "ps aux --sort=-%cpu | head -10",
    "echo '=== Service Status ===",
    "systemctl list-units --type=service --state=running | head -20",
    "echo '=== Health Check ===", "curl -s -o /dev/null -w '%{http_code}' http://localhost:80/health"
  ]}'
```

### Capacity Pre-Warning Report

```
[AIOPS_PREVENTIVE] EC2 Capacity Report — {{date}}
  Instance: i-xxx (t3.medium)
  CPU: Current 72% → Forecast 88% in 7 days ⚠️
  Risk: Exceeds 80% safe threshold within 1 week
  Action: [AI_ASSIST] Recommend resize to t3.large (+$XX/mo)
```