# Security Hub Core Concepts

AWS Security Hub architecture, components, and operational concepts.

## Service Overview
**AWS Security Hub** — Centralized security and compliance view. Aggregates findings from AWS services (GuardDuty, Inspector, Macie, etc.) and partner products. Provides security standards (CIS, PCI DSS, NIST) and automated compliance checks.

## Architecture

```
AWS Services / Partner Products
  ├─ GuardDuty → findings
  ├─ Inspector → findings
  ├─ Macie → findings
  ├─ Config → compliance
  ├─ Firewall Manager → findings
  └─ 3rd Party → findings
         │
         ▼
   Security Hub (aggregator)
         │
    ┌────┴────┐
    ▼         ▼
 Insights  Action Targets
    │         │
    ▼         ▼
 Dashboard  EventBridge → SNS/Auto-remediation
```

## Hub
- One hub per region per account
- `SubscribedAt` — timestamp when enabled
- `AutoEnableControls` — auto-enable new controls when standards added
- Organization admin account can manage member accounts

## Security Standards
| Standard | ARN Pattern | Controls |
|----------|-------------|----------|
| CIS AWS Foundations | `arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0` | ~50 |
| PCI DSS | `arn:aws:securityhub:::ruleset/pci-dss/v/3.2.1` | ~40 |
| NIST SP 800-53 | `arn:aws:securityhub:::ruleset/nist-800-53/v/5.0.0` | ~50 |
| AWS Foundational Security Best Practices | `arn:aws:securityhub:::ruleset/aws-foundational-security-best-practices/v/1.0.0` | ~200 |

Check available standards:
```bash
aws securityhub describe-standards --region {{user.region}}
```

## Controls
- Each standard contains controls (e.g. `CIS.1.1`, `S3.1`)
- Status: `ENABLED` | `DISABLED`
- Compliance: `PASSED` | `FAILED` | `WARNING` | `NOT_AVAILABLE`
- Can be disabled with reason (e.g. "Not applicable — no S3 buckets")

## Findings
- **SchemaVersion**: `2018-10-08`
- **Severity**: `INFORMATIONAL` | `LOW` | `MEDIUM` | `HIGH` | `CRITICAL`
- **Workflow.Status**: `NEW` | `NOTIFIED` | `SUPPRESSED` | `RESOLVED`
- **RecordState**: `ACTIVE` | `ARCHIVED`
- **Compliance.Status**: `PASSED` | `FAILED` | `WARNING` | `NOT_AVAILABLE`

## Insights
- Saved filter queries with grouping
- `GroupByAttribute`: `ResourceId`, `Type`, `AwsAccountId`, etc.
- Used for dashboard widgets and monitoring

## Action Targets
- Custom response targets for findings
- ARN format: `arn:aws:securityhub:{{region}}:{{account}}:action/custom/{{name}}/{{id}}`
- Typically mapped to EventBridge rules or Lambda functions

## Automation Rules
- Auto-triage findings based on criteria
- `RuleOrder`: lower = higher priority (evaluated first)
- `RuleStatus`: `ENABLED` | `DISABLED`
- Actions: `FINDING_FIELDS_UPDATE` (severity, workflow, note)

## Configuration Policy (Organizations)
- Central policy for multi-account Security Hub setup
- Defines: service enabled/disabled, standards, controls
- Applied at Organization root, OU, or account level
- Admin account manages policies; member accounts inherit

## Quotas
| Resource | Default Limit |
|----------|--------------|
| Insights per region | 100 |
| Action targets per region | 100 |
| Automation rules per region | 100 |
| Batch import findings per call | 100 |
| Batch update findings per call | 100 |
| GetFindings max results | 100 |

## Pricing
- First 10,000 findings/month free per region
- Beyond 10,000: ~$0.001 per finding
- No charge for standards, controls, or insights

## Best Practices
- Enable in all regions where resources exist
- Use Organizations for centralized management
- Set up automation rules for common triage patterns
- Archive resolved findings to reduce noise
- Disable controls that are not applicable with documented reason
- Use EventBridge for automated response workflows
