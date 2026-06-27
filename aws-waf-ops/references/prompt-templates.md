# GCL Prompt Templates — `aws-waf-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-waf-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-waf-ops` |
| `{{skill.service}}` | `waf` |
| `{{skill.aws_cli_svc}}` | `wafv2` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if trace lacks `{{output.safety_confirm_token}}` for any destructive
  op (delete-web-acl, delete-rule-group, delete-ip-set).
- Safety = 0 if any credential-like values appear in the trace (rule A9).
- Correctness = 0 if `Name` / `Id` / `Scope` was not echoed from a
  `get-web-acl` / `list-web-acls` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; trace must record exact literal per operation (`confirm=DELETE_WEB_ACL <name>`, `confirm=DELETE_RULE_GROUP <name>`, etc.) |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | WAF regional ACLs require this region; CloudFront ACLs require `us-east-1` (rule A7) |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER prompt user; NEVER log (rule A9) |
| `{{env.AWS_SESSION_TOKEN}}` | runtime env (when using STS temporary creds) | NEVER log; mask even more aggressively than long-term keys |
| `{{env.AWS_ACCOUNT_ID}}` | runtime env or `aws sts get-caller-identity` | used to validate resource ARN region match |
| `{{output.rubric}}` | `references/rubric.md` of the active skill | injected as a literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | `command`, `args`, `exit_code`, `result` (masked), `post_state`, `errors` |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification of the user request | one of the listed operation types |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL prompt templates for `aws-waf-ops` |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
