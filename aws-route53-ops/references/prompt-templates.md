# GCL Prompt Templates — `aws-route53-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-route53-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-route53-ops` |
| `{{skill.service}}` | `route53` |
| `{{skill.aws_cli_svc}}` | `route53` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Correctness = 0 if `delete-hosted-zone` was called while
  `list-resource-record-sets` returned any record other than the
  apex `NS` and `SOA`.
- Safety = 0 if `change-resource-record-sets: DELETE` was called
  without `confirm=DELETE_RECORD <zone>:<name>:<type>` in trace.
- Safety = 0 if `change-resource-record-sets: DELETE` was called
  on a record resolving to a resource serving prod traffic (ALB
  with non-zero `RequestCount` in last 5 min) without
  `confirm=DELETE_PROD_DNS_RECORD <name>`.
- Correctness = 0 if `delete-health-check` was called while any
  CloudWatch alarm references it.
- Correctness = 0 if `delete-reusable-delegation-set` was called
  while any hosted zone references it.
- Correctness = 0 if the hosted zone id / record name was not
  echoed from a `get-hosted-zone` / `list-resource-record-sets`
  lookup (rule A8).
- Correctness = 0 if `--region` is not `us-east-1` (rule A7;
  Route 53 is global).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | Route 53 is global; canonical `us-east-1`; rule A7 |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | masked |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of the listed operation types |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL prompt templates for `aws-route53-ops` (Phase 1, required, not pilot) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
