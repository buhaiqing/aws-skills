# Generator ↔ GCL Integration

> **When to read this section:** before declaring a new skill "done", and
> before any change to a skill whose frontmatter carries a `gcl.enabled: true`
> block. Full spec: [`gcl-spec.md`](gcl-spec.md). Top-level index: `AGENTS.md` §11.

## Why this matters

The **Generator-Critic-Loop (GCL)** is the repository's adversarial
quality gate for high-side-effect AWS operations. The Generator skill
(this one) is the **only** place a new skill can opt in or out. If a
generated skill has a destructive op (`delete-*`, `terminate-*`,
`deregister-*`, `revoke-*`, `detach-*`, IAM / KMS / DDL) and is missing
GCL scaffolding, **the skill is incomplete** — a downstream agent will
execute that op without an independent critic.

## Destructive-op classification

For every operation listed in the new skill's `## Operations` section,
classify it as one of:

| Class | Examples | GCL required? |
|---|---|---|
| `read-only` | `describe-*`, `list-*`, `get-*` | no |
| `create` | `create-*`, `run-instances`, `put-*` (idempotent) | no (still passes through GCL with relaxed Safety) |
| `mutate` | `update-*`, `modify-*`, `put-key-policy` | **yes** if state-changing; no if purely cosmetic |
| `destructive` | `delete-*`, `terminate-*`, `deregister-*`, `revoke-*`, `detach-*` | **yes, always** |

When in doubt, classify up (treat cosmetic `update-*` as `destructive` if
the change is hard to reverse). The Per-Skill Defaults table in
`AGENTS.md` §11.5 is the source of truth for the destructive list of
each existing service — match your new skill's row to it.

## When a new skill MUST ship GCL scaffolding

If **any** op is `destructive` (or matches a `required` row in §11.5),
the generated skill MUST include all four of:

1. **`metadata.gcl` block in `SKILL.md` frontmatter** — see frontmatter template below.
2. **`## Quality Gate (GCL)` section in `SKILL.md`** — see existing
   pilots (`aws-ec2-ops`, `aws-iam-ops`, `aws-kms-ops`) for the exact layout.
3. **`references/rubric.md` (v1)** — 5-dimension rubric + per-op overrides.
4. **`references/prompt-templates.md` (v1)** — thin specialization of shared skeleton.

#### Frontmatter template (add to `metadata:`)

```yaml
metadata:
  gcl:
    enabled: true
    class: required            # or recommended / optional
    max_iter: 2                # 2 for destructive, 3 for recommended, 5 for optional
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false               # true ONLY for the first 1–3 skills of a rollout batch
```

> **Do NOT set `pilot: true`** unless you are deliberately starting a
> new rollout wave. Pilots are coordination markers for changelogs.

## When a new skill does NOT need GCL

If every op is `read-only` or `create` (no destructive, no state-mutating
update), the skill:

- does NOT need `metadata.gcl`
- does NOT need `## Quality Gate (GCL)`
- does NOT need `rubric.md` / `prompt-templates.md`

The skill's `## Safety Gates` section still must call out the no-secret /
no-credential-logging rule (rule A9) and the `--region` rule (A7).

## How to write a service-specific rubric

1. **Start from the spec** — read `gcl-spec.md` §3 for the 5-dimension template.
2. **List every destructive op** in the skill and write a per-op override row.
3. **List service-specific Safety auto-fail rules** — concrete patterns
   that this service's APIs can silently get wrong.
4. **Reference the repo-wide AWS rules A1–A10 by ID** — do not paste the
   full text into the rubric. `gcl-spec.md` §8 is the canonical home.
5. **Pick a `max_iter` per the §11.5 table** — do not invent a new value.

## How to write service-specific prompt templates

1. **Start from any existing pilot** (`aws-ec2-ops/references/prompt-templates.md`
   is the canonical simple example; `aws-kms-ops` is the most
   secret-handling-heavy example).
2. **List every operation type** in the prompt's `operation type:` enum.
3. **For each destructive op, document the exact confirmation string**
   the user must type.
4. **For each op that has a pre-flight chain**, spell out the exact step
   order in the prompt. The critic will refuse if the chain is incomplete.
5. **Critic prompt MUST hide the raw user request** — generator output
   only. This is `gcl-spec.md` §7 hard rule, not a suggestion.
6. **Variable Convention table** at the bottom — copy the structure
   from a pilot; do not invent new placeholder types.

## Using the shared prompt skeleton (O3 — mandatory for new skills)

> **Background:** Before 2026-06-27, every skill duplicated the
> Generator/Critic/Orchestrator templates inline. As of spec v1.12.0, the
> canonical templates live in [`prompt-skeletons.md`](prompt-skeletons.md)
> (231 lines), and each skill's `prompt-templates.md` is a **thin specialization**.

#### Required structure for a new skill's `prompt-templates.md`

```
# GCL Prompt Templates — `<skill>`

> Specialization of the shared skeleton:
> [`references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)

## Skill metadata (used by skeleton `{{skill.*}}` placeholders)

| Placeholder | Value |
|---|---|
| `{{skill.name}}` | `<skill>` |
| `{{skill.service}}` | `<service>` |
| `{{skill.aws_cli_svc}}` | `<aws-cli-namespace>` |
| `{{skill.max_iter}}` | `<2|3>` |
| `{{skill.type}}` | `base` \| `composite` |
| `{{skill.provides}}` | operations this skill handles |
| `{{skill.delegate}}` | composite→base skill/operation map |

## Hard rules (Critic template injection)

```text
<bullet list citing gcl-spec.md §8 A-ids>
```

## Confirmation Strings

| Operation | Confirmation token |
|---|---|
| `<op>` | `confirm=<OP> <resource>` |

## Variable Convention (skill-specific deltas)

> Common placeholders defined in `prompt-skeletons.md`. Only unique entries below.

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | <date> | Initial GCL prompt templates |
```

#### Rules for new skills

1. **Do NOT duplicate the Generator / Critic / Orchestrator bodies.**
2. **Hard rules block is the ONLY service-specific content in the Critic prompt.**
3. **Each Hard rule MUST reference a `gcl-spec.md` §8 A-id** (A1–A16) OR
   a named operation in `references/rubric.md`.
4. **Confirmation strings table is mandatory** for every destructive op.
5. **Variable Convention deltas** — only list placeholders unique to this skill.
6. **After writing the file, dry-run the sync to verify extraction:**

   ```bash
   python3 scripts/_sync_prompt_skeletons.py --skill <your-skill> --dry-run
   ```

#### Rules for extending an existing skill

When you add a new operation to an existing skill:

1. Add a new bullet under `## Hard rules (Critic template injection)`.
2. Add a new row to the `## Confirmation Strings` table if destructive.
3. Do NOT modify the skeleton file unless the new rule is **repo-wide**
   (applies to ≥3 services).

#### Verifying the specialization is complete

```bash
python3 scripts/gcl_runner.py --skill <your-skill> --print-critic
python3 scripts/gcl_runner.py --skill <your-skill> --request "list" --self-test
python3 scripts/_sync_prompt_skeletons.py --skill <your-skill> --dry-run \
  | grep -E "^## Hard rules \(Critic|^```text$" | head -2
```

## When a service is added to an existing skill (not a new skill)

If you are extending `aws-s3-ops` with a new destructive op:

1. Update `references/rubric.md` — add override row + Safety special case if needed
2. Update `references/prompt-templates.md` — add op to `operation type:` enum
3. Update `## Quality Gate (GCL)` in `SKILL.md` — add op to gating list
4. Update `references/aws-cli-usage.md` — the actual CLI command
5. **Do NOT bump `rubric_version` for minor additions** — bump to `v2`
   only when changing the 5-dimension weights or thresholds

## Verifying the rollout

After scaffolding is in place, confirm:

- `awk '/^---$/{c++; if(c==2){exit}} c==1' SKILL.md` returns full frontmatter
- YAML frontmatter parses cleanly with the `gcl:` block visible
- Every `aws-<x>-ops` referenced in SHOULD NOT / recovery / GCL rubric exists
- `references/rubric.md` and `references/prompt-templates.md` exist
  and reference `gcl-spec.md` rather than duplicating it

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Added §Generator ↔ GCL Integration; P0 checklist requires GCL classification |
| 1.1.0 | 2026-06-27 | O3 wiring: shared prompt-skeleton mandatory; verification commands added |
