# Cost Tracking — ELB per-LB Cost Analysis

_Lastest update: 2026-05-31_

This document defines how to track ELB cost using AWS Cost Explorer with tags.

---

## Prerequisite: Tag ALL LBs

```bash
aws elbv2 add-tags \
  --resource-arns "{{lb_arn}}" \
  --tags Key=Environment,Value={{env}} Key=Application,Value={{app}} Key=AIOps,Value=true
```

## Per-LB Cost Query

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-05-01,End=2026-05-31 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Load Balancing"]}}' \
  --group-by '[{"Type":"TAG","Key":"Environment"}]'
```

## Per-Environment Cost Breakdown

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-05-01,End=2026-05-31 \
  --granularity DAILY \
  --metrics "UnblendedCost" "UsageQuantity" \
  --group-by '[{"Type":"TAG","Key":"Application"}]'
```

## Idle LB Cost Savings Report

Use data from CO-01 idle detection + cost API:

```bash
{
  "lb_name": "staging-alb",
  "idle_days": 7,
  "estimated_monthly_cost": 18.50,
  "recommendation": "Delete or stop",
  "annual_savings": 222.00
}
```
