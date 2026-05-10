# Secrets Manager Core Concepts

AWS Secrets Manager architecture, components, and operational concepts.

## Service Overview

**AWS Secrets Manager** - Service for securely storing and managing secrets.

**Key Benefits:**
- Automatic rotation
- Encryption at rest (KMS)
- Fine-grained access control
- Audit logging (CloudTrail)
- Cross-region replication
- No hardcoded credentials

## Secret Types

### Database Credentials
- Username/password pairs
- Connection strings
- Automatic rotation support

### API Keys
- Third-party API keys
- OAuth tokens
- Service credentials

### Application Secrets
- Encryption keys
- Signing keys
- Configuration secrets

## Rotation

### Automatic Rotation
- **Frequency**: Configurable (default 30 days)
- **Mechanism**: Lambda function
- **Process**: Generate new secret → Update application → Archive old version

### Rotation Lambda
AWS provides templates for common databases:
- Amazon RDS (MySQL, PostgreSQL, Aurora)
- Amazon DocumentDB
- Amazon Redshift
- Other databases

## Secret Versions

### Version Stages
- **AWSCURRENT**: Current active version
- **AWSPENDING**: Pending rotation
- **AWSPREVIOUS**: Previous version
- Custom stages

### Versioning
- Multiple versions per secret
- Automatic versioning on update
- Previous versions retained

## Replication

### Primary-Replica
- Primary secret in one region
- Replicas in other regions
- Automatic synchronization
- Independent KMS keys per region

## Quotas

| Resource | Default | Notes |
|----------|---------|-------|
| Secrets per region | 40,000 | - |
| Versions per secret | 100 | - |
| Secret size | 65,536 bytes | - |
| Rotation functions | 1 per secret | - |

## Pricing

- **Secret storage**: $0.40 per secret per month
- **API calls**: $0.05 per 10,000 requests
- **Cross-region replication**: Standard charges apply

## Best Practices

### Security
- Use automatic rotation
- Enable deletion recovery
- Restrict access with IAM policies
- Monitor with CloudTrail

### Operations
- Tag secrets by application/environment
- Use descriptive names
- Test rotation regularly
- Document secret usage

### Cost
- Delete unused secrets
- Archive old versions
- Use Parameter Store for non-sensitive data