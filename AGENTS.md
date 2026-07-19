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
- A natural "next task" prompt when the user says "继续"

After completing each task, immediately mark it `completed` and check
`TaskList` for the next item. Do not batch completions.

### Fan-out Subagents (as much as feasible) — 强制

**本规则为硬约束，后续每一个动作严格执行。** 任何可并行、可独立交付的子任务，
**必须尽可能 fan-out 给子 Agent（subagent）并发执行**，主 Agent 只做编排与汇总，
不替代子 Agent 把活儿自己干完。

判定与执行准则：

- **可 fan-out 的信号**：任务能被拆成 ≥2 个互相独立、无共享可变状态的子任务
  （如：多个 skill 的同类修改、多个独立的查询/校验、多个文件的同类评审）。
- **优先并发**：凡独立的子任务，在**同一条消息**里发多个 Agent 调用，让它们并行跑；
  不要串行化本可并行的活儿。
- **主 Agent 职责**：拆任务 → 写自包含 prompt（含文件路径/行号/验收标准）→ 汇总结果 → 对用户负责。
  **不要**把"理解"委托给子 Agent——你先读懂，再下精确的 spec。
- **写-heavy 串行**：写同一批文件的实现任务一次只跑一个（避免 merge 冲突），
  但不同文件区域、不同技能可并行；只读研究类任务可自由并行。
- **子 Agent 失败**：先 `SendMessage` 续跑并带错误上下文；纠正仍失败则换思路或上报用户，
  不要无限空转。
- **不可 fan-out 的情形**（例外）：单点依赖链（B 必须等 A 的产物）、
  <5 行的纯 typo/注释改动、需主 Agent 直接接管的安全/破坏性操作。

> 来源：2026-07-19 session 用户硬约束「fan out subagents as much as feasible，
> 后续严格贯彻到每一个动作」。本规则与 §12 分流门禁、§13 CADL 沉淀闭环协同：
> fan-out 完成后，每个子任务仍须走对应的 Grep/CodeGraph 分流与资产沉淀。

### Token Efficiency Monitor（强制门禁 — 每个 task 必经）

**本规则为硬约束，后续每一个动作严格执行。** 任何实质 task（含子 Agent 交付）完成后，
**必须**经过一个独立的 **Token Efficiency Monitor** 子 Agent 评审，确认本次产出的
token 效率是否已达最优；未达最优则**直接由该 Monitor 重构（refactor）至最优**，
或（若重构代价 > 收益）明确判定「已达当前最优、无需再优」方可收尾。

判定与执行准则：

- **触发**：每个 task 完成（或子 Agent 回报完成）即触发，**先于**对用户宣告「完成」。
- **Monitor 职责**：从 token 效率视角审计本次产出，重点看：
  1. **冗余**：是否有重复内容（多文件同段、AI 回复里的重复解释、可 dedupe 的模板）？
  2. **可压缩**：长输出/长 prompt 能否用更短等效表达？是否夹带与任务无关的背景？
  3. **可读性代价**：压缩是否牺牲了可维护性（README/AGENTS 这类长期资产不可为省 token 牺牲清晰度）？
  4. **fan-out 是否充分**：本可并行的子任务是否被串行化了（反 Fan-out 规则）？
- **处置三选一**（Monitor 必须明确选一个并说明）：
  - **`OPTIMAL`** — 已达最优，放行（附 ≤2 句理由）。
  - **`REFACTOR-NOW`** — 直接重构至最优（Monitor 自行改文件 + 提交，或发精确 spec 给原执行者改）。
  - **`ACCEPT-SUBOPTIMAL`** — 重构代价 > 收益（如长期资产不宜过度压缩），记录理由后放行。
- **不可绕过**：主 Agent 不得在未经 Monitor 同意前宣称 task 完成；Monitor 的
  `OPTIMAL` / `ACCEPT-SUBOPTIMAL` 是收尾前置条件。
- **与 CADL 协同**：Monitor 发现的"可复用压缩模式"须按 §13 落点（通用模式→AGENTS.md，
  踩坑→failure-patterns.md），形成 token 效率复利。
- **长期资产豁免**：AGENTS.md / README / SKILL.md 等面向人/多 agent 的长期文档，
  token 效率让位于清晰与可检索性——Monitor 对此类文件默认 `ACCEPT-SUBOPTIMAL` 或轻量 `REFACTOR-NOW`。

> 来源：2026-07-19 session 用户硬约束「所有 task 都要经过 token efficiency 监控
> subagent 同意，看它能不能优化到最优，没有的话就安排它完成」。自下一个 task 起
> 强制纳入执行流：主 Agent 在 task 收尾前 spawn Monitor，按其三选一处置，严格参照执行。

### GCL Skip Threshold

GCL (Generator-Critic-Loop) is required for >5 line code changes,
but can be skipped for:
- Single-line constant additions (e.g., adding a metric to a dict)
- Import list updates (e.g., expanding `__init__.py` exports)
- Documentation-only changes (adding notes, clarifying existing text)

The判断标准: if the change is purely additive (no logic changes,
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

### Composite / Copilot Skills (L2)

Base skills (`aws-<svc>-ops`, L1) are single-service runbooks. Composite
skills (L2, `metadata.type: composite`) **orchestrate only** — they declare
`delegate:` to L1 skills and contain no service-level operation logic.

Contract (enforced by aws-skill-generator Charter C7):
- `metadata.type`: `base` | `composite` (既有等价值 `orchestrator-meta` 亦视为 composite)
- `metadata.provides`: operations this skill handles
- `metadata.delegate`: composite→base skill/operation map (dirs must exist)

Runtime-agnostic: any agent globs `aws-*-ops/SKILL.md` and reads frontmatter
— no per-agent loader (see §12 CodeGraph for cross-agent MCP discovery).

## Self-reflection rule (project policy)

> **Rule**: After every skill update, auto-run **2 rounds** of self-review
> and fix all discovered issues. Do not hand back to the user between rounds.
>
> Full spec (check tables, verification scripts, dedup procedures,
> implementation notes) at
> [`docs/post-update-self-review.md`](docs/post-update-self-review.md)

| Round | Scope | Key Checks |
|-------|-------|-----------|
| **R1: Structural** | Frontmatter / Trigger / Variables / Token Efficiency | C1–C6, TE-1…TE-6, **C6 MUST PASS** |
| **R2: Content** | CLI validation / error codes / safety gates / link integrity / dedup / TODO.md sync | F1–F8, **F5/F6/F8 MUST PASS** |

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

After round 2 passes cleanly, report a one-line summary per modified
skill: `[OK] aws-<service>-ops v<version> — 2 rounds clean`.

If round 2 still finds issues, run additional rounds until clean. Do
**not** stop after 2 rounds if problems remain.

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

> 完整 37 行 Per-Skill Defaults 表（含每 skill 的 GCL 分级、`max_iter`、破坏性操作清单）外移至 [`docs/gcl-per-skill-defaults.md`](docs/gcl-per-skill-defaults.md)。

要点：所有 `required` / `recommended` skill 均已 rollout 完整 GCL 实现；`optional` 与 read-only 类（cloudtrail / topo-discovery / aiops-cruise）按降级策略处理。每 skill 可在自身 `SKILL.md` 的 `## Quality Gate (GCL)` 下覆盖 `max_iter`。未列出的 skill 默认 GCL **disabled**。

### 11.6 Trace & audit (mandatory)

Every GCL run persists a JSON trace to
`./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` per the schema in spec §6.
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

## 12. CodeGraph Integration（代码知识图谱集成）

本地优先的代码知识图谱工具（[colbymchenry/codegraph](https://github.com/colbymchenry/codegraph)，已装 `/Users/bohaiqing/.local/bin/codegraph`，Node v22.19.0）。用 tree-sitter 建本地 SQLite 图谱（`.codegraph/codegraph.db`），通过 MCP（工具 `codegraph_explore` / `codegraph_node`）集成。**设计目标：跨 coding agent 通用**——同一份 `codegraph serve --mcp` 定义，自动投影到 OpenCode / Cursor / Claude Code / Codex / Hermes Agent / Kiro / CodeBuddy 等各自的原生配置，无需 per-agent 适配。100% 本地、无数据外泄。

### 目的

编辑技能 `SKILL.md` / `references/` 或共享脚本（`scripts/gcl_runner.py`、`_shared.py` 等）前，用 CodeGraph 校验**跨技能引用一致性**与**变更影响半径**，补强 §Operational Guidelines 的"跨文件引用三方同步"规则。

本仓库 34 个 `aws-<svc>-ops` 技能委托引用频繁（如 `aws-rds-ops`→`aws-aurora-ops`、`aws-elb-ops`↔`aws-vpc-ops`），改一处可能影响多处。`codegraph explore "aws-aurora-ops"` 实测返回 36 符号跨 3 文件 + blast radius（`run_aws` 有 61 调用者跨 15+ 文件）。

### 命令

```bash
codegraph init .              # 首次建图（实测 564 nodes / 1,329 edges）
codegraph sync .              # 增量同步自上次索引以来的变更（每次代码变更前必跑）
codegraph explore "<symbol>"  # 查影响半径 / 跨文件调用点
codegraph status              # 查索引状态（Files/Nodes/Edges/DB Size）
```

### MCP 集成（跨 agent 通用，一次到位）

**单一技术**：`codegraph serve --mcp`（stdio）。同一份 server 定义，通过
`codegraph install -t all` 自动投影到各 agent 的原生配置文件
（OpenCode / Cursor / Claude Code / Codex / Hermes / Kiro / CodeBuddy 等），
各 agent 读自己的配置即可，**无需 per-agent 适配代码**：

```bash
codegraph install -t all      # 投影 codegraph MCP 到所有已装 agent 的全局配置
# 或指定： codegraph install -t opencode,cursor,claude,codex,hermes,codebuddy
```

- **仓库级自动发现**：本仓库根已放 `.mcp.json`（声明 `mcpServers.codegraph`），
  支持项目级 MCP 的 agent（Cursor / Claude Code / CodeBuddy 开 project-MCP）打开
  本目录即自动感知并加载，无需手动 install。
- **CLI 等价命令**（`codegraph explore` / `codegraph node` / `codegraph sync`）
  始终可用，无 MCP 也可用——AGENTS.md §12 的"改前 sync + 跨技能校验"不依赖 MCP。
- 安装后**重启对应 agent session** 生效；卸载用 `codegraph uninstall -t all`。

### 规则

| 项 | 要求 |
|----|------|
| **每次代码文件变更前**（`.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` 等 tree-sitter 支持的语言，非 `.md`/`.yaml` 文档） | **必跑 `codegraph sync .`**（增量同步），确保后续 `explore` / `impact` 基于最新索引；索引不存在时先 `codegraph init .` |
| `.codegraph/` | 内容已被其自带 `.gitignore`（`*` + `!.gitignore`）屏蔽，禁止提交索引；根 `.gitignore` 可补 `.codegraph/`（可选，为 `git status` 静默） |
| 改共享脚本 / 委派引用前 | 先 `codegraph sync .` 再 `codegraph explore "<symbol>"` 确认调用点与文档描述一致 |
| GCL 任务 R2 内容评审 | 用 CodeGraph 辅助校验跨技能委托引用存在性（如 `SHOULD` / `SHOULD NOT` 指向的目录真实存在） |
| 与 self-review 关系 | 不替代 2-round self-review，仅作跨技能引用的机器校验增强 |

### 适用边界（分场景 — 来自 2026-07-19 session 复盘）

> **关键事实（已实测）：** CodeGraph 用 tree-sitter 建**代码**符号图谱，**不索引 Markdown frontmatter**。本仓库技能 corpus 以 Markdown 主导（实测 `aws-*` 目录内 `.md` ≈ 72% / `.py` ≈ 9%），其 `metadata:` / `delegate:` / 委托目录引用**对 CodeGraph 不可见**。
> 因此必须**按文件类型（代码 vs 非代码文档）分流**，而非按具体语言——CodeGraph 经 tree-sitter 覆盖所有受支持语言，不限于 Python；否则会"该用时没用、用了也查不到"：

| 改动类型 | 正确工具 | 是否走 CodeGraph |
|----------|----------|------------------|
| **代码文件**（任意 tree-sitter 支持的语言：`.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` 等，含 `_inference.py` / `_shared.py` / `gcl_runner.py` / `collectors` / `daily-health-check.py`） | `codegraph sync .` + `codegraph explore "<symbol>"` 查 blast radius | ✅ **必走** — CodeGraph 用 tree-sitter 建代码符号图，覆盖所有受支持语言，不限于 Python |
| **Markdown 技能**（`SKILL.md` / `references/*.md` / `AGENTS.md` 的 frontmatter、委托表、路由表） | `git grep` / Grep 工具（按目录存在性、字符串引用校验） | ❌ **不必走** — CodeGraph 不索引 `.md`，强行走会返回 "No relevant code" |

> **改进闭环（dogfood）：** 本 session 曾全程用 Grep 替代 CodeGraph（违反 §12），但根因是**工具错配**——Markdown 主导需求本就不该走 CodeGraph。修正做法：
> 1. 改 Python 脚本前，**先 `codegraph sync .` 再 `explore`** 复核影响半径（如改 `_inference.py` 前确认 `apply_chain_inference` 的 16 caller 不受影响）；
> 2. 改 Markdown 技能用 Grep/`git grep`，不强行 CodeGraph；
> 3. 若要让 CodeGraph 覆盖技能 corpus，需给它加 Markdown frontmatter 提取器（**超出本 §12 scope**，独立 plan）。

### 强制分流门禁（data-driven，必须严格执行 — 2026-07-19 对比实验结论）

> **决策依据（实测，非 vibe）：** 本 session 对两类查询做了 A/B 实测（Grep=B 当前方式，CodeGraph CLI=候选方式），结果：
>
> | 实验 | 查询类型 | Grep 结果 | CodeGraph 结果 | 优胜 |
> |------|----------|-----------|------------------|------|
> | E1 | Markdown 委托引用（谁引用 aurora-ops） | **4/4 recall，0 漏报**，0.03s | 返回"36 个代码符号"，对实际 Markdown 委托问题 **0/4** | **Grep** |
> | E2 | 代码符号影响半径（make_incident） | 59 唯一直调用点，原始、无测试标注 | 42 去重调用者 + `⚠️ no-test` 标注 | **CodeGraph** |
> | E3-Q1/3/5 | 非代码文档图（Markdown 技能） | 正确*（需正则写对）*；Q5 因**本人 glob 写错**漏报（真值=2：`aws-elb-ops/assets/example-config.yaml` + `aws-aiops-orchestrator/SKILL.md`，Grep 返回 0） | 对 `.md` **结构性失明** | **Grep**（查询正确时） |
> | E3-Q2/4 | 代码符号调用图（Python 等 tree-sitter 语言） | 71 原始行，需手动去重 | 61/34 调用者 + 测试标注，即时 | **CodeGraph** |
>
> **结论：** 单一工具强制（"全用 CodeGraph" 或 "全用 Grep"）会让本仓库**一半查询质量下降**。正确策略是**按文件类型强制分流**——这也是 §12「适用边界」小节被本实验**数据验证成立**的结论。

| 查询/改动类型 | **强制**工具 | 禁用 | 理由（实测） |
|---------------|------------|------|----------------|
| **非代码文档**（`.md` 的 frontmatter/委托表/路由表、`references/*.md`、`AGENTS.md`、`*.yaml` 配置文档） | **Grep / `git grep`** | ❌ 不得走 CodeGraph | CodeGraph 不索引非代码文档，E1 实测 0/4 |
| **代码文件**（任意 tree-sitter 语言：`.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` 等）的影响半径 / 调用点 | **`codegraph sync .` + `codegraph explore`** | ❌ 不得仅用 Grep 了事 | E2 实测 CodeGraph 多给去重 + 测试覆盖标注；tree-sitter 覆盖所有受支持语言，不限于 Python |
| **任何查询** | 查询必须**正确构造**（glob/正则/参数须匹配仓库实际布局） | ❌ 不得用错误 glob/正则/参数蒙混 | E3-Q5：本人 glob `aws-*-ops` 漏匹配 `aws-aiops-orchestrator`（无 `-ops` 后缀）致漏报，真值=2 而非 0/1——烂查询=静默错答，与工具无关 |

> **最终评断（2026-07-19 对比实验结论，5 位评审 unanimous）：**
> 单一工具强制（"全用 CodeGraph" 或 "全用 Grep"）会让本仓库**约一半查询质量下降**。CodeGraph（tree-sitter 代码符号图）与 Grep 是**互补**而非替代关系——前者对**所有受支持语言的代码文件**生效，后者对**非代码文档**（`.md`/`.yaml` frontmatter）生效。
> **胜出方案 = 按文件类型强制分流**（非按语言、非二选一）：
> - 🟢 代码文件（任意 tree-sitter 语言）→ `codegraph sync .` + `explore`
> - 🟢 非代码文档（`.md`/`.yaml`）→ Grep / `git grep`
> - 🟢 任何查询 → 先核对 glob/正则是否匹配仓库实际目录布局
>
> **执行纪律（用户硬约束）：** 一旦本分流决策确定，**后续每一个动作严格贯彻**——凡非代码文档类查询一律 Grep、凡代码类影响半径一律 CodeGraph，不得凭习惯回退到单一工具。违反即视为质量回归。本门禁与 §13 CADL、§Operational Guidelines「Fan-out Subagents」协同：每个子任务仍须走对应分流 + 资产沉淀。

> **资产落地（CADL 正确落点）：** 本实验最可迁移的踩坑教训——"**错误查询（烂 glob/正则）比错误工具更隐蔽，会静默错答**"（E3-Q5）——须另写入 `docs/failure-patterns.md`（踩坑类资产归 failure-patterns，而非 AGENTS.md），供任何未来 agent 检索复用。

## 13. 复利资产沉淀机制（Compound-Asset Distillation Loop, CADL）

**工作闭环，非单条规范**：任何实质任务完成后，Agent 必须走完「提取 → 落点判定 → 写入 → 门禁」才能结束——任务不做沉淀 = 任务未完成。让每次踩坑、评审、跨技能协作都变成下一次的可复用资产，形成复利。

> CADL 闭环机制，适配本仓库术语：`{{env.*}}`/`{{user.*}}`/`{{output.*}}` 占位符、Reflexion Memory（`docs/failure-patterns.md`）、CodeGraph（§12）、AGENTS.md 行数门禁（≤500 行）。

### 触发条件（满足任一即走 CADL）

- 多步 / 跨文件任务完成
- 跨 Skill 协作（delegation matrix 或并行 agent / oracle / explore）
- 评审 / 修复循环（GCL、2-round self-review、Oracle 咨询）
- 发现 repo 缺陷 / 坑（即使不在本次 scope）
- 验证中发现预存 FAIL 并归因
- 用户给出可复用的工作流偏好（如"双写子命令绕过 CLI bug"）

### 闭环步骤

```
1. 提取   → 抽象可复用模式（踩坑避免/评审维度/协作模式/验证命令/helper）
             格式："问题 → 反模式 → 正确做法（含代码示例）"
2. 落点判定 → 离开本仓库？→ ~/.config/opencode/AGENTS.md
             仅本仓库？→ 本项目 AGENTS.md
             失败模式/坑？→ docs/failure-patterns.md
             某 skill 专属能力？→ 独立 Skill（经 aws-skill-generator）
3. 写入   → 可执行+有示例+有边界；先 grep 目标文件确认未覆盖
4. 门禁   → 写入前 wc -l，本文件 ≥500 行先精简再写（注：当前已 ~675 行，溢出源为 §11 GCL 既有体量 + §12/§13 扩展；下次优化可外移 §11 长表）
5. 复用   → 下次同类任务读目标文件即获得该资产 → 复利生效
```

### Skill 侧钩子（让每个 Skill 自带沉淀意识）

- **源头**：`aws-skill-generator` 在生成每个 skill 时，须在 SKILL.md 末尾注入一行：
  `> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。`
  未来所有 `aws-<svc>-ops` 自动继承此意识。
- **现存 skill**：逐批在 SKILL.md 末尾补同一行提示，使大模型调用任何 skill 后都看到触发信号。（存量 34 个 `aws-*-ops` 的钩子注入为渐进式，不在本次 CADL 迁移 scope，后续按需补入。）

### 反模式（违反 CADL）

| 反模式 | 正确做法 |
|---|---|
| 任务做完就结束，不沉淀 | 走完 CADL 闭环再交付 |
| 把一次性上下文当资产写进 AGENTS.md | 只沉淀跨任务可复用的模式 |
| 重复已有条目 | 写入前 grep 确认未覆盖 |
| 只在 CodeGraph 相关任务才沉淀 | 评审/修复/协作/验证都触发 |
| 踩坑类资产写进 AGENTS.md 而非 failure-patterns.md | 踩坑/失败模式归 `docs/failure-patterns.md`，通用模式归 AGENTS.md |

### 复利资产示例：声明式契约优先（来自 `skill-as-infrastructure` 落地）

> 复用模式（跨任务 / 跨企业 LLM 生态通用）：
> **问题** → agent 技能体系需让复合/copilot 技能被机器识别、可组合。
> **反模式** → 引入私有 registry / 专属 loader（耦合到具体 agent 运行时）。
> **正确做法** → 在既有 frontmatter 中加**最小声明式契约**字段
> (`metadata.type` / `provides` / `delegate`)，用**现有**自检框架
> (Charter C7) 强制校验，任何 agent 只需 `glob aws-*-ops/SKILL.md`
> 读 frontmatter 即可组合——零私有加载器、运行时无关。
> 通用化：凡"让 X 被机器识别/可组合"的需求，优先加声明式字段 +
> 复用既有 gate，而非造私有基础设施。

### 复利资产示例：契约演进须 grandfather 存量（来自 C7 复盘）

> 复用模式（跨任务 / 跨企业 LLM 生态通用）：
> **问题** → 新加契约（如 `metadata.type: composite`）时，存量 skill
> 已用不同取值（如 `orchestrator-meta`）会被新 gate 误判 orphan / HALT。
> **反模式** → 改契约后忽略存量，或强改存量 frontmatter 去对齐（扩 scope、引入回归）。
> **正确做法** → 契约的允许值集合**显式纳入存量等价值**
> （`composite` ≡ `orchestrator-meta`），在模板注释 / Charter / AGENTS.md 三处同步，
> 不触碰存量 skill 本身。新增契约前先 `grep` 全盘，确认无遗漏的既有取值。

## 14. Token Efficiency 硬性要求与去重规范（TE Hard Gate）

> 仓库级硬性要求，约束 `aws-skill-generator` 生成输出**以及任何手动编辑 skill 的人**。
> 与 `aws-skill-generator/SKILL.md` §Token Efficiency Requirements（C6 MUST-PASS）同源。完整门槛 / 去重先例 / 存量整改策略见 [`docs/te-hard-gate.md`](docs/te-hard-gate.md)。

**核心门槛（C6 硬指标，任一不过不得 merge）：**
- **G1** `SKILL.md` ≤ 120 行；**G2** 无 >5 行硬编码静态表（用 API 替代，TE-1）；**G3** JSON paths 仅顶部声明一次（TE-4）；**G4** 无跨文件重复流程 / boilerplate（TE-6）；**G5** boto3 无 docstring（TE-2）；**G6** 错误表紧凑（TE-3）。
- **去重原则**：内容出现在 ≥2 个 skill 必须抽到单一真相源（先例：`_sync_prompt_skeletons.py` 将 31 skill 的 ~5,800 行 GCL boilerplate 抽到 231 行骨架 + 薄 delta）。
- **存量渐进整改**：新/改 skill 必须达标；34 个存量 `aws-*-ops` 超长者（ec2/cloudwatch/cloudtrail/dynamodb/config/ram/acm/waf）按需顺带压回 ≤120 行。

### 复利资产示例：纪律须 dogfood 自身（来自 finsecops-optimization 复盘）

> 复用模式（跨任务 / 跨企业 LLM 生态通用）：
> **问题** → 仓库纪律（如"implement 前先写 spec+plan"）容易被后续改动悄悄违反，且无自检锚点。
> **反模式** → 纪律只写在 AGENTS.md，落地 commit 不引用对应 spec/plan。
> **正确做法** → 纪律的**推行 commit 自身**须携带引用该纪律的 spec+plan
> （先例：`33f18ba` 加 `Spec + Plan Before Implement` 规范时，同时落盘
> `2026-07-19-finsecops-optimization-design.md` + 对应 plan）。让纪律"自己遵守自己"，
> 任何 agent 回溯 commit 即可验证纪律被 dogfooded，而非仅声明。

## Changelog

| Date | Change |
|------|--------|
| 2026-07-04 | Added §Operational Guidelines: Task Tracking, GCL Skip Threshold, Pre-existing Lint Baseline |
| 2026-07-11 | Added §12 CodeGraph Integration: local code knowledge graph (colbymchenry/codegraph) for cross-skill reference consistency + blast-radius checks; `codegraph init .` indexed 564 nodes / 1,329 edges |
| 2026-07-18 | Added §13 复利资产沉淀机制 (CADL); wires 提取→落点判定→写入→门禁 loop into every substantial task; generator injects CADL hook line into new skills' SKILL.md |
| 2026-07-19 | Added §Operational Guidelines `### Fan-out Subagents (as much as feasible) — 强制`; user hard constraint: fan out independent subtasks to parallel subagents, main Agent only orchestrates+synthesizes, strictly enforced in every subsequent action |
| 2026-07-19 | CodeGraph A/B 对比实验（spec+plan+record 三件套，`99adbde`+`f3f66c9`；数据决策 commit `d1f0daa`/`4d77f57`）：结论=按文件类型强制分流（代码文件→CodeGraph，非代码文档 `.md`/`.yaml`→Grep），非二选一；5 位评审 unanimous 支持决策。门禁已合并入 §12 强制分流门禁，并改为语言无关（tree-sitter 覆盖所有受支持语言，不限于 Python） |
| 2026-07-19 | Added §Operational Guidelines `### Token Efficiency Monitor（强制门禁）`; user hard constraint: every task must pass an independent Token Efficiency Monitor subagent (OPTIMAL / REFACTOR-NOW / ACCEPT-SUBOPTIMAL) before being declared done; strictly enforced from next task |
