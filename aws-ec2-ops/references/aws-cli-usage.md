# AWS CLI Usage — EC2

## Command Map

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Run instance | `aws ec2 run-instances` | `.Instances[0].InstanceId` |
| Describe instance | `aws ec2 describe-instances` | `.Reservations[0].Instances[0]` |
| Start instance | `aws ec2 start-instances` | `.StartingInstances[0].InstanceId` |
| Stop instance | `aws ec2 stop-instances` | `.StoppingInstances[0].InstanceId` |
| Terminate instance | `aws ec2 terminate-instances` | `.TerminatingInstances[0].InstanceId` |
| List instances | `aws ec2 describe-instances` | `.Reservations[].Instances[]` |
| Create keypair | `aws ec2 create-key-pair` | `.KeyMaterial` (private key) |
| Describe keypairs | `aws ec2 describe-key-pairs` | `.KeyPairs[]` |
| Describe images (AMIs) | `aws ec2 describe-images` | `.Images[]` |

## Key CLI Conventions

### Output Format
Always use `--output json` for agent parsing.

### Region
Pass `--region` or rely on `AWS_DEFAULT_REGION`.

### Pagination
CLI auto-paginates for `describe-instances`. For explicit control:
```bash
aws ec2 describe-instances --starting-token TOKEN --max-items N
```

## Common Patterns

### Run Instance (Full Example)
```bash
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t3.micro \
  --key-name my-keypair \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678 \
  --region us-east-1 \
  --tag-specifications '[{"ResourceType":"instance","Tags":[{"Key":"Name","Value":"my-instance"}]}]' \
  --output json
```

### Describe Instance State
```bash
aws ec2 describe-instances \
  --instance-ids i-1234567890abcdef0 \
  --region us-east-1 \
  --output json \
  | jq '.Reservations[0].Instances[0].State.Name'
```

### List All Running Instances
```bash
aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=running \
  --region us-east-1 \
  --output json
```

### Query by Tag
```bash
aws ec2 describe-instances \
  --filters Name=tag:Name,Values=my-instance \
  --region us-east-1 \
  --output json
```

### Get Latest Amazon Linux AMI
```bash
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" "Name=state,Values=available" \
  --query "Images[-1].ImageId" \
  --region us-east-1 \
  --output text
```

## CLI vs API Coverage Gap

| Operation (API) | CLI Available | Notes |
|-----------------|---------------|-------|
| RunInstances | ✅ | `run-instances` |
| DescribeInstances | ✅ | `describe-instances` |
| StartInstances | ✅ | `start-instances` |
| StopInstances | ✅ | `stop-instances` |
| TerminateInstances | ✅ | `terminate-instances` |
| ModifyInstanceAttribute | ✅ | `modify-instance-attribute` |
| CreateKeyPair | ✅ | `create-key-pair` |
| DescribeKeyPairs | ✅ | `describe-key-pairs` |
| DescribeImages | ✅ | `describe-images` |
| CreateSecurityGroup | ✅ | `create-security-group` (delegate to appropriate skill) |

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```

## Retry Strategy (CLI)

CLI has built-in retry logic. Configure in `~/.aws/config`:
```ini
[default]
retry_mode = adaptive
max_attempts = 3
```