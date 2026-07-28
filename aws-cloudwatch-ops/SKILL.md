---
name: aws-cloudwatch-ops
description: >-
  Use when managing CloudWatch alarms, metrics, dashboards, log groups, anomaly detection,
  logs insights, metric math, cost analysis, and observability. Invoke when user mentions
  "CloudWatch", "CW", "monitoring", "alarms", "logs", "insights", "anomaly", "metric math",
  "forecast", "dashboard", or needs AWS resource observability and alerting.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access to CloudWatch endpoints.
metadata:
  author: aws
  version: "2.5.0"
  last_updated: "2026-07-19"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
  cross_skill_deps:
    - aws-elb-ops
    - aws-ec2-ops
    - aws-vpc-ops
    - aws-route53-ops
    - aws-acm-ops
    - aws-cloudtrail-ops
    - aws-aurora-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'capacity-forecast']
    produces_facts: ['metric', 'log']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
---

# AWS CloudWatch Operations Skill

## Common JSON Paths

```
.MetricAlarms[] / .CompositeAlarms[] → AlarmName, StateValue | .Metrics[] / .MetricDataResults[] / .Datapoints[]
.DashboardEntries[].DashboardName | .logGroups[]; start-query → .queryId; get-query-results → .status, .results
.InsightRules[] / .Canaries[].{Name,Status}
```

## Trigger & Scope

### SHOULD Use When

- User mentions: "CloudWatch", "CW", metrics, alarms, monitoring, logs, dashboards, anomaly, metric math, FORECAST, Synthetics, Contributor Insights
- AIOps: elb-monitoring, elb-rca, capacity-forecast, cert-expiry

### SHOULD NOT Use When

- EC2/S3/RDS/Lambda/ASG → respective `aws-*-ops`
- ELB resource ops → `aws-elb-ops`

### Delegation

- ELB → `aws-elb-ops`
- Certs → `aws-acm-ops`
- VPC Flow → `aws-vpc-ops`
- Patrol/Orch → `aws-aiops-cruise` / `aws-aiops-orchestrator`

## Variable Convention

| Placeholder | Source | Action |
|-------------|--------|--------|
| `{{env.AWS_ACCESS_KEY_ID}}` / `{{env.AWS_SECRET_ACCESS_KEY}}` | Env | NEVER ask; fail if unset |
| `{{env.AWS_SESSION_TOKEN}}` | Env | STS temp creds only |
| `{{env.AWS_DEFAULT_REGION}}` / `{{env.AWS_PROFILE}}` | Env | Region/profile |
| `{{user.region}}` | User/env | Default `us-east-1` |
| `{{user.alarm}}` / `{{user.ns}}` / `{{user.metric}}` | User | Alarm/metric identifiers |
| `{{user.log}}` / `{{user.dash}}` | User | Log group / dashboard name |
| `{{output.qid}}` / `{{output.*}}` | API response | `.queryId` / parse per JSON paths above |

## Execution Flow Pattern

**Pre-flight → Execute CLI/SDK → Validate → Recover on Error**

## Operations Index

See [operation-index.md](references/operation-index.md) for the full routing table.
Per-category: [aws-cli-usage.md](references/aws-cli-usage.md) (alarms/metrics/logs/synthetics) ·
[predictive-operations.md](references/predictive-operations.md) (capacity-forecast) ·
[aiops-scenarios.md](references/aiops-scenarios.md) (RCA / cert expiry / auto-heal).

## Cross-Skill References

`aws-aiops-cruise` · `aws-aiops-orchestrator` (capacity-forecast) · `aws-ec2-ops` / `aws-rds-ops` (metric source) · `aws-elb-ops` (ELB metrics) · `aws-acm-ops` (certs) · `aws-vpc-ops` (flow logs) · `aws-cloudtrail-ops` (audit).

## Token Efficiency (TE-1…TE-6)

TE-1 API > hardcoded tables · TE-2 no boto3 docstrings · TE-3 compact error tables · TE-4 JSON paths in header · TE-5 YAML anchors · TE-6 detail in references/.

## Safety Gates

`delete-alarms` · `delete-dashboards` · `delete-insight-rules` · `delete-canary` · `put-retention-policy` — all require explicit human confirmation with name + impact (destructive / irreversible).

## Reference Files

[Prompt Examples](references/prompt-examples.md) · [Operation Index](references/operation-index.md) · [AWS CLI](references/aws-cli-usage.md) · [boto3](references/boto3-sdk-usage.md) · [Core Concepts](references/core-concepts.md) · [Troubleshooting](references/troubleshooting.md) · [ELB Templates](references/elb-monitoring-templates.md) · [AIOps Scenarios](references/aiops-scenarios.md) · [Layered Inspection](references/layered-inspection-template.md) · [GCL Rubric](references/rubric.md) · [GCL Prompts](references/prompt-templates.md)

## Quality Gate (GCL) & AIOps Delegate

GCL `recommended` max_iter=3 · rubric/prompts in references/ · trace `audit-results/gcl-trace-*.json` · destructive: `delete-alarms|insight-rules|dashboards|canary`, `put-retention-policy` (Rules A7–A10). Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate` block, 24h idempotency_key, destructive requires `confirmation_token`, propagate `trace_id` in User-Agent, emit `aiops_context` JSON. See [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md) for runbooks. CADL per root AGENTS.md.
