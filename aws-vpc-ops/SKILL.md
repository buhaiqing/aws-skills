---
name: aws-vpc-ops
description: >-
  Use when managing AWS VPC resources, creating/deleting VPCs, subnets, security
  groups, route tables, IGWs, NAT Gateways, or peering connections; even if user
  doesn't mention "VPC" but needs network infrastructure or troubleshooting.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials with EC2/VPC permissions.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-05-28"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_SESSION_TOKEN
---
# AWS VPC Ops Skill

AWS VPC operational skill for AI Agent automation.

## Trigger & Scope

### SHOULD Use When
- User mentions "VPC", "subnet", "security group", "route table", "NAT Gateway", "Internet Gateway"
- Task involves creating, deleting, or modifying VPC networking resources
- User requests VPC Peering connection setup
- Keywords: vpc, subnet, cidr, security-group, route, gateway, peering
- Network connectivity troubleshooting within VPC scope

### SHOULD NOT Use When
- EC2 instance ops → delegate to: `aws-ec2-ops`
- IAM → delegate to: `aws-iam-ops`
- Load Balancer → delegate to: `aws-elb-ops`
- Route53 DNS → delegate to: `aws-route53-ops`
- Direct Connect/VPN → delegate to: `aws-network-ops`

## Scope & Quick Reference

| Resource | CLI | Safety Gate |
|----------|-----|-------------|
| VPC | `aws ec2 create-vpc --cidr-block {{cidr}}` | Delete: confirm + deps check |
| Subnet | `aws ec2 create-subnet --vpc-id {{id}} --cidr-block {{cidr}}` | Delete: confirm |
| Security Group | `aws ec2 create-security-group --group-name {{name}} --description {{desc}} --vpc-id {{id}}` | Delete: confirm |
| Route Table | `aws ec2 create-route-table --vpc-id {{id}}` | Delete: disassociate first |
| IGW | `aws ec2 create-internet-gateway` | Delete: detach first |
| NAT Gateway | `aws ec2 create-nat-gateway --subnet-id {{id}} --allocation-id {{eip}}` | Delete: confirm |
| VPC Peering | `aws ec2 create-vpc-peering-connection --vpc-id {{id}} --peer-vpc-id {{id}}` | Accept/reject: confirm |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{user.vpc_cidr}}` | User input | Ask once; reuse |
| `{{user.vpc_name}}` | User input | Ask once; reuse |
| `{{user.subnet_cidr}}` | User input | Ask once; reuse |
| `{{output.vpc_id}}` | Last API response | Parse: `.Vpc.VpcId` |
| `{{output.subnet_id}}` | Last API response | Parse: `.Subnet.SubnetId` |
| `{{output.sg_id}}` | Last API response | Parse: `.GroupId` |

## Execution Flow

### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] Region={{env.AWS_DEFAULT_REGION}} Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx`
```bash
# Quota check
aws service-quotas get-service-quota --service-code ec2 --quota-code L-F678F1CE  # VPCs per region
aws service-quotas get-service-quota --service-code ec2 --quota-code L-3633C6E3  # NAT Gateways per AZ
```

### Execute (Primary: CLI)
See [references/aws-cli-usage.md](references/aws-cli-usage.md).

### Execute (Fallback: boto3)
After 3 CLI failures — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

### Validate
| Operation | Max Wait |
|-----------|----------|
| Create VPC / Subnet / SG | 30s (`vpc_available`, `subnet_available`) |
| Create NAT Gateway | 180s (`nat_gateway_available`) |
| Peering Accept | 60s (`describe-vpc-peering-connections`) |

### Recover
| Error | Action |
|-------|--------|
| InvalidParameter / CIDR Conflict | HALT — fix params |
| QuotaExceeded (VpcLimitExceeded) | HALT — request increase |
| ResourceDependencyViolation | HALT — cleanup dependencies |
| Throttling | Backoff, retry 3x |
| 5xx | Retry 3x; HALT |

## Safety Gates

### VPC Deletion
```
⚠️ VPC deletion is irreversible. Dependencies must be removed in order:
1. EC2 instances → 2. NAT Gateways → 3. Detach/Delete IGW →
4. Delete Route Tables (except main) → 5. Delete Subnets → 6. Delete VPC
```
Confirm deletion: Type `DELETE {{user.vpc_id}}` to proceed.

### Dependency Cleanup Sequence
```bash
aws ec2 describe-instances --filters Name=vpc-id,Values={{id}}  # Check instances
aws ec2 describe-nat-gateways --filter Name=vpc-id,Values={{id}}  # Check NAT GWs
aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values={{id}}  # Check IGWs
aws ec2 describe-route-tables --filters Name=vpc-id,Values={{id}}  # Check RTs (skip main)
aws ec2 describe-subnets --filters Name=vpc-id,Values={{id}}  # Check subnets
```

## Output Convention

All commands use `--output json`. Key JSON paths (centralized):
```
# Create/Describe VPC:    .Vpc.{VpcId,CidrBlock,State}
# Create Subnet:          .Subnet.{SubnetId,CidrBlock,VpcId,State,AvailabilityZone}
# Create SG:              .GroupId
# Create Route Table:     .RouteTable.RouteTableId
# Create IGW:             .InternetGateway.InternetGatewayId
# Create NATGW:           .NatGateway.{NatGatewayId,State}
# Create Peering:         .VpcPeeringConnection.{VpcPeeringConnectionId,Status.Code}
# Describe (list):        .Vpcs[].{VpcId,CidrBlock,State}  / .Subnets[]  / .SecurityGroups[]  / .RouteTables[] / .NatGateways[]
```

## Delegation
| Condition | Skill |
|-----------|-------|
| EC2 instance in subnet | `aws-ec2-ops` |
| RDS in VPC | `aws-rds-ops` |
| Lambda VPC config | `aws-lambda-ops` |
| VPN connection | `aws-network-ops` |

## Reference Files
- `references/aws-cli-usage.md` — CLI commands
- `references/boto3-sdk-usage.md` — SDK patterns
- `references/core-concepts.md` — Architecture, CIDR, quotas
- `references/troubleshooting.md` — Error codes, cleanup, connectivity
- `assets/example-config.yaml` — Configuration templates