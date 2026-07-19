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
  orchestrator_compat: ">=0.1.0"
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

**SHOULD Use When**: "CloudWatch", "CW", metrics, alarms, monitoring, logs, dashboards, anomaly, metric math, FORECAST, Synthetics, Contributor Insights; AIOps: elb-monitoring, elb-rca, capacity-forecast, cert-expiry. **SHOULD NOT Use When**: EC2/S3/RDS/Lambda/ASG → respective `aws-*-ops`; ELB resource ops → `aws-elb-ops`. **Delegation**: ELB → `aws-elb-ops` | Certs → `aws-acm-ops` | VPC Flow → `aws-vpc-ops` | Patrol/Orch → `aws-aiops-cruise` / `aws-aiops-orchestrator`.

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

All operation details (CLI + boto3 + validate + recover tables):

| Category | Reference |
|----------|-----------|
| Alarms: create/describe/delete, composite, anomaly detection | [aws-cli-usage.md](references/aws-cli-usage.md) |
| Metrics: list, get-statistics, get-data, put-custom | [aws-cli-usage.md](references/aws-cli-usage.md) |
| Logs: Insights query, Contributor Insights, dashboards, retention | [aws-cli-usage.md](references/aws-cli-usage.md) |
| Synthetics: canary create/delete/diagnose | [aws-cli-usage.md](references/aws-cli-usage.md) |
| **Predictive: capacity-forecast, FORECAST trend** | [predictive-operations.md](references/predictive-operations.md) |
| **AIOps: cost RCA, cert expiry, three-layer inspection, auto-heal, ELB templates** | [aiops-scenarios.md](references/aiops-scenarios.md) |

Full routing table: [operation-index.md](references/operation-index.md)

## Cross-Skill References

`aws-aiops-cruise` → calls `get-capacity-forecast` | `aws-aiops-orchestrator` → delegates capacity-forecast | `aws-ec2-ops` / `aws-rds-ops` → metric source

## Token Efficiency (TE-1…TE-6)

TE-1: API commands > hardcoded tables. TE-2: No docstrings in boto3. TE-3: Compact error tables. TE-4: JSON paths declared once at top. TE-5: YAML anchors in `assets/example-config.yaml`. TE-6: All operation detail in reference files — no cross-file duplicate flows.

## Safety Gates

| Operation | Gate |
|-----------|------|
| `delete-alarms` / `delete-dashboards` / `delete-insight-rules` | Human confirm with name + impact |
| `put-retention-policy` / `delete-canary` | Human confirm — permanent/irreversible |

## Reference Files

[Prompt Examples](references/prompt-examples.md) · [Operation Index](references/operation-index.md) · [AWS CLI](references/aws-cli-usage.md) · [boto3](references/boto3-sdk-usage.md) · [Core Concepts](references/core-concepts.md) · [Troubleshooting](references/troubleshooting.md) · [ELB Templates](references/elb-monitoring-templates.md) · [AIOps Scenarios](references/aiops-scenarios.md) · [Layered Inspection](references/layered-inspection-template.md) · [GCL Rubric](references/rubric.md) · [GCL Prompts](references/prompt-templates.md)

## Quality Gate (GCL)

`recommended` · `max_iterations=3` · rubric: `references/rubric.md` · prompts: `references/prompt-templates.md` · trace: `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json`. Destructive ops: `delete-alarms`, `delete-insight-rules`, `delete-dashboards`, `delete-canary`, `put-retention-policy`. Rules A7–A10: `aws-skill-generator/references/gcl-spec.md` §8.

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md). Parse `aiops_delegate:` (`request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope`, `trace_id`). Writes: idempotency_key (24h dedup); destructive ops need `confirmation_token`; propagate `trace_id` in User-Agent; always emit `aiops_context:` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

> After completing a task, review and distill reusable assets per the root AGENTS.md "Compound-Asset Distillation Loop (CADL)".
