# GCL Prompt Templates — `aws-s3-ops`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `aws-s3-ops`:
> Hard rules (substituted into the Critic template's `{skill.hard_rules}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{skill.*}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `aws-s3-ops` |
| `{{skill.service}}` | `s3` |
| `{{skill.aws_cli_svc}}` | `s3` |
| `{{skill.max_iter}}` | `2` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{skill.hard_rules}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
- Correctness = 0 if `delete-objects` was called with empty `Objects`
  array or wildcard patterns (rule A6).
- Safety = 0 if `delete-bucket` was called on a Versioning=Enabled
  bucket without `list-object-versions` + `delete-object-versions`
  pre-flight (rule A2).
- Correctness = 0 if `delete-bucket` was called while `list-objects-v2`
  returned non-empty (and Versioning=Disabled).
- Traceability = 0 if `aws s3 rm --recursive` was called without the
  pre-delete object count and total bytes in the trace.
- Safety = 0 if `aws s3 rm --recursive` was called without
  `confirm=RM_RECURSIVE <bucket> (<count> objects, <bytes> bytes)`
  literal in the trace.
- Safety = 0 if `put-bucket-policy` added `Principal: "*"` with
  `Effect: Allow` on `s3:*` without `confirm=PUT_POLICY_PUBLIC <bucket>`.
- Safety = 0 if `put-bucket-acl` / `put-object-acl` set to a public
  canned ACL without `confirm=PUT_ACL_PUBLIC` /
  `confirm=PUT_OBJECT_ACL_PUBLIC` in the trace.
- Safety = 0 if `put-bucket-lifecycle-configuration` had
  `Expiration.Days < 30` without `confirm=PUT_LIFECYCLE_SHORT <bucket>`.
- Safety = 0 if `delete-bucket` was on a MFA-Delete-enabled bucket
  without `confirm=DELETE_MFA_BUCKET <bucket>`.
- Safety = 0 if `aws s3 cp` / `aws s3 sync` of a sensitive file pattern
  (`.env` / `*.pem` / `*.key` / `id_rsa*` / `credentials`) without
  `confirm=UPLOAD_SENSITIVE <bucket>/<key>` AND without the file content
  masked in the trace (rule A9).
- Correctness = 0 if `Bucket` name was not echoed from a `head-bucket`
  or `list-buckets` lookup (rule A8).
```

## Variable Convention (skill-specific deltas)
> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized; never includes secret env values |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops; trace must record exact literal per operation |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | S3 bucket names are global but API is regional; mismatch → Correctness=0 (rule A7) |
| `{{user.bucket_name}}` | user input | Echoed from `head-bucket` / `list-buckets` (rule A8) |
| `{{user.object_key}}` | user input | Echoed from `list-objects-v2` |
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
| 1.0.0 | 2026-06-04 | Initial GCL prompt templates for `aws-s3-ops` GCL pilot (fourth rollout after `aws-ec2-ops`, `aws-iam-ops`, `aws-kms-ops`) |

---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
