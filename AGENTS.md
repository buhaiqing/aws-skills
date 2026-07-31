# AGENTS.md

Repo-specific guidance for OpenCode/AI agents. Read `CLAUDE.md` first for the
shared baseline (architecture, credential convention, dual-path execution,
safety gates, error-recovery table). This file only records things an agent
would otherwise get wrong.

## What this repo is

A flat collection of AI-Agent runbooks for AWS services. Every top-level
`aws-<service>-ops/` directory is a *skill*, not source code. There is no
conventional application build; repository governance scripts and unit tests
live under `scripts/` and `scripts/tests/`. "Editing the codebase" includes
Markdown skill files, YAML/JSON assets, and their governance tooling.

There is exactly one meta-skill, `aws-skill-generator/`, that scaffolds and
governs all `aws-<service>-ops/` skills. Treat it as the source of truth for
structure, frontmatter, and review rules.

## Repo design documents (orientation)

Before editing skills, also consult these architecture docs:

- [`docs/agentic-maturity-model.md`](docs/agentic-maturity-model.md) — **L1–L4 capability inventory**
  (implemented vs partial vs in-progress vs planned vs gap). Single source of truth
  for "what maturity level does this repo achieve today" and the path to L4.
- [`docs/adr/0001-l4-production-evidence-loop.md`](docs/adr/0001-l4-production-evidence-loop.md) — stable L4 delivery gate; **M1/M2 engineering done** (shadow plan_hash + proxy hard gate); next = M3; progress in ADR §M1/§M2.
- [`docs/level3-progress.md`](docs/level3-progress.md) — Level 3 cross-skill routing
  coverage (8 skills closed-loop).
- [`docs/gcl-per-skill-defaults.md`](docs/gcl-per-skill-defaults.md) — GCL 37-line
  Per-Skill Defaults table.
- [`docs/te-hard-gate.md`](docs/te-hard-gate.md) — Token Efficiency G1–G6 hard gate
  full definition.
- [`docs/failure-patterns.md`](docs/failure-patterns.md) — Reflexion memory
  (cross-session failure patterns).

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

## SKILL.md frontmatter gotcha (fixed — aws-ec2-ops verified clean 2026-07-12)

YAML frontmatter is a **single** block delimited by one opening and one
closing `---`. Previously, `aws-ec2-ops/SKILL.md` accidentally split the
block (a stray `---` after the `description` value), which broke
frontmatter parsers. This has been verified clean as of 2026-07-12.

When you create or edit a SKILL.md:

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
  the AIOps section both reference per-skill versions). **Verify after
  every version bump:**
  ```bash
  for d in aws-*-ops; do
    v=$(grep -m1 'version:' "$d/SKILL.md" | awk '{print $2}' | tr -d '"');
    grep -q "$v" README.md README_cn.md || echo "MISMATCH: $d=$v";
  done
  ```
  Empty output = all synced. Alternatively, the CI workflow
  `.github/workflows/version-sync.yml` auto-fixes mismatches and opens a PR
  on push to `main`.
- `.omc/` holds OpenCode session state and project memory — do not commit
  changes there as part of skill edits.

## Operational Guidelines (agent workflow)

### Task Tracking for Multi-Step Work

For any work involving 3+ distinct steps, create tasks via `TaskCreate`
before starting. This provides:
- Progress visibility to the user
- A checklist that prevents skipping steps
- A natural "next task" prompt when the user says "continue"

After completing each task, immediately mark it `completed` and check
`TaskList` for the next item. Do not batch completions.

### Fan-out Subagents (as much as feasible) — MANDATORY

**This is a hard constraint; enforce it strictly in every subsequent action.**
Any subtask that can be parallelized and delivered independently **must be
fanned out to subagents for concurrent execution as much as feasible**; the
main Agent only orchestrates and synthesizes, and must not do the work
itself instead of the subagents.

Determination and execution rules:

- **Signals for fan-out**: a task can be split into ≥2 mutually independent
  subtasks with no shared mutable state (e.g., similar edits across multiple
  skills, multiple independent queries/checks, similar reviews across
  multiple files).
- **Prefer concurrency**: for any independent subtasks, issue multiple Agent
  calls in the **same message** so they run in parallel; do not serialize work
  that could be parallel.
- **Main Agent responsibility**: split tasks → write self-contained prompts
  (including file paths / line numbers / acceptance criteria) → synthesize
  results → be accountable to the user. **Do not** delegate "understanding" to
  subagents — you read and understand first, then issue precise specs.
- **Write-heavy is serial**: implementation tasks that write the same batch of
  files run one at a time (to avoid merge conflicts), but different file
  regions and different skills can be parallel; read-only research tasks may
  be freely parallelized.
- **Subagent failure**: first `SendMessage` to continue with error context;
  if correction still fails, switch approach or escalate to the user; do not
  spin endlessly.
- **Cases that cannot be fanned out** (exceptions): single-point dependency
  chains (B must wait for A's output), <5-line pure typo/comment fixes, and
  security/destructive operations that require the main Agent to take over
  directly.

> Source: 2026-07-19 session user hard constraint "fan out subagents as much as
> feasible, strictly enforced in every subsequent action". This rule works with
> the §12 routing gate and the §13 CADL asset-distillation loop: after fan-out,
> each subtask must still go through the corresponding Grep/CodeGraph routing
> and asset distillation.

### Token Efficiency Monitor (MANDATORY GATE — every task must pass)

**This is a hard constraint; enforce it strictly in every subsequent action.**
After any substantive task (including subagent deliverables) is completed, it
**must** pass review by an independent **Token Efficiency Monitor** subagent,
which confirms whether the token efficiency of this output is already optimal;
if not optimal, the Monitor **directly refactors it to optimal**, or (if the
refactor cost exceeds the benefit) explicitly judges "already at current
optimal, no further optimization needed" before wrapping up.

Determination and execution rules:

- **Trigger**: fires on every task completion (or subagent report of
  completion), **before** declaring "done" to the user.
- **Monitor responsibility**: audit this output from a token-efficiency
  perspective, focusing on:
  1. **Redundancy**: duplicated content (same paragraph in multiple files,
     repeated explanations in AI replies, templated text that could be deduped)?
  2. **Compressibility**: can long outputs/long prompts be expressed more
     briefly with equivalent effect? Is irrelevant background mixed in?
  3. **Readability cost**: does compression sacrifice maintainability (long-lived
     assets like README/AGENTS must not sacrifice clarity to save tokens)?
  4. **Sufficient fan-out**: were subtasks that could have been parallelized
     serialized instead (violating the Fan-out rule)?
- **Three-way disposition** (the Monitor must pick exactly one and explain):
  - **`OPTIMAL`** — already optimal, pass (with ≤2 sentences of rationale).
  - **`REFACTOR-NOW`** — refactor directly to optimal (Monitor edits the file
    and commits itself, or sends a precise spec to the original executor to fix).
  - **`ACCEPT-SUBOPTIMAL`** — refactor cost exceeds benefit (e.g., long-lived
     assets should not be over-compressed); record rationale and pass.
- **Cannot be bypassed**: the main Agent must not claim a task is done before
  the Monitor agrees; the Monitor's `OPTIMAL` / `ACCEPT-SUBOPTIMAL` is a
  prerequisite for wrap-up.
- **Works with CADL**: reusable compression patterns found by the Monitor must
  land per §13 (general patterns → AGENTS.md, pitfalls → failure-patterns.md),
  compounding token efficiency over time.
- **Long-lived asset exemption**: long-lived docs aimed at humans / multiple
  agents like AGENTS.md / README / SKILL.md yield to clarity and
  retrievability over token efficiency — the Monitor defaults such files to
  `ACCEPT-SUBOPTIMAL` or light `REFACTOR-NOW`.

> Source: 2026-07-19 session user hard constraint "every task must pass a token
> efficiency monitor subagent for approval — see whether it can optimize to
> optimal, and if not, assign it to complete that". Mandatory in the execution
> flow from the next task onward: the main Agent spawns the Monitor before
> wrapping up a task, and executes per its three-way disposition, strictly
> following it.

### GCL Skip Threshold

GCL (Generator-Critic-Loop) is required for >5 line code changes,
but can be skipped for:
- Single-line constant additions (e.g., adding a metric to a dict)
- Import list updates (e.g., expanding `__init__.py` exports)
- Documentation-only changes (adding notes, clarifying existing text)

The judgment standard: if the change is purely additive (no logic changes,
no control flow, no error handling), GCL overhead exceeds its value.

### Pre-change CodeGraph Sync (mandatory)

**Every code change must run `codegraph sync .` first** to refresh the
local index before editing. This guarantees that `codegraph explore` /
`codegraph impact` queries during the change reflect current state, so
cross-skill reference drift and blast radius are caught early.

```bash
codegraph sync .    # incremental sync; if no index exists, run codegraph init . first
```

- For documentation-only Markdown changes, sync is still recommended (cheap,
  keeps the graph current) but not strictly required.
- Full setup and rules: see §12 CodeGraph Integration.

### Pre-existing Lint Baseline

When running `ruff check` / `eslint` after changes, always run the
linter on the **entire file** first to establish which errors are
pre-existing. Only errors on **new or modified lines** count as
regressions. Report pre-existing errors separately if the user asks
for a full lint report.

This prevents false-positive code reviews where the reviewer flags
errors that existed before the change.

### Spec + Plan Before Implement (mandatory)

Any non-trivial implementation MUST first define a **spec** and a **plan**
under `docs/superpowers/` before writing code:

- **Spec** → `docs/superpowers/specs/<YYYY-MM-DD>-<topic>-design.md`
  (gap/need analysis with disk-verified evidence, scope boundary).
- **Plan** → `docs/superpowers/plans/<YYYY-MM-DD>-<topic>.md`
  (checkbox tasks referencing the spec, with acceptance criteria).

**Triggers** (any one ⇒ spec + plan required): code/config/skill change
>5 lines; new feature module; cross-file or cross-skill refactor.
**Exempt**: pure-doc typo fixes, single-line constant additions, import
list updates (purely additive, no logic/control-flow change).
**Precedent**: `docs/superpowers/specs/2026-07-11-level3-coverage-design.md`
and its plan are the canonical template — every new implement task follows
the same path.

### Per-Phase / Milestone Full Review (mandatory)

After **all tasks in a Phase (or Milestone)** complete, run one **full
review** and **fix every issue found** before proceeding or handing off.
Cover: (1) structure — markdown tables/fences closed, headings coherent;
(2) consistency — no conflict with §11 GCL / §12 CodeGraph / §14 TE gate,
paths align with the level3 precedent; (3) scope — `git diff --stat` shows
only intended files; (4) gate — line count under §14 soft cap, frontmatter
valid. Fix each finding, re-run the check until zero issues. Unfixable
residue must be recorded and escalated for human decision — never ignored.
Record the review conclusion (scope / found / fixed / residue) before
marking the Phase done.

### Staged Self-Reflection & Knowledge Distillation (mandatory, per TDD step)

The end-of-Phase review (above) and the 3-round Self-Reflection rule (below)
are **not** sufficient on their own. Self-reflection must happen at every
TDD step, otherwise the lessons learned in step N are lost by step N+3.

**Per-step checkpoints** (apply to any RED → GREEN → REFACTOR cycle):

| Phase | Checkpoint | Output |
|---|---|---|
| **RED** | Capture the test oracle: "what does the failure look like and why?" | One-line note in the plan or commit body; never skip |
| **GREEN** | Capture the minimal change: "what was the smallest diff that made RED go green?" | If the diff is >50 lines, you batched too much — split |
| **REFACTOR** | Capture the lesson: "what invariant or anti-pattern did this step expose?" | Append to `docs/superpowers/learnings.md` keyed by date + topic |

**Per-Pilot / Per-Phase promotion** (after the final GREEN of a pilot / phase):

For each lesson in `learnings.md` that meets ALL of the following, **promote
it to AGENTS.md as a standing rule**:

1. The lesson is **general** (applies to ≥3 future tasks, not a one-off fix).
2. The lesson is **actionable** (can be phrased as "do X" or "never Y" — not a postmortem narrative).
3. The lesson is **mechanically verifiable** (a future agent can check compliance with a script, a Charter check, or a single grep).

If a lesson is one-off, keep it in `learnings.md` only. If it is general but
not yet mechanically verifiable, leave it in `learnings.md` and label it
`[awaiting-promotion]` until a verification hook is built.

**Anti-pattern** (banned): running 3 rounds of self-reflection at the very
end, then trying to "remember" all the lessons. Most lessons are lost this
way — you forget the bug that the test caught, the assumption that turned
out to be wrong, the off-by-one in the helper. Catch them while they are
fresh, in the step where you discovered them.

> Source: 2026-07-28 TE Gate C6 Debt Pilot retro. The pilot was 6 atomic
> TDD steps (frontmatter compress, JSON paths, Trigger & Scope, etc.); each
> step exposed a lesson that, when captured in-step, made the next step
> faster. Trying to recall them at the end produced a 6-lesson dump that
> would have been 2-3 lessons if forced to be remembered later.

### Standing Rules (distilled from past pilots)

These are **promoted** lessons from `docs/superpowers/learnings.md` —
general, actionable, mechanically verifiable. Each rule states a
recurring pattern that future agents must follow without re-deriving it.

When a new pilot/phase exposes a lesson that meets the promotion
criteria (general + actionable + verifiable), append a new rule here
and move the corresponding entry out of `learnings.md` to keep the
candidates list short.

#### SR-1 — TDD step size: one section per commit (≥50-line rewrite ⇒ split)

When a SKILL.md refactor or large file rewrite is required, **do not** write
a single replacement script that touches ≥50 lines at once. Instead, break
the work into atomic steps where each step:

- Touches ≤50 lines of a single file (or a small set of related lines).
- Is followed by a hard-verification call (`te_gate.py`, `pytest`, `ruff`).
- Can be reverted in isolation if it regresses.

**Why**: a single 169-line replacement script failed on a whitespace
mismatch in step 1; recovery cost was 10× the time of having split into
6 atomic steps (which the 2026-07-28 TE Gate pilot did, finishing in
~20 min).

**Mechanically verifiable**: PR review should flag any commit where the
net `git diff` is ≥50 lines and not split into multiple commits. Use
`git diff --stat` before staging.

> Promoted 2026-07-28 from `learnings.md` Lesson 6 (TE Gate C6 Debt Pilot).

#### SR-2 — Charter C2 literal sub-headers: never strip `### SHOULD Use When`

When compressing a SKILL.md `## Trigger & Scope` section to fit the G1
line cap, **always keep** the literal sub-headers:

```markdown
## Trigger & Scope

### SHOULD Use When
<compressed content>

### SHOULD NOT Use When
<compressed content>
```

A single paragraph with bold (`**SHOULD**: ... **SHOULD NOT**: ...`) violates
Charter C2 even if the semantic content is preserved — the Charter check
looks for the literal sub-heading text.

**Why**: Charter C2 (per `governance-review.md`) requires both
`### SHOULD Use When` and `### SHOULD NOT Use When` headings; compressing
the content between them is fine, deleting the headings is not.

**Mechanically verifiable**: any skill-updating agent or
`scripts/te_gate.py` augmentation can grep for the literal sub-headers.
A missing header is a Charter violation, not a style preference.

> Promoted 2026-07-28 from `learnings.md` Lesson 4 (TE Gate C6 Debt Pilot).

#### SR-3 — Frontmatter inline arrays: `[a, b, c]` is valid YAML, saves 4-5 lines

When a SKILL.md frontmatter block has multi-line YAML lists
(`environment:`, `cross_skill_deps:`, etc.), prefer the **inline array
form** unless readability demands otherwise:

```yaml
environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION]
cross_skill_deps: [aws-iam-ops, aws-vpc-ops, aws-ec2-ops]
```

This is valid YAML, parses identically to the multi-line form, and saves
4-5 lines per block. For 37 skills × 2 blocks, that's ~150 lines
recoverable across the repo without any Charter impact.

**Exception**: when the list has more than ~5 items AND each item has a
trailing comment, the multi-line form is more readable. Inline the rest.

**Mechanically verifiable**: lint can flag `environment:` followed by a
list of >3 single-key items on separate lines and suggest the inline form.

> Promoted 2026-07-28 from `learnings.md` Lesson 3 (TE Gate C6 Debt Pilot).

#### SR-4 — Cross-file anchor links: anchor must exist in target

When adding a markdown link of the form
`[text](references/<file>.md#<anchor>)` to a SKILL.md, **the anchor
must exist as a heading in the target file**. The current link-integrity
check only verifies that the **file** exists, not the **anchor**.

**Mandatory check** before merging any SKILL.md change:

1. List every `[...](<file>.md#<anchor>)` link in the modified SKILL.md.
2. For each anchor, parse the headings of the target file with
   GitHub-style slug rules (lowercase, spaces → `-`, strip `:.,&()?!/`).
3. Reject the change if any anchor is not found.

**Why**: the 2026-07-28 pilot added
`[references/operations.md#config-placeholders](...)` to
`aws-ram-ops/SKILL.md` while the actual section was in the SKILL.md, not
in operations.md — silent broken link.

**Mechanically verifiable**: a 30-line `scripts/links_lint.py` can
implement the above. Until that script exists, manual review of every
new cross-file link is mandatory; mark them with a `<!-- link-check:manual -->`
HTML comment so a future automated scan can find them.

> Promoted 2026-07-28 from `learnings.md` Lesson 5 (TE Gate C6 Debt Pilot).

### Composite / Copilot Skills (L2)



Base skills (`aws-<svc>-ops`, L1) are single-service runbooks. Composite
skills (L2, `metadata.type: composite`) **orchestrate only** — they declare
`delegate:` to L1 skills and contain no service-level operation logic.

Contract (enforced by aws-skill-generator Charter C7):
- `metadata.type`: `base` | `composite` (the equivalent value `orchestrator-meta`
  also counts as composite)
- `metadata.provides`: operations this skill handles
- `metadata.delegate`: composite→base skill/operation map (dirs must exist)

Runtime-agnostic: any agent globs `aws-*-ops/SKILL.md` and reads frontmatter
— no per-agent loader (see §12 CodeGraph for cross-agent MCP discovery).

`aws-aiops-copilot` is the canonical L2 example (type: composite, delegates to
aws-aiops-cruise + aws-aiops-orchestrator).

## Self-reflection rule (project policy)

> **Rule**: After every skill update, auto-run **3 rounds** of self-review
> and fix all discovered issues. Do not hand back to the user between rounds.
>
> Full spec (check tables, verification scripts, dedup procedures,
> implementation notes) at
> [`docs/post-update-self-review.md`](docs/post-update-self-review.md)

> **Per-step note**: The 3 rounds below run at the **end** of a skill update.
> Per-TDD-step reflection (RED / GREEN / REFACTOR) is required in addition —
> see **"Staged Self-Reflection & Knowledge Distillation"** in
> §Operational Guidelines above for the per-step discipline that feeds into
> this end-of-update review. The two are complementary, not substitutes:
> per-step captures lessons while fresh; end-of-update consolidates them
> into the skill's `post-update-self-review.md`.

| Round | Scope | Key Checks |
|-------|-------|------------|
| **R1: Structural** | Frontmatter / Trigger / Variables / Token Efficiency | C1–C6, TE-1…TE-6, **C6 MUST PASS** |
| **R2: Content** | CLI validation / error codes / safety gates / link integrity / dedup / README sync | F1–F8, **F5/F6/F8 MUST PASS** |
| **R3: Cross-cutting + Lessons Learned** | CADL consistency / TE audit / delegation drift / lessons captured | §12 split gate, §14 TE hard gate, GCL table sync, **≥1 lesson recorded** |

Each round, for every modified skill:

1. Re-read the modified SKILL.md from disk (do not trust memory).
2. **Verify Charter C1–C6** (see `governance-review.md`). Failure →
   report `[CHARTER VIOLATION] C{n}: {reason}` and auto-fix.
3. **Verify Token Efficiency TE-1…TE-6** per `aws-skill-generator/SKILL.md`.
   C6 is a MUST PASS gate — see [post-update-self-review.md](docs/post-update-self-review.md) §TE verification.
4. **Verify frontmatter** parses (single `---` open + close, see §frontmatter gotcha).
5. **Verify delegation references** — every `aws-<x>-ops` in SHOULD/SHOULD NOT
   or recovery tables must point to an existing directory.
6. **Verify destructive ops** (`delete`, `terminate`, `detach`, `revoke`)
   each have explicit confirmation in pre-flight.
7. **Verify JSON paths** match `references/aws-cli-usage.md` and the
   centralized "Common JSON Paths" block at SKILL.md top.
8. **Verify README sync** — `README.md` and `README_cn.md` tables reflect state.
9. **TE Post-Change Audit** — scan references/ for token waste per
   [post-update-self-review.md](docs/post-update-self-review.md) §Content Deduplication.
10. **R3 CADL Check** — verify §12 split gate not violated (code→CodeGraph, docs→Grep),
    §14 TE hard gate (SKILL.md ≤ 120 lines), GCL Per-Skill Defaults sync,
    and record ≥1 lesson in the per-skill `post-update-self-review.md`.

After round 3 passes cleanly, report a one-line summary per modified
skill: `[OK] aws-<service>-ops v<version> — 3 rounds clean`.

If round 3 still finds issues, run additional rounds until clean. Do
**not** stop after 3 rounds if problems remain.

### Reflexion Memory (cross-session learning)

Failed operations leave structured failure patterns in
[`docs/failure-patterns.md`](docs/failure-patterns.md). Before executing any
high-risk operation, the agent MUST check this file for known failure modes
of the target resource type. Each pattern records:

| Field | Purpose |
|-------|---------|
| `resource_type` | Which AWS resource (e.g., `aws-rds-db-instance`) |
| `failure_mode` | What went wrong (e.g., `final-snapshot-skip-in-prod`) |
| `root_cause` | Why it happened |
| `fix` | What the agent should do differently |
| `severity` | `P0` (block) / `P1` (warn) / `P2` (info) |
| `added_date` | When the pattern was recorded |

Patterns are appended after every GCL `SAFETY_FAIL` or `MAX_ITER` with
unresolved safety issues. The agent treats these as **hard constraints** —
not suggestions — when planning or executing operations.

## When the user asks for a new AWS skill

Load `aws-skill-generator` first, then collect the inputs listed under
"Quick Start Checklist → P0" in its SKILL.md before generating any
files. The directory you create must mirror the layout above exactly,
and the generated SKILL.md must pass the Charter and TE rules on the
first round of self-reflection — if it does not, fix the generator
output, not just the symptom in the new skill.

## 11. Generator-Critic-Loop (GCL) — Adversarial Quality Gate

> Inspired by GAN's Generator/Discriminator idea, but deliberately **not** a
> real GAN. Naming: **GCL (Generator-Critic-Loop)** to avoid misleading
> reviewers and LLM trainees.

### 11.1 Purpose

Apply an adversarial **Generator ↔ Critic** loop with a quantitative rubric
to every skill execution. Most valuable in **high-side-effect AWS
operations** (`terminate-instances`, `delete-bucket`, `delete-db-instance`,
`iam delete-user`, `kms schedule-key-deletion`, etc.) where a single
mistake is unrecoverable.

The full specification lives in
[`aws-skill-generator/references/gcl-spec.md`](aws-skill-generator/references/gcl-spec.md).
This section is the **index, current rollout status, and Per-Skill
Defaults table** — read it first, then load the spec for detail.

| GAN (real) | GCL (this spec) |
|---|---|
| Discriminator learns sample distribution | Critic scores an **explicit rubric** |
| No termination condition | Must terminate: **PASS / MAX_ITER / SAFETY_FAIL** |
| G and D train in parallel | G and C run **sequentially** |
| Goal: "fool the D" | Goal: "pass the rubric threshold" |

### 11.2 Roles & isolation

| Role | Job | Forbidden |
|---|---|---|
| **Generator (G)** | Execute the AWS op via `aws --output json` (primary) / boto3 (fallback) | modifying the rubric; self-scoring |
| **Critic (C)** | Independently audit G's output against the rubric | calling `aws` / `boto3` / mutating anything |
| **Orchestrator (O)** | Loop control, termination, final return | executing or scoring on its own |

G and C MUST live in **isolated prompt contexts** (separate sessions or
sub-agents). Shared context is a "pseudo-GCL" and is banned — see spec §9.

### 11.3 Rubric (mandatory per skill)

Each skill declares its 5-dimension rubric in `references/rubric.md`:
**Correctness / Safety / Idempotency / Traceability / Spec Compliance** on
a 0 / 0.5 / 1 scale. **Safety = 0 → ABORT immediately**, regardless of
total score. Full rules in spec §3.

### 11.4 Termination (first match wins)

| Condition | Behavior |
|---|---|
| **PASS** | Every rubric dimension meets its threshold → return G's result |
| **MAX_ITER** | Reached `max_iterations` → return **best-so-far** + unresolved rubric items |
| **SAFETY_FAIL** | Safety = 0 → **ABORT**; never return partial output |

### 11.5 Per-Skill Defaults

> The full 37-line Per-Skill Defaults table (with each skill's GCL tier,
> `max_iter`, and destructive-op list) has been moved out to
> [`docs/gcl-per-skill-defaults.md`](docs/gcl-per-skill-defaults.md).

Key points: all `required` / `recommended` skills have rolled out full GCL
implementations; `optional` and read-only tiers (cloudtrail /
topo-discovery / aiops-cruise) are handled via a downgrade strategy. Each
skill may override `max_iter` under its own `SKILL.md`'s
`## Quality Gate (GCL)`. Skills not listed default to GCL **disabled**.

### 11.6 Trace & audit (mandatory)

Every GCL run persists a JSON trace to
`./audit-results/gcl-trace-YYYYMMDD-HHMMSS-<run-id>.json` per the schema in spec §6.
`audit-results/` is git-ignored; traces retained 30 days; old traces pruned
by the Phase 2 Orchestrator runner.

### 11.7 Prompt templates (mandatory per skill)

Each skill's `references/prompt-templates.md` is a **thin specialization**
of the canonical shared skeleton at
[`references/prompt-skeletons.md`](aws-skill-generator/references/prompt-skeletons.md)
(spec §7). The per-skill file contains ONLY:

1. Skill metadata table (`{{skill.*}}` placeholders)
2. Hard rules (Critic template injection) — one bullet per
   service-specific rule, each citing a `gcl-spec.md` §8 A-id (A1–A16)
3. Confirmation Strings table — mandatory for every destructive op
4. Variable Convention deltas — only entries unique to this skill

The three canonical templates (Generator / Critic / Orchestrator) are
resolved from the shared skeleton at runtime by
`scripts/gcl_runner.py` via `render_critic_prompt()`. Placeholders MUST
follow the repository-wide `{{env.*}}` / `{{user.*}}` / `{{output.*}}`
convention. Critic prompt MUST hide the raw user request to prevent
"answer-aligned" rubber-stamping. New skill creators MUST use the
[`assets/new-skill-template/prompt-templates.md`](aws-skill-generator/assets/new-skill-template/prompt-templates.md)
copy-paste template; run `--dry-run` before merging.

### 11.8 Anti-patterns (banned)

- ❌ **Shared context G+C** — defeats independence → banned
- ❌ **Subjective scoring** — Critic must use the rubric, not "vibes" → banned
- ❌ **Unbounded loop** — always hard-cap iterations → banned
- ❌ **Critic sees the user request** — encourages rubber-stamping → banned
- ❌ **Silently downgrade on Safety fail** — must ABORT visibly → banned
- ❌ **Trace not persisted** — no post-mortem possible → banned
- ❌ **Critic mutates resources** — Critic is read-only by definition → banned
- ❌ **`aws --output json` placed before subcommand** — non-portable;
  convention is `aws <svc> <op> --output json` (see CLAUDE.md) → banned
  in GCL traces and examples
- ❌ **Parallel GCL: Generators share mutable state** — race conditions → banned
- ❌ **Parallel GCL: Generators modify the same file** — merge conflicts → banned
- ❌ **Parallel GCL: Critic audits only one Generator output** — must audit ALL

### 11.9 AWS-specific rules (repo-wide)

Codified in `gcl-spec.md` §8. Highlights:

- **A1** `terminate-instances` requires user `--no-dry-run` opt-in
- **A7** `--region` must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
- **A8** Resource id must be echoed back from a `describe-*` lookup
- **A9** Plaintext `KeyMaterial` / `PasswordData` / `UserData` credentials
  in trace → Safety = 0; mask with `***` and length only
- **A10** `aws sts get-caller-identity` MUST be the first command in trace
- **A11** `cloudfront delete-distribution` must `disable → poll Deployed` first
- **A12** `elbv2 deregister-targets` ≥50% → requires drain confirmation
- **A13** `ec2 delete-vpc` requires 8-describe pre-flight
- **A14** `rds --skip-final-snapshot` → requires `DELETE_NO_SNAPSHOT` token
- **A15** `s3 put-bucket-policy` widening to `Principal: *` → requires public confirmation
- **A16** `autoscaling --force-delete` with `DesiredCapacity > 0` → must scale-to-0 first

### 11.10 Rollout roadmap

- **Phase 1 (in progress)** — spec + this index shipped; pilots on
  **`aws-ec2-ops`** (compute, destructive workload),
  **`aws-iam-ops`** (identity, secret-handling + wildcard-policy guards),
  **`aws-kms-ops`** (encryption, irreversible deletion + plaintext
  masking), and **`aws-s3-ops`** (storage, Versioned-bucket guard +
  public-access widening + `--recursive` rm count confirmation). Roll
  forward to remaining `required` skills one at a time (see §11.5 table).
- **Phase 2** — add `scripts/gcl_runner.py` as a reusable Orchestrator
  (invokes G, then C in isolated context, persists trace, enforces
  termination). Independent of any specific agent runtime.
- **Phase 3** — feed `gcl-trace-*.json` into a CloudWatch dashboard /
  Athena query for Quality Gate pass-rate and per-skill failure-mode
  histograms.
- **Phase 4** — wire rubric pass-rate to CloudWatch Alarms; production
  incidents refine thresholds.

### 11.11 Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL specification added (`aws-skill-generator/references/gcl-spec.md`) and `AGENTS.md` §11 index; pilot scoped to **`aws-ec2-ops`** with `references/rubric.md` (v1) and `references/prompt-templates.md` (v1); Per-Skill Defaults table covers all 22 existing skills |
| 1.1.0 | 2026-06-04 | Second GCL pilot on **`aws-iam-ops`** (v1.1.0) — added `references/rubric.md` (v1) and `references/prompt-templates.md` (v1); IAM-specific safety rules for `*:*` / `AdministratorAccess` attach, root-account `create-access-key` refusal, `Principal: *` trust policy guard, attached-policies pre-flight for `delete-user`, `SecretAccessKey` never logged |
| 1.2.0 | 2026-06-04 | Third GCL pilot on **`aws-kms-ops`** (v2.1.0) — added `references/rubric.md` (v1) and `references/prompt-templates.md` (v1); KMS-specific safety rules for irreversible `schedule-key-deletion` (`--pending-window-in-days ≥ 7`, literal `PERMANENTLY DELETE <key-id>` confirmation), outstanding-grants pre-flight, `Principal: *` widening `put-key-policy` guard, `delete-custom-key-store` requires no `Enabled` CMKs; **`Plaintext` and `CiphertextBlob` never logged** (masked to `***<len>` and first16+last4 respectively) |
| 1.3.0 | 2026-06-04 | Fourth GCL pilot on **`aws-s3-ops`** (v1.1.0) — added `references/rubric.md` (v1) and `references/prompt-templates.md` (v1); S3-specific safety rules for Versioned `delete-bucket` (rule A2 — must `list-object-versions` + `delete-object-versions` first), `delete-objects` empty-array refusal (rule A6), `aws s3 rm --recursive` count-and-bytes confirmation, `Principal: *` widening `put-bucket-policy` guard, public canned ACL refusal, MFA-Delete bucket confirmation, sensitive-file upload (`.env`/`*.pem`/`*.key`) gated + content masked (rule A9) |
| 1.4.0 | 2026-06-04 | Group 1 GCL rollout: **`aws-rds-ops`** (v1.1.0) final-snapshot guard (rule A5: `--skip-final-snapshot` needs `DELETE_NO_SNAPSHOT`), `MasterUserPassword` MUST be Secrets Manager ARN (rule A9); **`aws-lambda-ops`** (v1.1.0) `delete-function` irreversibility + event source mapping guard, ALL env vars masked (rule A9), pre-existing Charter fix `## Flow Pattern` → `## Execution Flow Pattern`; **`aws-dynamodb-ops`** (v1.1.0) `delete-table` irreversibility + GSIs/LSIs pre-flight, GSI REMOVE confirm, TTL enable confirm (irreversible 48 h), item values ALL masked (rule A9). Helper scripts `_add_gcl_to_skill.py` + `_gen_rubric.py` shipped. |
| 1.5.0 | 2026-06-04 | Group 2 GCL rollout: **`aws-vpc-ops`** (v1.3.0) `delete-vpc` 8-describe pre-flight (subnets/IGWs/NATs/RTs/SGs/endpoints/peering/NACLs), main RT undeletable, default SG undeletable while VPC has instances, public SG ingress on sensitive ports; **`aws-route53-ops`** (v1.2.0) `change-resource-record-sets: DELETE` + prod DNS guard, `delete-hosted-zone` non-NS/SOA refusal; **`aws-cloudfront-ops`** (v1.1.0) `delete-distribution` MUST disable first (poll `Status=Deployed`), OAC vs OAI guard; **`aws-elb-ops`** (v2.2.0, **recommended**, max_iter=3) `deregister-targets` 50%/100% drain threshold, default rule undeletable. |
| 1.6.0 | 2026-06-07 | New skill — **`aws-autoscaling-ops`** (v1.0.0) with full GCL scaffolding: `delete-auto-scaling-group` (`--force-delete` guard + scale-to-0 pre-flight), `delete-launch-configuration`, `detach-instances` (decrement guard), `set-desired-capacity` → 0 guard, `suspend-processes` (HealthCheck/ReplaceUnhealthy) safety, `confirm=DELETE <asg-name>` / `confirm=DETACH <instance-id>` patterns; rubric.md and prompt-templates.md shipped. |
| 1.7.0 | 2026-06-07 | New skills — **`aws-config-ops`** (v1.0.0, recommended, max_iter=3) with `delete-config-rule`, `stop-configuration-recorder`, `delete-configuration-recorder` guards; **`aws-eventbridge-ops`** (v1.0.0, recommended, max_iter=3) with `delete-rule` target-cleanup guard, `delete-event-bus`, `delete-schedule`, `delete-pipe`; both shipped with full rubric.md and prompt-templates.md. |
| 1.8.0 | 2026-06-12 | Added 5 skills to §11.5 Per-Skill Defaults table (back-filled from Groups 6–7 GCL rollout): **`aws-athena-ops`** (required, max_iter=2), **`aws-guardduty-ops`** (required, max_iter=2), **`aws-opensearch-ops`** (required, max_iter=2), **`aws-ram-ops`** (required, max_iter=2), **`aws-securityhub-ops`** (required, max_iter=2) — all shipped with rubric.md and prompt-templates.md. |
| 1.9.0 | 2026-06-13 | New skill — **`aws-aurora-ops`** (v1.0.0→**v1.1.0** AIOps): orchestrator delegate contract, 8 prompt scenarios, layered inspection, AIOps metrics CLI, cross-skill chains; **`aws-rds-ops`** delegates Aurora failover; **`aws-aiops-cruise`** / **`aws-aiops-orchestrator`** route Aurora cluster ops here. |
| 1.10.0 | 2026-06-13 | **`aws-aurora-ops`** v1.2.0 P2: orchestrator runbooks RB-023–RB-027, detection rules FD-15/16 PD-08/09, `incident-schema` v1.1.0 Aurora/`RDSProxy` resource types + examples. |
| 1.11.0 | 2026-06-27 | **GCL hardening pass.** (a) Migrated 22 skill `prompt-templates.md` files to route `{{user.region}}` → `{{output.requested_region}}` and `{{user.safety_confirm}}` → `{{output.safety_confirm_token}}` inside the Critic section, eliminating the rubber-stamp vector (`gcl-spec.md` §9 anti-pattern); added §7.1 to `gcl-spec.md` documenting the placeholder mapping. (b) Shipped `scripts/gcl_runner.py` (Phase 2 reusable Orchestrator: §4 loop, §5 termination, §6 trace schema, 30-day prune, `--self-test` mode for unit verification). (c) `aws-guardduty-ops` rubric migrated from continuous 1.0/0.8/0.7 weights to spec-mandated 0/0.5/1 discrete scale + explicit ABORT-on-Safety-0 clause; `aws-guardduty-ops` prompt templates migrated from bare `{{cli_command}}` / `{{boto3_code}}` / `{{generator_output}}` to spec-compliant `{{output.*}}` namespaces. (d) `aws-iam-ops` rubric now explicitly references rules **A3** / **A7** / **A8** / **A9** / **A10** by id; `aws-vpc-ops` rubric added A9 (`UserData` / `KeyMaterial` masking) clause. (e) `gcl-spec.md` changelog extended to v1.11.0; "22 skills" references corrected to the actual 31-skill scope (28 required/recommended + 2 meta read-only + 1 generator meta). |
| 1.12.0 | 2026-06-27 | **O1 (A11–A16) + O3 (prompt-skeleton extraction) + `--print-critic` runtime.** `gcl-spec.md` §8 gained six new repo-wide safety rules: **A11** (CloudFront distribution delete requires disable→Deployed first), **A12** (ELB `deregister-targets` 50%/100% drain confirmation), **A13** (VPC `delete-vpc` 8-describe pre-flight), **A14** (RDS/Aurora `--skip-final-snapshot` guard, supersedes legacy A5 in `aws-aurora-ops`), **A15** (S3 `Principal: *` policy widening), **A16** (ASG `--force-delete` requires scale-to-0 + `InstanceProtection=false`). Backfilled A-id labels into the 7 affected rubrics (cloudfront/elb/vpc/rds/aurora/s3/autoscaling). Created `aws-skill-generator/references/prompt-skeletons.md` (canonical Generator/Critic/Orchestrator templates + shared Variable Convention table; 231 lines). New `scripts/_sync_prompt_skeletons.py` retro-migrated all 31 skill `prompt-templates.md` files from ~5,800 lines of duplicated boilerplate to **~2,200 lines of thin deltas (-78%)**; idempotent; supports `--skill <name>`, `--all`, `--dry-run`, `--restore`. `scripts/gcl_runner.py` now exposes `render_critic_prompt()` + `--print-critic` for inspecting the merged Critic prompt at runtime. All three termination paths (PASS / SAFETY_FAIL / MAX_ITER) verified end-to-end via `--self-test` after migration. Net repo diff vs pre-v1.11.0: 48 files changed, **-3,456 lines**. |
| 1.13.0 | 2026-06-27 | **§11.7 updated to reflect shared skeleton architecture (prompt-templates.md is now a thin specialization, not self-contained) + §11.9 extended with A11–A16 highlights + §11.5 Per-Skill Defaults table annotated with A-rules for 7 skills (cloudfront/elb/vpc/rds/aurora/s3/autoscaling). New copy-paste template at `aws-skill-generator/assets/new-skill-template/prompt-templates.md` for new skill creators.** |
| 1.14.0 | 2026-07-04 | **Parallel GCL added (§12 in gcl-spec.md).** Documents the multi-Generator + single-Critic pattern for composite tasks that decompose into independent subtasks (e.g., WAF-ALB-01). Includes flow diagram, 5 rules, 4 anti-patterns, and worked example. Applicable to `aws-aiops-cruise` and `aws-aiops-orchestrator` composite rule development. |

### 11.12 See also

- [`aws-skill-generator/references/gcl-spec.md`](aws-skill-generator/references/gcl-spec.md) — full GCL specification
- [`aws-ec2-ops/references/rubric.md`](aws-ec2-ops/references/rubric.md) — pilot rubric instance
- [`aws-ec2-ops/references/prompt-templates.md`](aws-ec2-ops/references/prompt-templates.md) — pilot G/C/O skeletons
- [`aws-iam-ops/references/rubric.md`](aws-iam-ops/references/rubric.md) — second pilot rubric instance
- [`aws-iam-ops/references/prompt-templates.md`](aws-iam-ops/references/prompt-templates.md) — second pilot G/C/O skeletons
- [`aws-kms-ops/references/rubric.md`](aws-kms-ops/references/rubric.md) — third pilot rubric instance
- [`aws-kms-ops/references/prompt-templates.md`](aws-kms-ops/references/prompt-templates.md) — third pilot G/C/O skeletons
- [`aws-s3-ops/references/rubric.md`](aws-s3-ops/references/rubric.md) — fourth pilot rubric instance
- [`aws-s3-ops/references/prompt-templates.md`](aws-s3-ops/references/prompt-templates.md) — fourth pilot G/C/O skeletons
- [`aws-rds-ops/references/rubric.md`](aws-rds-ops/references/rubric.md) — Group 1 rubric
- [`aws-lambda-ops/references/rubric.md`](aws-lambda-ops/references/rubric.md) — Group 1 rubric
- [`aws-dynamodb-ops/references/rubric.md`](aws-dynamodb-ops/references/rubric.md) — Group 1 rubric
- [`aws-vpc-ops/references/rubric.md`](aws-vpc-ops/references/rubric.md) — Group 2 rubric
- [`aws-route53-ops/references/rubric.md`](aws-route53-ops/references/rubric.md) — Group 2 rubric
- [`aws-cloudfront-ops/references/rubric.md`](aws-cloudfront-ops/references/rubric.md) — Group 2 rubric
- [`aws-elb-ops/references/rubric.md`](aws-elb-ops/references/rubric.md) — Group 2 rubric (recommended)
- [`aws-athena-ops/references/rubric.md`](aws-athena-ops/references/rubric.md) — Group 6 rubric
- [`aws-athena-ops/references/prompt-templates.md`](aws-athena-ops/references/prompt-templates.md) — Group 6 G/C/O skeletons
- [`aws-guardduty-ops/references/rubric.md`](aws-guardduty-ops/references/rubric.md) — Group 6 rubric
- [`aws-guardduty-ops/references/prompt-templates.md`](aws-guardduty-ops/references/prompt-templates.md) — Group 6 G/C/O skeletons
- [`aws-opensearch-ops/references/rubric.md`](aws-opensearch-ops/references/rubric.md) — Group 6 rubric
- [`aws-opensearch-ops/references/prompt-templates.md`](aws-opensearch-ops/references/prompt-templates.md) — Group 6 G/C/O skeletons
- [`aws-ram-ops/references/rubric.md`](aws-ram-ops/references/rubric.md) — Group 7 rubric
- [`aws-ram-ops/references/prompt-templates.md`](aws-ram-ops/references/prompt-templates.md) — Group 7 G/C/O skeletons
- [`aws-securityhub-ops/references/rubric.md`](aws-securityhub-ops/references/rubric.md) — Group 7 rubric
- [`aws-securityhub-ops/references/prompt-templates.md`](aws-securityhub-ops/references/prompt-templates.md) — Group 7 G/C/O skeletons
- Top-level `CLAUDE.md` — shared baseline (dual-path, credentials, recovery table)

## 12. CodeGraph Integration (Code Knowledge-Graph Integration)

Local-first code knowledge graph tool ([colbymchenry/codegraph](https://github.com/colbymchenry/codegraph),
installed at `/Users/bohaiqing/.local/bin/codegraph`, Node v22.19.0). Builds a
local SQLite graph (`.codegraph/codegraph.db`) via tree-sitter, integrated
through MCP (tools `codegraph_explore` / `codegraph_node`). **Design goal:
cross-coding-agent universal** — one `codegraph serve --mcp` definition is
automatically projected to each agent's native config (OpenCode / Cursor /
Claude Code / Codex / Hermes Agent / Kiro / CodeBuddy, etc.) with no
per-agent adaptation. 100% local, no data leakage.

### Purpose

Before editing a skill's `SKILL.md` / `references/` or shared scripts
(`scripts/gcl_runner.py`, `_shared.py`, etc.), use CodeGraph to verify
**cross-skill reference consistency** and **change blast radius**, reinforcing
the Operational Guidelines rule "cross-file references must stay in sync across
three parties" (definitions / calls / docs).

This repo's 34 `aws-<svc>-ops` skills reference each other frequently (e.g.,
`aws-rds-ops`→`aws-aurora-ops`, `aws-elb-ops`↔`aws-vpc-ops`); changing one
place can affect many. `codegraph explore "aws-aurora-ops"` returned 36 symbols
across 3 files + blast radius in practice (`run_aws` has 61 callers across 15+
files).

### Commands

```bash
codegraph init .              # build graph first time (measured: 564 nodes / 1,329 edges)
codegraph sync .              # incremental sync of changes since last index (run before every code change)
codegraph explore "<symbol>"  # query blast radius / cross-file call sites
codegraph status              # query index status (Files/Nodes/Edges/DB Size)
```

### MCP Integration (cross-agent universal, done once)

**Single technique**: `codegraph serve --mcp` (stdio). One server definition is
automatically projected via `codegraph install -t all` into each agent's native
config (OpenCode / Cursor / Claude Code / Codex / Hermes / Kiro / CodeBuddy,
etc.); each agent just reads its own config — **no per-agent adapter code
needed**:

```bash
codegraph install -t all      # project codegraph MCP into all installed agents' global configs
# or specify: codegraph install -t opencode,cursor,claude,codex,hermes,codebuddy
```

- **Repo-level auto-discovery**: this repo root has `.mcp.json` (declares
  `mcpServers.codegraph`). Agents that support project-level MCP (Cursor /
  Claude Code / CodeBuddy with project-MCP) auto-detect and load it on opening
  this directory — no manual install needed.
- **CLI equivalents** (`codegraph explore` / `codegraph node` / `codegraph sync`)
  are always available even without MCP — the "sync + cross-skill check before
  editing" in AGENTS.md §12 does not depend on MCP.
- After install, **restart the relevant agent session** to take effect; uninstall
  with `codegraph uninstall -t all`.

### Rules

| Item | Requirement |
|------|-------------|
| **Before every code file change** (`.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` etc. tree-sitter-supported languages, not `.md`/`.yaml` docs) | **Must run `codegraph sync .`** (incremental sync) so subsequent `explore` / `impact` are based on the latest index; if no index exists, run `codegraph init .` first |
| `.codegraph/` | Its own `.gitignore` (`*` + `!.gitignore`) already excludes the contents; committing the index is forbidden; the root `.gitignore` may add `.codegraph/` (optional, keeps `git status` silent) |
| Before editing shared scripts / delegation refs | First `codegraph sync .` then `codegraph explore "<symbol>"` to confirm call sites match the docs |
| GCL task R2 content review | Use CodeGraph to help verify cross-skill delegation references exist (e.g., dirs pointed to by `SHOULD` / `SHOULD NOT` really exist) |
| Relation to self-review | Does not replace the 2-round self-review; only adds machine verification for cross-skill references |

### Boundary of applicability (by scenario — from 2026-07-19 session retro)

> **Key fact (measured):** CodeGraph builds a **code** symbol graph via
> tree-sitter and does **not index Markdown frontmatter**. This repo's skill
> corpus is Markdown-dominated (measured: within `aws-*` dirs, `.md` ≈ 72% /
> `.py` ≈ 9%); its `metadata:` / `delegate:` / delegation-dir references are
> **invisible to CodeGraph**.
> Therefore you must **route by file type (code vs non-code docs), not by
> specific language** — CodeGraph covers all supported languages via
> tree-sitter, not just Python; otherwise you get "didn't use it when you
> should, and used it but found nothing":

| Change type | Correct tool | Use CodeGraph? |
|------------|--------------|----------------|
| **Code files** (any tree-sitter-supported language: `.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` etc., including `_inference.py` / `_shared.py` / `gcl_runner.py` / `collectors` / `daily-health-check.py`) | `codegraph sync .` + `codegraph explore "<symbol>"` to check blast radius | ✅ **Must** — CodeGraph builds a code symbol graph via tree-sitter, covering all supported languages, not just Python |
| **Markdown skills** (`SKILL.md` / `references/*.md` / `AGENTS.md` frontmatter, delegation tables, routing tables) | `git grep` / Grep tool (verify by dir existence, string reference) | ❌ **Not needed** — CodeGraph does not index `.md`; forcing it returns "No relevant code" |

> **Improvement loop (dogfood):** This session once used Grep in place of
> CodeGraph throughout (violating §12), but the root cause was **tool
> mismatch** — a Markdown-dominated need should not have gone through CodeGraph
> in the first place. Corrected approach:
> 1. Before editing a Python script, **first `codegraph sync .` then `explore`**
>    to re-check blast radius (e.g., before editing `_inference.py`, confirm the
>    16 callers of `apply_chain_inference` are unaffected);
> 2. For editing Markdown skills, use Grep / `git grep`, do not force CodeGraph;
> 3. To make CodeGraph cover the skill corpus, it would need a Markdown
>    frontmatter extractor added (**out of scope for this §12**, a separate plan).

### Mandatory Split Gate (data-driven, must be strictly enforced — 2026-07-19 A/B comparison conclusion)

> **Decision basis (measured, not vibe):** This session ran an A/B test on two
> query types (Grep = B, current approach; CodeGraph CLI = candidate). Results:
>
> | Experiment | Query type | Grep result | CodeGraph result | Winner |
> |-----------|------------|-------------|------------------|--------|
> | E1 | Markdown delegation refs (who references aurora-ops) | **4/4 recall, 0 misses**, 0.03s | returned "36 code symbols", for the actual Markdown delegation question **0/4** | **Grep** |
> | E2 | Code symbol blast radius (make_incident) | 59 unique raw call sites, no test labels | 42 deduped callers + `⚠️ no-test` label | **CodeGraph** |
> | E3-Q1/3/5 | Non-code doc graph (Markdown skills) | correct* (regex must be right)*; Q5 missed because **my own glob was wrong** (truth=2: `aws-elb-ops/assets/example-config.yaml` + `aws-aiops-orchestrator/SKILL.md`, Grep returned 0) | structurally blind to `.md` | **Grep** (when query correct) |
> | E3-Q2/4 | Code symbol call graph (Python etc. tree-sitter languages) | 71 raw lines, needs manual dedup | 61/34 callers + test labels, instant | **CodeGraph** |
>
> **Conclusion:** Forcing a single tool ("all CodeGraph" or "all Grep") degrades
> **about half** the queries in this repo. The correct strategy is **routing by
> file type** — this is the conclusion that the §12 "Boundary of applicability"
> subsection is **validated by this experiment's data**.

| Query/change type | **Mandatory** tool | Forbidden | Rationale (measured) |
|-------------------|--------------------|-----------|----------------------|
| **Non-code docs** (`.md` frontmatter/delegation tables/routing tables, `references/*.md`, `AGENTS.md`, `*.yaml` config docs) | **Grep / `git grep`** | ❌ Must not use CodeGraph | CodeGraph does not index non-code docs; E1 measured 0/4 |
| **Code files** (any tree-sitter language: `.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` etc.) blast radius / call sites | **`codegraph sync .` + `codegraph explore`** | ❌ Must not just use Grep | E2 measured CodeGraph adds dedup + test-coverage labels; tree-sitter covers all supported languages, not just Python |
| **Any query** | Query must be **constructed correctly** (glob/regex/args must match repo's actual layout) | ❌ Must not fudge with wrong glob/regex/args | E3-Q5: my own glob `aws-*-ops` failed to match `aws-aiops-orchestrator` (no `-ops` suffix) causing a miss, truth=2 not 0/1 — a bad query = silent wrong answer, independent of the tool |

> **Final verdict (2026-07-19 A/B comparison conclusion, 5 reviewers unanimous):**
> Forcing a single tool ("all CodeGraph" or "all Grep") degrades **about half**
> the queries in this repo. CodeGraph (tree-sitter code symbol graph) and Grep
> are **complementary**, not substitutes — the former works on **code files of
> all supported languages**, the latter on **non-code docs** (`.md`/`.yaml`
> frontmatter).
> **Winning approach = route by file type** (not by language, not either/or):
> - 🟢 Code files (any tree-sitter language) → `codegraph sync .` + `explore`
> - 🟢 Non-code docs (`.md`/`.yaml`) → Grep / `git grep`
> - 🟢 Any query → first verify the glob/regex matches the repo's actual dir layout
>
> **Execution discipline (user hard constraint):** Once this routing decision is
> made, **enforce it strictly in every subsequent action** — all non-code doc
> queries use Grep, all code blast-radius queries use CodeGraph; do not fall back
> to a single tool out of habit. Violation is treated as a quality regression.
> This gate works with §13 CADL and the Operational Guidelines
> "Fan-out Subagents": each subtask must still go through the corresponding
> routing + asset distillation.
>
> **`sync` is not enough (finer lesson, 2026-07-19 Task #10 retro):**
> when CodeGraph *is* the right tool (code files), running only `codegraph sync .`
> builds the index but yields **nothing actionable** — the high-value step is the
> **integration-point query** (`explore` / `node` / `callers`) that reveals
> the call graph, signatures, and cross-file contracts *before* editing.
> This session, a fan-out added 5 collectors + inline inference blocks; `sync` ran but
> the `callers`/`node` queries were skipped during coding and only run post-hoc
> to answer a user challenge — they immediately surfaced the `(incidents, {svc:
> signals})` collector→inference contract and the `test_all_collectors_run`
> test that exercises all collectors, which Read-alone would have taken longer.
> **Disposition:** for code changes, run `sync` *then* `explore`/`callers`/`node`
> to locate integration points and callers **before** stitching — not just baseline sync.
> Do not claim "CodeGraph integrated" if only `sync` ran; be precise about what
> was actually done (matches the honesty bar in §12's wrong-query lesson).

> **Asset landing (correct CADL placement):** The most transferable lesson from
> this experiment — "a **wrong query (bad glob/regex) is more insidious than a
> wrong tool, it answers silently wrong**" (E3-Q5) — must be written separately
> to `docs/failure-patterns.md` (pitfall assets go to failure-patterns, not
> AGENTS.md), for any future agent to retrieve and reuse.


### Pre-commit Hard Gate (硬门禁 — automation, not suggestion)

The rules above are **enforced**, not advisory. `scripts/hooks/pre-commit` runs
automatically on `git commit` (after one-time `bash scripts/install-hooks.sh`).
Five triggers, all blocking:

1. `aws-*-ops/*/SKILL.md` staged → for each changed skill, verify every name in
   `metadata.cross_skill_deps` / `metadata.delegate` keys points to an existing
   directory in this repo (`test -d`); fail commit if any miss.
2. `scripts/gcl_runner.py` or `scripts/te_gate.py` staged → run their
   `--self-test` / `--all --strict` modes respectively; fail commit on regression.
3. **Every commit** → run the complete repository unit-test suite
   `pytest -p no:rerunfailures scripts/tests/ -q`; every collected test MUST
   pass before `git commit` may proceed. A failed, errored, timed-out, skipped
   due to missing dependencies, or unexecuted required test blocks the commit;
   fix the regression or restore the required test environment first. Do not
   weaken, delete, mark `xfail`, or skip a test merely to make the gate pass.
4. Code files (`.py`/`.ts`/`.go`/`.rs`/`.js`/`.java`) staged → `codegraph sync .`
   runs as part of the hook (mandatory pre-flight per §12 above).
5. `REPO_ROOT` env var overrides auto-detection (testability only).

**Bypass**: only for emergency hotfixes, with `git commit --no-verify`; the
bypass event MUST be logged in the commit body.


## 13. Compound-Asset Distillation Loop (CADL)

**A working loop, not a single rule**: after any substantive task, the Agent
must complete "extract → decide landing → write → gate" before finishing — a
task without distillation is an unfinished task. Make every pitfall, review,
and cross-skill collaboration into a reusable asset for next time, building
compound interest.

> CADL loop mechanism, adapted to this repo's terminology: `{{env.*}}`/
> `{{user.*}}`/`{{output.*}}` placeholders, Reflexion Memory
> (`docs/failure-patterns.md`), CodeGraph (§12), AGENTS.md line gate (≤500 lines).

### Triggers (apply CADL if any is met)

- Multi-step / cross-file task completed
- Cross-skill collaboration (delegation matrix or parallel agent / oracle / explore)
- Review / fix loop (GCL, 2-round self-review, Oracle consultation)
- Discovered a repo defect / pitfall (even if outside this scope)
- Found a pre-existing FAIL during verification and attributed its cause
- User gave a reusable workflow preference (e.g., "dual-write subcommand to bypass CLI bug")

### Loop steps

```
1. Extract   → abstract a reusable pattern (pitfall to avoid / review dimension / collaboration pattern / verification command / helper)
               format: "problem → anti-pattern → correct approach (with code example)"
2. Decide landing → leaving this repo? → ~/.config/opencode/AGENTS.md
                    this repo only? → this project's AGENTS.md
                    failure mode / pitfall? → docs/failure-patterns.md
                    a skill-specific capability? → standalone Skill (via aws-skill-generator)
3. Write     → executable + with example + with boundaries; first grep the target file to confirm uncovered
4. Gate      → wc -l before writing; if this file is ≥500 lines, trim before writing (note: currently ~675 lines; overflow source is §11 GCL's existing bulk + §12/§13 extensions; next optimization can move §11's long tables out)
5. Reuse     → next time a similar task reads the target file and gets the asset → compound interest takes effect
```

### Skill-side hook (give every Skill its own distillation awareness)

- **Source**: `aws-skill-generator`, when generating each skill, must inject one
  line at the end of SKILL.md:
  `> After completing a task, review and distill reusable assets per the root AGENTS.md "Compound-Asset Distillation Loop (CADL)".`
  All future `aws-<svc>-ops` automatically inherit this awareness.
- **Existing skills**: progressively add the same hint line at the end of each
  SKILL.md so any model invoking any skill sees the trigger signal. (Injecting
  the hook into the 34 existing `aws-*-ops` is incremental, not in this CADL
  migration scope; add later as needed.)

### Anti-patterns (violating CADL)

| Anti-pattern | Correct approach |
|---|---|
| Finish a task and stop, no distillation | Complete the CADL loop before delivering |
| Write one-off context into AGENTS.md as an asset | Only distill patterns reusable across tasks |
| Duplicate an existing entry | grep to confirm uncovered before writing |
| Distill only on CodeGraph-related tasks | Reviews/fixes/collaboration/verification all trigger |
| Write pitfall assets into AGENTS.md instead of failure-patterns.md | Pitfalls/failure modes go to `docs/failure-patterns.md`, general patterns go to AGENTS.md |

### Compound asset example: declarative-contract-first (from `skill-as-infrastructure` rollout)

> Reusable pattern (cross-task / cross-enterprise LLM ecosystem general):
> **Problem** → an agent skill system needs composite/copilot skills to be
> machine-recognizable and composable.
> **Anti-pattern** → introduce a private registry / dedicated loader (coupled to
> a specific agent runtime).
> **Correct approach** → add **minimal declarative-contract** fields to the
> existing frontmatter (`metadata.type` / `provides` / `delegate`), enforced by
> the **existing** self-check framework (Charter C7); any agent only needs to
> `glob aws-*-ops/SKILL.md` and read frontmatter to compose — zero private
> loader, runtime-agnostic.
> Generalize: for any need to "make X machine-recognizable / composable", prefer
> adding declarative fields + reusing the existing gate, rather than building
> private infrastructure.

### Compound asset example: contract evolution must grandfather existing (from C7 retro)

> Reusable pattern (cross-task / cross-enterprise LLM ecosystem general):
> **Problem** → when adding a new contract (e.g., `metadata.type: composite`),
> existing skills already using a different value (e.g., `orchestrator-meta`)
> would be misjudged orphan / HALT by the new gate.
> **Anti-pattern** → ignore existing assets after changing the contract, or
> force-edit existing frontmatter to align (expands scope, introduces regressions).
> **Correct approach** → explicitly include the existing equivalent value in the
> contract's allowed-value set (`composite` ≡ `orchestrator-meta`), synchronize
> in three places — template comment / Charter / AGENTS.md — without touching
> the existing skills themselves. Before adding a new contract, first `grep`
> globally to confirm no missing legacy values.

## 14. Token Efficiency Hard Gate & Deduplication Spec (TE Hard Gate)

> Repo-wide hard requirement, constraining both the output of
> `aws-skill-generator` **and** anyone manually editing a skill.
> Same source as `aws-skill-generator/SKILL.md` §Token Efficiency Requirements
> (C6 MUST-PASS). Full thresholds / dedup precedents / existing-asset remediation
> strategy in [`docs/te-hard-gate.md`](docs/te-hard-gate.md).

**Core thresholds (C6 hard metrics, any fail ⇒ no merge):**
- **G1** `SKILL.md` ≤ 120 lines; **G2** no >5-line hardcoded static table (use
  an API instead, TE-1); **G3** JSON paths declared only once at top (TE-4);
  **G4** no cross-file duplicated flow / boilerplate (TE-6); **G5** boto3 no
  docstring (TE-2); **G6** compact error table (TE-3).
- **Dedup principle**: content appearing in ≥2 skills must be extracted to a
  single source of truth (precedent: `_sync_prompt_skeletons.py` reduced 31
  skills' ~5,800 lines of GCL boilerplate to a 231-line skeleton + thin deltas).
- **Incremental remediation of existing assets**: new/changed skills must meet
  the bar; of the 34 existing `aws-*-ops` over-length ones
  (ec2/cloudwatch/cloudtrail/dynamodb/config/ram/acm/waf), trim back to ≤120
  lines as opportunity allows.

### Compound asset example: discipline must dogfood itself (from finsecops-optimization retro)

> Reusable pattern (cross-task / cross-enterprise LLM ecosystem general):
> **Problem** → repo discipline (e.g., "write spec+plan before implement") is
> easily and quietly violated by later changes, with no self-check anchor.
> **Anti-pattern** → discipline lives only in AGENTS.md; the landing commit does
> not reference the corresponding spec/plan.
> **Correct approach** → the discipline's **own rollout commit** must carry the
> spec+plan that references the discipline (precedent: when `33f18ba` added the
> `Spec + Plan Before Implement` rule, it also landed
> `2026-07-19-finsecops-optimization-design.md` + the corresponding plan). Make
> the discipline "obey itself", so any agent reviewing the commit can verify the
> discipline was dogfooded, not merely declared.

## 15. Runtime Safety Hook Protocol (L4 dim #6)

The compile-time checks (A1–A16, GCL rubric, §12 cross-skill sync) defend
against unsafe *patterns*. The runtime hook (`scripts/runtime_safety.py`,
L4 dim #6) defends against unsafe *executions* by checking an in-flight
tool call against the historical failure library
(`docs/failure-patterns.md`, written by `_reflexion.py`).

> **Hard rule**: every agent that executes destructive AWS ops
> (`delete*` / `terminate*` / `detach*` / `revoke*` / `disable*` /
> `deregister*` / `drop*` / `destroy*`) MUST invoke the runtime hook
> in its `pre_tool_use` phase. Skipping it is treated as a §11 GCL
> violation and a §14 TE gate violation.

### Decision table

| `is_destructive` | `safety_confirm` | Pattern match (count ≥ 3) | Pattern match (count < 3) | No match | Decision |
|---|---|---|---|---|---|
| `false` | any | — | — | — | **ALLOW** |
| `true`  | empty | — | — | — | **BLOCK** |
| `true`  | non-empty | — | — | yes | **ALLOW only with exact plan token** |
| `true`  | any | yes | — | — | **BLOCK** |
| `true`  | non-empty | — | yes | — | **BLOCK** |

`count >= 3` is the empirically chosen threshold (L4 maturity model's
gap #3 fix). Lower it cautiously — every lower threshold
inflates false-positive BLOCKs and erodes agent trust.

### Agent integration

```bash
echo '{"tool_name":"aws ec2 terminate-instances","args":{"instance_ids":["i-xxx"]},"is_destructive":true,"safety_confirm":"<token>"}' \
  | python3 scripts/runtime_safety.py --patterns docs/failure-patterns.md
# stdout: {"decision":"ALLOW|WARN|BLOCK","reason":"...","matched_patterns":[...]}
# exit 0 = ALLOW, 1 = BLOCK, 2 = WARN
```

| Runtime | Integration point |
|---|---|
| OpenCode / Codex CLI | `pre_tool_use` hook in `~/.codex/config.toml` |
| Claude Code | `PreToolUse` matcher in `settings.json` → call `runtime_safety.py` |
| Custom agent | invoke via subprocess; respect exit code (0/1/2) |

`is_destructive` is derived inside `runtime_safety.py` from the operation name;
the caller-provided legacy field is ignored for the decision. Destructive
operations require the exact token generated by
`build_confirmation_token(ToolCall(...))`, which binds the normalized
operation and arguments. A random non-empty confirmation is not sufficient.

For executable tool calls, prefer the single proxy boundary:

```bash
echo '{"command":["aws","ec2","terminate-instances","--instance-ids","i-xxx"],"args":{"instance_ids":["i-xxx"]},"safety_confirm":"<exact-token>"}' \
  | python3 scripts/safe_tool_proxy.py --patterns docs/failure-patterns.md
```

The proxy executes only `ALLOW`; it never executes `WARN` or `BLOCK`. It
accepts only the trusted `aws` executable resolved from `PATH`, derives the
confirmation plan from the actual argv, and passes a reduced environment to
the child process (AWS credential variables are retained only for the AWS
CLI child; arbitrary caller executables are rejected).

### Library API

```python
from runtime_safety import ToolCall, CheckResult, check_tool_call

call = ToolCall(
    tool_name="aws ec2 terminate-instances",
    args={"instance_ids": ["i-xxx"]},
    is_destructive=True,
    safety_confirm="CONFIRM-X",
)
patterns = load_failure_patterns(Path("docs/failure-patterns.md"))
result: CheckResult = check_tool_call(call, patterns)
# result.decision ∈ {"ALLOW", "WARN", "BLOCK"}
```

Spec: [`docs/superpowers/specs/2026-07-25-runtime-safety-design.md`](docs/superpowers/specs/2026-07-25-runtime-safety-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-runtime-safety.md`](docs/superpowers/plans/2026-07-25-runtime-safety.md).

## 16. Eval-Driven Dev Protocol (L4 #7)

The compile-time gates (§11 / §12 / §14) enforce invariants; the runtime gate
(§15) catches dangerous executions. **Eval-Driven Dev** (L4 #7) catches
*silent capability regressions*: a SKILL.md change that breaks a happy-path
scenario without violating any compile-time rule.

> **Hard rule**: every L1/L2 skill must ship a `golden-scenarios.yaml`
> fixture with **≥5 scenarios**. Any PR that touches `aws-<svc>-ops/SKILL.md`
> or its `references/` MUST re-run `python3 scripts/golden_eval.py diff`
> and report `0 regressions` before merge.

### Scenario anatomy

```yaml
# aws-<svc>-ops/golden-scenarios.yaml
---
skill: aws-<svc>-ops
description: |
  Golden suite for aws-<svc>-ops v<version>. <N> scenarios.
scenarios:
  - id: <unique-scenario-id>
    description: <1-line human description>
    request: <user natural-language request>
    expected_status: PASS | SAFETY_FAIL | MAX_ITER
    user_region: <aws-region>       # optional, defaults to ""
    safety_confirm: <token>         # optional, defaults to ""
```

`expected_status` MUST be one of `PASS`, `SAFETY_FAIL`, `MAX_ITER` (the
three GCL termination outcomes from `gcl-spec.md` §5). Other strings
rejected at load time.

### Coverage minimums

Per skill, scenarios should cover the matrix:

| Bucket | Min count | Examples |
|---|---|---|
| Read-only happy path | ≥2 | `list X`, `describe Y` |
| Confirmed destructive | ≥2 | `terminate with --confirm=...` |
| Destructive without confirm | ≥1 | `terminate without --confirm` |
| Idempotency check | ≥1 | request followed by same request |

For a base skill that is small (e.g. `aws-ram-ops`), 5 scenarios is
acceptable. For composite skills (`aws-aiops-copilot` etc.), 10+.

### CLI reference

```bash
# 1. Run all scenarios, persist JSON results
python3 scripts/golden_eval.py run \
  --skill aws-ec2-ops \
  --scenarios aws-ec2-ops/golden-scenarios.yaml \
  --out audit-results/golden/aws-ec2-ops.json

# 2. Save the current run as the canonical baseline (one-time, in CI hook)
python3 scripts/golden_eval.py run ... --out /path/to/baseline.json
git add aws-ec2-ops/golden-scenarios.yaml audit-results/golden/aws-ec2-ops.json

# 3. Detect regressions on subsequent runs
python3 scripts/golden_eval.py diff \
  --current audit-results/golden/aws-ec2-ops.json \
  --baseline audit-results/golden/aws-ec2-ops-baseline.json
# exit 0 = no regression, 1 = regression detected
```

### Library API

```python
from golden_eval import (
    Scenario, ScenarioResult, BaselineReport,
    load_scenarios, run_scenario, run_scenarios,
    compare_to_baseline, save_results, load_results,
)

scenarios = load_scenarios(Path("aws-ec2-ops/golden-scenarios.yaml"))
results = run_scenarios(scenarios, skill="aws-ec2-ops")
baseline = load_results(Path("audit-results/golden/baseline.json"))
report = compare_to_baseline(results, baseline)
if report.has_regression:
    raise SystemExit(f"regressions: {report.regressions}")
```

### Decision table — when to add scenarios

| Trigger | Action |
|---|---|
| New skill published | bootstrap with 5 scenarios |
| New operation in `references/aws-cli-usage.md` | add ≥1 scenario |
| Operator reports a real-world failure | add scenario that **reproduces** the failure (`expected_status: SAFETY_FAIL`) |
| F-# (failure-pattern) added with count ≥ 5 | promote the failure to a golden scenario so the suite covers it |
| Quarterly review | scan last 30 days of `gcl-trace-*.json`, derive new scenarios from real user requests |

### Strict-mode gate (CI integration)

Add to `.github/workflows/golden.yml` (out of scope for this PR):

```yaml
- run: python3 scripts/golden_eval.py diff --current audit-results/golden/$SKILL.json --baseline audit-results/golden/$SKILL-baseline.json
  name: golden regression check
```

Spec: [`docs/superpowers/specs/2026-07-25-eval-driven-dev-design.md`](docs/superpowers/specs/2026-07-25-eval-driven-dev-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-eval-driven-dev.md`](docs/superpowers/plans/2026-07-25-eval-driven-dev.md).

## 17. Telemetry Dashboard Protocol (L4 #8)

§11 (GCL) writes traces; §13 (CADL) writes reflection; §15 (Runtime Safety)
writes blocks; §16 (Golden Eval) writes baselines. **§17 (Telemetry Dashboard)**
unifies all of them into a single 30-day rolling view that human reviewers
and CI bots can both read.

> **Hard rule**: every CI pipeline that runs GCL/Golden must also
> run `python3 scripts/telemetry_dashboard.py alert` and respect exit
> code 1 as a blocking alert.

### Sources (3 readers, 1 schema)

| Source | Path | Schema |
|---|---|---|
| GCL trace | `audit-results/gcl-trace-*.json` | `{skill, final.status, iterations[].critic.scores}` |
| Golden run | `audit-results/golden/*.json` | `{skill, results:[{matched_status, ...}]}` |
| Reflexion | `docs/failure-patterns.md` (count >= 3 rows) | `{skill, command, count}` |

All three sources normalize into `SignalSlice { skill, status, timestamp, source }`,
then aggregate into `Dashboard { by_skill: [SkillMetric], by_fail_mode, ... }`.

### CLI reference

```bash
# Render dashboard
python3 scripts/telemetry_dashboard.py dashboard \
  --audit-dir audit-results/ \
  --window-days 30 \
  --out docs/telemetry/dashboard.md

# CI alert: exit 1 if any skill's pass_rate drops ≥ threshold vs prior 30 days
python3 scripts/telemetry_dashboard.py alert \
  --audit-dir audit-results/ \
  --window-days 30 \
  --drop-threshold 0.05
# stdout: ## Alerts
#         - aws-ec2-ops: pass_rate 1.00 -> 0.77 (Δ-0.23)
# exit 0 = no regression, 1 = regression detected
```

### Library API

```python
from telemetry_dashboard import (
    SignalSlice, SkillMetric, Dashboard,
    load_signals, compute_dashboard,
    detect_regressions, render_markdown,
)

signals = load_signals(Path("audit-results/"))
dash = compute_dashboard(signals, window_days=30, prior_window_days=30)
flagged = detect_regressions(dash, drop_threshold=0.05)
md = render_markdown(dash)
```

### Alert decision table

| Current window | Prior window | Delta | Threshold=0.05 | Action |
|---|---|---|---|---|
| ≥1 signal | ≥1 signal | >= -0.05 | safe | **exit 0** |
| ≥1 signal | ≥1 signal | < -0.05 (e.g. -0.10) | regressed | **exit 1** alert |
| ≥1 signal | 0 signals | n/a | insufficient history | **exit 0** (do not alert on first 30 days) |
| 0 signals | any | n/a | no recent activity | **exit 0** |

The "first 30 days" exclusion prevents false alarms when telemetry is
first wired up — it's a generous warm-up window.

### CI integration

```yaml
# .github/workflows/telemetry-alert.yml
- name: Telemetry regression check
  run: |
    python3 scripts/telemetry_dashboard.py alert \
      --audit-dir audit-results/ \
      --drop-threshold 0.05
- name: Generate dashboard artifact
  if: always()
  run: |
    python3 scripts/telemetry_dashboard.py dashboard \
      --audit-dir audit-results/ \
      --out docs/telemetry/dashboard.md
- uses: actions/upload-artifact@v4
  with:
    name: telemetry-dashboard
    path: docs/telemetry/dashboard.md
```

Spec: [`docs/superpowers/specs/2026-07-25-telemetry-dashboard-design.md`](docs/superpowers/specs/2026-07-25-telemetry-dashboard-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-telemetry-dashboard.md`](docs/superpowers/plans/2026-07-25-telemetry-dashboard.md).

## 18. A/B Test Hard Gate Protocol (L4 #9)

P2.2 (`§16 Eval-Driven Dev`) ships the **what to test** (golden scenarios).
P2.3 (`§17 Telemetry Dashboard`) ships the **aggregate view**.
**§18 (A/B Hard Gate)** ships the **CI gate**: when you change a skill,
the build fails if any golden scenario regressed.

> **Hard rule**: every PR that touches `aws-<svc>-ops/SKILL.md`, its
> `references/`, or any L2 composite's `metadata.cross_skill_deps`
> MUST pass `python3 scripts/ab_gate.py gate --baseline <before.json>
> --candidate <after.json>` with exit 0. CI uses the `--json` form.

### Decision matrix

| Scenario state | baseline ↦ candidate | Action | exit_code |
|---|---|---|---|
| matched | True ↦ True | **unchanged** | 0 |
| matched | True ↦ False | **regression** | 1 |
| matched | False ↦ True | **fixed** | 0 |
| missing_in_baseline | new scenario | not a regression | 0 |
| missing_in_candidate | scenario disappeared | **regression** | 1 |
| file not found | n/a | error | **2** |
| invalid JSON | n/a | error | **2** |

Exit codes follow POSIX conventions: 0 = pass, 1 = regression, 2 = misuse.

### CLI reference

```bash
# 1. Standard CI gate
python3 scripts/ab_gate.py gate \
  --baseline audit-results/golden/aws-ec2-ops-baseline.json \
  --candidate audit-results/golden/aws-ec2-ops.json

# 2. JSON output (CI consumes directly)
python3 scripts/ab_gate.py gate \
  --baseline ... --candidate ... --json
# stdout: {"regressions":["..."],"fixed":["..."],"unchanged":["..."],"exit_code":1}

# 3. Cascade discovery (advisory, not part of gate decision)
python3 scripts/ab_gate.py cascade --skill aws-aiops-copilot
# stdout: cascaded skills for aws-aiops-copilot:
#         - aws-aiops-cruise
#         - aws-aiops-orchestrator
```

### CI workflow integration

```yaml
# .github/workflows/ab-gate.yml
- name: A/B gate
  run: |
    # baseline is the saved baseline.json from main branch
    git show origin/main:audit-results/golden/aws-ec2-ops-baseline.json \
      > /tmp/baseline.json || echo '{"results":[]}' > /tmp/baseline.json
    python3 scripts/golden_eval.py run \
      --skill aws-ec2-ops \
      --scenarios aws-ec2-ops/golden-scenarios.yaml \
      --out /tmp/candidate.json
    python3 scripts/ab_gate.py gate \
      --baseline /tmp/baseline.json \
      --candidate /tmp/candidate.json \
      --json
```

### Library API

```python
from ab_gate import ABReport, run_ab_gate, cascaded_skills

report = run_ab_gate(
    Path("audit-results/baseline.json"),
    Path("audit-results/candidate.json"),
)
if report.exit_code == 1:
    raise SystemExit(f"regressions: {report.regressions}")

cascaded = cascaded_skills("aws-aiops-copilot")
# Returns list[str] of cross_skill_deps dir names.
# Advisory; the gate does NOT recurse automatically.
```

### Why separate from §17 (Telemetry)?

| | §17 Telemetry | §18 A/B Gate |
|---|---|---|
| Input | All signals over 30 days | Two snapshots (T0, T1) |
| Granularity | Per-skill pass-rate delta | Per-scenario matched_status |
| Latency | Real-time after data accumulates | At PR time |
| Exit | 1 if any skill regressed | 1 if any scenario regressed |
| Use case | "is prod healthy?" | "is this PR safe to merge?" |

Both can run in the same CI: gate (fast, per-PR) → telemetry (slow, post-merge).
A regression caught by gate SHOULD also surface in telemetry within 1 day.

Spec: [`docs/superpowers/specs/2026-07-25-ab-gate-design.md`](docs/superpowers/specs/2026-07-25-ab-gate-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-ab-gate.md`](docs/superpowers/plans/2026-07-25-ab-gate.md).

## 19. Cross-Session Memory Protocol (L4 #10)

P2.1-P2.4 in-memory and file-backed signals (failure patterns, golden
baselines, telemetry traces). **§19 (Cross-Session Memory)** is the only
piece that survives an **agent restart** — it persists project-context
into `.omc/conventions.json`, the sidecar that complements
(but does not replace) the auto-scanned `.omc/project-memory.json`.

> **Hard rule**: every new agent session SHOULD call
> `python3 scripts/session_memory.py render --max-chars 2000` at startup
> and prepend the output to its first user-facing message. This loads
> prior learnings without re-derivation.

### Sidecar file

`.omc/conventions.json` is an **agent-managed** JSON file. Schema is **flat**
on purpose — JSON rather than Markdown so any runtime (Python, JS, Shell)
can parse it cheaply.

```json
{
  "version": "1.0.0",
  "updated_at": "2026-07-25T...",
  "records": [
    {
      "id": "mem-001",
      "timestamp": "2026-07-25T...",
      "scope": "convention" | "user-pref" | "repo-fact" | "tool-choice",
      "summary": "≤ 120 char headline",
      "detail": "optional longer form",
      "confidence": 0.0..1.0,
      "source_session": "session-uuid",
      "tags": ["safety", "runtime-hook"]
    }
  ]
}
```

> **NB**: do NOT mix this with `.omc/project-memory.json` (842 lines, auto-
> scanned tech-stack). They serve different purposes; agents should write
> only to `.omc/conventions.json`.

### Scopes (decide which one fits)

| Scope | When to use |
|---|---|
| `user-pref` | user's explicit preference (e.g., "Chinese docs canonical") |
| `repo-fact` | hard fact about the repo ("31 skills, 22 required") |
| `convention` | agreed-upon rule (e.g., "always run ruff before commit") |
| `tool-choice` | technology decision (e.g., "use ruff instead of flake8") |

### CLI reference

```bash
# 1. Record (manual or agent-derived)
python3 scripts/session_memory.py record \
  --scope convention \
  --summary "Always invoke runtime_safety before destructive ops" \
  --detail "§15 hard rule" \
  --confidence 0.95 \
  --source-session $OMC_SESSION_ID \
  --tag safety --tag runtime-hook

# 2. Query (keyword search, top-k)
python3 scripts/session_memory.py query "aws region safety" --top 3

# 3. Render (for system-prompt injection)
python3 scripts/session_memory.py render --max-chars 2000

# 4. List (humans debugging)
python3 scripts/session_memory.py list
```

### Derive-vs-record flow

Heuristic v0 (`derive_candidates(transcript)`) extracts candidate
records with `confidence=0.6`. Agent reviews candidates and only
**explicitly saves** the ones worth keeping. This prevents the
convention file from filling with noise.

```python
from session_memory import (
    MemoryRecord, load_memory, save_memory,
    derive_candidates, add_record,
)

# End of session: derive candidates from transcript, save keepers
transcript = [...]  # [{role, content}, ...]
records = load_memory(Path(".omc/conventions.json"))
for c in derive_candidates(transcript, source_session=SESSION_ID):
    # Agent-judgment filter (user runs review, no auto-save)
    if c.confidence >= 0.8 and len(c.summary) >= 12:
        add_record(records, scope=c.scope, summary=c.summary,
                   detail=c.detail, confidence=c.confidence,
                   source_session=SESSION_ID, tags=c.tags)
save_memory(records, Path(".omc/conventions.json"))
```

### Decision matrix — derive, record, or skip?

| Trigger | Action |
|---|---|
| User says "convention: ..." | derive → record (high conf) |
| User corrects agent behavior | derive → record |
| Agent discovers new repo fact | record manually (skip heuristic) |
| One-off task outcome | skip (use failure-patterns.md instead) |
| Routine Q&A | skip (transient) |

### Pruning (TBD)

Currently no auto-prune. Add `--older-than-days` flag in a future iteration
when records exceed a few hundred.

### Integration with §15 (Runtime Safety Hook)

The runtime hook already records to `docs/failure-patterns.md`. Cross-session
memory is **complementary**: failures stay in `failure-patterns.md`
(canonical, signal-rich), conventions stay in `conventions.json`
(low-volume, preference-bearing).

Spec: [`docs/superpowers/specs/2026-07-25-cross-session-memory-design.md`](docs/superpowers/specs/2026-07-25-cross-session-memory-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-cross-session-memory.md`](docs/superpowers/plans/2026-07-25-cross-session-memory.md).

## 20. Cross-Runtime Portability Protocol (L4 #11)

§15-§19 ship L4 protocols in one agent runtime (Codex CLI). §20 broadens
the contract: a skill authored here must be **portable** across the major
agent runtimes (Codex CLI, Claude Code, Cursor).

> **Hard rule**: every PR that adds a new skill or updates an existing
> skill's runtime integration must pass
> `python3 scripts/cross_runtime_lint.py lint --skill <name>` with
> score >= 0.85. CI runs `lint --all` against the whole repo.

### Why static lint, not "run on all 3 runtimes"?

Each agent runtime requires its own sandbox (Codex CLI shell, Claude Code
license, Cursor subscription). Running the same prompt through 3 runtimes
inside one CI job is expensive + flaky. **Static lint catches 80% of
portability issues** without that overhead. Phase P3.3 (auto skill
generation) may revisit this with a smaller smoke-test matrix.

### Detection patterns (12 known)

| Pattern | Runtime | Severity |
|---|---|---|
| `~/.codex/` hardcode | Codex CLI | high |
| `~/.claude/` hardcode | Claude Code | high |
| `~/.cursor/` hardcode | Cursor | high |
| `/Users/<name>/` in skill content | host path | critical |
| `/home/<name>/` in skill content | host path | critical |
| `python3.X.Y` exact pin | py-version | medium |
| `<N.N.N>` exact version | version-pin | medium |
| `/usr/local/bin/X` absolute | usr-local | medium |
| `/usr/bin/X` absolute | usr-bin | low |
| `wheel install` instructions | wheel-install | low |
| `sudo apt` instructions | sudo-apt | high |
| `` `brew install` `` | brew | low |

### Scoring

```python
score = max(0.0, 1.0 - (sum_weighted_hits / 10.0))
```

- `score == 1.0` — no detected coupling (clean)
- `score >= 0.85` — at most minor hits (CI pass)
- `score 0.6–0.85` — review recommended
- `score < 0.6` — must fix before merge

The `/ 10.0` divisor makes hit counts additive but bounded:
1 critical hit + 2 medium hits = (1.5 + 0.4 + 0.4) / 10 = 0.23 → score 0.77.

### CLI reference

```bash
# Single skill
python3 scripts/cross_runtime_lint.py lint --skill aws-ec2-ops --repo .

# Whole repo (CI / nightly)
python3 scripts/cross_runtime_lint.py lint --all \\
    --out docs/runtime/cross-runtime-2026-07-25.md

# JSON for CI consumption
python3 scripts/cross_runtime_lint.py lint --skill aws-ec2-ops --json
```

### Portable-fix hints (auto-generated)

Each runtime triggers a specific fix:

| Runtime hit | Suggested fix |
|---|---|
| `codex` | move `~/.codex/config.toml` reference to AGENTS.md §15 integration table; symlink for portability |
| `claude` | same, for `~/.claude/settings.json` |
| `host-path` | replace `/Users/<name>/` with `$HOME/` or `python3 scripts/...` |
| `py-version` | remove `python3.X.Y` pin; rely on shebang `#!/usr/bin/env python3` |
| `version-pin` | use `>=N.N` instead of exact `N.N.N` |

### CI integration

```yaml
# .github/workflows/portability.yml
- name: Cross-runtime portability
  run: |
    python3 scripts/cross_runtime_lint.py lint --all \\
      --out docs/runtime/cross-runtime.md
    SCORE=$(python3 -c "
import json,sys
from cross_runtime_lint import lint_repo
from pathlib import Path
r = lint_repo(Path('.'))
print(min((x.score for x in r.values()), default=1.0))
")
    if (( $(echo "$SCORE < 0.85" | bc -l) )); then
      echo "FATAL: portability score $SCORE < 0.85"
      exit 1
    fi
```

Spec: [`docs/superpowers/specs/2026-07-25-cross-runtime-lint-design.md`](docs/superpowers/specs/2026-07-25-cross-runtime-lint-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-cross-runtime-lint.md`](docs/superpowers/plans/2026-07-25-cross-runtime-lint.md).

## Changelog

| Date | Change |
|------|--------|
| 2026-07-04 | Added §Operational Guidelines: Task Tracking, GCL Skip Threshold, Pre-existing Lint Baseline |
| 2026-07-11 | Added §12 CodeGraph Integration: local code knowledge graph (colbymchenry/codegraph) for cross-skill reference consistency + blast-radius checks; `codegraph init .` indexed 564 nodes / 1,329 edges |
| 2026-07-18 | Added §13 Compound-Asset Distillation Loop (CADL); wires the extract→decide-landing→write→gate loop into every substantial task; generator injects the CADL hook line into new skills' SKILL.md |
| 2026-07-19 | Added §Operational Guidelines `### Fan-out Subagents (as much as feasible) — MANDATORY`; user hard constraint: fan out independent subtasks to parallel subagents, main Agent only orchestrates+synthesizes, strictly enforced in every subsequent action |
| 2026-07-19 | CodeGraph A/B comparison experiment (spec+plan+record three-piece set, `99adbde`+`f3f66c9`; data-decision commits `d1f0daa`/`4d77f57`): conclusion = route by file type (code files→CodeGraph, non-code docs `.md`/`.yaml`→Grep), not either/or; 5 reviewers unanimously backed the decision. The gate was merged into §12 Mandatory Split Gate and made language-agnostic (tree-sitter covers all supported languages, not just Python) |
| 2026-07-19 | Added §Operational Guidelines `### Token Efficiency Monitor (MANDATORY GATE)`; user hard constraint: every task must pass an independent Token Efficiency Monitor subagent (OPTIMAL / REFACTOR-NOW / ACCEPT-SUBOPTIMAL) before being declared done; strictly enforced from next task |

## 21. Self-Reflection Protocol (L4 #12)

> **Rule**: After every Phase (P0/P1/P2/P3) completes, the main Agent **MUST**
> run the Self-Reflection Protocol via `scripts/self_review.py`. Findings are
> **never** left in chat context — they go to `docs/superpowers/findings/F-NNN-*.md`
> so the next session can learn from them.

### 21.1 Why this exists

L3 closure + P0~P3.2 surfaced 23 findings (F-1 ~ F-23). Most lived only in
chat context — they vanish with the session. **CADL violation** (experience
must compound, not evaporate). §21 makes self-review a **protocol**, not a
one-off gesture.

### 21.2 The 4 finding fields (machine-checkable contract)

Every finding has frontmatter:

| Field | Allowed | Example |
|---|---|---|
| `id` | `F-NNN` (3-digit zero-pad) | `F-001` |
| `severity` | `P0` / `P1` / `P2` | `P0` |
| `status` | `open` / `fixed` / `accepted` | `fixed` |
| `phase` | the Phase that produced it | `l3-closure` |

### 21.3 Severity semantics

| Severity | Meaning | When to use |
|---|---|---|
| `P0` | Block release. Must have a passing test or fix commit before phase closes | Bugs that cause silent data loss (e.g. F-23 0-byte file), or false-positive safety blocks (F-3 substring matcher) |
| `P1` | Process / convention bug. No code fix possible; document the convention | F-1 multi-replace state desync — fix is "always reverse-verify" |
| `P2` | Improvement / hygiene. May stay open across phases | F-23 still open if no follow-up committed |

### 21.4 Protocol — when to run

| Trigger | Required action |
|---|---|
| End of P0 / P1 / P2 / P3 phase | `python3 scripts/self_review.py record ...` for each new finding |
| Before declaring phase "DONE" | `python3 scripts/self_review.py verify` must exit `0` (no stale P0) |
| Before merge to main | `python3 scripts/self_review.py report --phase <id> --out docs/superpowers/reports/<id>.md` |

### 21.5 CLI cheat-sheet

```bash
# Record a finding (auto-increment id, write .md file)
python3 scripts/self_review.py record \
    --severity P0 --title "..." --root-cause "..." \
    --fix "..." --lesson "..." --phase <phase-id>

# List all P0 (or any severity)
python3 scripts/self_review.py list --severity P0

# Verify — exit 0 iff no stale P0
python3 scripts/self_review.py verify

# Generate phase-level Markdown report
python3 scripts/self_review.py report --phase l4-closure \
    --out docs/superpowers/reports/l4-closure.md
```

### 21.6 Reverse-verification principle (the F-1 lesson)

Any time the Agent does multi-step file mutation (heredoc, sed, multi-replace),
**the protocol demands a reverse-verify step at the end**:

1. `git grep` for stale markers
2. `pytest` to confirm tests still pass
3. `ruff check` for new lint regressions

If any reverse-verify fails, the previous mutations are **untrusted** — re-run
them in a fresh `exec_command`. This is the F-1 lesson codified.

### 21.7 Worked example (F-3 record)

```bash
python3 scripts/self_review.py record \
    --severity P0 \
    --title "runtime_safety substring matcher" \
    --root-cause "substring match of terminate-instances also hits describe-instances" \
    --fix "switch to token-level regex \\b\\b in runtime_safety.detect_destructive()" \
    --lesson "destructive-op detection must use regex word boundary, never str.find()" \
    --phase l3-closure
# → writes docs/superpowers/findings/F-001-runtime-safety-substring-matcher.md
# → returns "F-001"
```

### 21.8 Cross-references

- §13 CADL — findings are CADL artifacts (experience must compound)
- §11 GCL — GCL `SAFETY_FAIL` and `MAX_ITER` MUST auto-record as P0 finding
  via `_reflexion.append_or_increment` integration (already wired in P1)
- §16 Eval-Driven Dev — golden scenarios that fail repeatedly must record a P2 finding

### 21.9 Final closure archive

The full L3 → L4 closure process is archived at
[`docs/superpowers/reports/l4-final.md`](docs/superpowers/reports/l4-final.md).
That document contains the complete timeline, phase-by-phase deliverables,
tooling stack, patch inventory, codified findings, and verification commands.
Future agents reproducing or auditing the L4 closure should start there.
