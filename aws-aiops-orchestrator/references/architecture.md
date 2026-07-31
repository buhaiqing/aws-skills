# Architecture — Layered Model & Core Concepts

## Overview

The **AIOps Orchestrator** is the cross-service brain on top of the
`aws-*-ops` skill fleet. It does not perform AWS operations itself; instead it:

1. Routes user intents to one or more `aws-*-ops` skills.
2. Correlates signals (metrics, logs, events, config, cost) across services.
3. Drives multi-skill remediation workflows (e.g., ELB target drain → ASG
   scale-out → Route53 failover).
4. Provides cross-service capacity & cost forecasting.
5. Implements the unified AIOps closed-loop:
   **Data Collection → Detection → RCA → Decision → Action → Feedback**.

This skill reuses the blueprint from
`aws-elb-ops/references/aiops-automation-engine.md` (the 6-layer, 31-scenario
model) and generalizes it across the entire `aws-*-ops` fleet.

## Layered Model (reused & extended from `aws-elb-ops`)

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 0: Intent Router (this skill)                             │
│   User intent → scope graph → delegate plan                     │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: Data Collection (delegated)                            │
│   CloudWatch Metrics | Logs | CloudTrail | Config | Cost Explorer│
│   Compute Optimizer | DevOps Guru | Trusted Advisor | AWS Health │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Detection & Analysis (this skill + delegated)          │
│   Anomaly Detection | Forecast | Logs Insights                  │
│   Contributor Insights | Time-series alignment                  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Root Cause Analysis (this skill)                       │
│   Cross-service correlation graph                               │
│   Timeline tracing | Change-event association                   │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: Decision & Planning (this skill)                       │
│   [AUTO_HEAL]   — execute via delegated skills (< 15 min)       │
│   [AI_ASSIST]   — recommend, user confirms (1-4 h)              │
│   [MANUAL]      — human judgment required (> 4 h)               │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5: Automated Execution (delegated)                        │
│   Each action goes through the responsible aws-*-ops skill       │
├─────────────────────────────────────────────────────────────────┤
│ Layer 6: Feedback & Learning (this skill)                       │
│   Outcome tracking | False-positive rate                        │
│   Knowledge base update | Threshold calibration                 │
└─────────────────────────────────────────────────────────────────┘
```

## Core Concepts

- **Scope Graph** — the dependency map of AWS resources in scope (VPC →
  Subnet → ALB → TG → EC2 → ASG → RDS, etc.). Used for blast-radius
  analysis and RCA traversal. See [`correlation-graph.md`](correlation-graph.md).
- **Delegate Contract** — the standardized way this skill invokes an
  `aws-*-ops` skill and parses its response. See
  [`delegate-routing.md`](delegate-routing.md).
- **Runbook Recipe** — a deterministic multi-step remediation plan
  (e.g., RB-007: "ELB 5xx surge on prod ALB"). See
  [`runbook-recipes.md`](runbook-recipes.md).
- **Detection Rule** — a (metric, condition, scope, severity) tuple
  used by Layer 2. See [`detection-rules.md`](detection-rules.md).
- **Decision Boundary** — when to AUTO_HEAL vs AI_ASSIST vs MANUAL
  (inherited from README §AIOps Decision Types). See
  [`decision-boundary.md`](decision-boundary.md).

## Cross-Skill Dependencies & Reuse

This skill **does not reimplement** the 6-layer AIOps loop from
`aws-elb-ops/references/aiops-automation-engine.md`. It uses that file as
the blueprint and the matching `aws-*-ops` skills as the executors.

| Orchestrator Need | Delegate To |
|-------------------|-------------|
| Metrics / Anomaly / Forecast | `aws-cloudwatch-ops` |
| Change event correlation | `aws-cloudtrail-ops` |
| Resource compliance / drift | `aws-config-ops` |
| Load balancer diagnosis & auto-heal | `aws-elb-ops` (full AIOps engine) |
| Compute-side diagnosis & reboot | `aws-ec2-ops` |
| Database-side diagnosis | `aws-rds-ops` |
| Network-side diagnosis | `aws-vpc-ops` |
| Certificate lifecycle | `aws-acm-ops` |
| Traffic anomaly mitigation | `aws-waf-ops` |
| DNS failover | `aws-route53-ops` |
| Capacity scaling | `aws-autoscaling-ops` |
| Encryption compliance | `aws-kms-ops` |
| Permissions drift | `aws-iam-ops` |
| Threat correlation | `aws-guardduty-ops` |
| Security findings aggregation | `aws-securityhub-ops` |
| Storage cost / lifecycle | `aws-s3-ops` |
| Topology + causal graph | `aws-topo-discovery` (causal graph operations) |
| Event-driven triggers | `aws-eventbridge-ops` |
| Alert fanout | `aws-sns-ops` |
| Async work queue | `aws-sqs-ops` |

## Token Efficiency (TE-1 … TE-6)

- TE-1: No hardcoded version/port/state tables — all version states in
  `references/` and `README.md`.
- TE-2: No SDK docstrings — `boto3-sdk-usage.md` lives in delegated skills.
- TE-3: Compact error table (see [`execution-flow.md`](execution-flow.md)).
- TE-4: JSON paths declared once per reference file top.
- TE-5: YAML anchors in `assets/example-scope-graph.yaml`.
- TE-6: No duplicated flows across SKILL.md and references — references
  hold the detailed flows, SKILL.md holds the orchestration summary.
