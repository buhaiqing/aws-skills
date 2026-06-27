# GCL Prompt Templates — `aws-elb-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-elb-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-elb-ops` |
| `{{skill.service}}` | `elb` |
| `{{skill.aws_cli_svc}}` | `elbv2` |
| `{{skill.max_iter}}` | `3` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if `deregister-targets` batch was ≥ 50% of healthy
  targets without `confirm=DEREGISTER_DRAIN <tg-arn> count=<n>/<total>`.
- Safety = 0 if `deregister-targets` removed ALL healthy targets
  without `confirm=DEREGISTER_ALL <tg-arn>`.
- Correctness = 0 if `delete-load-balancer` was called while any
  listener exists.
- Correctness = 0 if `delete-rule` was called on the **default rule**.
- Correctness = 0 if `delete-target-group` was called while any LB /
  listener rule references it.
- Correctness = 0 if `delete-trust-store` was called while any
  listener uses it.
- Safety = 0 if `modify-load-balancer-attributes` disabled
  `deletion_protection` without `confirm=DISABLE_DELETION_PROTECTION`.
- Correctness = 0 if LB arn / target id / listener arn not echoed
  from a `describe-*` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | ALB / NLB are regional; rule A7 |
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
| 1.0.0 | 2026-06-04 | Initial GCL prompt templates for `aws-elb-ops` (Phase 1, **recommended**, not pilot) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
