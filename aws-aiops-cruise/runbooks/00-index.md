# Runbook Index — AWS Full-Chain AIOps Cruise

> Entry index. Each runbook defines CLI steps, thresholds, and report templates for one patrol scenario.

## Scenario Overview

| ID | Scenario | Trigger | Frequency | Risk | ETA |
|----|----------|---------|-----------|------|-----|
| 01 | Daily health check | schedule / manual | every 6h | Low | 5–15 min |
| 02 | Emergency troubleshoot | alarm / ticket | on-demand | High | 3–8 min |
| 03 | Capacity planning | schedule | weekly | Medium | 5–10 min |
| 04 | Pre-launch check | manual | before event | High | 10–20 min |
| 05 | Slow query diagnosis | alarm / manual | on-demand | Medium | 5–15 min |
| 06 | DB connection storm | connections > 85% | on-demand | High | 3–8 min |
| 07 | Bottleneck localization | user report | on-demand | High | 5–12 min |
| 08 | ElastiCache performance | memory > 80% | on-demand | Medium | 3–8 min |
| 09 | Auto Scaling optimization | forecast / manual | on-demand | Medium | 3–10 min |

## Universal Safety (non-overridable)

| Action | Policy |
|--------|--------|
| Delete / terminate / stop / modify | **FORBIDDEN** — Safety = 0 |
| SG / NACL / IAM changes | **FORBIDDEN** — recommend only |
| Credential output | Mask `AKIA******` |
| Full-account scan | Requires explicit `scope=full` |
| Default untagged sweep | HALT unless user confirms |

## Three-Phase Pattern

```
Phase 1: Sniff + topology  → Resource scope + inventory + sniff report
Phase 2: Deep collection   → CloudWatch 6h + WoW; optional SSM / PI / CloudTrail
Phase 3: Infer + report      → inference-rules.md → Markdown + JSON incidents
```

## Acceptance Grades

| Grade | Meaning |
|-------|---------|
| PASS | All checks within Warning thresholds |
| WARNING | Any metric in Warning band or rising trend |
| CRITICAL | Critical threshold or service unavailable |
| ERROR | Patrol script failed (API/auth) |

## Layout

```
aws-aiops-cruise/
├── SKILL.md
├── runbooks/
│   ├── 00-index.md
│   ├── 01-daily-health-check.md … 09-auto-scaling-optimization.md
│   └── scripts/
│       ├── daily-health-check.py
│       └── cruise-orchestrator.py
├── scripts/agents/perceive/
├── references/
└── reports/templates/
```
