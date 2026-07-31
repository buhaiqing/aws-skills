# Generation Checklist & Process

## Generation Process Overview

```
Input → Analyze Sources → Create Layout → Populate Files → Verify
```

## Directory Layout

```
aws-[service]-ops/
├── SKILL.md                    # ~70–120 lines: triggers, scope, flow overview
├── references/
│   ├── aws-cli-usage.md        # CLI commands + JSON paths (verified)
│   ├── boto3-sdk-usage.md      # SDK patterns (no docstrings — TE-2)
│   ├── core-concepts.md        # Service architecture, quotas
│   └── troubleshooting.md      # Compact error table (TE-3)
└── assets/
```

## Quick Start Checklist

### P0 — MUST Complete

- [ ] Product name + primary resource type identified
- [ ] Official AWS docs URL provided
- [ ] AWS CLI support verified (`aws [service] help`)
- [ ] SDK (boto3) module identified
- [ ] Trigger & Scope with SHOULD/SHOULD-NOT defined
- [ ] `{{env.*}}` placeholders (no secret literals)
- [ ] Execution flows: Pre-flight → Execute → Validate → Recover
- [ ] Safety gates for destructive operations
- [ ] Dual-path: AWS CLI (primary) + boto3 SDK (fallback)
- [ ] **[TE] Token Efficiency applied** — C6 gates MUST pass: `SKILL.md` ≤120 lines, no hard-coded static tables >5 rows (TE-1), JSON paths declared once (TE-4), no cross-file duplicated flow (TE-6), boto3 no docstrings (TE-2), compact error table (TE-3). Run `python3 scripts/te_gate.py <skill> --strict`.
- [ ] **[GCL] Destructive-op classification recorded** — see [`gcl-integration.md`](gcl-integration.md). If any op matches a `required` row in `AGENTS.md` §11.5, ship `references/rubric.md` + `references/prompt-templates.md` + `## Quality Gate (GCL)`.
- [ ] **[GCL] Prompt templates use the shared skeleton** — see [`gcl-integration.md`](gcl-integration.md) §Using the shared prompt skeleton. `prompt-templates.md` is a thin specialization of [`prompt-skeletons.md`](prompt-skeletons.md).
- [ ] **[CADL] 沉淀钩子注入** — append to generated `SKILL.md`: `> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。`

### P1 — SHOULD Complete

- [ ] Cross-service delegation documented
- [ ] Idempotency behavior documented
- [ ] Response JSON paths verified with real runs
- [ ] Troubleshooting error code table
- [ ] **[TE] core-concepts.md** — avoid static version/port/state tables; use API commands instead
- [ ] **[TE] boto3-sdk-usage.md** — omit docstrings; use inline comments
- [ ] **[TE] example-config.yaml** — use YAML anchors for shared fields

## Key Principles

| Principle | Enforcement |
|-----------|-------------|
| **CLI-first with SDK fallback** | Primary path: AWS CLI; fallback: boto3 after 3 CLI failures |
| **OpenAPI accuracy** | All fields traceable to AWS API docs |
| **Safety gates** | Human confirmation before destructive operations |
| **Credential isolation** | Only `{{env.*}}` placeholders; never real secrets |
| **TE: Token Efficiency** | See [`token-efficiency-guide.md`](token-efficiency-guide.md) |

## When to Use (Quick Reference)

| Use This Skill | Do NOT Use |
|----------------|------------|
| Creating a new AWS service skill | Executing AWS operations directly |
| Aligning existing skill to template | Billing-only or IAM-only tasks |
| Updating skill after AWS API changes | Non-AWS cloud work |
