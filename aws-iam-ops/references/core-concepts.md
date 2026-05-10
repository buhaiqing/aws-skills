# Core Concepts — IAM

## What is AWS IAM

- **Purpose**: Identity and Access Management — control who can access AWS resources
- **Category**: Security, Identity & Compliance
- **Console**: https://console.aws.amazon.com/iam/
- **Docs**: https://docs.aws.amazon.com/IAM/latest/UserGuide/

## Primary Resources

| Resource | Description | Console Path |
|----------|-------------|--------------|
| User | Identity for people/applications | /iam/home#/users |
| Group | Collection of users | /iam/home#/groups |
| Role | Identity for AWS services/federation | /iam/home#/roles |
| Policy | Permission document | /iam/home#/policies |
| Access Key | Credential for programmatic access | User → Security credentials |

## IAM Components

### Authentication (Who)
| Type | Description | Use Case |
|------|-------------|----------|
| User | Long-term identity | Humans, long-lived applications |
| Role | Temporary identity | AWS services, cross-account, federation |
| Access Key | Programmatic credential | CLI, SDK, API access |

### Authorization (What)
| Type | Description | Use Case |
|------|-------------|----------|
| Identity-based policy | Attached to user/group/role | Grant permissions to identity |
| Resource-based policy | Attached to resource (S3, Lambda) | Grant access to resource |

## Policy Types

| Type | Scope | Reusable |
|------|-------|----------|
| AWS Managed | Pre-built by AWS | Yes |
| Customer Managed | Custom reusable | Yes |
| Inline | Embedded in single identity | No |

## Policy Structure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OptionalStatementId",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::bucket", "arn:aws:s3:::bucket/*"],
      "Condition": {
        "StringEquals": {"aws:PrincipalOrg": "o-123456"}
      }
    }
  ]
}
```

## Trust Policy (Role)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Common Trust Policy Principals

| Principal | Use Case |
|-----------|----------|
| `{"Service": "ec2.amazonaws.com"}` | EC2 instances |
| `{"Service": "lambda.amazonaws.com"}` | Lambda functions |
| `{"Service": "s3.amazonaws.com"}` | S3 bucket replication |
| `{"AWS": "arn:aws:iam::123:root"}` | Cross-account access |
| `{"Federated": "arn:aws:iam::...:saml-provider/..."}` | SAML federation |

## Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Users per account | 5000 | Yes |
| Groups per account | 300 | Yes |
| Roles per account | 1000 | Yes |
| Policies per account | 1500 | Yes |
| Access keys per user | 2 | No |
| Groups per user | 10 | Yes |
| Policies per identity | 10 managed + 20 inline | No |

## Entity Naming Rules

| Entity | Max Length | Allowed Characters |
|--------|------------|-------------------|
| User name | 64 | Letters, digits, +, =, ., @, -, _ |
| Group name | 128 | Letters, digits, +, =, ., @, -, _ |
| Role name | 64 | Letters, digits, +, =, ., @, -, _ |
| Policy name | 128 | Letters, digits, +, =, ., @, -, _ |

## Path Convention

Paths organize entities hierarchically:
- Default: `/`
- Custom: `/department/engineers/`
- Used for grouping and permission boundaries

## Eventual Consistency

IAM changes propagate globally within **seconds to minutes**:
- Create/update/delete operations may take time
- Verify changes before production workflows depend on them
- Do NOT include IAM changes in critical, high-availability code paths

## Best Practices

### Security
- Use IAM roles instead of users for applications
- Least privilege: grant minimum required permissions
- Rotate access keys regularly
- Enable MFA for console users
- Use IAM Access Analyzer for policy validation

### Organization
- Use groups for permission management
- Avoid inline policies (use managed policies)
- Use permission boundaries for delegation
- Naming convention: `org-project-role-name`

### Cost
- IAM is free (no charge for users, roles, policies)
- Only charged for STS AssumeRole calls
- IAM Access Analyzer has charges for unused access analysis