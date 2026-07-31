# Operational Scenarios

Worked examples showing how the orchestrator routes intents through the
6-layer model. See [`architecture.md`](architecture.md) for layer definitions.

## Scenario 1 — "线上有问题吗？" (health overview)

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

## Scenario 2 — "为什么 502 飙升？" (cross-service RCA)

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
Layer 3: build timeline; correlate changes with symptom onset; build causal graph:
  - aws-topo-discovery → get-causal-graph via scripts/causal-graph.sh
  - aws-topo-discovery → find-root-cause via scripts/causal_inference.py
  - Delegate to product-level skill for targeted deep diagnosis
Layer 4: emit top-3 hypotheses ranked by likelihood
Layer 5: optionally trigger runbook (auto-heal tier only)
Layer 6: record RCA outcome for future learning
```

## Scenario 3 — "下个月账单多少？" (cost forecast)

```
Intent: cost-forecast, time_window=next_30d
Layer 1: delegate to
  - aws-cloudwatch-ops (FORECAST on cost-relevant metrics)
  - Cost Explorer via direct CLI (GetCostForecast, GetCostAndUsage)
Layer 2: combine → trend + seasonality + one-time items
Layer 3: flag top-3 cost drivers + projected delta vs current month
Layer 4: recommendations: rightsizing, idle resource cleanup, RI/SP coverage
Layer 5: none (recommend only)
Layer 6: persist forecast for trend tracking
```

## Scenario 4 — "这个变更影响什么？" (change impact)

```
Intent: change-impact, change="delete SG sg-prod-web"
Layer 0: scope graph traversal → find resources referencing this SG
Layer 1: enumerate dependent resources (ELB, EC2, RDS, Lambda ENI, etc.)
Layer 3: trace blast radius → direct + transitive
Layer 4: classify risk → if any prod resource, force [MANUAL]
Layer 5: none unless confirmed
```

## Scenario 5 — "自动修复生产" (coordinated self-heal)

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

## Scenario 6 — "自动遏制失陷实例 / 根账号使用" (security incident containment)

```
Intent: self-heal, scope=security-rule (SD-01 / SD-07), action_mode=auto-heal
Layer 0: parse SD-01 (GuardDuty CRITICAL on EC2) or SD-07 (root user event)
        → look up trigger_runbook in detection-rules.md
        → match RB-SEC-01 (compromised instance) or RB-SEC-18 (root account)
Layer 1: delegate to
  - aws-guardduty-ops (RB-SEC-01 S1/S5)  / aws-cloudtrail-ops (RB-SEC-18 S1)
  - aws-ec2-ops (RB-SEC-01 S3/S4)
  - aws-cloudtrail-ops (RB-SEC-01 S2)
  - aws-cloudwatch-ops (RB-SEC-18 S4)
Layer 2: enrich finding/event with context (account/region, ENIs, source IP)
Layer 3: correlate recent API activity for forensic timeline
Layer 4: classify — all security runbooks force [AI_ASSIST] tier;
        destructive EC2 write (RB-SEC-01 S4) requires confirmation token
        before execution; RB-SEC-18 S4/S5 are local mutates (idempotent)
Layer 5: execute RB-SEC-01 S1-S6 / RB-SEC-18 S1-S5 sequentially
        → halt at any halt branch (S3/S4 of RB-SEC-01; S1 of RB-SEC-18)
        → S6/S7 emit mitigation proposals only (no writes)
Layer 6: track MTTR; archive finding (RB-SEC-01 S5); post-check SSM reachability
        and zero new outbound connections for PT30M
```
