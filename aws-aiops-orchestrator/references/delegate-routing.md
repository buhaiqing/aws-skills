# Delegate Routing — How the Orchestrator Invokes `aws-*-ops` Skills

## 1. Purpose

The AIOps Orchestrator does **not** execute AWS operations directly. Every
read or write goes through a delegated `aws-*-ops` skill (or, for read-only
primitives that don't have a dedicated skill, through the matching AWS CLI
command under the orchestrator's `cli_applicability: read-mostly` mode).

This document defines:
- The **delegate contract**: request/response schema between orchestrator
  and a delegated skill.
- The **routing matrix**: which orchestrator intent maps to which skill.
- **Idempotency and safety** conventions every delegated write must follow.

## 2. Delegate Contract

### 2.1 Request Envelope (from orchestrator → delegated skill)

The orchestrator invokes a delegated skill via a structured prompt. The
delegated skill must recognize the `aiops_delegate` block and return the
`aiops_context` block.

```yaml
aiops_delegate:
  orchestrator_version: "0.1.0"
  request_id: "<uuid>"             # for trace correlation
  parent_intent: <one of:
    health-check | rca | self-heal | cost-forecast
    capacity-forecast | change-impact | compliance-scan | forensic>
  target_skill: "<aws-*-ops name>" # e.g., aws-elb-ops
  action_mode: <observe | recommend | auto-heal | manual>
  scope:
    region: "<region or '*'>"
    resource_ids: ["<id>", ...]    # empty = skill discovers its own scope
    tags: { "<k>": "<v>", ... }    # e.g., { Env: prod, Team: payments }
  time_window: "<e.g., last_1h | last_24h | last_7d | custom:YYYY-MM-DDThh:mmZ/YYYY-MM-DDThh:mmZ>"
  parameters:                      # skill-specific, see Section 3
    <key>: <value>
  decision_tier: <AUTO_HEAL | AI_ASSIST | MANUAL>
  trace_id: "<opaque>"             # propagated to all CLI/API calls
```

### 2.2 Response Envelope (from delegated skill → orchestrator)

Every delegated skill returns a normalized block **in addition to** its
normal human-readable answer:

```json
{
  "aiops_context": {
    "skill": "aws-elb-ops",
    "request_id": "<uuid>",
    "trace_id": "<opaque>",
    "status": "ok | partial | failed",
    "summary": "<one-sentence headline>",
    "facts": [
      {
        "kind": "metric | log | event | config | state | cost | finding",
        "subject": "<resource id or arn>",
        "name": "<metric/event name>",
        "value": "<number | string | object>",
        "window": "<time window the value applies to>",
        "severity": "info | low | medium | high | critical",
        "tags": { "...": "..." }
      }
    ],
    "anomalies": [
      {
        "rule_id": "FD-01",
        "subject": "i-0abc123",
        "description": "Target state flapping >3 times in 5 min",
        "first_seen": "2026-06-10T00:00:00Z",
        "confidence": 0.92
      }
    ],
    "recommendations": [
      {
        "tier": "AUTO_HEAL | AI_ASSIST | MANUAL",
        "action": "<verb phrase, e.g., 'deregister i-0abc123 from tg-prod-web'>",
        "rationale": "<why>",
        "blast_radius": ["<resource id>", ...],
        "estimated_cost_delta_usd": 0.0,
        "rollback": "<how to undo>"
      }
    ],
    "next_skill": "<optional: suggested next delegation>"
  }
}
```

### 2.3 Contract Rules

1. **No secrets in the envelope.** Use `{{env.*}}` placeholders only.
2. **Stable JSON paths.** The orchestrator parses by exact field names.
3. **Always include `request_id` and `trace_id`** so the orchestrator can
   correlate across multiple delegated calls.
4. **`status` is mandatory** — orchestrator treats anything other than
   `"ok"` as a partial result and applies degraded-mode logic.
5. **`recommendations[].tier` is mandatory** — orchestrator uses this to
   decide whether to auto-execute, ask, or halt.
6. **`blast_radius` MUST be non-empty** for any recommendation that
   touches a resource with dependents.

## 3. Routing Matrix

The orchestrator builds a delegate plan from the user's intent. The matrix
below maps intents to (skill, primary CLI command(s)). All commands assume
`--output json`.

### 3.1 Health-check intents

| Sub-intent | Primary Skill | Key Commands |
|------------|---------------|--------------|
| Resource-level health overview | `aws-cloudwatch-ops` | `describe-alarms`, `get-metric-statistics` |
| LB health & 5xx | `aws-elb-ops` | `describe-target-health`, `describe-load-balancers` |
| EC2 health | `aws-ec2-ops` | `describe-instance-status`, `describe-instances` |
| DB health (standalone RDS) | `aws-rds-ops` | `describe-db-instances` |
| Aurora cluster health | `aws-aurora-ops` | `describe-db-clusters`, cluster CW metrics |
| Cache health | `aws-elasticache-ops` | `describe-replication-groups` |
| Search health | `aws-opensearch-ops` | `describe-domain`, `describe-domain-health` |
| DNS health | `aws-route53-ops` | `get-health-check-status` |
| Cert expiry | `aws-acm-ops` | `list-certificates` + `describe-certificate` |
| Threat posture | `aws-guardduty-ops` | `list-findings` (severity ≥ HIGH, unarchived) |
| Security score | `aws-securityhub-ops` | `get-insights` + `describe-hub` |
| **Full-chain patrol (read-only)** | **`aws-aiops-cruise`** | `daily-health-check.py` → `cruise-*.json` + `aiops_context` |
| **Topology + health overlay** | **`aws-topo-discovery`** | `topo-scan.sh` + `--health-json` from cruise overlay |

When `aws-aiops-cruise` returns `aiops_context.next_skill: aws-aiops-orchestrator` (≥ 3 CRITICAL), the orchestrator **consumes** the cruise envelope and may delegate to per-service skills below for RCA/self-heal.

### 3.1a Full-chain patrol (`aws-aiops-cruise`)

| Sub-intent | CLI entry | `parameters` |
|------------|-----------|--------------|
| Scheduled health | `runbooks/scripts/daily-health-check.py` | `scenario: daily_check`, `resource_group`, `regions` |
| Emergency | `runbooks/scripts/emergency-troubleshoot.py` | `symptom`, `resource_group` |
| Topology render | `--render-topology` or `cruise-topo-render.py` | `cruise_json`, `topo_mode: brief\|detailed` |

Delegate example:

```yaml
aiops_delegate:
  parent_intent: health-check
  target_skill: aws-aiops-cruise
  action_mode: observe
  scope:
    region: us-east-1
    tags: { Environment: production }
  parameters:
    scenario: daily_check
    resource_group: prod-web-rg
    render_topology: true
    enable_xray: false
  decision_tier: AI_ASSIST
```

Cruise response MUST include `aiops_context` per [`aws-aiops-cruise/references/orchestrator-integration.md`](../../aws-aiops-cruise/references/orchestrator-integration.md).

### 3.1b Topology manifest (`aws-topo-discovery`)

| Sub-intent | CLI entry | Notes |
|------------|-----------|-------|
| Inventory scan | `scripts/topo-scan.sh` | Read-only parallel describe |
| Health overlay | `--health-json` from cruise | Colors Mermaid/ASCII by incident level |
| Baseline diff | `baseline-manager.py` | Drift vs saved manifest |

```yaml
aiops_delegate:
  parent_intent: health-check
  target_skill: aws-topo-discovery
  action_mode: observe
  parameters:
    mode: detailed
    health_json: audit-results/health-overlay-<run_id>.json
```

### 3.2 Root-cause intents

| Symptom | Primary skill | RCA chain (in order) |
|---------|---------------|----------------------|
| **Full-stack degradation (unknown layer)** | **`aws-aiops-cruise`** | cruise (observe) → orchestrator if ≥3 CRITICAL → elb → rds/aurora → vpc |
| 5xx surge | `aws-elb-ops` | elb → ec2 → rds/eks → vpc → cloudtrail |
| High latency | `aws-elb-ops` | elb → ec2 → rds/eks → cloudwatch (logs insights) |
| Connection timeout | `aws-elb-ops` | elb → vpc (SG/NACL) → ec2 → rds |
| TLS handshake failure | `aws-elb-ops` | elb → acm → cloudwatch (logs) |
| DNS failure | `aws-route53-ops` | route53 → elb → waf (block?) |
| DB slowdown (standalone RDS) | `aws-rds-ops` | rds (perf insights) → ec2 (app) → vpc (network) |
| Aurora replica lag / writer failure | `aws-aurora-ops` | aurora (lag, members) → cloudwatch → vpc |
| Connection timeout (Aurora + Proxy) | `aws-aurora-ops` | aurora (proxy targets, connections) → vpc → secretsmanager |
| **Edge / CDN / static origin** | **`aws-aiops-cruise`** | cloudfront → s3/apigw/alb origins → target health |
| WAF block spike | `aws-waf-ops` | waf → elb → ec2 (origin) |
| Cost anomaly | direct (Cost Explorer) | cost-explorer → cloudwatch → resource-level detail |
| Cert expired | `aws-acm-ops` | acm → route53 (DNS validation?) → cloudtrail |
| KMS decrypt fail | `aws-kms-ops` | kms → iam (grants?) → cloudtrail |
| Lambda throttling | `aws-lambda-ops` | lambda → event-source (sqs/sns/ddb/kinesis) → cloudwatch |

### 3.3 Self-heal intents

| Incident type | Runbook | Skills invoked (in order) |
|---------------|---------|---------------------------|
| Target flapping | RB-001 | elb → ec2 → asg |
| Target unhealthy | RB-002 | elb → ec2 → vpc → iam |
| Latency spike | RB-003 | elb → rds → ec2 |
| Cert 7-day expiry | RB-004 | acm → route53 (validation) |
| WAF DDoS pattern | RB-005 | waf → elb (rate limit) → cloudwatch (alarm) |
| Cost spike | RB-006 | direct Cost Explorer → recommend only → optional s3 lifecycle / asg rightsize |
| Production 5xx surge | RB-007 | elb → ec2 → rds → asg (scale) → route53 (failover if multi-region) → sns (notify) |
| Compliance drift | RB-008 | config → iam → s3 → kms → acm |
| Idle LB detection | RB-009 | elb → cloudwatch (LCU consumption 30d) → recommend delete |

### 3.4 Forecast intents

| Forecast | Primary Skill | Method |
|----------|---------------|--------|
| LB capacity | `aws-cloudwatch-ops` | FORECAST on `RequestCount`, `ConsumedLCUs`, `ActiveConnectionCount` |
| EC2 CPU pressure | `aws-cloudwatch-ops` | FORECAST on `CPUUtilization` (per instance, per ASG) |
| RDS storage | `aws-cloudwatch-ops` | FORECAST on `FreeStorageSpace` (linear from 30d trend) |
| Aurora Serverless capacity | `aws-aurora-ops` | FORECAST on `ServerlessDatabaseCapacity` vs MaxCapacity |
| RDS connections | `aws-cloudwatch-ops` | FORECAST on `DatabaseConnections` |
| Cert expiry | `aws-acm-ops` | Compute days remaining from `NotAfter` |
| Cost (next 30/90 days) | direct Cost Explorer | `GetCostForecast` |
| Quota exhaustion | direct Service Quotas | `get-service-quota` + recent usage trend |

### 3.5 Cost-optimization intents

| Recommendation source | Skill | Output |
|-----------------------|-------|--------|
| Idle LB | `aws-elb-ops` | LCU < 5% of provisioned for 14d |
| Idle NAT GW | `aws-vpc-ops` | bytes < 1 GB/day for 30d |
| Unattached EBS | `aws-ec2-ops` | `available` state > 7d |
| Unassociated EIP | `aws-ec2-ops` | not associated > 24h |
| S3 lifecycle gap | `aws-s3-ops` | bucket without lifecycle rule, > 90d old |
| RDS over-provisioned | `aws-rds-ops` | avg CPU < 10% for 14d |
| Aurora idle readers / Serverless oversize | `aws-aurora-ops` | reader CPU < 10% 14d; MaxCapacity >> p99 ACU |
| ElastiCache over-provisioned | `aws-elasticache-ops` | `CPUUtilization` < 10% for 14d |
| Rightsizing (general) | Compute Optimizer (direct CLI) | `get-ec2-instance-recommendations`, `get-rds-db-instance-recommendations` |

## 4. Delegation Mechanics

### 4.1 Invocation Order

For any orchestrator operation:

1. **Discover** — list relevant resources via `aws-resource-explorer`
   (if enabled) or via per-service `describe-*` calls.
2. **Plan** — build the delegate plan (ordered list of skill calls).
3. **Invoke** — invoke delegated skills in parallel when there are no
   dependencies; serially when there are (e.g., elb → ec2 → rds).
4. **Collect** — aggregate `aiops_context.facts` from all responses.
5. **Analyze** — orchestrator runs Layer 2/3 logic on the collected facts.
6. **Decide** — orchestrator chooses action tier per recommendation.
7. **Execute** — for `[AUTO_HEAL]`, re-invoke the delegated skill with
   `action_mode: auto-heal` and `decision_tier: AUTO_HEAL`. For
   `[AI_ASSIST]`, present the plan and wait for confirmation.

### 4.2 Delegated Write Invocation

When the orchestrator invokes a delegated skill for a **write** action:

```yaml
aiops_delegate:
  request_id: "<uuid>"
  parent_intent: "self-heal"
  target_skill: "aws-elb-ops"
  action_mode: "auto-heal"   # or "manual" / "recommend"
  scope: { resource_ids: ["arn:...:my-alb"] }
  parameters:
    operation: "deregister-targets"
    target_group_arn: "arn:..."
    targets: ["i-0abc123"]
  decision_tier: "AUTO_HEAL"
  idempotency_key: "<uuid>"  # delegated skill MUST use this to dedupe
  confirmation_token: "<user-supplied 'confirm'>"
  trace_id: "<opaque>"
```

**Rules**:
- The orchestrator MUST supply `idempotency_key`. The delegated skill
  MUST honor it (skip if already executed with the same key).
- The orchestrator MUST supply `confirmation_token` for any
  `[AI_ASSIST]` or `[MANUAL]` action. The delegated skill MUST verify
  this token matches a recent user prompt before executing.

## 5. Failure Modes

| Failure | Orchestrator response |
|---------|-----------------------|
| Delegated skill returns `status: failed` | Treat as `[AI_ASSIST]`; surface error; halt auto-heal chain |
| Delegated skill not found | HALT; tell user to install the skill |
| Delegated skill returns invalid `aiops_context` | Log schema mismatch; fall back to parsing raw stdout; if still unparseable, `[AI_ASSIST]` |
| Two delegated skills return conflicting facts | `[AI_ASSIST]`; present both findings side-by-side |
| Timeout on delegated call | Retry once with backoff; then `[AI_ASSIST]` |
| Delegated write returns 5xx | Retry 3x with exponential backoff; then `[MANUAL]` |

## 6. Versioning & Compatibility

- The `aiops_delegate` envelope is **versioned** via
  `orchestrator_version`. Delegated skills MUST accept any version they
  don't recognize by ignoring unknown fields (forward-compatible).
- Delegated skills MUST publish their own version in `aiops_context.skill`.
- Breaking changes to the envelope require a major version bump and
  must be reflected in this document.

## 7. Implementation Checklist (for delegated skill authors)

If you maintain an `aws-*-ops` skill and want it to be orchestrator-aware:

- [ ] Add a section in your `SKILL.md` "## AIOps Delegate Contract"
      pointing to this file.
- [ ] Recognize `aiops_delegate:` blocks in user prompts.
- [ ] Always return an `aiops_context:` block in your final response.
- [ ] Honor `idempotency_key` on every write operation.
- [ ] Honor `confirmation_token` on destructive operations.
- [ ] Use `{{env.*}}` only — never echo credentials.
- [ ] Test by running a smoke invocation from the orchestrator against
      your skill in observe mode.

## 8. Cross-product skills (read-only patrol)

These skills are **not** `aws-*-ops` service skills but participate in the same
`aiops_context` contract:

| Skill | Role | Orchestrator uses when… |
|-------|------|-------------------------|
| `aws-aiops-cruise` | Producer: full-chain patrol + chain inference | User wants end-to-end health, pre-launch, emergency cruise; or ≥3 CRITICAL escalation source |
| `aws-topo-discovery` | Producer: static topology + optional health overlay | User needs manifest/HCL/baseline; or cruise `--render-topology` companion |

**Escalation path**: `aws-aiops-cruise` sets `next_skill: aws-aiops-orchestrator` when  
`incidents` contains ≥ 3 `CRITICAL`. Orchestrator MUST NOT auto-heal from cruise alone —  
re-delegate to the appropriate `aws-*-ops` skill with `action_mode: recommend` or `manual` first.

See also: [`aws-aiops-cruise/references/orchestrator-integration.md`](../../aws-aiops-cruise/references/orchestrator-integration.md).

## Parallel GCL (composite orchestration)

When the Orchestrator decomposes a user request into independent subtasks
(e.g., WAF rule update + ALB metric addition), use **Parallel GCL**: fan
out to multiple Generators (each modifies different files/resources), then
a single Critic audits all outputs with cross-referencing.

See `gcl-spec.md` §12 for the full pattern, rules, and anti-patterns.