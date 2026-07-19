# SSM Automation Auto-Remediation Playbook

> AWS Config Conformance Pack + SSM Automation automatic remediation手册.
> For use with `aws ssm start-automation-execution`.

## Remediation Scenarios

### 1. S3 Public Access Block (CIS 6.1/6.2, CRITICAL)

| Field | Value |
|-------|-------|
| SSM Document | `AWS-DisableS3BucketPublicReadWrite` |
| Trigger | `S3_BUCKET_LEVEL_PUBLIC_ACCESS_PROHIBITED` non-compliant |
| Parameters | `S3BucketName` (required), `IsApplyToBucketOnExisting` (optional) |
| Human Confirm | **YES** — public access changes affect data availability |
| Reversible | Yes — `aws s3api delete-public-access-block` |
| CLI | `aws ssm start-automation-execution --document-name AWS-DisableS3BucketPublicReadWrite --parameters '{"S3BucketName":["{{bucket_name}}"]}' --region us-east-1` |

### 2. IAM Password Policy (CIS 2.2, MEDIUM)

| Field | Value |
|-------|-------|
| SSM Document | `AWSConfigRemediation-SetIAMPasswordPolicy` |
| Trigger | `iam-password-policy` non-compliant |
| Parameters | `MinimumPasswordLength` (default: 14), `RequireSymbols` (true), `RequireNumbers` (true), `RequireUppercaseCharacters` (true), `RequireLowercaseCharacters` (true), `MaxPasswordAge` (90), `PasswordReusePrevention` (24) |
| Human Confirm | No — security hardening, no user impact |
| Reversible | Yes — `aws iam update-account-password-policy` |
| CLI | `aws ssm start-automation-execution --document-name AWSConfigRemediation-SetIAMPasswordPolicy --parameters '{"MinimumPasswordLength":["14"],"RequireSymbols":["true"]}' --region us-east-1` |

### 3. CloudWatch Alarm Actions (CIS 4.1, MEDIUM)

| Field | Value |
|-------|-------|
| SSM Document | `AWSConfigRemediation-EnableCloudWatchAlarmActions` |
| Trigger | `cloudwatch-alarm-action-check` non-compliant |
| Parameters | `AlarmName` (required), `AlarmAction` (required), `TopicArn` (optional) |
| Human Confirm | **YES** — alarm action changes affect alerting behavior |
| Reversible | Yes — `aws cloudwatch put-alarm-actions` |
| CLI | `aws ssm start-automation-execution --document-name AWSConfigRemediation-EnableCloudWatchAlarmActions --parameters '{"AlarmName":["{{alarm_name}}"],"AlarmAction":["arn:aws:sns:{{region}}:{{account}}:{{topic}}"]}' --region us-east-1` |

### 4. EBS Encryption by Default (CIS, HIGH)

| Field | Value |
|-------|-------|
| SSM Document | `AWSConfigRemediation-EnableEBSEncryptionByDefault` |
| Trigger | `ebs-in-backup-plan` or `ebs-volume-inactive` non-compliant |
| Parameters | `KmsKeyId` (optional, uses default if not provided), `ApplyOrNot` (true) |
| Human Confirm | **YES** — encryption changes may affect existing volumes |
| Reversible | Yes — `aws ec2 disable-ebs-encryption-by-default` |
| CLI | `aws ssm start-automation-execution --document-name AWSConfigRemediation-EnableEBSEncryptionByDefault --parameters '{"ApplyOrNot":["true"]}' --region us-east-1` |

### 5. EBS Snapshot Public Restore Prevention (HIGH)

| Field | Value |
|-------|-------|
| SSM Document | `AWSConfigRemediation-ModifyEBSSnapshotPermission` |
| Trigger | `ebs-snapshot-public-restorable-check` non-compliant |
| Parameters | `SnapshotId` (required), `AttributeType` (createVolumePermission), `AttributeOperation` (remove) |
| Human Confirm | **YES** — snapshot sharing changes affect data access |
| Reversible | Yes — re-add permissions if needed |
| CLI | `aws ssm start-automation-execution --document-name AWSConfigRemediation-ModifyEBSSnapshotPermission --parameters '{"SnapshotId":["{{snapshot_id}}"],"AttributeOperation":["remove"]}' --region us-east-1` |

### 6. RDS Public Access (CRITICAL)

| Field | Value |
|-------|-------|
| SSM Document | `AWSConfigRemediation-ModifyRDSDBInstancePublicAccess` |
| Trigger | `rds-instance-public-access-check` non-compliant |
| Parameters | `DBInstanceIdentifier` (required), `PubliclyAccessible` (false) |
| Human Confirm | **YES** — connectivity changes affect applications |
| Reversible | Yes — set `PubliclyAccessible` to true if needed |
| CLI | `aws ssm start-automation-execution --document-name AWSConfigRemediation-ModifyRDSDBInstancePublicAccess --parameters '{"DBInstanceIdentifier":["{{db_instance}}"],"PubliclyAccessible":["false"]}' --region us-east-1` |

### 7. VPC Default Security Group (CIS 1.1, HIGH)

| Field | Value |
|-------|-------|
| SSM Document | `AWSConfigRemediation-RevokeSecurityGroupIngress` |
| Trigger | `vpc-default-security-group-closed` non-compliant |
| Parameters | `GroupId` (required), `IpPermissions` (egress-only rule) |
| Human Confirm | **YES** — SG rule changes affect connectivity |
| Reversible | Yes — re-add rules if needed |
| CLI | `aws ssm start-automation-execution --document-name AWSConfigRemediation-RevokeSecurityGroupIngress --parameters '{"GroupId":["{{sg_id}}"]}' --region us-east-1` |

## Remediation Matrix

| Scenario | SSM Document | Severity | Confirm | Reversible |
|----------|-------------|----------|---------|------------|
| S3 Public Access | `AWS-DisableS3BucketPublicReadWrite` | CRITICAL | YES | Yes |
| IAM Password Policy | `AWSConfigRemediation-SetIAMPasswordPolicy` | MEDIUM | NO | Yes |
| CloudWatch Alarm | `AWSConfigRemediation-EnableCloudWatchAlarmActions` | MEDIUM | YES | Yes |
| EBS Encryption | `AWSConfigRemediation-EnableEBSEncryptionByDefault` | HIGH | YES | Yes |
| EBS Snapshot | `AWSConfigRemediation-ModifyEBSSnapshotPermission` | HIGH | YES | Yes |
| RDS Public Access | `AWSConfigRemediation-ModifyRDSDBInstancePublicAccess` | CRITICAL | YES | Yes |
| VPC SG | `AWSConfigRemediation-RevokeSecurityGroupIngress` | HIGH | YES | Yes |

## Execution Examples

```bash
# List non-compliant resources for a conformance pack
aws configservice get-conformance-pack-compliance-details \
  --conformance-pack-name cis-baseline \
  --compliance-types NON_COMPLIANT \
  --query 'ConformancePackRuleCompliance[?ComplianceType==`NON_COMPLIANT`]' \
  --output json

# Execute remediation for S3 bucket
aws ssm start-automation-execution \
  --document-name AWS-DisableS3BucketPublicReadWrite \
  --parameters '{"S3BucketName":["my-bucket"]}'

# Check execution status
aws ssm describe-automation-executions \
  --filters "Key=DocumentName,Values=AWS-DisableS3BucketPublicReadWrite" \
  --output json
```
