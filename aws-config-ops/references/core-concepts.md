# Core Concepts — AWS Config

## What is AWS Config

- **Purpose**: Resource inventory, configuration history tracking, compliance evaluation against rules
- **Category**: Management & Governance
- **Console**: https://console.aws.amazon.com/config/
- **Docs**: https://docs.aws.amazon.com/config/latest/developerguide/

## Primary Resources

| Resource | Description |
|----------|-------------|
| Configuration Recorder | Records configuration changes of supported AWS resources |
| Delivery Channel | Delivers config snapshots and notifications to S3/SNS |
| Config Rule | Evaluates resource configuration against desired state (managed or custom) |
| Conformance Pack | Collection of Config rules and remediation actions deployed as a group |
| Configuration Aggregator | Aggregates compliance data from multiple accounts/regions |
| Organization Config Rule | Config rule applied across all accounts in AWS Organizations |

## Architecture

### How Config Works
```
Resource Change Event → Configuration Recorder → History + Snapshot
                           ↓
                    Config Rules (Managed/Custom)
                           ↓
                    Compliance Evaluation Results
                           ↓
                    Delivery Channel → S3 + SNS
```

### Recording Modes
- **All resources**: Records all supported resource types in the region
- **Specific types**: Records only specified resource types
- **Global resources**: Records IAM users, IAM policies, etc. (needs `includeGlobalResourceTypes=true`)

## Quotas

| Quota | Default | Adjustable? |
|-------|---------|-------------|
| Config rules per region | 200 | Yes |
| Conformance packs per region | 50 | Yes |
| Conformance pack template size | 50 KB | No |
| Organization rules per region | 50 | Yes |
| Aggregator accounts per region | 500 | No |
| Max resource types per rule scope | 100 | No |
| Max evaluation results per rule | 100 | No |
| Delivery frequency | 1h / 3h / 6h / 12h / 24h | Configurable |
| Max retention period | 7 years | Configurable |

## Rule Types

| Type | Source | Use Case |
|------|--------|----------|
| Managed Rule | AWS-owned | 400+ pre-built rules (S3 public access, EC2 encryption, etc.) |
| Custom Lambda Rule | Customer Lambda | Custom logic not covered by managed rules |
| Managed Organization Rule | AWS-owned | Same as managed but applied org-wide |
| Custom Org Rule | Customer Lambda | Org-wide custom evaluation |

## Managed Rule Examples

| Identifier | Evaluates |
|------------|-----------|
| `S3_BUCKET_PUBLIC_READ_PROHIBITED` | S3 bucket public read access |
| `EC2_EBS_ENCRYPTION_BY_DEFAULT` | EBS default encryption |
| `IAM_USER_MFA_ENABLED` | IAM user MFA |
| `RDS_INSTANCE_PUBLIC_ACCESS_CHECK` | RDS public accessibility |
| `CLOUD_TRAIL_ENABLED` | CloudTrail enabled |
| `RESTRICTED_INCOMING_TRAFFIC` | Security group unrestricted access |

## Delivery Channel

| Property | Description |
|----------|-------------|
| S3 bucket | Required; stores config history and snapshots |
| S3 key prefix | Optional; organizes S3 objects |
| SNS topic | Optional; notifications for config events |
| Delivery frequency | How often snapshots are delivered (Min: 1 hour) |

## Compliance States

| State | Description |
|-------|-------------|
| COMPLIANT | Resource conforms to rule |
| NON_COMPLIANT | Resource does not conform |
| NOT_APPLICABLE | Rule does not apply to resource type |
| INSUFFICIENT_DATA | Not enough data to evaluate |
| IGNORED | Resource excluded from evaluation |

## Pricing Model

- **Configuration items**: $0.003 per configuration item recorded
- **Config rules**: $0.001 per rule per evaluation (first 10k evaluations free)
- **Conformance packs**: $0.001 per pack per evaluation
- **Aggregator**: $0.01 per account per region per day

## Best Practices

- Enable `allSupported=true` for comprehensive inventory
- Enable `includeGlobalResourceTypes=true` for IAM/OU coverage
- Start with managed rules before building custom Lambda rules
- Use conformance packs for multi-rule compliance frameworks
- Set up aggregator for multi-account visibility
- Use `select-resource-config` (SQL) for ad-hoc resource queries
- Set appropriate delivery frequency (daily for most cases)
- Tag rules with purpose for easier management