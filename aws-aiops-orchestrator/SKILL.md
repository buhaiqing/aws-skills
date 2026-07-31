---
name: aws-aiops-orchestrator
description: >-
  Use when the user asks cross-service questions spanning multiple AWS resources:
  health, RCA, forecasting, cost optimization, change impact, or coordinated auto-heal.
  Routes to aws-*-ops skills; does NOT execute AWS ops directly.
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, CloudWatch/CloudTrail/Config/Cost Explorer access; requires aws-*-ops skills in runtime.
metadata:
  author: aws
  version: 0.1.0
  last_updated: '2026-07-31'
  status: validated
  runtime: Harness AI Agent
  cli_applicability: read-mostly
  type: orchestrator-meta
  aiops_level: cross-service-orchestrator
  reuses: [aws-elb-ops/references/aiops-automation-engine.md, aws-cloudwatch-ops, aws-cloudtrail-ops, aws-config-ops]
  cross_skill_deps: [aws-cloudwatch-ops, aws-cloudtrail-ops, aws-config-ops, aws-elb-ops, aws-ec2-ops, aws-rds-ops, aws-aurora-ops, aws-vpc-ops, aws-acm-ops, aws-waf-ops, aws-route53-ops, aws-autoscaling-ops, aws-kms-ops, aws-iam-ops, aws-guardduty-ops, aws-securityhub-ops, aws-s3-ops, aws-lambda-ops, aws-stepfunctions-ops, aws-eventbridge-ops, aws-aiops-cruise, aws-topo-discovery, aws-sns-ops, aws-sqs-ops, aws-dynamodb-ops, aws-elasticache-ops, aws-opensearch-ops, aws-eks-ops, aws-cloudfront-ops, aws-athena-ops, aws-ram-ops, aws-secretsmanager-ops]
  provides: [cross-service-rca, capacity-forecast, cost-anomaly-detection, change-impact-analysis, coordinated-auto-healing, predictive-failure-detection, security-posture-summary]
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
    rubric_version: v1
---

# AWS AIOps Orchestrator

Cross-service brain over the `aws-*-ops` fleet: route intents, correlate signals, drive multi-skill remediation, forecast capacity/cost. Reuses `aws-elb-ops/references/aiops-automation-engine.md` blueprint. Details in references.

## Trigger & Scope

### SHOULD Use When

- Cross-service health ("is everything OK", "site is slow", prod outage).
- RCA across 2+ services ("why 502", latency, connection timeout).
- Predictive/cost analysis ("next month's bill", quota exhaustion, FinOps).
- Change-impact ("what breaks if I delete X", blast radius).
- Coordinated auto-heal ("self-heal production", runbook RB-007).
- Alarm/EventBridge schedules needing cross-service diagnosis.
- Keywords: `aiops`, `cross-service`, `incident`, `SRE`, `RCA`, `self-heal`, `forecast`, `FinOps`, `runbook`.

### SHOULD NOT Use When

- Single-service CRUD → matching `aws-*-ops` (e.g. S3 bucket → `aws-s3-ops`).
- Pure CloudWatch setup → `aws-cloudwatch-ops`.
- App-layer debugging (code/SQL/K8s pod internals) → `aws-ssm-ops` or app tooling.
- Legal/compliance security IR → `aws-guardduty-ops` + `aws-securityhub-ops`; escalate humans.

## Placeholder Convention

| Token | Source | Notes |
|-------|--------|-------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | Fail closed if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | Fail closed if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Single-region scope default |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{u.scope}}` | User input | `region` / `cross-region` / `account` / `global` |
| `{{u.time_window}}` | User input | e.g. `last_1h`, `last_24h`, `last_7d` |
| `{{u.severity_filter}}` | User input | `critical` / `high` / `medium` / `low` / `all` |
| `{{u.action_mode}}` | User input | `observe` / `recommend` / `auto-heal` / `manual` |
| `{{o.*}}` | Delegated skill response | Parsed from `aiops_context` JSON |

Never instruct the user to paste secrets.

## Execution Flow

**Pre-flight → Execute → Validate → Recover** at orchestration level; each delegated skill runs the same pattern. Pre-flight: parse intent, resolve scope graph, validate `{{env.*}}`, build delegate plan. Execute: Layer 0–6 (route → collect → detect → RCA → decide → act → feedback). CLI primary (`aws <svc> <cmd> --output json`), boto3 after 3 failures. Destructive `{delete, terminate, deregister, detach, disable}` always need human confirm before delegated write. Full steps, recover table, action_mode defaults: [`execution-flow.md`](references/execution-flow.md).

## Quality Gate (GCL)

Recommended GCL, `max_iter=3`. Composite orchestration may use Parallel GCL (fan-out Generators, single Critic). See [`delegate-routing.md`](references/delegate-routing.md) §Parallel GCL and `gcl-spec.md` §12.

## Reference Files

[`architecture.md`](references/architecture.md) · [`execution-flow.md`](references/execution-flow.md) · [`operational-scenarios.md`](references/operational-scenarios.md) · [`decision-boundary.md`](references/decision-boundary.md) · [`safety-gates.md`](references/safety-gates.md) · [`delegate-routing.md`](references/delegate-routing.md) · [`correlation-graph.md`](references/correlation-graph.md) · [`detection-rules.md`](references/detection-rules.md) · [`runbook-recipes.md`](references/runbook-recipes.md) · `assets/example-scope-graph.yaml` · `assets/cost-forecast-template.json`

## Safety Gates

No credential prompts; destructive ops require confirm; `[MANUAL]` never auto-executes; cross-account always `[MANUAL]`; auto-heal stops on first same-action failure; all writes idempotent or state-guarded; audit every action. Hard rules: [`safety-gates.md`](references/safety-gates.md).

> After completing a task, review and distill reusable assets per the root AGENTS.md "Compound-Asset Distillation Loop (CADL)".
