# Execution Commands (CLI-Only)

This Skill uses only `aws` CLI for data collection. Below are the standard commands per phase:

## 1. VPC Foundation Network

```bash
aws ec2 describe-vpcs --region "$AWS_DEFAULT_REGION" --output json
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --region "$AWS_DEFAULT_REGION" --output json
```

## 2. Load Balancing & Public Entry Points

```bash
aws elbv2 describe-load-balancers --region "$AWS_DEFAULT_REGION" --output json
aws ec2 describe-addresses --region "$AWS_DEFAULT_REGION" --output json
aws ec2 describe-nat-gateways --region "$AWS_DEFAULT_REGION" --output json
```

## 3. Core Components (Detailed Mode)

```bash
aws ec2 describe-instances --region "$AWS_DEFAULT_REGION" --output json
aws rds describe-db-instances --region "$AWS_DEFAULT_REGION" --output json
aws eks list-clusters --region "$AWS_DEFAULT_REGION" --output json
aws ec2 describe-security-groups --region "$AWS_DEFAULT_REGION" --output json
aws lambda list-functions --region "$AWS_DEFAULT_REGION" --output json
aws s3api list-buckets --region "$AWS_DEFAULT_REGION" --output json
aws iam list-roles --output json
```

## JSON Output Path Mapping

| Resource | JSON Path (jq) |
|----------|---------------|
| VPC ID | `.Vpcs[].VpcId` |
| VPC CIDR | `.Vpcs[].CidrBlock` |
| Subnet ID | `.Subnets[].SubnetId` |
| Subnet CIDR | `.Subnets[].CidrBlock` |
| Subnet AZ | `.Subnets[].AvailabilityZone` |
| ELB Name | `.LoadBalancers[].LoadBalancerName` |
| ELB DNS | `.LoadBalancers[].DNSName` |
| ELB Type | `.LoadBalancers[].Type` |
| EIP AllocationId | `.Addresses[].AllocationId` |
| EIP Public IP | `.Addresses[].PublicIp` |
| NAT GW ID | `.NatGateways[].NatGatewayId` |
| NAT GW State | `.NatGateways[].State` |
| EC2 Instance ID | `.Reservations[].Instances[].InstanceId` |
| EC2 Name | `.Reservations[].Instances[].Tags[?Key=='Name'].Value` |
| EC2 Type | `.Reservations[].Instances[].InstanceType` |
| EC2 Private IP | `.Reservations[].Instances[].PrivateIpAddress` |
| RDS Instance ID | `.DBInstances[].DBInstanceIdentifier` |
| RDS Engine | `.DBInstances[].Engine` |
| RDS Endpoint | `.DBInstances[].Endpoint.Address` |
| EKS Cluster | `.clusters[]` |
| Lambda Name | `.Functions[].FunctionName` |
| Lambda Runtime | `.Functions[].Runtime` |
| S3 Bucket | `.Buckets[].Name` |
| IAM Role | `.Roles[].RoleName` |
| SG ID | `.SecurityGroups[].GroupId` |
| SG Name | `.SecurityGroups[].GroupName` |

> All commands use `--output json`. Use `--query` or `jq` for field filtering.
