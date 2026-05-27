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