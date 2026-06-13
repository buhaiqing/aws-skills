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
  version: "2.4.0"
  last_updated: "2026-06-13"
  runtime: Harness AI Agent
  cli_applicability: dual-path
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
    pilot: false
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

## Common JSON Paths (Centralized)

```
# Alarms/Composite: .MetricAlarms[] / .CompositeAlarms[] → AlarmName, StateValue, MetricName, Namespace
# Metrics/Data:     .Metrics[] / .MetricDataResults[] / .Datapoints[]
# Dashboards:       .DashboardEntries[].DashboardName
# Logs:             .logGroups[]; start-query → .queryId; get-query-results → .status, .results
# Insights/Canary:  .InsightRules[] / .Canaries[].{Name,Status}
```

## Trigger & Scope

### SHOULD Use When
- User mentions "CloudWatch", "CW", metrics, alarms, monitoring, logs, dashboards
- Task: **alarms, metrics, dashboards, log groups, Logs Insights, anomaly detection, metric math, FORECAST, Contributor Insights, Synthetics**
- **(AIOps)** cross-module RCA, capacity FORECAST, cert-expiry metrics; keywords: elb-monitoring, elb-rca, cert-expiry

### SHOULD NOT Use When
- EC2 → `aws-ec2-ops` | S3 → `aws-s3-ops` | RDS → `aws-rds-ops` | Aurora → `aws-aurora-ops`
- Lambda code → `aws-lambda-ops` | SSM → `aws-ssm-ops` | SNS → `aws-sns-ops`
- ASG → `aws-autoscaling-ops` | ELB resource ops → `aws-elb-ops`

### Delegation
ELB ARNs/health → `aws-elb-ops` | Certs → `aws-acm-ops` | VPC Flow Logs → `aws-vpc-ops`
Patrol → `aws-aiops-cruise` | Orchestrator → `aws-aiops-orchestrator`
Layered inspection + AIOps scenarios → [layered-inspection-template.md](references/layered-inspection-template.md), [aiops-scenarios.md](references/aiops-scenarios.md)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask; fail if unset |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | STS temp creds only |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Fallback for `{{user.region}}` |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{user.region}}` | User input or env | Default `us-east-1` |
| `{{user.alarm}}` / `{{user.ns}}` / `{{user.metric}}` / `{{user.log}}` / `{{user.dash}}` | User input | Ask once; reuse |
| `{{output.qid}}` | API response | `.queryId` from `start-query` |
| `{{output.*}}` | Last response | Parse per JSON paths above |

`assets/example-config.yaml`: load `.env`, substitute `{{env.*}}` / `{{user.*}}`, then render.

## Execution Flow

**Pre-flight → Execute → Validate → Recover** on every operation.

**Pre-flight**: `aws --version` + `aws sts get-caller-identity --region {{user.region}} --output json`

**Execute (CLI)**: [references/aws-cli-usage.md](references/aws-cli-usage.md) — routing: [references/operation-index.md](references/operation-index.md)

**Execute (boto3)**: After 3 CLI failures — [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md)

**Validate**: `describe-alarms` / `list-metrics` / `describe-log-groups` / poll `get-query-results` until `Complete`

**Recover**: [references/troubleshooting.md](references/troubleshooting.md)

| Error | Action |
|-------|--------|
| InvalidParameterValue (400) | Fix; retry once |
| ResourceNotFound (404) | Verify via describe/list |
| Throttling (429) | Backoff; retry 3x |
| InternalError (5xx) | Retry 3x; HALT |

## Scope

| Operation / Scenario | Safety Gate |
|---------------------|-------------|
| Create / modify alarm (incl. composite, anomaly, metric math) | Warn if `--alarm-actions` empty; anomaly needs ≥14d data |
| Delete alarm / insight rule / dashboard / canary | **Human confirm** (see [operation-index.md](references/operation-index.md)) |
| Metrics list / get / FORECAST | — |
| Logs Insights / Contributor Insights | — |
| Dashboard create; ELB templates + [elb-aiops-dashboard.json](assets/elb-aiops-dashboard.json) | Delegate ELB ARNs to `aws-elb-ops` first |
| Log retention | **Human confirm** (permanent data loss) |
| Diagnose alarm | — |
| AIOps cost RCA / cert expiry / feedback | — |

Discover namespaces via `list-metrics` (TE-1); do not hardcode metric tables in SKILL.

## Quality Gate (GCL)

| Setting | Value |
|---|---|
| Class / `max_iterations` | `recommended` / `3` |
| Rubric / Prompts | `references/rubric.md` / `references/prompt-templates.md` |
| Trace | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops need trace confirmation: `delete-alarms`, `delete-insight-rules`, `delete-dashboards`, `delete-canary`, `put-retention-policy`. Rules A7–A10: `aws-skill-generator/references/gcl-spec.md` §8.

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md). Parse `aiops_delegate:` (`request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope`, `trace_id`). Writes: idempotency_key (24h dedup); destructive ops need `confirmation_token`; respect decision tier; propagate `trace_id` in User-Agent; always emit `aiops_context:` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

## Reference Files

[prompt-examples](references/prompt-examples.md) · [operation-index](references/operation-index.md) · [aws-cli-usage](references/aws-cli-usage.md) · [elb-monitoring-templates](references/elb-monitoring-templates.md) · [aiops-scenarios](references/aiops-scenarios.md) · [feedback-loop](references/feedback-loop.md) · [layered-inspection](references/layered-inspection-template.md) · [boto3](references/boto3-sdk-usage.md) · [core-concepts](references/core-concepts.md) · [troubleshooting](references/troubleshooting.md) · [elb-dashboard](assets/elb-aiops-dashboard.json) · [example-config](assets/example-config.yaml) · [integration](../aws-skill-generator/references/integration.md)
