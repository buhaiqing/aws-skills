---
name: aws-aiops-cruise
description: >-
  Use when the user needs end-to-end AWS health cruise (read-only patrol) across
  EIP → ALB/NLB → EC2 → RDS/ElastiCache → NAT Gateway → Security Groups — not
  single-resource ops. Triggers: "daily health check", "full chain inspection",
  "cruise prod", "pre-launch check", "emergency troubleshoot", "capacity planning",
  "slow query diagnosis", "connection storm", "bottleneck localization".
  Includes 7 Perceive Agents (HealthCruise/TopoScan/ConfigDrift/CostWatch/
  SecurityScan/AuditTrail/AdvisorScan). Pure read-only — no resource mutations.
  Do NOT use for create/modify/delete, single-service ops, or topology-only scans
  (use aws-topo-discovery) or cross-service RCA/self-heal (use aws-aiops-orchestrator).
license: MIT
compatibility: >-
  AWS CLI v2, jq, Python 3.10+, valid AWS credentials (ReadOnlyAccess or
  equivalent), CloudWatch/GetMetricStatistics, Resource Groups Tagging API.
  Read-only Describe/List/Get APIs strictly enforced.
metadata:
  author: aws
  version: "2.2.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: cross-product-aiops-cruise
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
  cross_skill_deps: [aws-topo-discovery, aws-cloudwatch-ops, aws-rds-ops, aws-aurora-ops, aws-elb-ops, aws-ec2-ops, aws-ecs-ops, aws-apigateway-ops, aws-ebs-ops, aws-aiops-orchestrator]
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ["health-check", "rca", "pre-flight-check", "capacity-review"]
    produces_facts: ["metric", "log", "event", "state", "topology"]
    idempotency_ttl: "PT24H"
  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, AWS_SESSION_TOKEN, AWS_PROFILE]
---

# AWS Full-Chain AIOps Cruise — aws-aiops-cruise

> **One-liner**: AWS-native read-only cruise — Route53/WAF → ALB → EC2/ECS/EKS/Lambda → RDS/ElastiCache/DynamoDB → NAT, enriched with CloudWatch Alarms, DevOps Guru, Performance Insights, Security Hub, Config, and chain inference.

Stack layers, cross-skill matrix, EKS rules, Perceive agents, runbooks, CI/CD: [`references/skill-body-extras.md`](references/skill-body-extras.md). Layer model: [`references/aws-aiops-stack.md`](references/aws-aiops-stack.md).

## Trigger & Scope

### SHOULD Use When

- Full-chain health check for a tagged workload or AWS Resource Group
- Troubleshoot failures from public entry to backend database
- Capacity planning (30-day trend) or pre-event (3× traffic) readiness check
- Security compliance audit (SG open ports + GuardDuty + CloudTrail anomalies)
- Periodic patrol with structured findings (Incident schema) and runbook execution

### SHOULD NOT Use When

- Single resource only → delegate to matching `aws-*-ops` skill
- Create/modify/delete resources → delegate to matching `aws-*-ops` skill
- Metrics-only, no chain inference → `aws-cloudwatch-ops`
- Topology/inventory/HCL export only → `aws-topo-discovery`
- Cross-service RCA, coordinated self-heal, cost forecast orchestration → `aws-aiops-orchestrator`

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Fail closed if unset; mask secrets |
| `{{user.resource_group}}`, `{{user.tag_key}}`, `{{user.tag_value}}` | User input | Scope filter (RG preferred) |
| `{{user.scenario}}`, `{{user.regions}}`, `{{user.assume_role_arn}}` | User input | Runbook + multi-region / cross-account |
| `{{user.enable_ssm}}`, `{{user.enable_pi}}`, `{{user.enable_guru}}`, `{{user.enable_xray}}` | User input | Deep modes (default PI/Guru Y) |
| `{{user.safety_confirm}}` | User input | Required for full-account patrol |
| `{{output.topology}}`, `{{output.metrics}}`, `{{output.chain_inference}}` | Run output | TopoScan, CloudWatch, Phase-3 inference |

Full table: [`references/skill-body-extras.md#variable-convention-full`](references/skill-body-extras.md#variable-convention-full).

## Execution Flow

Every runbook: **Pre-flight → Execute → Validate → Recover**. Pre-flight: `aws sts get-caller-identity`, scope (RG/tag or `scope=full` + confirm), CLI/jq. Execute: 3-phase sniff → deep collect → infer (see [`references/execution-guide.md`](references/execution-guide.md)). Validate: PASS/WARNING/CRITICAL per [`references/incident-schema.md`](references/incident-schema.md). Recover: throttle backoff 3×; AccessDenied or empty scope → HALT.

**Read-only safety**: any create/delete/terminate/stop/modify → HALT (Safety = 0). No SG mutations; recommend via `aws-vpc-ops` after user confirm. Reports → `audit-results/` (git-ignored).

**CLI entry**: `python3 runbooks/scripts/daily-health-check.py --resource-group <rg> --region <regions> --non-interactive`. Alarm: `bash runbooks/scripts/alarm-trigger.sh`. Orchestrator: `cruise-orchestrator.py --scenario daily_check`. Workflow: `workflow-runner.py --runbook 01`.

## Quality Gate (GCL)

Recommended GCL, `max_iter=3`. Rubric: [`references/rubric.md`](references/rubric.md). Prompts: [`references/prompt-templates.md`](references/prompt-templates.md). Safety = 0 on any write API. Thresholds: Correctness ≥0.5, Safety =1, Idempotency ≥0.8, Traceability ≥0.8, Spec ≥0.8. Full rubric: [`references/skill-body-extras.md#quality-gate-gcl--full-rubric`](references/skill-body-extras.md#quality-gate-gcl--full-rubric).

## Orchestrator & Risk

Emit `aiops_context` JSON; escalate ≥3 CRITICAL. See [`references/orchestrator-integration.md`](references/orchestrator-integration.md). Risk model: [`references/risk-model.md`](references/risk-model.md).

## Reference Files

[`skill-body-extras.md`](references/skill-body-extras.md) · [`execution-guide.md`](references/execution-guide.md) · [`inference-rules.md`](references/inference-rules.md) · [`threshold-definitions.md`](references/threshold-definitions.md) · [`incident-schema.md`](references/incident-schema.md) · [`perceive-design.md`](references/perceive-design.md) · [`runbooks/00-index.md`](runbooks/00-index.md) · [`changelog.md`](references/changelog.md)
