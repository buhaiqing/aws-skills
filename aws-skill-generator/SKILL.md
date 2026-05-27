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

## See Also

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Agent Skills OpenSpec](https://agentskills.io/specification)