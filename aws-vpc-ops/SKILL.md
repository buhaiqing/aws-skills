# aws-vpc-ops

AWS VPC (Virtual Private Cloud) operational skill for AI Agent automation.

## Triggers

**SHOULD activate when**:
- User requests VPC creation, deletion, or modification
- Subnet management operations (create, delete, describe)
- Security Group rule changes
- Route table configuration
- Internet Gateway or NAT Gateway setup
- VPC Peering connection requests
- CIDR block allocation or conflicts
- Network connectivity troubleshooting within VPC scope

**SHOULD-NOT activate when**:
- EC2 instance operations only (delegate to `aws-ec2-ops`)
- IAM policy changes (delegate to `aws-iam-ops`)
- Direct Connect or VPN operations (delegate to `aws-network-ops`)
- Load Balancer management (delegate to `aws-elb-ops`)
- Route 53 DNS changes (delegate to `aws-route53-ops`)

## Scope

| Resource Type | Operations Supported |
|---------------|---------------------|
| VPC | create, delete, describe, modify-attribute |
| Subnet | create, delete, describe, modify-attribute |
| Security Group | create, delete, describe, authorize-ingress/egress, revoke-ingress/egress |
| Route Table | create, delete, describe, create-route, delete-route, associate-subnet |
| Internet Gateway | create, delete, describe, attach, detach |
| NAT Gateway | create, delete, describe |
| VPC Peering Connection | create, delete, describe, accept, reject |

## Variable Convention

| Placeholder | Source | Rule |
|-------------|--------|------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | Use default if skill allows region override |
| `{{env.AWS_SESSION_TOKEN}}` | Environment | Required for temporary credentials |
| `{{user.vpc_cidr}}` | User input | Ask once; validate CIDR format |
| `{{user.vpc_name}}` | User input | Ask once; used for Name tag |
| `{{user.subnet_cidr}}` | User input | Validate within VPC CIDR range |
| `{{user.peer_vpc_id}}` | User input | Cross-region VPC peering requires region |

**Never commit real AWS credentials. Always use `{{env.*}}` placeholders.**

## Execution Flow

### Pre-flight Checklist

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

3. AWS CLI installed and version >= 2.0
4. Region specified: `AWS_DEFAULT_REGION` or `{{user.region}}`
5. CIDR block validation: RFC 1918 private ranges preferred
6. Quota check: VPCs per region (default 5), subnets per VPC (default 200)

### Execute

**Primary Path**: AWS CLI with `--output json`
```bash
aws ec2 create-vpc --cidr-block {{user.vpc_cidr}} --output json
```

**Fallback Path**: boto3 SDK (after 3 CLI failures)
```python
import boto3
ec2 = boto3.client('ec2', region_name='{{env.AWS_DEFAULT_REGION}}')
response = ec2.create_vpc(CidrBlock='{{user.vpc_cidr}}')
```

### Validate

| Operation | Validation Method | Max Wait |
|-----------|------------------|----------|
| Create VPC | `describe-vpcs` → `State: available` | 30s |
| Create Subnet | `describe-subnets` → `State: available` | 30s |
| Create NAT Gateway | `describe-nat-gateways` → `State: available` | 180s |
| Create Security Group | `describe-security-groups` → exists check | 30s |
| VPC Peering Accept | `describe-vpc-peering-connections` → `Status: active` | 60s |

Polling pattern: exponential backoff, initial 5s, max interval 30s.

### Recover

| Error Type | Recovery Action |
|------------|-----------------|
| InvalidParameter (400) | Log error; fix parameters; retry once |
| QuotaExceeded (VpcLimitExceeded) | HALT; report quota limit and request increase URL |
| Throttling (RequestLimitExceeded) | Exponential backoff; max 3 retries |
| DependencyViolation (VPC has resources) | HALT; list dependencies; require cleanup order |
| CIDR Conflict (InvalidVpc.Range) | HALT; report conflicting CIDR |
| 5xx InternalError | Retry 3x with backoff; then HALT |

## Safety Gates

### Destructive Operations
VPC deletion requires explicit human confirmation before execution:

```
⚠️ VPC deletion is destructive and irreversible.
Dependencies must be removed first:
- Subnets, Security Groups, Route Tables
- Internet Gateway (detached)
- NAT Gateways (deleted)
- VPC Peering Connections
- EC2 instances in VPC

Confirm deletion? [YES/NO]
```

**Required checks before VPC deletion**:
1. List all subnets in VPC
2. Check for EC2 instances via `describe-instances --filters Name=vpc-id`
3. Verify Internet Gateway detachment
4. Confirm NAT Gateway deletion
5. Check VPC Peering Connections status

### Dependency Cleanup Sequence
```
1. Delete EC2 instances → 2. Delete NAT Gateways → 3. Detach/Delete IGW →
4. Delete Route Tables (except main) → 5. Delete Subnets → 6. Delete VPC
```

## Output Format

All outputs use JSON for agent parsing:
```json
{
  "Vpc": {
    "VpcId": "vpc-0a1b2c3d4e5f6g7h",
    "CidrBlock": "10.0.0.0/16",
    "State": "available",
    "Tags": [{"Key": "Name", "Value": "{{user.vpc_name}}"}]
  }
}
```

## Delegation

| Condition | Delegate To |
|-----------|------------|
| EC2 instance in subnet | `aws-ec2-ops` |
| RDS in VPC | `aws-rds-ops` |
| Lambda VPC config | `aws-lambda-ops` |
| VPN connection | `aws-network-ops` |

## Quick Reference

| Action | CLI Command |
|--------|-------------|
| Create VPC | `aws ec2 create-vpc --cidr-block CIDR` |
| List VPCs | `aws ec2 describe-vpcs` |
| Create Subnet | `aws ec2 create-subnet --vpc-id ID --cidr-block CIDR` |
| Create SG | `aws ec2 create-security-group --group-name NAME --description DESC --vpc-id ID` |
| Add SG Rule | `aws ec2 authorize-security-group-ingress --group-id ID --protocol PROTO --port PORT` |
| Create IGW | `aws ec2 create-internet-gateway` |
| Attach IGW | `aws ec2 attach-internet-gateway --internet-gateway-id ID --vpc-id ID` |
| Create NAT GW | `aws ec2 create-nat-gateway --subnet-id ID --allocation-id EIP` |
| Create Peering | `aws ec2 create-vpc-peering-connection --vpc-id ID --peer-vpc-id ID` |

## See Also

- `references/aws-cli-usage.md` — Complete CLI command reference
- `references/boto3-sdk-usage.md` — Python SDK patterns
- `references/core-concepts.md` — VPC architecture and quotas
- `references/troubleshooting.md` — Error codes and recovery
- `assets/example-config.yaml` — Configuration templates