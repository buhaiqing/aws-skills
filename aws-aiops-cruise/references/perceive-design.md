# Perceive Layer Design — aws-aiops-cruise

## Purpose

Seven scheduled/on-demand **read-only** agents collect signals before runbook inference. Each agent is a thin shell wrapper calling Python runbooks or sibling skills.

## Architecture

```
scripts/agents/perceive/__init__.sh
├── infra/
│   ├── healthcruise.sh   → daily-health-check.py
│   ├── toposcan.sh       → aws-topo-discovery/topo-scan.sh
│   └── configdrift.sh    → aws-topo-discovery/baseline-manager.py diff
├── cost/
│   └── costwatch.sh      → Cost Explorer CLI (read-only)
├── security/
│   ├── securityscan.sh   → SG audit + GuardDuty + Security Hub counts
│   └── audittrail.sh     → CloudTrail lookup-events
└── advisor/
    └── advisorscan.sh    → support/trusted-advisor checks (where API available)
```

## Delegation matrix

| Agent | Primary data source | Delegated skill |
|-------|---------------------|-----------------|
| HealthCruise | CloudWatch + inventory | (internal runbook) |
| TopoScan | EC2/ELB/RDS APIs | `aws-topo-discovery` |
| ConfigDrift | Baseline manifest | `aws-topo-discovery` |
| CostWatch | Cost Explorer | read-only CLI |
| SecurityScan | EC2 SG + GuardDuty | `aws-guardduty-ops`, `aws-securityhub-ops` |
| AuditTrail | CloudTrail | `aws-cloudtrail-ops` |
| AdvisorScan | Trusted Advisor / Compute Optimizer | read-only CLI |

## Runtime output

All agents write under `${RUNTIME_AUDIT_DIR}/perceive/` (default: `audit-results/perceive/`).

## Scheduling (recommended)

| Agent | Cron |
|-------|------|
| HealthCruise | `0 */6 * * *` |
| TopoScan | `0 2 * * *` |
| ConfigDrift | after TopoScan or on-demand |
| CostWatch | `0 9 * * *` |
| SecurityScan | `0 8 * * *` |
| AuditTrail | `0 */4 * * *` or alarm-driven |
| AdvisorScan | `0 9 * * 1` |

## vs aws-aiops-orchestrator

| Skill | Role |
|-------|------|
| **aws-aiops-cruise** | Scheduled patrol, standardized incidents, runbook workflows |
| **aws-aiops-orchestrator** | Cross-service RCA, multi-skill remediation, cost forecast orchestration |

Cruise findings may feed orchestrator as `aiops_context.facts[]` for escalation (≥3 CRITICAL).
