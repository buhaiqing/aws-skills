# Finding Priority Matrix

> ≥10 common finding types with Source, Severity, and Auto-Remediation routing.
> CRITICAL findings → HALT + alert (no auto-remediation).
> See also: [`playbook-routes.md`](playbook-routes.md), [`incident-schema.md`](incident-schema.md).

| # | Finding Type | Source | Severity | Auto-Remediation | Notes |
|---|-------------|--------|----------|-----------------|-------|
| 1 | Exposed credentials (API key / access key in plaintext) | GuardDuty | **CRITICAL** | **HALT + alert** | Immediate notification required; rotate key via `aws-iam-ops rotate-access-key` after user confirm |
| 2 | Port 22 (SSH) or 3389 (RDP) open to 0.0.0.0/0 | Config | HIGH | `aws-vpc-ops restrict-sg` | Restrict SG ingress to known IP ranges |
| 3 | IAM policy with `*` principal (overly permissive) | IAM Access Analyzer | HIGH | `aws-iam-ops restrict-policy` | Narrow to specific principals/arns |
| 4 | Unencrypted EBS volume | Config | HIGH | `aws-ec2-ops enable-encryption` | Enable EBS encryption by default |
| 5 | GuardDuty CryptoCurrency mining | GuardDuty | **CRITICAL** | **HALT + isolate** | Isolate instance immediately; user confirm before terminate |
| 6 | IAM MFA disabled for console users | IAM Access Analyzer | HIGH | `aws-iam-ops enforce-mfa` | Enable MFA via IAM console |
| 7 | Secrets older than 90 days (no rotation) | Secrets Manager | MEDIUM | `aws-secretsmanager-ops rotate-secret` | Rotate and update dependent services |
| 8 | S3 bucket public access (ACL or policy) | Config | **CRITICAL** | `aws-s3-ops remove-public` | Block public access via bucket settings |
| 9 | RDS instance publicly accessible | Config | HIGH | `aws-rds-ops disable-public-access` | Set `PubliclyAccessible=false` |
| 10 | Lambda function with public access | Config | MEDIUM | `aws-lambda-ops restrict-permissions` | Remove public invoke URL |
| 11 | KMS key rotation disabled | KMS | MEDIUM | `aws-kms-ops enable-rotation` | Enable annual automatic rotation |
| 12 | GuardDuty Backdoor:EC2/S3 | GuardDuty | **CRITICAL** | **HALT + alert** | Possible compromised resource; isolate + investigate |
| 13 | CloudTrail not recording multi-region | Config | MEDIUM | `aws-cloudtrail-ops enable-multi-region` | Enable multi-region trail for audit |
| 14 | EBS volume not encrypted | Config | HIGH | `aws-ec2-ops enable-encryption` | Enable encryption by default |
| 15 | Security group allows all traffic (0.0.0.0/0 all ports) | Config | HIGH | `aws-vpc-ops restrict-sg` | Restrict to minimum required ports |

## Severity Definitions

| Level | Description | Behavior |
|-------|-------------|----------|
| CRITICAL | Active breach, exposed credentials, active crypto-mining | **HALT** — alert immediately, require explicit user confirmation before any action |
| HIGH | Significant misconfiguration, high risk | Delegate to base skill remediation; require user confirmation |
| MEDIUM | Moderate risk, best-practice violation | Log and route; auto-remediate if user pre-approved |
| LOW | Informational, minor drift | Log only; no immediate action required |

## Severity Triage Flow

```
finding.severity
  ├── CRITICAL → HALT → notify_user → await user confirm
  ├── HIGH     → log → require confirm → delegate to base skill
  ├── MEDIUM   → log → route → auto-remediate if pre-approved
  └── LOW      → log only
```

## Finding Type ID Mapping

| ID | Short Code | Full Name |
|----|-----------|-----------|
| F01 | CRED-EXPOSED | Exposed credentials |
| F02 | NET-OPEN-PORT | Open port to 0.0.0.0/0 |
| F03 | IAM-WILD-PRINCIPAL | Wildcard principal policy |
| F04 | VOL-UNENCRYPTED | Unencrypted volume |
| F05 | CRYPTO-MINING | Cryptocurrency mining |
| F06 | IAM-MFA-DISABLED | MFA disabled |
| F07 | SEC-OLD-SECRET | Secret not rotated |
| F08 | S3-PUBLIC | S3 public access |
| F09 | RDS-PUBLIC | RDS publicly accessible |
| F10 | LAMBDA-PUBLIC | Lambda public access |
| F11 | KMS-NO-ROTATION | KMS rotation disabled |
| F12 | BD-EC2-S3 | Backdoor EC2/S3 |
| F13 | CT-NO-MULTI | CloudTrail not multi-region |
| F14 | VOL-UNENCRYPTED | Unencrypted EBS |
| F15 | SG-ALL-TRAFFIC | Security group all traffic |
