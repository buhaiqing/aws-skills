# AGENTS.md

Repo-specific guidance for OpenCode/AI agents. Read `CLAUDE.md` first for the
shared baseline (architecture, credential convention, dual-path execution,
safety gates, error-recovery table). This file only records things an agent
would otherwise get wrong.

## What this repo is

A flat collection of AI-Agent runbooks for AWS services. Every top-level
`aws-<service>-ops/` directory is a *skill*, not source code. There is no
build, no lint, no test runner, no CI. "Editing the codebase" means editing
Markdown skill files and the YAML/JSON assets they ship.

There is exactly one meta-skill, `aws-skill-generator/`, that scaffolds and
governs all `aws-<service>-ops/` skills. Treat it as the source of truth for
structure, frontmatter, and review rules.

## Source-of-truth files (read these before editing skills)

- `aws-skill-generator/SKILL.md` — generation process, Charter (C1–C6),
  Token Efficiency rules (TE-1…TE-6).
- `aws-skill-generator/references/aws-skill-template.md` — required SKILL.md
  skeleton (frontmatter + section order).
- `aws-skill-generator/references/governance-review.md` — pre-merge
  checklist and adversarial scenarios (A–H). Skills failing C1–C6 or H1–H6
  must be auto-fixed, not merged.
- `aws-skill-generator/references/aws-cli-conventions.md`,
  `boto3-sdk-usage.md`, `integration.md` — shared conventions; individual
  skills reference these instead of duplicating.

## Skill layout (must match exactly)

```
aws-<service>-ops/
  SKILL.md                 # ~70–120 lines, "what to do" only
  references/
    aws-cli-usage.md       # CLI commands + JSON paths (verified)
    boto3-sdk-usage.md     # SDK patterns (no docstrings — TE-2)
    core-concepts.md       # Service architecture, quotas
    troubleshooting.md     # Compact error table (TE-3)
  assets/                  # example-config.yaml, dashboards, etc.
```

`prompt-examples.md`, `cost-tracking.md`, `escalation.md`,
`aiops-automation-engine.md` are optional extensions used by mature skills
(e.g. `aws-elb-ops`). Do not invent new file names without updating
`aws-skill-template.md` and the README.

## SKILL.md frontmatter gotcha (real bug currently in repo)

YAML frontmatter is a **single** block delimited by one opening and one
closing `---`. `aws-ec2-ops/SKILL.md` accidentally splits the block (a
stray `---` after the `description` value), which breaks frontmatter
parsers. When you create or edit a SKILL.md:

- Exactly two `---` markers, both at the start of the file.
- `description: >-` folded scalars must end with a blank line, **not** a
  `---` line.
- After editing frontmatter, verify with:
  `awk '/^---$/{c++; if(c==2){exit}} c==1' SKILL.md` returns the whole
  frontmatter block, and `head -1` is `---`.

## Mandatory sections in every SKILL.md

Enforced by Charter C1–C6 (see `governance-review.md`). Missing any of these
means the skill is invalid and must be auto-fixed:

1. YAML frontmatter with `name`, `description`, `license`, `compatibility`,
   `metadata`.
2. `## Trigger & Scope` with both `### SHOULD Use When` and
   `### SHOULD NOT Use When` (delegate names must point to skills that
   actually exist in this repo).
3. `## Variable Convention` table using only `{{env.*}}`, `{{user.*}}`,
   `{{output.*}}` placeholders. Never instruct the user to paste secrets;
   `{{env.AWS_ACCESS_KEY_ID}}` / `{{env.AWS_SECRET_ACCESS_KEY}}` must fail
   closed if unset.
4. Execution flow per operation: **Pre-flight → Execute → Validate → Recover**.
5. Explicit human confirmation step before any destructive op (delete,
   terminate, deregister, detach).
6. Token Efficiency (TE-1…TE-6): no hardcoded version/port/state tables,
   no SDK docstrings, compact error tables, JSON paths declared once at
   file top, YAML anchors in `example-config.yaml`, no duplicated flows
   across SKILL.md and references.

## Repo conventions worth knowing

- Always invoke CLI with `--output json`; assets and references assume
  JSON output so agents can `jq` paths.
- CLI is primary, boto3 is fallback after 3 CLI failures (CLAUDE.md).
- Credentials load order (highest first): shell env → `.env` → defaults.
  `.env` is git-ignored; `.env.example` is the template.
- `README.md` and `README_cn.md` must be kept in sync when adding,
  removing, or version-bumping a skill (the "Existing Skills" table and
  the AIOps section both reference per-skill versions).
- `.omc/` holds OpenCode session state and project memory — do not commit
  changes there as part of skill edits.

## Self-reflection rule (project policy)

After **any** change to a SKILL.md or its `references/` / `assets/`,
the agent must run **2 rounds** of self-reflection on the touched skill
and proactively fix every issue it finds. Do not hand back to the user
between rounds. Each round runs the same checks; round 2 must report
"no findings" before completion.

Each round, for every modified skill:

1. Re-read the modified SKILL.md from disk (do not trust memory).
2. Verify Charter C1–C6 (see `governance-review.md`). For each failure:
   report `[CHARTER VIOLATION] C{n}: {reason}` and auto-fix using the
   template.
3. Verify Token Efficiency TE-1…TE-6. Fix per the rules in
   `aws-skill-generator/SKILL.md` §Token Efficiency Requirements.
4. Verify SKILL.md frontmatter parses (single `---` open + single `---`
   close, see "frontmatter gotcha" above).
5. Verify every delegation reference (`aws-<x>-ops` mentioned in
   SHOULD/SHOULD NOT, cross-skill chains, recovery tables) points to a
   directory that exists in this repo.
6. Verify destructive operations (`delete`, `terminate`, `deregister`,
   `detach`, `revoke`) each have an explicit confirmation step in
   pre-flight.
7. Verify JSON paths shown in SKILL.md match the ones in
   `references/aws-cli-usage.md` and the centralized "Common JSON Paths"
   block at the top of SKILL.md.
8. Verify `README.md` and `README_cn.md` "Existing Skills" tables reflect
   the new state (add/remove/version row).

After round 2 passes cleanly, report a one-line summary per modified
skill: `[OK] aws-<service>-ops v<version> — 2 rounds clean`.

If round 2 still finds issues, run additional rounds until clean. Do
**not** stop after 2 rounds if problems remain.

## When the user asks for a new AWS skill

Load `aws-skill-generator` first, then collect the inputs listed under
"Quick Start Checklist → P0" in its SKILL.md before generating any
files. The directory you create must mirror the layout above exactly,
and the generated SKILL.md must pass the Charter and TE rules on the
first round of self-reflection — if it does not, fix the generator
output, not just the symptom in the new skill.
