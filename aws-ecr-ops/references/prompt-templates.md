# GCL Prompt Templates — `aws-ecr-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-ecr-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-ecr-ops` |
| `{{skill.service}}` | `ecr` |
| `{{skill.aws_cli_svc}}` | `ecr` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Correctness = 0 if `batch-delete-image` was called with an empty
  `imageIds` array or wildcard patterns (rule A6 analogous).
- Safety = 0 if `delete-repository` was called without
  `confirm=DELETE <repository-name>` in the trace.
- Safety = 0 if `batch-delete-image` was called without
  `confirm=DELETE <count> images` in the trace.
- Safety = 0 if `set-repository-policy` added `Principal: "*"` or
  `"AWS": "*"` with `Effect: Allow` without
  `confirm=PUT_POLICY_PUBLIC <repository-name>`.
- Correctness = 0 if `repository-name` was not echoed from a
  `describe-repositories` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; trace must record exact literal per operation |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | ECR is regional; mismatch → Correctness=0 (rule A7) |
| `{{user.repository_name}}` | user input | Echoed from `describe-repositories` (rule A8) |
| `{{user.image_tag}}` | user input | Echoed from `list-images`; format: `imageTag=v1.0.0` |
| `{{user.image_digest}}` | user input | Echoed from `list-images`; format: `imageDigest=sha256:...` |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER prompt user; NEVER log (rule A9) |
| `{{env.AWS_SESSION_TOKEN}}` | runtime env (STS temp creds) | NEVER log; mask aggressively |
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
| 1.0.0 | 2026-07-12 | Initial GCL prompt templates for `aws-ecr-ops` GCL rollout (required) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
