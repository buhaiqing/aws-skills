---
name: aws-aiops-copilot
description: >-
  Unified AIOps entry point. Use when a user wants a health check, root-cause
  analysis, or patrol across AWS services and needs the right AIOps skill
  selected and delegated (single-service patrol vs cross-service correlation).
license: MIT
compatibility: >-
  AWS CLI v2, valid AWS credentials, network access to AWS endpoints;
  delegates to aws-aiops-cruise and aws-aiops-orchestrator.
metadata:
  author: aws
  version: "0.1.0"
  status: "design-draft"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible
  type: composite
  provides:
    - "aiops-health-check"
    - "aiops-rca"
    - "aiops-patrol"
  delegate:
    aws-aiops-cruise:
      - "health-check"
      - "rca"
      - "patrol"
    aws-aiops-orchestrator:
      - "cross-service-rca"
  cross_skill_deps:
    - aws-aiops-cruise
    - aws-aiops-orchestrator
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
---

# AWS AIOps Copilot (Composite L2 Skill)

> **One-liner**: Unified AIOps entry point that selects and delegates the right
> AIOps skill — `aws-aiops-cruise` for single-service patrol / RCA, or
> `aws-aiops-orchestrator` for cross-service correlation. **Orchestrates only;
> contains no service-level operation logic.**

## Layering Contract (type / provides / delegate)

This skill is **L2 (composite)**. It declares `metadata.type: composite` and a
`delegate` map, and **orchestrates only**. It contains:

- **No** service-level operation logic (no metric/log/event queries, no inference rules).
- **No** `scripts/`, no new collectors, no new AIOps rules.
- **No** mutating AWS calls — it is doc-only and routes intents to base skills.

Delegated targets (both directories verified to exist in this repo):

| Delegate skill | Operations handled | Role |
|----------------|--------------------|------|
| `aws-aiops-cruise` | `health-check`, `rca`, `patrol` | Single-service / full-chain read-only patrol + chain inference |
| `aws-aiops-orchestrator` | `cross-service-rca` | Cross-service correlation, multi-skill RCA orchestration |

Per Charter C7, every `delegate` target directory (`aws-aiops-cruise`,
`aws-aiops-orchestrator`) must exist — both are present.

## Trigger & Scope

**SHOULD Use When**:

- User wants a unified AIOps entry point ("check my AWS health", "why is prod slow").
- Request maps cleanly to a single-service patrol / RCA → delegate to `aws-aiops-cruise`.
- Symptoms span multiple services and need correlation → delegate to `aws-aiops-orchestrator`.

**SHOULD NOT Use When**:

- Direct single-service operations (create/modify/delete, per-resource runbooks) →
  delegate to the appropriate base `aws-<svc>-ops` skill.
- The user already named a specific base skill → load that skill directly.

## Cross-Skill References

| Copilot operation | Delegated skill | Notes |
|-------------------|-----------------|-------|
| `aiops-health-check` | `aws-aiops-cruise` | Read-only full-chain patrol |
| `aiops-rca` | `aws-aiops-cruise` | RCA within one service / chain |
| `aiops-patrol` | `aws-aiops-cruise` | Scheduled / ad-hoc patrol |
| `aiops-cross-service-rca` | `aws-aiops-orchestrator` | Correlation across services |

See [`references/delegate-routing.md`](references/delegate-routing.md) for the
full routing decision table.

## Quality Gate (GCL)

| Dimension | Threshold | Notes |
|-----------|-----------|-------|
| Correctness | ≥ 0.5 | Delegation targets match live `delegate` map |
| Safety | = 1 | Doc-only; no AWS calls |
| Idempotency | ≥ 0.8 | Same intent → same delegation plan |
| Traceability | ≥ 0.8 | `run_id`, delegation decisions logged |
| Spec Compliance | ≥ 0.8 | Layering contract + Charter C7 |
| **Delegation Correctness** | = 1 | Every `delegate` dir exists; every op within target's `provides`/`cross_skill_deps` |

GCL: **recommended**, `max_iter=3`. Prompts: [`references/prompt-templates.md`](references/prompt-templates.md). Rubric: [`references/rubric.md`](references/rubric.md).

> L2 rubric adds **Delegation Correctness** (design P4): a missing delegate
> directory or an operation outside the target skill's scope is a BLOCKER.

## Token Efficiency Guidelines

Follow the 6 TE rules from `aws-skill-generator/references/prompt-skeletons.md`
and `AGENTS.md` §14:

- TE-1: No hardcoded version/port/state tables.
- TE-2: No SDK docstrings; inline comments only.
- TE-3: Compact error tables (single row where possible).
- TE-4: JSON paths / delegate map centralized at file top.
- TE-5: Prefer YAML anchors in any example config.
- TE-6: No duplicated flows across `SKILL.md` and `references/`.
