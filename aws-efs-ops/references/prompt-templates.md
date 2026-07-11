# GCL Prompt Templates — `aws-efs-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-efs-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-efs-ops` |
| `{{skill.service}}` | `efs` |
| `{{skill.aws_cli_svc}}` | `efs` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Correctness = 0 if `delete-file-system` was called while mount targets
  or access points still exist — must pre-flight `describe-mount-targets`
  and `describe-access-points` and delete all dependencies first.
- Safety = 0 if `delete-file-system` was called without
  `confirm=DELETE_FS <file-system-id>` in the trace.
- Safety = 0 if `delete-mount-target` was called without
  `confirm=DELETE_MOUNT_TARGET <mount-target-id>` in the trace.
- Safety = 0 if `delete-access-point` was called without
  `confirm=DELETE_ACCESS_POINT <access-point-id>` in the trace.
- Safety = 0 if `put-file-system-policy` added `Principal: "*"` or
  `"AWS": "*"` with `Effect: Allow` without
  `confirm=PUT_POLICY_PUBLIC <file-system-id>`.
- Correctness = 0 if `file-system-id` was not echoed from a
  `describe-file-systems` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; trace must record exact literal per operation |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | EFS is regional; mismatch → Correctness=0 (rule A7) |
| `{{user.file_system_id}}` | user input | Echoed from `describe-file-systems` (rule A8) |
| `{{user.mount_target_id}}` | user input | Echoed from `describe-mount-targets` |
| `{{user.access_point_id}}` | user input | Echoed from `describe-access-points` |
| `{{user.file_system_token}}` | agent-generated | Fresh UUID v4 for `create-file-system --creation-token` |
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
| 1.0.0 | 2026-07-12 | Initial GCL prompt templates for `aws-efs-ops` GCL rollout (required) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
