# Tag Compliance Reference

## Required Tags

| Tag Key | Description | Example |
|---|---|---|
| `Environment` | Deployment environment | `prod`, `staging`, `dev` |
| `Application` | Application or service name | `order-service`, `data-pipeline` |
| `Owner` | Team or individual responsible | `platform-team`, `user@example.com` |
| `CostCenter` | Cost allocation unit | `CC-001`, `finance` |

## Query Tag Coverage via Cost Explorer

```bash
# Group costs by Environment tag
aws ce get-cost-and-usage \
  --time-period Start={{start_date}},End={{end_date}} \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Environment \
  --output json

# Multi-tag grouping
aws ce get-cost-and-usage \
  --time-period Start={{start_date}},End={{end_date}} \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by '[{"Type":"TAG","Key":"Environment"},{"Type":"TAG","Key":"Application"}]' \
  --output json
```

## Compliance Rate Formula

```
compliance_rate = (resources_with_all_required_tags / total_tagged_resources) × 100%
```

Where:
- **total_tagged_resources**: resources with at least one tag in Cost Explorer
- **resources_with_all_required_tags**: resources that have all 4 required tags

## Compliance Thresholds

| Level | Threshold | Action |
|---|---|---|
| OK | ≥ 80% | No action needed |
| WARNING | 60% – 79% | Send tag compliance report to team leads |
| CRITICAL | < 60% | Block new resource creation until compliance improves |

## Tag Audit via Resource Groups

```bash
# List all tag-based resource groups
aws resourcegroupstaggingapi get-resources \
  --resource-type-filters ec2:instance,ec2:volume,rds:db \
  --tag-filters Key=Environment,Values=prod \
  --output json

# Find untagged resources (resources without required tags)
aws resourcegroupstaggingapi get-resources \
  --resource-type-filters ec2:instance \
  --output json | jq '.ResourceTagMappingList[] | select(.Tags | length < 4)'
```
