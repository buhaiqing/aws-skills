# GCL Prompt Templates — `aws-autoscaling-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-autoscaling-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-autoscaling-ops` |
| `{{skill.service}}` | `autoscaling` |
| `{{skill.aws_cli_svc}}` | `autoscaling` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if the trace lacks the `{{output.safety_confirm_token}}` flag for any
  destructive operation (see `rubric.md` §Safety special cases).
- Safety = 0 if `delete-auto-scaling-group` was executed without a
  pre-deletion `describe-auto-scaling-groups` snapshot (rule A8).
- Safety = 0 if `set-desired-capacity` to 0 was executed without user
  confirmation (effectively terminates all instances).
- Safety = 0 if `detach-instances` was executed without explicitly asking
  about `--should-decrement-desired-capacity`.
- Safety = 0 if `UserData` or credential values appear anywhere in the
  trace (rule A9).
- Correctness = 0 if the operation's ASG name does not match the value
  echoed from a `describe-auto-scaling-groups` call (rule A8).
- Correctness = 0 if min > desired or desired > max (invalid state).
- Correctness = 0 if the operation's `--region` does not match
  `{{output.requested_region}}` or `{{env.AWS_DEFAULT_REGION}}` (rule A7).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; gate enforced by Orchestrator; trace must record exact string `confirm=<OP> <id>` |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | rule A7; mismatch → Correctness=0 |
| `{{user.asg_name}}` | user input | Auto Scaling Group name; resolved via describe |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset (see AGENTS.md §Variable Convention) |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER prompt user; NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` of the active skill | injected as a literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | `command`, `args`, `exit_code`, `result`, `post_state`, `errors` |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification of the user request | one of the listed operation types |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-07 | Initial GCL prompt templates for `aws-autoscaling-ops` GCL rollout |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
