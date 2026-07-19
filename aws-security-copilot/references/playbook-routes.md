# Playbook Routes

> Each finding type maps to the base ops skill + operation for remediation.
> CRITICAL findings → HALT before any remediation.
> See also: [`findings-matrix.md`](findings-matrix.md), [`incident-schema.md`](incident-schema.md).

## Finding → Remediation Routing Table

| Finding Type | Finding ID | Severity | Delegate Skill | Remediation Action | Confirmation Required |
|-------------|-----------|----------|----------------|-------------------|---------------------|
| Exposed credentials | F01-CRED-EXPOSED | CRITICAL | `aws-iam-ops` | `rotate-access-key` | **HALT + alert** |
| Port 22/3389 open to 0.0.0.0/0 | F02-NET-OPEN-PORT | HIGH | `aws-vpc-ops` | `restrict-sg` | Yes |
| Policy with `*` principal | F03-IAM-WILD-PRINCIPAL | HIGH | `aws-iam-ops` | `restrict-policy` | Yes |
| Unencrypted EBS volume | F04-VOL-UNENCRYPTED | HIGH | `aws-ec2-ops` | `enable-encryption` | Yes |
| GuardDuty CryptoCurrency | F05-CRYPTO-MINING | CRITICAL | `aws-ec2-ops` | `isolate-instance` | **HALT + isolate** |
| IAM MFA disabled | F06-IAM-MFA-DISABLED | HIGH | `aws-iam-ops` | `enforce-mfa` | Yes |
| Secrets > 90 days | F07-SEC-OLD-SECRET | MEDIUM | `aws-secretsmanager-ops` | `rotate-secret` | Pre-approved |
| S3 public access | F08-S3-PUBLIC | CRITICAL | `aws-s3-ops` | `remove-public` | **HALT + alert** |
| RDS publicly accessible | F09-RDS-PUBLIC | HIGH | `aws-rds-ops` | `disable-public-access` | Yes |
| Lambda public access | F10-LAMBDA-PUBLIC | MEDIUM | `aws-lambda-ops` | `restrict-permissions` | Pre-approved |
| KMS rotation disabled | F11-KMS-NO-ROTATION | MEDIUM | `aws-kms-ops` | `enable-rotation` | Pre-approved |
| GuardDuty Backdoor | F12-BD-EC2-S3 | CRITICAL | `aws-ec2-ops` | `investigate` | **HALT + alert** |
| CloudTrail not multi-region | F13-CT-NO-MULTI | MEDIUM | `aws-cloudtrail-ops` | `enable-multi-region` | Pre-approved |
| EBS volume not encrypted | F14-VOL-UNENCRYPTED | HIGH | `aws-ec2-ops` | `enable-encryption` | Yes |
| SG allows all traffic | F15-SG-ALL-TRAFFIC | HIGH | `aws-vpc-ops` | `restrict-sg` | Yes |

## HALT Scenarios (CRITICAL — stop immediately)

| Scenario | Immediate Action | Next Step |
|----------|-----------------|-----------|
| F01: Exposed credentials | `notify_user()` with finding details | Await user confirm → `aws-iam-ops rotate-access-key` |
| F05: CryptoCurrency mining | `notify_user()` + isolate instance | Await user confirm → `aws-ec2-ops terminate` |
| F08: S3 public access | `notify_user()` + block public access setting | Await user confirm → `aws-s3-ops remove-public` |
| F12: Backdoor EC2/S3 | `notify_user()` + log CloudTrail events | Await user confirm → `aws-ec2-ops investigate` |

## Confirmation Patterns

| Severity | Pattern | Example |
|----------|---------|---------|
| CRITICAL (HALT) | `confirm=HALT <finding-id>` | `confirm=HALT F01-CRED-EXPOSED` |
| HIGH | `confirm=<action> <resource-id>` | `confirm=restrict-sg sg-0123456789abcdef0` |
| MEDIUM | Pre-approved playbook | No explicit confirm needed |
| LOW | Log only | No action required |
