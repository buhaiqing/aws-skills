# GCL Prompt Templates — `aws-eventbridge-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
 > This file contains only the **service-specific deltas** for `aws-eventbridge-ops`:
 > Hard rules (substituted into the Critic template's `{{skill.hard_rules}}`),
 > Confirmation strings, and Variable Convention deltas. The three canonical
 > templates (Generator / Critic / Orchestrator) are referenced from the
 > skeleton file; do not duplicate them here.
 
 ## Skill metadata (used by skeleton `{{skill.*}}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-eventbridge-ops` |
| `{{skill.service}}` | `eventbridge` |
| `{{skill.aws_cli_svc}}` | `eventbridge` |
| `{{skill.max_iter}}` | `3` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

 ## Hard rules (Critic template injection)
 
 > These bullets are substituted into the Critic template's
 > `{{skill.hard_rules}}` slot in `prompt-skeletons.md` §2.
 > They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if missing `confirm=` for destructive ops
- Safety = 0 if `delete-rule` done without `remove-targets` first
- Correctness = 0 if no `describe-*` echo-back (A8) or region mismatch (A7)
- Safety = 0 if credentials in trace (A9); Traceability = 0 if sts not first (A10)
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Source | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | user | `confirm=<OP> <id>` |
| `{{user.region}}` | user or env | A7 |
| `{{output.rubric}}` | rubric.md | injected |
| `{{output.generator_output}}` | previous Generator | empty on iter 1 |
| `{{output.trace}}` | execution buffer | |
| `{{output.critic_scores}}` | previous Critic | empty on iter 1 |
| `{{output.iter}}` | counter | starts at 1 |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
