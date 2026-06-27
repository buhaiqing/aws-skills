# GCL Prompt Templates — `aws-securityhub-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-securityhub-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-securityhub-ops` |
| `{{skill.service}}` | `securityhub` |
| `{{skill.aws_cli_svc}}` | `securityhub` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if `disable-security-hub` was called without
  `confirm=DISABLE_SECURITY_HUB` in the trace.
- Safety = 0 if `delete-insight` was called without
  `confirm=DELETE_INSIGHT <arn>` in the trace.
- Safety = 0 if `delete-action-target` was called without
  `confirm=DELETE_ACTION_TARGET <arn>` in the trace.
- Safety = 0 if `disable-import-findings-for-product` was called without
  `confirm=DISABLE_PRODUCT <arn>` in the trace.
- Safety = 0 if `delete-automation-rule` was called without
  `confirm=DELETE_AUTOMATION_RULE <arn>` in the trace.
- Safety = 0 if `delete-configuration-policy` was called without
  `confirm=DELETE_POLICY <id>` in the trace.
- Correctness = 0 if resource ARN/ID in the request was not echoed from a
  `describe-*` / `get-*` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; trace must record exact literal per operation |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | Security Hub is regional; mismatch -> Correctness=0 (rule A7) |
| `{{user.insight_arn}}` | user input | required for insight operations |
| `{{user.action_target_arn}}` | user input | required for action target operations |
| `{{user.product_subscription_arn}}` | user input | required for product subscription operations |
| `{{user.automation_rule_arn}}` | user input | required for automation rule operations |
| `{{user.policy_id}}` | user input | required for configuration policy operations |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | `command`, `args`, `exit_code`, `result` (masked), `post_state`, `errors` |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of the listed operation types |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial GCL prompt templates for `aws-securityhub-ops` (required) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
