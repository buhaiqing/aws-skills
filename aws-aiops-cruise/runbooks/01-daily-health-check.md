---
runbook_id: "01"
scenario: "Daily health check"
version: "1.0.0"
last_updated: "2026-06-13"
trigger: "Schedule (every 6h) / manual"
risk_level: "low"
execution_time_estimate: "5-15 min (< 50 resources)"
---

> **Script**: [`runbooks/scripts/daily-health-check.py`](../scripts/daily-health-check.py)

# Daily Health Check

## 1. Purpose

Patrol core chain resources for a scoped workload: **EIP → ALB/NLB → EC2 → RDS/ElastiCache → NAT Gateway → Security Groups**. Output health score + standardized incidents.

### Read-only policy

No create/modify/delete/stop. Recommendations only; execution via delegated `aws-*-ops` after user confirmation.

## 2. Pre-flight

```bash
aws sts get-caller-identity --output json
command -v jq >/dev/null || exit 1
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
SCOPE="{{user.resource_group}}"  # or tag {{user.tag_key}}/{{user.tag_value}}
```

HALT if credentials missing or `sts` fails.

## 3. Execution

### Phase 1 — Scope + inventory

```bash
# Resource Group (preferred)
aws resource-groups list-group-resources \
  --group-name "$SCOPE" --output json

# Or tag scope
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key="{{user.tag_key}}",Values="{{user.tag_value}}" \
  --output json
```

Enrich with service describes (parallel):

```bash
aws ec2 describe-instances --region "$REGION" --output json
aws elbv2 describe-load-balancers --region "$REGION" --output json
aws rds describe-db-instances --region "$REGION" --output json
aws elasticache describe-cache-clusters --region "$REGION" --output json
aws ec2 describe-nat-gateways --region "$REGION" --output json
aws ec2 describe-addresses --region "$REGION" --output json
```

Filter to in-scope ARNs/IDs from Phase 1.

### Phase 2 — Metrics (6h window, 5-min period)

Example EC2 CPU:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --start-time "$(date -u -v-6H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 300 --statistics Average Maximum \
  --output json
```

Key metrics — see [`references/threshold-definitions.md`](../references/threshold-definitions.md).

| Layer | Namespace | Metrics |
|-------|-----------|---------|
| EC2 | AWS/EC2 | CPUUtilization, StatusCheckFailed |
| ALB | AWS/ApplicationELB | UnHealthyHostCount, TargetResponseTime, HTTPCode_Target_5XX_Count |
| RDS | AWS/RDS | CPUUtilization, DatabaseConnections, FreeStorageSpace |
| ElastiCache | AWS/ElastiCache | CPUUtilization, DatabaseMemoryUsagePercentage |
| NAT | AWS/NATGateway | ActiveConnectionCount, ErrorPortAllocation |

### Phase 3 — Inference + report

Apply rules from [`references/inference-rules.md`](../references/inference-rules.md). Emit:

- Markdown summary → `audit-results/cruise-<run_id>.md`
- JSON incidents → `audit-results/cruise-<run_id>.json`

## 4. Automated run

```bash
python3 runbooks/scripts/daily-health-check.py \
  --resource-group prod-web-rg \
  --region us-east-1 \
  --non-interactive
```

Or tag scope:

```bash
python3 runbooks/scripts/daily-health-check.py \
  --tag-key Environment --tag-value production \
  --region us-east-1
```

## 5. Validate

- `overall_grade` in `{PASS, WARNING, CRITICAL, ERROR}`
- Every incident has `level`, `rule_id`, `dedup_key`
- First command in trace: `aws sts get-caller-identity`

## 6. Recover

| Error | Action |
|-------|--------|
| AccessDenied | HALT; list missing IAM actions |
| Throttling | Backoff 3× |
| Empty scope | HALT; ask user to fix RG/tag |
