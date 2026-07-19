# GCL Prompt Templates — `aws-aiops-copilot`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **composite-skill deltas** for `aws-aiops-copilot`:
> Hard rules (substituted into the Critic template's `{{skill.hard_rules}}`),
> and Variable Convention deltas. The three canonical templates (Generator /
> Critic / Orchestrator) are referenced from the skeleton file; do not
> duplicate them here.
>
> **Orchestration-only skill** — no AWS operations, no Confirmation Strings table.

## Skill metadata (used by skeleton `{{skill.*}}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-aiops-copilot` |
| `{{skill.service}}` | `aws-aiops-copilot` (composite L2 AIOps entry point) |
| `{{skill.aws_cli_svc}}` | none — delegates to `aws-aiops-cruise` / `aws-aiops-orchestrator` |
| `{{skill.max_iter}}` | `3` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{{skill.hard_rules}}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Delegation Correctness = 0 if any `metadata.delegate` directory does not
  exist on disk (Charter C7 violation).
- Delegation Correctness = 0 if any delegated operation is not declared in the
  target skill's `provides` / `cross_skill_deps`.
- Correctness = 0 if the copilot emits any AWS CLI / SDK call (doc-only skill;
  it must delegate instead).
- Safety = 0 if any `create|delete|modify|terminate|stop|start|authorize|revoke`
  API call appears in the trace.
```

## Variable Convention (skill-specific deltas)

> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.intent}}` | User input | Raw AIOps request (health-check / rca / patrol / cross-service-rca) |
| `{{user.services}}` | User input | Service list — empty = copilot must infer single vs cross-service |
| `{{output.delegated_skill}}` | Copilot decision | `aws-aiops-cruise` or `aws-aiops-orchestrator` |
| `{{output.delegated_ops}}` | Copilot decision | One or more ops from `metadata.delegate` |
| `{{output.run_id}}` | Copilot | Opaque id for trace correlation |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-19 | Initial L2 composite copilot skill (delegates to cruise + orchestrator). |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
