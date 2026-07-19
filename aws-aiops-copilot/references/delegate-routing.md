# Delegate Routing — How the Copilot Invokes AIOps Skills

## 1. Purpose

`aws-aiops-copilot` is an **L2 composite** skill. It does **not** execute AWS
operations and contains **no** service-level logic. It selects the correct
delegated AIOps skill from the user's intent and hands off.

This document defines the **routing decision table**: given a user request,
route to either `aws-aiops-cruise` (single-service patrol / RCA) or
`aws-aiops-orchestrator` (cross-service correlation).

## 2. Delegate Contract

The copilot reads `metadata.delegate` from its own frontmatter:

```yaml
delegate:
  aws-aiops-cruise:      # dir MUST exist (Charter C7)
    - "health-check"
    - "rca"
    - "patrol"
  aws-aiops-orchestrator:  # dir MUST exist (Charter C7)
    - "cross-service-rca"
```

Every delegated operation MUST fall within the target skill's declared
`provides` / `cross_skill_deps`. The copilot never invents operations outside
this map. The copilot forwards the request to the chosen skill using that
skill's own invocation contract (e.g.
[`aws-aiops-orchestrator/references/delegate-routing.md`](../aws-aiops-orchestrator/references/delegate-routing.md)).

## 3. Routing Matrix

| User request | Signals | Route to | Operations |
|--------------|---------|----------|------------|
| Single-service health / patrol | one service, metrics/logs/events, "check ALB health", "daily patrol" | `aws-aiops-cruise` | `health-check`, `rca`, `patrol` |
| Full-chain read-only cruise | "is the full stack healthy", "pre-launch check", "emergency troubleshoot" | `aws-aiops-cruise` | `patrol`, `health-check` |
| RCA within one service / chain | "why is RDS slow", "ALB 5xx" (single service) | `aws-aiops-cruise` | `rca` |
| Symptoms span multiple services | "why is the site slow", "502 spike across stack", needs correlation graph | `aws-aiops-orchestrator` | `cross-service-rca` |
| Cross-service cost / capacity forecast | "predict next quarter cost", "what will fail next month" | `aws-aiops-orchestrator` | `cross-service-rca` |

### 3.1 Decision rules

1. **Single service, observe-only** → `aws-aiops-cruise`.
2. **Unknown layer / symptoms across ≥ 2 services** → `aws-aiops-orchestrator`.
3. If `aws-aiops-cruise` escalates (`next_skill: aws-aiops-orchestrator`,
   ≥ 3 CRITICAL), the copilot re-delegates to `aws-aiops-orchestrator`.

## 4. Failure Modes

| Failure | Copilot response |
|---------|------------------|
| Delegated skill directory missing | HALT; report Charter C7 violation |
| Request matches no route | Ask user to clarify scope (single vs cross-service) |
| Delegated skill returns `status: failed` | Surface error; do not retry AWS calls |

## 5. Versioning & Compatibility

- Copilot runtime-agnostic: any agent globs `aws-*-ops/SKILL.md` and reads
  `metadata.delegate`.
- Breaking changes to the delegate map require a version bump in
  `metadata.version` and an update to this document.
