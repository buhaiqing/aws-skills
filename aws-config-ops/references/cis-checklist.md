# CIS AWS Foundations Benchmark v1.5.0 Checklist

> Manual verification checklist + AWS Config automated rule mapping.
> Run `aws configservice describe-config-rules --output json` to verify rules deployed.

## 1. Identity and Access Management

- [ ] **CIS 1.1** — VPC Default Security Group restricts all traffic
  - Console: VPC → Security Groups → default SG → Inbound/Outbound Rules
  - Config: `vpc-default-security-group-closed`
  - CLI: `aws ec2 describe-security-groups --filters Name=group-name,Values=default --query 'SecurityGroups[0].IpPermissions'`

- [ ] **CIS 1.2** — No security group allows unrestricted SSH (0.0.0.0/0:22)
  - Console: EC2 → Security Groups → check inbound rules
  - Config: `restricted-ssh`
  - CLI: `aws ec2 describe-security-groups --filters Name=ip-permission.from-port,Values=22 --query 'SecurityGroups[?IpPermissions[?FromPort==\`22\` && IpRanges[?CidrIp==\`0.0.0.0/0\`]]]'`

- [ ] **CIS 1.3** — AWS Config enabled in all regions
  - Console: AWS Config → Settings → recording is on
  - Config: `multi-region-cloudtrail-enabled`
  - CLI: `aws configservice describe-configuration-recorders --query 'ConfigurationRecorders[0].name'`

- [ ] **CIS 2.1** — MFA enabled for console users
  - Console: IAM → Users → MFA column
  - Config: `mfa-enabled-for-iam-console-access`
  - CLI: `aws iam get-credential-report --output json --query 'Content' | base64 -d | csvtool col 8 -`

- [ ] **CIS 2.2** — IAM password policy meets complexity requirements
  - Console: IAM → Account Settings → Password Policy
  - Config: `iam-password-policy`
  - CLI: `aws iam get-account-password-policy --output json`

- [ ] **CIS 2.3** — Access keys rotated within 90 days
  - Console: IAM → Users → Security Credentials → Access keys
  - Config: `access-key-rotated`
  - CLI: `aws iam list-access-keys --user-name <user> --query 'AccessKeyMetadata[*].{UserName:UserName,AccessKeyId:AccessKeyId,LastRotated:LastRotated}'`

- [ ] **CIS 2.4** — MFA enabled for root account
  - Console: IAM → Dashboard → Activate MFA on root account
  - Config: `iam-user-mfa-enabled`
  - CLI: `aws iam list-virtual-mfa-devices --query 'VirtualMFADevices[?User.UserName==\`<root>\`]'`

## 2. Logging

- [ ] **CIS 3.1** — CloudTrail enabled across all regions
  - Console: CloudTrail → Trails → Multi-region trail enabled
  - Config: `multi-region-cloudtrail-enabled`
  - CLI: `aws cloudtrail describe-trails --query 'Trails[?IsMultiRegionTrail==\`true\`]'`

- [ ] **CIS 3.2** — CloudTrail logs to CloudWatch Logs
  - Console: CloudTrail → Trails → CloudWatch Logs configured
  - Config: `cloud-trail-cloud-watch-logs-enabled`
  - CLI: `aws cloudtrail get-event-selectors --trail-name <name> --query 'EventSelectors[0].CloudWatchLogsLogGroupArn'`

- [ ] **CIS 3.3** — CloudTrail uses KMS encryption
  - Console: CloudTrail → Trails → Encrypt with KMS
  - Config: `cloud-trail-encryption-enabled`
  - CLI: `aws cloudtrail describe-trails --query 'Trails[?KmsKeyId==\`null\`]'`

- [ ] **CIS 3.4** — S3 bucket access logging enabled
  - Console: S3 → Bucket → Properties → Server access logging
  - Config: `s3-bucket-logging-enabled`
  - CLI: `aws s3api get-bucket-logging --bucket <name> --query 'LoggingEnabled'`

## 3. Networking

- [ ] **CIS 4.1** — CloudWatch alarms have actions enabled
  - Console: CloudWatch → Alarms → Actions tab
  - Config: `cloudwatch-alarm-action-check`
  - CLI: `aws cloudwatch describe-alarms --query 'MetricAlarms[?AlarmActions==\`[]\` || SNSTopicArns==\`[]\`]'`

- [ ] **CIS 4.2** — VPC flow logs enabled
  - Console: VPC → Your VPCs → Flow Logs
  - Config: `vpc-flow-logs-enabled`
  - CLI: `aws ec2 describe-flow-logs --query 'FlowLogs[?LogDestinationType==\`cloud-watch-logs\`]'`

## 4. Storage

- [ ] **CIS 5.1** — S3 bucket public read prohibited
  - Console: S3 → Bucket → Permissions → Block public access
  - Config: `s3-bucket-public-read-prohibited`
  - CLI: `aws s3api get-public-access-block --bucket <name> --query 'PublicAccessBlockConfiguration.BlockPublicReadAcls'`

- [ ] **CIS 5.2** — S3 bucket public write prohibited
  - Console: S3 → Bucket → Permissions → Block public access
  - Config: `s3-bucket-public-write-prohibited`
  - CLI: `aws s3api get-public-access-block --bucket <name> --query 'PublicAccessBlockConfiguration.BlockPublicPolicy'`

- [ ] **CIS 5.3** — EBS volumes encrypted
  - Console: EC2 → Volumes → Encrypted column
  - Config: `ebs-encryption-enabled`
  - CLI: `aws ec2 describe-volumes --filters Name=encrypted,Values=false --query 'Volumes[?Encrypted==\`false\`]'`

## 5. Database

- [ ] **CIS 6.1** — RDS instances not publicly accessible
  - Console: RDS → Instances → Publicly Accessible column
  - Config: `rds-instance-public-access-check`
  - CLI: `aws rds describe-db-instances --query 'DBInstances[?PubliclyAccessible==\`true\`]'`

- [ ] **CIS 6.2** — RDS storage encrypted
  - Console: RDS → Instances → Storage column
  - Config: `rds-storage-encrypted`
  - CLI: `aws rds describe-db-instances --query 'DBInstances[?StorageEncrypted==\`false\`]'`

## Compliance Summary

| Category | Total | Pass | Fail | Coverage |
|----------|-------|------|------|----------|
| Identity (1.x-2.x) | 7 | | | |
| Logging (3.x) | 4 | | | |
| Networking (4.x) | 2 | | | |
| Storage (5.x) | 3 | | | |
| Database (6.x) | 2 | | | |
| **Total** | **18** | | | |

## Run Full Audit

```bash
# Deploy CIS Conformance Pack
aws configservice put-conformance-pack \
  --conformance-pack-name cis-benchmark \
  --template-body 'file://cis-conformance-pack.yaml'

# Get compliance summary
aws configservice get-conformance-pack-compliance-summary \
  --conformance-pack-name cis-benchmark \
  --output json

# Get detailed non-compliant resources
aws configservice get-conformance-pack-compliance-details \
  --conformance-pack-name cis-benchmark \
  --compliance-types NON_COMPLIANT \
  --query 'ConformancePackRuleCompliance[?ComplianceType==`NON_COMPLIANT`]'
```
