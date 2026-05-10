# Core Concepts Template (AWS Services)

Use this template when creating `references/core-concepts.md` for a new AWS service skill.

## Sections to Document

### 1. Service Overview

```markdown
## What is [Service Name]

- **Purpose**: Brief description of service capability
- **Category**: Compute / Storage / Database / Network / Security / Analytics
- **AWS Console URL**: https://console.aws.amazon.com/[service]/
- **Official Docs**: https://docs.aws.amazon.com/[service]/
```

### 2. Primary Resources

```markdown
## Primary Resources

| Resource Type | Description | Console Path |
|---------------|-------------|--------------|
| [Resource A] | Main resource | /[service]/a |
| [Resource B] | Dependent resource | /[service]/b |
```

### 3. Architecture & Limits

```markdown
## Architecture & Limits

### Region Availability
- Global service OR Regional service
- Supported regions: [list or link]

### Quotas (Service Limits)
| Quota Name | Default Limit | Adjustable? |
|------------|---------------|-------------|
| Max [Resource] | X | Yes/No |
| Max concurrent operations | Y | No |

### Limits
- Max size: [specify]
- Max throughput: [specify]
- Rate limits: [specify]
```

### 4. Resource Lifecycle

```markdown
## Resource Lifecycle

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| creating | Initial provisioning | None (wait) |
| available/running | Operational | All operations |
| updating | Configuration change | Limited |
| deleting | Deletion in progress | None |
| deleted | Terminal state | N/A |
```

### 5. Dependencies & Relationships

```markdown
## Dependencies

| Dependency | Required? | Created By |
|------------|-----------|------------|
| VPC | Yes | `aws-vpc-ops` |
| IAM Role | Optional | `aws-iam-ops` |
| Security Group | Yes | `aws-ec2-ops` |

## Delegation Rules

1. VPC must exist before creating [resource] → delegate to `aws-vpc-ops`
2. IAM role must exist for certain operations → delegate to `aws-iam-ops`
```

### 6. Pricing Model (Brief)

```markdown
## Pricing Model (Summary)

- **Pricing type**: On-demand / Reserved / Spot
- **Key dimensions**: Instance type, storage size, data transfer
- **Free tier**: Yes/No; [details]
- **Estimator**: https://calculator.aws/#/
```

### 7. Best Practices

```markdown
## Best Practices

### Security
- [Recommendation 1]
- [Recommendation 2]

### Availability
- Multi-AZ deployment recommended
- Backup strategy

### Cost
- Right-sizing recommendations
- Reserved instance strategy
```

### 8. Common Patterns

```markdown
## Common Deployment Patterns

### Pattern 1: [Name]
- Use case: ...
- Architecture: ...
- CLI/SDK steps: ...

### Pattern 2: [Name]
- Use case: ...
- Architecture: ...
- CLI/SDK steps: ...
```

## Example (EC2)

```markdown
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

## Architecture & Limits

### Regions
- All AWS regions supported
- Region list: https://docs.aws.amazon.com/ec2/latest/instancetypes/

### Quotas
| Quota | Default | Adjustable |
|-------|---------|------------|
| Max instances per region | 20 | Yes (via quota increase) |
| Max vCPU per region | varies | Yes |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| VPC | Yes | `aws-vpc-ops` |
| Security Group | Yes | `aws-ec2-ops` |
| Key Pair | SSH access | `aws-ec2-ops` |
```