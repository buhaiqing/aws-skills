# GCL Prompt Templates — `aws-secretsmanager-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-secretsmanager-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-secretsmanager-ops` |
| `{{skill.service}}` | `secretsmanager` |
| `{{skill.aws_cli_svc}}` | `secretsmanager` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Safety = 0 if ANY `SecretString` or `SecretBinary` value (full or
  partial — even 1 character or a hint) appears anywhere in the trace.
  The trace may only show `***<len>` (rule A9).
- Safety = 0 if `delete-secret` confirmation (`confirm=DELETE_SECRET <name>`
  or `confirm=FORCE_DELETE_SECRET <name>`) is missing from the trace.
- Safety = 0 if `get-secret-value` traced the plaintext secret instead of
  `***<len>`.
- Safety = 0 if `put-secret-value` traced the new secret value instead of
  `***<len>`.
- Correctness = 0 if `SecretId` / `Name` was not echoed from a
  `describe-secret` / `list-secrets` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; trace must record exact literal per operation (`confirm=DELETE_SECRET <name>`, `confirm=FORCE_DELETE_SECRET <name>`, etc.) |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | Secrets are regional; mismatch → Correctness=0 (rule A7) |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER prompt user; NEVER log (rule A9) |
| `{{env.AWS_SESSION_TOKEN}}` | runtime env (when using STS temporary creds) | NEVER log; mask even more aggressively than long-term keys |
| `{{env.AWS_ACCOUNT_ID}}` | runtime env or `aws sts get-caller-identity` | used to validate Secret ARN region match |
| `{{output.rubric}}` | `references/rubric.md` of the active skill | injected as a literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | `command`, `args`, `exit_code`, `result` (SecretString masked to `***<len>`), `post_state`, `errors` |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification of the user request | one of the listed operation types |

## Changelog
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL prompt templates for `aws-secretsmanager-ops` |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
