# Security Baseline Rules (CIS + FSBP)

> CIS AWS Foundations Benchmark v1.5.0 + AWS Foundational Security Best Practices (FSBP).
> Use with `aws configservice describe-config-rules --output json`.

## CIS AWS Foundations Benchmark (Core Rules)

### CIS 1.x — Identity and Access Management

| CIS ID | Config Rule | Description | Severity | Detection CLI |
|--------|-------------|-------------|----------|---------------|
| CIS 1.1 | `aws configservice describe-config-rules` → `vpc-default-security-group-closed` | Ensure VPC default SG blocks inbound traffic | HIGH | `aws ec2 describe-security-groups --filters Name=group-name,Values=default --query SecurityGroups[0].IpPermissions` |
| CIS 1.2 | `restricted-ssh` | Ensure SG does not allow unrestricted SSH access (0.0.0.0/0) | HIGH | `aws ec2 describe-security-groups --filters Name=ip-permission.from-port,Values=22` |
| CIS 1.3 | `multi-region-cloudtrail-enabled` | Ensure CloudTrail is enabled across all regions | HIGH | `aws cloudtrail describe-trails --query Trails[?!IsMultiRegionTrail]` |
| CIS 2.1 | `mfa-enabled-for-iam-console-access` | Ensure MFA for all users with console access | HIGH | `aws iam get-credential-report --output json --query 'Content[0]'` |
| CIS 2.2 | `iam-password-policy` | Ensure IAM password policy meets complexity requirements | MEDIUM | `aws iam get-account-password-policy --output json` |
| CIS 2.3 | `access-key-rotated` | Ensure access keys rotated within 90 days | MEDIUM | `aws iam list-access-keys --user-name <user> --query 'AccessKeyMetadata[?LastRotated<\`date -d -90days\`]'` |
| CIS 2.4 | `iam-user-mfa-enabled` | Ensure root account MFA is enabled | CRITICAL | `aws iam list-virtual-mfa-devices --query 'VirtualMFADevices[?User.UserName==\`<root>\`]'` |

### CIS 3.x — Logging

| CIS ID | Config Rule | Description | Severity | Detection CLI |
|--------|-------------|-------------|----------|---------------|
| CIS 3.1 | `cloud-trail-cloud-watch-logs-enabled` | Ensure CloudTrail logs to CloudWatch | HIGH | `aws cloudtrail get-event-selectors --trail-name <name> --query 'EventSelectors[0].CloudWatchLogsLogGroupArn'` |
| CIS 3.2 | `cloud-trail-encryption-enabled` | Ensure CloudTrail uses KMS encryption | HIGH | `aws cloudtrail describe-trails --query 'Trails[?KmsKeyId==\`null\`]` |
| CIS 3.3 | `s3-bucket-logging-enabled` | Ensure S3 access logging is enabled | MEDIUM | `aws s3api get-bucket-logging --bucket <name> --query 'LoggingEnabled'` |
| CIS 4.1 | `cloudwatch-alarm-action-check` | Ensure CloudWatch alarms have action enabled | MEDIUM | `aws cloudwatch describe-alarms --query 'MetricAlarms[?AlarmActions==\`[]\`]` |

### CIS 5.x — Networking

| CIS ID | Config Rule | Description | Severity | Detection CLI |
|--------|-------------|-------------|----------|---------------|
| CIS 5.1 | `vpc-sg-open-only-to-authorized-ports` | Ensure SG allows only authorized ports | HIGH | `aws ec2 describe-security-groups --filters Name=ip-permission.to-port,Values=443` |
| CIS 5.2 | `rds-instance-public-access-check` | Ensure RDS instances are not publicly accessible | CRITICAL | `aws rds describe-db-instances --query 'DBInstances[?PubliclyAccessible==\`true\`]'` |

### CIS 6.x — Storage

| CIS ID | Config Rule | Description | Severity | Detection CLI |
|--------|-------------|-------------|----------|---------------|
| CIS 6.1 | `s3-bucket-public-read-prohibited` | Ensure S3 buckets prohibit public read | CRITICAL | `aws s3api get-public-access-block --bucket <name> --query 'PublicAccessBlockConfiguration'` |
| CIS 6.2 | `s3-bucket-public-write-prohibited` | Ensure S3 buckets prohibit public write | CRITICAL | `aws s3api get-public-access-block --bucket <name> --query 'PublicAccessBlockConfiguration.BlockPublicPolicy==\`true\`'` |

## AWS FSBP (Foundational Security Best Practices)

| FSBP Rule | Description | Severity | Detection CLI |
|-----------|-------------|----------|---------------|
| `AUTOSCALING_ELB_HEALTH_CHECK_REQUIRED` | ASG must have ELB health checks configured | HIGH | `aws autoscaling describe-auto-scaling-groups --query 'AutoScalingGroups[?!LoadBalancerTargetGroups]'` |
| `API_GW_CERT_AND_PUBLIC_ACCESS_BLOCKED` | API Gateway must use ACM cert and block public access | HIGH | `aws apigateway get-rest-apis --query 'items[?endpointConfiguration.types==[\`EDGE\`]]'` |
| `DYNAMODB_TABLE_ENCRYPTED_KMS` | DynamoDB tables must be encrypted with KMS | HIGH | `aws dynamodb list-tables --query 'TableNames[*]' | xargs -I{} aws dynamodb describe-table --table-name {} --query 'Table[?!KMSKeyArn]'` |
| `ECR_PRIVATE_SUBNET_ONLY` | ECR must be in private subnets only | MEDIUM | `aws ecr describe-repositories --query 'repositories[?vpcEndpointConfiguration]'` |
| `ELBv2_ACM_CERTIFICATE_REQUIRED` | ALB/NLB must use ACM certificates | HIGH | `aws elbv2 describe-load-balancers --query 'LoadBalancers[?!Certificates[?CertificateArn==\`null\`]]'` |
| `RDS_STORAGE_ENCRYPTED` | RDS storage must be encrypted | HIGH | `aws rds describe-db-instances --query 'DBInstances[?StorageEncrypted==\`false\`]'` |
| `REDSHIFT_CLUSTER_ENCRYPTION` | Redshift clusters must be encrypted | HIGH | `aws redshift describe-clusters --query 'Clusters[?ClusterEncrypted==\`false\`]'` |
| `S3_BUCKET_LEVEL_PUBLIC_ACCESS_PROHIBITED` | S3 buckets must block bucket-level public access | CRITICAL | `aws s3api get-public-access-block --bucket <name> --query 'PublicAccessBlockConfiguration.BlockPublicAcls==\`true\`'` |
| `EC2_INSTANCES_IN_VPC` | EC2 instances must be in a VPC | MEDIUM | `aws ec2 describe-instances --filters Name=instance-state-name,Values=running --query 'Reservations[?Instances[?VpcId==\`null\`]]'` |
| `EBS_ENCRYPTED_BY_DEFAULT` | EBS volumes must be encrypted by default | HIGH | `aws ec2 describe-account-attributes --attribute-names `ec2-ebs-encrypted-by-default`` |

## Severity Legend

| Level | Color | Action |
|-------|-------|--------|
| CRITICAL | Red | Immediate remediation required |
| HIGH | Orange | Remediate within 24h |
| MEDIUM | Yellow | Remediate within 7 days |

## Config Rule Deployment

```bash
# Deploy all CIS rules via Conformance Pack
aws configservice put-conformance-pack \
  --conformance-pack-name cis-baseline \
  --template-body 'file://cis-conformance-pack.yaml' \
  --region us-east-1

# Check compliance
aws configservice get-conformance-pack-compliance-summary \
  --conformance-pack-name cis-baseline \
  --region us-east-1
```
