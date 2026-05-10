# Core Concepts — EC2

## What is Amazon EC2

- **Purpose**: Scalable compute capacity (virtual servers)
- **Category**: Compute
- **Console**: https://console.aws.amazon.com/ec2/
- **Docs**: https://docs.aws.amazon.com/ec2/

## Primary Resources

| Resource | Description | Console Path |
|----------|-------------|--------------|
| Instance | Virtual machine | /ec2/home#Instances |
| AMI | Machine image | /ec2/home#AMIs |
| Volume | EBS storage | /ec2/home#Volumes |
| KeyPair | SSH key | /ec2/home#KeyPairs |
| Security Group | Firewall rules | /ec2/home#SecurityGroups |

## Instance Lifecycle

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| pending | Launching | None (wait) |
| running | Operational | Stop, Reboot, Terminate |
| stopping | Stopping in progress | None (wait) |
| stopped | Stopped | Start, Terminate |
| shutting-down | Terminating | None (wait) |
| terminated | Deleted | N/A |

## Instance Types (Common)

| Type | Use Case | vCPU | Memory |
|------|----------|------|--------|
| t3.micro | General purpose | 2 | 1GB |
| t3.small | General purpose | 2 | 2GB |
| m5.large | Balanced | 2 | 8GB |
| c5.large | Compute optimized | 2 | 4GB |
| r5.large | Memory optimized | 2 | 16GB |

## Quotas (Service Limits)

| Quota | Default | Adjustable |
|-------|---------|------------|
| Max instances (on-demand) | 20 per region | Yes (via Service Quotas) |
| Max vCPU (on-demand) | varies | Yes |
| Max spot instances | varies | Yes |

## Dependencies

| Dependency | Required? | Skill |
|------------|-----------|-------|
| VPC | Yes | `aws-vpc-ops` |
| Subnet | Yes | `aws-vpc-ops` |
| Security Group | Yes | `aws-ec2-ops` (create) or `aws-vpc-ops` |
| Key Pair | SSH access | `aws-ec2-ops` |
| AMI | Yes | Pre-built or custom |

## Regions

EC2 available in all AWS regions.

Common regions:
- `us-east-1` (N. Virginia)
- `us-west-2` (Oregon)
- `eu-west-1` (Ireland)
- `ap-northeast-1` (Tokyo)

## Pricing Model

- **On-demand**: Pay per hour
- **Reserved**: 1-3 year commitment, up to 75% discount
- **Spot**: Bid-based, up to 90% discount
- **Free tier**: 750 hours/month of t2.micro/t3.micro for 12 months

## Best Practices

### Security
- Use Security Groups (stateful firewall)
- Disable password authentication (use keypair)
- Regularly patch OS
- Use IAM roles for AWS API access

### Availability
- Deploy across multiple AZs
- Use Auto Scaling for resilience
- Regular backups (snapshots)

### Cost
- Right-size instances
- Use Reserved Instances for steady workloads
- Use Spot for flexible/fault-tolerant workloads
- Stop unused instances