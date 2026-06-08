# GuardDuty Core Concepts

AWS GuardDuty architecture, components, and operational concepts.

## Service Overview
**AWS GuardDuty** — Intelligent threat detection service using ML, anomaly detection, and integrated threat intelligence. Monitors AWS CloudTrail, VPC Flow Logs, DNS logs, S3 data events, EKS audit logs, and RDS login activity.

## Detector
- **One per region** per account. Auto-created in new regions if enabled.
- **Status**: `ENABLED` | `DISABLED`
- **Finding publishing frequency**: `FIFTEEN_MINUTES` (default), `ONE_HOUR`, `SIX_HOURS`

## Finding Types
| Category | Examples |
|----------|----------|
| Reconnaissance | UnauthorizedAccess:EC2/SSHBruteForce, Discovery:S3/BucketEnumeration |
| Instance compromise | CryptoCurrency:EC2/BitcoinTool.B!, Trojan:EC2/BlackholeTraffic |
| Account compromise | Stealth:S3/ServerAccessLoggingDisabled, Policy:IAM/User/RootCredentialUsage |
| Bucket compromise | CryptoCurrency:S3/TorIPCaller, Exfiltration:S3/ObjectRead.Unusual |
| Kubernetes | CredentialAccess:EKS/AnomalousBehavior.ModifyPrincipal |

## Severity Levels
| Level | Range | Action |
|-------|-------|--------|
| Low | 0.1 - 3.9 | Review weekly |
| Medium | 4.0 - 6.9 | Review within 24h |
| High | 7.0 - 8.9 | Immediate response |
| Critical | 9.0 - 10.0 | Immediate + escalate |

## IP Sets & Threat Intel Sets
- **IP Set**: Trusted/untrusted IP ranges. Format: `TXT` (one IP per line)
- **Threat Intel Set**: Known malicious IPs/domains. Formats: `TXT`, `STIX`, `OTX_CSV`, `ALIEN_VAULT`, `PROOF_POINT`, `FIRE_EYE`
- **Status**: `ACTIVE` | `INACTIVE` (must be activated to take effect)
- **Location**: S3 URL (`https://s3.amazonaws.com/bucket/key.txt`)

## Filters
- **Action**: `ARCHIVE` | `NOOP`
- **Rank**: 1-100 (evaluation order)
- **FindingCriteria**: JSON with `Criterion` key (field, condition, value)

## Master / Member Accounts
- **Master**: Central account that views findings from member accounts
- **Member**: Account that shares findings with master
- **RelationshipStatus**: `Invited` | `Enabled` | `Removed` | `EmailVerificationInProgress` | `Resigned`

## Publishing Destinations
- **Type**: `S3`
- **Properties**: `DestinationArn` (S3 bucket), `KmsKeyArn` (optional)
- **Status**: `PUBLISHING` | `STOPPED` | `PENDING_VERIFICATION` | `UNABLE_TO_PUBLISH`

## Quotas
| Resource | Default Limit |
|----------|--------------|
| Detectors per region | 1 |
| IP sets per detector | 6 |
| Threat intel sets per detector | 6 |
| Filters per detector | 100 |
| Member accounts per master | 5000 |
| Publishing destinations per detector | 1 |

## Best Practices
- Enable in all active regions; use Organizations auto-enable
- Use IP sets for known trusted ranges to reduce false positives
- Integrate with EventBridge for automated response
- Archive findings only after investigation
- Use master/member for multi-account visibility
