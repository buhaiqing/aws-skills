# GCL Prompt Templates — `<SKILL_NAME>`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `<SKILL_NAME>`:
> Hard rules (substituted into the Critic template's `{{skill.hard_rules}}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{{skill.*}}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `<SKILL_NAME>` (e.g. `aws-rds-ops`) |
| `{{skill.service}}` | `<SERVICE>` (e.g. `rds`) |
| `{{skill.aws_cli_svc}}` | `<AWS_CLI_SVC>` (e.g. `rds`; overrides for vpc→ec2, elb→elbv2, waf→wafv2) |
| `{{skill.max_iter}}` | `<2|3>` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |

## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{{skill.hard_rules}}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).
>
> **Rule format:** every bullet MUST cite a `gcl-spec.md` §8 A-id
> (A1–A16) OR a named operation in `references/rubric.md`. Bare prose
> without a reference becomes untrackable.

```text
<!--
  Replace this block with one bullet per service-specific Hard rule.
  Delete the comments before merging. Example:

- Safety = 0 if `delete-<resource>` was called without
  `confirm=DELETE_<RESOURCE> <id>` literal in the trace (rule A<N>).
- Correctness = 0 if `<resource-id>` was not echoed from a
  `describe-<resource>` / `list-<resource>` lookup (rule A8).
-->
```

## Confirmation Strings

> Mandatory for every destructive op. Non-destructive skills may omit
> the table entirely. Format: literal `confirm=<OP> <resource>` token
> that the user must type; the Generator captures it into
> `{{output.safety_confirm_token}}` for the Critic to verify.

| Operation | Confirmation token |
|---|---|
| `delete-<resource>` | `confirm=DELETE_<RESOURCE> <id>` |
| `<other-destructive-op>` | `confirm=<OP>_<RESOURCE> <id>` |

## Variable Convention (skill-specific deltas)

> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)
> are defined once in `prompt-skeletons.md` §Variable convention.
> Only entries unique to this skill are listed below.

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.<service-specific-field>}}` | <source> | <why this skill needs it> |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | <YYYY-MM-DD> | Initial GCL prompt templates (shared skeleton specialization; see `aws-skill-generator/SKILL.md` §Using the shared prompt skeleton) |

---

> See [`prompt-skeletons.md`](../../references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.

---

## How to use this template

```bash
# 1. Copy this template into your new skill
cp aws-skill-generator/assets/new-skill-template/prompt-templates.md \
   <SKILL_NAME>/references/prompt-templates.md

# 2. Fill in the four `<...>` placeholders at the top:
#    - <SKILL_NAME>     (e.g. aws-rds-ops)
#    - <SERVICE>        (e.g. rds)
#    - <AWS_CLI_SVC>    (e.g. rds; override for vpc/elb/waf — see table)
#    - <2|3>            (the skill's max_iter from metadata.gcl.max_iter)

# 3. Replace the comment block in "Hard rules (Critic template injection)"
#    with one bullet per service-specific Hard rule. Cite an A-id from
#    gcl-spec.md §8 (A1–A16) or a named operation in rubric.md.

# 4. Add one row to "Confirmation Strings" per destructive op.

# 5. Add skill-specific placeholders to "Variable Convention (deltas)".

# 6. Verify the skeleton + delta merge at runtime:
python3 scripts/gcl_runner.py --skill <SKILL_NAME> --print-critic
# expect: ~70 lines of rendered Critic prompt with your Hard rules
#         injected before the canonical A7/A8/A9/A10 block

# 7. Verify the dry-run extraction captures your Hard rules:
python3 scripts/_sync_prompt_skeletons.py --skill <SKILL_NAME> --dry-run \
  | grep -E '^## Hard rules \(Critic|^```text$' | head -2
# expect: 2 lines — `## Hard rules (Critic template injection)` + fence

# 8. Run the runner self-test end-to-end:
python3 scripts/gcl_runner.py --skill <SKILL_NAME> --request "list" --self-test
# expect: status: PASS  iter: 1
```

If any step produces unexpected output, the file is not properly wired
into the GCL shared skeleton — fix before merging.

See [`aws-skill-generator/SKILL.md`](../../SKILL.md) §Using the shared
prompt skeleton for the full rules and rationale.
