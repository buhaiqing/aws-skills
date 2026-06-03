---
name: aws-skill-generator
description: >-
  Use when the user wants to create a new AWS cloud operational skill, scaffold
  AWS service capabilities, or update an existing AWS skill after API changes
  — even without explicitly using words like "skill," "scaffold," or "generator."
  Generates complete skill structure from AWS documentation, CLI references,
  and boto3 SDK. NOT for executing live AWS operations.
license: MIT
compatibility: >-
  Access to AWS official documentation, AWS CLI docs, boto3 SDK references,
  aws-skill-generator/references/aws-skill-template.md, and agentskills.io
  frontmatter conventions.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: meta-skill
---

# AWS Skill Generator (Meta-Skill)

## What This Skill Does

This **meta-skill** scaffolds new AWS operational skills (`aws-[service]-ops`) for this repository. It does NOT execute live AWS operations—use the generated skills for that.

## When to Use

| Use This Skill | Do NOT Use |
|----------------|------------|
| Creating a new AWS service skill | Executing AWS operations directly |
| Aligning existing skill to template | Billing-only or IAM-only tasks |
| Updating skill after AWS API changes | Non-AWS cloud work |

## Generation Process Overview

```
Input → Analyze Sources → Create Layout → Populate Files → Verify
```

## Quick Start Checklist

### P0 — MUST Complete
- [ ] Product name + primary resource type identified
- [ ] Official AWS docs URL provided
- [ ] AWS CLI support verified (`aws [service] help`)
- [ ] SDK (boto3) module identified
- [ ] Trigger & Scope with SHOULD/SHOULD-NOT defined
- [ ] `{{env.*}}` placeholders (no secret literals)
- [ ] Execution flows: Pre-flight → Execute → Validate → Recover
- [ ] Safety gates for destructive operations
- [ ] Dual-path: AWS CLI (primary) + boto3 SDK (fallback)
- [ ] **[TE] Token Efficiency applied** — see §Key Principles below
- [ ] **[GCL] Destructive-op classification recorded** — see §Generator ↔ GCL Integration below. If any op matches a `required` row in `AGENTS.md` §11.5, the skill MUST ship `references/rubric.md` + `references/prompt-templates.md` + a `## Quality Gate (GCL)` section.

### P1 — SHOULD Complete
- [ ] Cross-service delegation documented
- [ ] Idempotency behavior documented
- [ ] Response JSON paths verified with real runs
- [ ] Troubleshooting error code table
- [ ] **[TE] core-concepts.md** — avoid static version/port/state tables; use API commands instead
- [ ] **[TE] boto3-sdk-usage.md** — omit docstrings; use inline comments
- [ ] **[TE] example-config.yaml** — use YAML anchors for shared fields

## Directory Layout

---

## Post-Generation Self-Check (生成后自检 — 宪章执行)

> **机制：生成完成后自动执行，不符合则循环修复直到通过。**
> **参考：** `references/governance-review.md` §0 Charter

### Charter Compliance Checklist (强制执行)

| # | Check | Pass Criteria | Auto-Fix |
|---|-------|--------------|----------|
| C1 | Frontmatter | Starts with `---`, has `name`, `description`, `license`, `compatibility`, `metadata` | Add from aws-skill-template.md |
| C2 | SHOULD/SHOULD NOT | Both trigger sections present | Add Trigger & Scope section |
| C3 | Trigger & Scope | Complete with product keywords | Add from template |
| C4 | Variable Convention | `{{env.AWS_*}}`, `{{user.*}}`, `{{output.*}}` | Add placeholder table |
| C5 | Safety Gates | Destructive ops have confirmation | Add pre-flight safety gate |
| **C6** | **Token Efficiency** | All 6 TE rules applied (see §Token Efficiency Requirements) | Report violations; fix per TE guidelines |

> **自解流程**：C1-C6 失败 → HALT → REPORT → REMEDIATE → RE-CHECK → LOOP

---

## Key Principles

| Principle | Enforcement |
|-----------|-------------|
| **CLI-first with SDK fallback** | Primary path: AWS CLI; fallback: boto3 after 3 CLI failures |
| **OpenAPI accuracy** | All fields traceable to AWS API docs |
| **Safety gates** | Human confirmation before destructive operations |
| **Credential isolation** | Only `{{env.*}}` placeholders; never real secrets |
| **TE: Token Efficiency** | See §Token Efficiency Requirements below |

## Token Efficiency Requirements (P0 — 强制)

> 目标：在保持 Agent 可执行性的前提下，最小化每份 skill 的 Token 消耗。

### TE-1: 用 API 查询替代硬编码静态数据
```markdown
# ❌ BAD: 硬编码引擎版本表（50+ 行）
## MySQL
- Versions: 5.7, 8.0
- Default Port: 3306
## PostgreSQL
- Versions: 12, 13, 14, 15, 16
...

# ✅ GOOD: 用 API 可查 + 精简表
## Supported Engines (Use API for latest)
aws rds describe-db-engine-versions --engine mysql
| Engine | Default Port | Storage Min |
|--------|-------------|-------------|
| MySQL | 3306 | 20 GB |
| PostgreSQL | 5432 | 20 GB |
```
**节约**: 每静态表 ~30 Token/行 × 10 行 = ~300 Token

### TE-2: boto3 SDK 省略 docstring
```python
# ❌ BAD: 每函数 8-15 行 docstring
def create_resource(...):
    """
    Create a new resource.
    Args:
        name: Resource name
        ...
    Returns:
        dict: Resource details
    """
    try: ...

# ✅ GOOD: inline comment 或者直接 code
def create_resource(name, ...):
    try: return client.create_resource(Name=name)['Resource']
    except ClientError as e: handle_error(e)
```
**节约**: ~120 Token/函数 × 10 函数 = ~1,200 Token

### TE-3: 错误表 → 紧凑格式
```markdown
# ❌ BAD: 每个错误 8-15 行
#### DBInstanceAlreadyExists
```
Error: DB instance exists
```
Cause: ...
Resolution: ...

# ✅ GOOD: 紧凑表格
| Error | Resolution |
|-------|-----------|
| AlreadyExists | HALT — use different identifier |
| NotFound | Verify identifier or region |
```
**节约**: ~400 Token/文件

### TE-4: JSON paths 集中声明（不重复） 
```markdown
# ❌ BAD: 每个命令后单独列出 JSON paths
## Create
JSON paths: .Resource.Id, .Resource.Status
## Describe
JSON paths: .Resources[0].Id, .Resources[0].Status

# ✅ GOOD: 文件顶部集中声明一次
# Common JSON Paths:
# Create: .Resource.{Id,Status}
# Describe: .Resources[0].{Id,Status}
```
**节约**: ~30 Token/文件

### TE-5: YAML anchors 消除重复字段
```yaml
# ❌ BAD: Dev/Prod/Test 各写 15 行重复字段
# ✅ GOOD: 共享 &dev / &prod 锚
x-dev: &dev
  multi_az: false
  deletion_protection: false
  storage_type: "gp3"

x-prod: &prod
  multi_az: true
  deletion_protection: true
```
**节约**: ~300 Token/文件

### TE-6: 消除跨文件重复流程
- SKILL.md 已有完整 Pre-flight → Execute → Validate → Recover
- `example-config.yaml` 中的 Complete Workflow Example 和 `boto3-sdk-usage.md` 中的 Complete Create Flow Example 是重复内容 → 删除
- 各函数 try/except pattern 在文件头部声明一次即可，不需每个函数重复

### TE Side Effects — 不可牺牲的内容
| 可压缩 | 不可压缩 |
|--------|---------|
| DocStrings、静态表格、重复流程 | Agent 可执行命令本身（参数、JSON paths） |
| 长篇描述、百科全书式概念 | 错误恢复逻辑、安全门、Credential 规则 |
| 多个示例变体（保留 1-2 个核心） | 跨技能编排链、AIOps 场景定义 |

## Reference Files (How to Details)

| Reference | Content |
|-----------|---------|
| [aws-skill-template.md](references/aws-skill-template.md) | Full skill template structure |
| [aws-cli-conventions.md](references/aws-cli-conventions.md) | CLI behavioral notes, output handling, retry strategy |
| [boto3-sdk-usage.md](references/boto3-sdk-usage.md) | boto3 patterns, error handling, polling |
| [integration.md](references/integration.md) | Environment setup (uv, credentials, multi-cloud) |
| [core-concepts-template.md](references/core-concepts-template.md) | Service architecture template |
| [troubleshooting-template.md](references/troubleshooting-template.md) | Error codes, diagnostics template |
| [governance-review.md](references/governance-review.md) | Pre-merge checklist, adversarial scenarios |
| [gcl-spec.md](references/gcl-spec.md) | **GCL** adversarial quality gate spec (5-dim rubric, AWS rules A1–A10, anti-patterns) |

## See Also

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)
## Generator ↔ GCL Integration

> **When to read this section:** before declaring a new skill "done", and
> before any change to a skill whose frontmatter carries a `gcl.enabled: true`
> block. Full spec: [`references/gcl-spec.md`](references/gcl-spec.md).
> Top-level index: `AGENTS.md` §11.

### Why this matters

The **Generator-Critic-Loop (GCL)** is the repository's adversarial
quality gate for high-side-effect AWS operations. The Generator skill
(this one) is the **only** place a new skill can opt in or out. If a
generated skill has a destructive op (`delete-*`, `terminate-*`,
`deregister-*`, `revoke-*`, `detach-*`, IAM / KMS / DDL) and is missing
GCL scaffolding, **the skill is incomplete** — a downstream agent will
execute that op without an independent critic.

### Destructive-op classification

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

### When a new skill MUST ship GCL scaffolding

If **any** op is `destructive` (or matches a `required` row in §11.5),
the generated skill MUST include all four of:

1. **`metadata.gcl` block in `SKILL.md` frontmatter** — see the template
   below.
2. **`## Quality Gate (GCL)` section in `SKILL.md`** — see existing
   pilots (`aws-ec2-ops`, `aws-iam-ops`, `aws-kms-ops`) for the exact
   layout.
3. **`references/rubric.md` (v1)** — 5-dimension rubric + per-op
   overrides + Safety special cases for that service's destructive
   patterns. Use the 3 existing pilots as templates; **copy the repo-wide
   AWS rules A1–A10 from `references/gcl-spec.md` §8 by reference**,
   don't duplicate.
4. **`references/prompt-templates.md` (v1)** — Generator / Critic /
   Orchestrator skeletons. Variable Convention MUST use `{{env.*}}` /
   `{{user.*}}` / `{{output.*}}` (never bare `{...}`).

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

### When a new skill does NOT need GCL

If every op is `read-only` or `create` (no destructive, no state-mutating
update), the skill:

- does NOT need `metadata.gcl`
- does NOT need `## Quality Gate (GCL)`
- does NOT need `rubric.md` / `prompt-templates.md`

The skill's `## Safety Gates` section still must call out the no-secret /
no-credential-logging rule (rule A9) and the `--region` rule (A7).

### How to write a service-specific rubric

1. **Start from the spec** — read `references/gcl-spec.md` §3 for the
   5-dimension template.
2. **List every destructive op** in the skill and write a per-op override
   row in the rubric's "Operation-specific overrides" table.
3. **List service-specific Safety auto-fail rules** — concrete patterns
   that this service's APIs can silently get wrong. Examples from existing
   pilots:
   - EC2: `DisableApiStop=true` blocks `stop-instances` silently
   - IAM: `*:*` policy widens to full admin
   - KMS: `--pending-window-in-days < 7` is below the AWS floor
4. **Reference the repo-wide AWS rules A1–A10 by ID** — do not paste the
   full text into the rubric. `gcl-spec.md` §8 is the canonical home.
5. **Pick a `max_iter` per the §11.5 table** — do not invent a new
   value.

### How to write service-specific prompt templates

1. **Start from any existing pilot** (`aws-ec2-ops/references/prompt-templates.md`
   is the canonical simple example; `aws-kms-ops` is the most
   secret-handling-heavy example).
2. **List every operation type** in the prompt's `operation type:` enum.
3. **For each destructive op, document the exact confirmation string**
   the user must type. EC2: `confirm=TERMINATE <id>`. IAM:
   `confirm=ATTACH_ADMIN <arn>`. KMS: literal `PERMANENTLY DELETE <id>`.
4. **For each op that has a pre-flight chain** (IAM `delete-user`,
   EC2 `terminate-instances` with EIP, etc.), spell out the exact step
   order in the prompt. The critic will refuse if the chain is
   incomplete.
5. **Critic prompt MUST hide the raw user request** — generator output
   only. This is `gcl-spec.md` §7 hard rule, not a suggestion.
6. **Variable Convention table** at the bottom — copy the structure
   from a pilot; do not invent new placeholder types.

### When a service is added to an existing skill (not a new skill)

If you are extending `aws-s3-ops` with a new op (e.g. adding
`delete-bucket-ownership-controls`), and the new op is destructive:

1. Update `references/rubric.md` — add a row to "Operation-specific
   overrides" and a Safety special case if needed
2. Update `references/prompt-templates.md` — add the new op to the
   `operation type:` enum
3. Update `## Quality Gate (GCL)` in `SKILL.md` — add the new op to
   the per-operation gating list
4. Update `references/aws-cli-usage.md` — the actual CLI command
5. **Do NOT bump `rubric_version` for minor additions** — bump to `v2`
   only when changing the 5-dimension weights or thresholds

### Verifying the rollout

After scaffolding is in place, confirm:

- `awk '/^---$/{c++; if(c==2){exit}} c==1' SKILL.md` returns the full
  frontmatter (single `---` open + single `---` close, no stray
  markers in body)
- `python3 -c "import yaml,re; yaml.safe_load(re.search(r'^---\n(.*?)\n---', open('SKILL.md').read(), re.DOTALL).group(1))"`
  parses cleanly with the `gcl:` block visible
- Every `aws-<x>-ops` referenced in SHOULD NOT / recovery tables / GCL
  rubric Safety special cases is a directory that actually exists in
  this repo
- `references/rubric.md` and `references/prompt-templates.md` exist
  and reference `references/gcl-spec.md` rather than duplicating it

### Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Added §Generator ↔ GCL Integration section; P0 checklist now requires GCL classification; Reference Files table now lists `gcl-spec.md` |
