---
name: aws-aiops-orchestrator
description: >-
  Use when the user asks cross-service questions that span multiple AWS resources
  at once, such as: "is the system healthy right now", "why is the site slow",
  "what will fail next month", "where is money being wasted", "investigate the 502
  spike", "predict next quarter's cost", or "auto-heal production". This skill is
  the **AIOps orchestrator brain** — it does NOT execute AWS operations directly.
  It routes intents to specific `aws-*-ops` skills, correlates signals across
  services, runs cross-service RCA, drives multi-skill remediation workflows,
  and provides capacity / cost forecasting with a global view.

  Coverage: anomaly detection, root cause analysis (cross-service), self-healing
  orchestration, capacity prediction, cost optimization, change-impact analysis,
  and the unified AIOps closed-loop across all 30 `aws-*-ops` skills.

  SHOULD NOT be loaded for single-service operations — delegate to the
  appropriate `aws-*-ops` skill instead.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access to
  CloudWatch / CloudTrail / AWS Config / Cost Explorer / Compute Optimizer /
  DevOps Guru endpoints. Depends on at least one `aws-*-ops` skill being
  available in the same agent runtime.
metadata:
  author: aws
  version: "0.1.0"
  last_updated: "2026-06-10"
  status: "design-draft"
  runtime: Harness AI Agent
  cli_applicability: read-mostly # orchestrator reads + invokes other skills;
                                  # writes go through delegated skills
  type: orchestrator-meta
  aiops_level: cross-service-orchestrator
  reuses:
    - aws-elb-ops/references/aiops-automation-engine.md  # 6-layer closed-loop blueprint
    - aws-cloudwatch-ops                                  # metrics / anomaly / forecast
    - aws-cloudtrail-ops                                  # change event correlation
    - aws-config-ops                                      # compliance / drift
  cross_skill_deps:
    - aws-cloudwatch-ops   # primary metrics + anomaly + forecast
    - aws-cloudtrail-ops   # change event timeline
    - aws-config-ops       # resource compliance + config drift
    - aws-elb-ops          # most mature AIOps engine; first-class delegate
    - aws-ec2-ops          # compute-side diagnosis + auto-reboot
    - aws-rds-ops          # standalone RDS diagnosis
    - aws-aurora-ops       # Aurora cluster diagnosis (lag, failover, Serverless)
    - aws-vpc-ops          # network-side diagnosis
    - aws-acm-ops          # certificate lifecycle
    - aws-waf-ops          # traffic anomaly mitigation
    - aws-route53-ops      # DNS failover
    - aws-autoscaling-ops  # capacity scaling actions
    - aws-kms-ops          # encryption compliance
    - aws-iam-ops          # permissions drift
    - aws-guardduty-ops    # threat correlation
    - aws-securityhub-ops  # cross-account security findings
    - aws-s3-ops           # storage cost + lifecycle
    - aws-lambda-ops       # serverless health
    - aws-stepfunctions-ops
    - aws-eventbridge-ops  # event-driven remediation triggers
    - aws-aiops-cruise     # read-only full-chain patrol producer
    - aws-topo-discovery   # topology manifest + health overlay
    - aws-sns-ops          # alert fanout
    - aws-sqs-ops          # async work queue
---

# AWS AIOps Orchestrator

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

## Trigger & Scope

### SHOULD Use When

- User asks a **cross-service health question** ("is everything OK",
  "what's wrong with prod", "site is slow, find the cause").
- User asks for **root cause analysis** across 2+ AWS services
  ("why 502", "why latency", "why connection timeout").
- User asks for **predictive analysis** with global scope
  ("when will we hit quota", "next month's bill", "what will saturate first").
- User asks for **cost optimization** across services
  ("where can we save money", "idle resources", "right-sizing").
- User asks for **change-impact analysis**
  ("what breaks if I delete X", "blast radius of this change").
- User asks for **coordinated auto-healing** spanning multiple skills
  ("self-heal production", "run runbook RB-007").
- User triggers via alarm / EventBridge schedule that needs cross-service
  diagnosis.
- Keywords: `aiops`, `cross-service`, `incident`, `SRE`, `outage`, `MTTR`,
  `correlation`, `anomaly`, `forecast`, `capacity`, `FinOps`, `cost anomaly`,
  `runbook`, `playbook`, `RCA`, `self-heal`, `closed-loop`.

### SHOULD NOT Use When

- Single-service operations → delegate to the matching `aws-*-ops` skill
  (e.g., "create an S3 bucket" → `aws-s3-ops`).
- Pure CloudWatch metric/alert setup → `aws-cloudwatch-ops`.
- Specific resource creation/deletion/termination → the relevant `aws-*-ops`.
- Real-time AWS console mimicry → delegate.
- Application-layer debugging (code, SQL, K8s pod internals) → use
  `aws-ssm-ops` for Session Manager / Run Command, or application-level
  tooling outside this skill.
- Security incident response with legal/compliance implications →
  `aws-guardduty-ops` + `aws-securityhub-ops` directly, escalate to humans.

## Placeholder Convention

| Token | Source | Notes |
|-------|--------|-------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | Fail closed if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | Fail closed if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Used when scope is single-region |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{u.scope}}` | User input | One of: `region`, `cross-region`, `account`, `global` |
| `{{u.time_window}}` | User input | e.g., `last_1h`, `last_24h`, `last_7d` |
| `{{u.severity_filter}}` | User input | `critical` / `high` / `medium` / `low` / `all` |
| `{{u.action_mode}}` | User input | `observe` / `recommend` / `auto-heal` / `manual` |
| `{{o.*}}` | Last delegated skill response | Parsed from `aiops_context` JSON |

**Critical**: never instruct the user to paste secrets. All credentials come
from `{{env.*}}` or `{{env.AWS_PROFILE}}`.

## Architecture

### Layered Model (reused & extended from `aws-elb-ops`)

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

### Core Concepts

- **Scope Graph** — the dependency map of AWS resources in scope (VPC →
  Subnet → ALB → TG → EC2 → ASG → RDS, etc.). Used for blast-radius
  analysis and RCA traversal. See `references/correlation-graph.md`.
- **Delegate Contract** — the standardized way this skill invokes an
  `aws-*-ops` skill and parses its response. See
  `references/delegate-routing.md`.
- **Runbook Recipe** — a deterministic multi-step remediation plan
  (e.g., RB-007: "ELB 5xx surge on prod ALB"). See
  `references/runbook-recipes.md`.
- **Detection Rule** — a (metric, condition, scope, severity) tuple
  used by Layer 2. See `references/detection-rules.md`.
- **Decision Boundary** — when to AUTO_HEAL vs AI_ASSIST vs MANUAL
  (inherited from README §AIOps Decision Types).

## Execution Flow (per operation)

The orchestrator follows the standard **Pre-flight → Execute → Validate →
Recover** pattern at the *orchestration* level, while each delegated skill
runs the same pattern at the *operation* level.

### Step 1 — Pre-flight

1. Parse user intent → identify scope, time window, action mode.
2. Resolve scope graph (which AWS resources are in scope).
3. Validate credentials via `{{env.*}}` checks; fail closed if missing.
4. Verify required `aws-*-ops` skills are available in runtime.
5. Decide **delegate plan**: ordered list of (skill, intent, params) tuples.
6. Surface assumptions to user before any read-heavy scan.

### Step 2 — Execute (Layered)

```
Intent → Layer 0 Routing
        ↓
        Layer 1 Data Collection (delegated read-only calls)
        ↓
        Layer 2 Detection (this skill analyzes collected data)
        ↓
        Layer 3 RCA (this skill correlates across services)
        ↓
        Layer 4 Decision (this skill chooses action tier)
        ↓
        Layer 5 Action (delegated write calls if AUTO_HEAL/confirmed)
        ↓
        Layer 6 Feedback (record outcome, update knowledge)
```

For each delegated call, use the dual-path pattern:
**AWS CLI** (`aws <svc> <cmd> --output json`) → fall back to **boto3** after
3 failures. Every command MUST use `--output json` (per CLAUDE.md).

### Step 3 — Validate

- Verify each delegated call returned expected shape (see delegate contract).
- Cross-check: do the collected signals agree? If not, escalate to
  `[AI_ASSIST]` instead of guessing.
- For any AUTO_HEAL action: confirm post-state matches expected state via
  a read-back call.

### Step 4 — Recover

| Error Type | Action |
|------------|--------|
| InvalidParameter (400) | Fix args; retry once |
| QuotaExceeded | HALT; report to user |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |
| Cross-skill inconsistency | `[AI_ASSIST]`; present both findings |
| AUTO_HEAL fails 2x | Degrade to `[MANUAL]` (per README boundary) |
| Data deletion in scope | Block; force `[MANUAL]` |

### Human Confirmation (mandatory before destructive actions)

Per repo policy (Charter C5): any action in the `{delete, terminate,
deregister, detach, disable}` set requires explicit user confirmation,
even if the orchestrator classifies it as AUTO_HEAL. The orchestrator
MUST present the proposed action and wait for `confirm` before invoking
the delegated destructive skill call.

## Variable Convention Notes

- `{{u.action_mode}}` defaults:
  - `observe`  — read-only, no recommendations offered
  - `recommend` — analyze + suggest; no writes
  - `auto-heal` — execute `[AUTO_HEAL]` tier only; confirm before
    `[AI_ASSIST]` and `[MANUAL]`
  - `manual` — never auto-execute; full report only

- All output IDs use the standard formats:
  - Instance: `i-xxxxxxxxxxxxxxxxx`
  - ALB ARN: `arn:aws:elasticloadbalancing:...`
  - DB identifier: `db-XXXXXXXXXXXXXXXXXXXXXXXXXX`
  - Lambda: `arn:aws:lambda:...:function:<name>:<ver>`

## Operational Scenarios

### Scenario 1 — "线上有问题吗？" (health overview)

```
Intent: health-check, action_mode=observe
Layer 0: parse → scope=region, action_mode=observe
Layer 1: delegate to
  - aws-cloudwatch-ops (alarm state summary)
  - aws-elb-ops (target health, 5xx rate, latency p99)
  - aws-rds-ops (DB health, replication lag, connections)
  - aws-ec2-ops (instance status checks)
  - aws-route53-ops (health check status)
  - aws-guardduty-ops (unarchived HIGH/CRITICAL findings count)
  - aws-securityhub-ops (security score delta)
  - aws-acm-ops (cert expiring within 30 days)
Layer 2: aggregate → compute health score per service
Layer 3: detect anomalies across services (correlated spikes?)
Layer 4: classify severity → tier
Layer 5: none (observe mode)
Layer 6: report summary table + drill-down links
```

### Scenario 2 — "为什么 502 飙升？" (cross-service RCA)

```
Intent: rca, symptom="5xx surge", scope=alb/prod
Layer 0: parse → symptom=5xx, primary=aws-elb-ops
Layer 1: delegate to
  - aws-elb-ops → unhealthy targets, target state change, recent config diffs
  - aws-ec2-ops → instance status, CPU, recent SSM commands
  - aws-vpc-ops → SG rules, NACL, route table changes
  - aws-rds-ops → DB connection saturation, slow query count
  - aws-acm-ops → cert validity/expiry (TLS handshake failure)
  - aws-waf-ops → recent WAF rule matches, block rate spike
  - aws-cloudtrail-ops → change events on each resource in last 1h
Layer 2: collect all signals
Layer 3: build timeline; correlate changes with symptom onset
Layer 4: emit top-3 hypotheses ranked by likelihood
Layer 5: optionally trigger runbook (auto-heal tier only)
Layer 6: record RCA outcome for future learning
```

### Scenario 3 — "下个月账单多少？" (cost forecast)

```
Intent: cost-forecast, time_window=next_30d
Layer 1: delegate to
  - aws-cloudwatch-ops (FORECAST on cost-relevant metrics: data processed,
    LCU consumption, NAT GW bytes)
  - Cost Explorer via direct CLI (GetCostForecast, GetCostAndUsage)
Layer 2: combine → trend + seasonality + one-time items
Layer 3: flag top-3 cost drivers + projected delta vs current month
Layer 4: recommendations: rightsizing, idle resource cleanup, RI/SP coverage
Layer 5: none (recommend only)
Layer 6: persist forecast for trend tracking
```

### Scenario 4 — "这个变更影响什么？" (change impact)

```
Intent: change-impact, change="delete SG sg-prod-web"
Layer 0: scope graph traversal → find resources referencing this SG
Layer 1: enumerate dependent resources (ELB, EC2, RDS, Lambda ENI, etc.)
Layer 3: trace blast radius → direct + transitive
Layer 4: classify risk → if any prod resource, force [MANUAL]
Layer 5: none unless confirmed
```

### Scenario 5 — "自动修复生产" (coordinated self-heal)

```
Intent: self-heal, scope=production-tagged
Layer 0: enumerate all production resources
Layer 1: full health scan
Layer 2: identify all anomalies
Layer 3: cluster anomalies into incidents (correlation-based)
Layer 4: for each incident → match runbook recipe
Layer 5: execute [AUTO_HEAL] tier actions sequentially
        → escalate to [AI_ASSIST] for any cluster
        → halt at first destructive action and request human confirmation
Layer 6: track MTTR per incident; update runbook success rate
```

## Detection Rule Library (summary)

See `references/detection-rules.md` for the full library. Each rule has:
`(service, metric_or_event, condition, window, severity, default_decision)`.

Categories:
- **Fault** — error rate, latency, unhealthy target, connection exhaustion
- **Predictive** — quota exhaustion, cert expiry, capacity saturation
- **Cost** — service cost anomaly, idle resources, RI coverage drop
- **Security** — GuardDuty CRITICAL, Config non-compliance, public S3/port
- **Change** — config drift, unexpected tag mutation, IAM policy changes

Default thresholds are **baselines** — Layer 2 MUST adjust against the
30-day per-resource baseline (collected on first scan, refreshed weekly).

## Decision Boundary (inherited from README §AIOps Decision Types)

| Label | When | Orchestrator Behavior |
|-------|------|----------------------|
| `[AUTO_HEAL]` | Target re-register, EC2 reboot, cross-zone enable, cert renew, compliance fix | Execute via delegated skill without prompt, but log the action |
| `[AI_ASSIST]` | Health check tuning, capacity scaling, SG change, first-seen anomaly | Present plan + diff; require `confirm` |
| `[MANUAL]` | Data deletion, cross-account, cost > $100/mo, blast radius > 5 prod resources | Stop; full report only |

**Override**: if the user explicitly states `action_mode=auto-heal` but the
incident is in the `[MANUAL]` tier, the orchestrator MUST downgrade to
`[AI_ASSIST]` and ask for confirmation regardless.

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
| Event-driven triggers | `aws-eventbridge-ops` |
| Alert fanout | `aws-sns-ops` |
| Async work queue | `aws-sqs-ops` |

## Token Efficiency (TE-1 … TE-6)

- TE-1: No hardcoded version/port/state tables — all version states in
  `references/` and `README.md`.
- TE-2: No SDK docstrings — `boto3-sdk-usage.md` lives in delegated skills.
- TE-3: Compact error table (this file, "Recover" section).
- TE-4: JSON paths declared once per reference file top.
- TE-5: YAML anchors in `assets/example-scope-graph.yaml`.
- TE-6: No duplicated flows across SKILL.md and references — references
  hold the detailed flows, SKILL.md holds the orchestration summary.

## Reference Index

- `references/delegate-routing.md` — delegate contract, routing matrix,
  request/response schema for `aws-*-ops` invocation.
- `references/correlation-graph.md` — AWS resource dependency graph,
  blast-radius traversal algorithm.
- `references/detection-rules.md` — full detection rule library with
  thresholds and severity tiers.
- `references/runbook-recipes.md` — standard remediation runbooks
  (RB-001 … RB-NNN) with multi-skill execution plans.
- `assets/example-scope-graph.yaml` — sample scope graph definition.
- `assets/cost-forecast-template.json` — cost forecast output template.

### Parallel GCL

When the Orchestrator decomposes a user request into independent subtasks
(e.g., WAF rule update + ALB metric addition), use **Parallel GCL**: fan
out to multiple Generators (each modifies different files/resources), then
a single Critic audits all outputs with cross-referencing. See
[`delegate-routing.md`](references/delegate-routing.md) §Parallel GCL
and `gcl-spec.md` §12.

## Safety Gates (hard rules)

1. No credential prompts to user. All `{{env.*}}` from runtime; fail
   closed if missing.
2. Destructive actions require explicit human confirmation, even if
   classified `[AUTO_HEAL]`.
3. `[MANUAL]` tier actions never auto-execute.
4. Cross-account actions always `[MANUAL]`.
5. Auto-heal stops at first failure of the same action (no cascade).
6. Idempotency: every delegated write must be idempotent or guarded
   by a state check.
7. Audit trail: every action MUST write a record (CloudTrail
   naturally + an internal `aiops_actions` log entry).