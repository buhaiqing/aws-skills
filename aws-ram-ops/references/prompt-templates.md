# GCL Prompt Templates — `aws-ram-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-ram-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-ram-ops` |
| `{{skill.service}}` | `ram` |
| `{{skill.aws_cli_svc}}` | `ram` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if missing `confirm=` for destructive ops
- Safety = 0 if `delete-resource-share` done with active associations without disassociating first
- Correctness = 0 if no `get-resource-shares` echo-back (A8)
- Correctness = 0 if region mismatch (A7)
- Safety = 0 if credentials in trace (A9)
- Traceability = 0 if sts not first (A10)
- Spec Compliance = 0 if external principals without --allow-external-principals
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | user confirmation | `confirm=<OP> <id>` |
| `{{user.region}}` | user or env | rule A7 |
| `{{output.rubric}}` | rubric.md | injected |
| `{{output.generator_output}}` | previous Generator | empty on iter 1 |
| `{{output.trace}}` | execution buffer | command, args, result, post_state |
| `{{output.critic_scores}}` | previous Critic | empty on iter 1 |
| `{{output.iter}}` | counter | starts at 1 |
| `{{output.operation}}` | classified op | see enum above |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
