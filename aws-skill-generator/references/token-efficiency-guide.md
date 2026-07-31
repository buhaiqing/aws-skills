# Token Efficiency Requirements (P0 — 强制)

> **硬性要求（Hard Gate）：** Token Efficiency 不是风格建议，而是 C6 MUST-PASS 门禁。
> 以下每条都附带**可 machine-verify 的检查**，generator 自检时必须执行，任一不过则 HALT。

## Objective pre-merge checks (generator 自检必跑)

客观硬指标由 `scripts/te_gate.py` 统一执行（machine-verifiable，与 Charter C6 / AGENTS.md §14 同源）：

```bash
# 对新生成 / 修改的 skill，必须全 PASS（strict 退出码 1 阻断 merge）
python3 scripts/te_gate.py <your-skill> --strict
#   → 检查 G1 (SKILL.md ≤120 行) / G3 (JSON paths 仅顶部声明一次) / G4 (无 GCL 模板正文重复)

# 对存量 aws-*-ops 扫描（仅报告，不阻断；渐进整改用）
python3 scripts/te_gate.py --all
```

> 静态表 (G2) / boto3 docstring (G5) / 错误表紧凑 (G6) 需人工 + LLM 双检，不在脚本 machine-check 范围（见 AGENTS.md §14）。
> `te_gate.py` 非 strict 模式只报告不卡死；CI / pre-merge hook 应加 `--strict` 使任一 gate FAIL 即退出码 1。

> 目标：在保持 Agent 可执行性的前提下，最小化每份 skill 的 Token 消耗。

## TE-1: 用 API 查询替代硬编码静态数据

```markdown
# ❌ BAD: 硬编码引擎版本表（50+ 行）
## MySQL
- Versions: 5.7, 8.0
...

# ✅ GOOD: 用 API 可查 + 精简表
aws rds describe-db-engine-versions --engine mysql
| Engine | Default Port | Storage Min |
|--------|-------------|-------------|
| MySQL | 3306 | 20 GB |
```

**节约**: 每静态表 ~30 Token/行 × 10 行 = ~300 Token

## TE-2: boto3 SDK 省略 docstring

```python
# ❌ BAD: 每函数 8-15 行 docstring
def create_resource(...):
    """Create a new resource..."""

# ✅ GOOD: inline comment 或者直接 code
def create_resource(name, ...):
    try: return client.create_resource(Name=name)['Resource']
    except ClientError as e: handle_error(e)
```

**节约**: ~120 Token/函数 × 10 函数 = ~1,200 Token

## TE-3: 错误表 → 紧凑格式

```markdown
# ❌ BAD: 每个错误 8-15 行
#### DBInstanceAlreadyExists
Cause: ...
Resolution: ...

# ✅ GOOD: 紧凑表格
| Error | Resolution |
|-------|-----------|
| AlreadyExists | HALT — use different identifier |
| NotFound | Verify identifier or region |
```

**节约**: ~400 Token/文件

## TE-4: JSON paths 集中声明（不重复）

```markdown
# ❌ BAD: 每个命令后单独列出 JSON paths
## Create
JSON paths: .Resource.Id, .Resource.Status

# ✅ GOOD: 文件顶部集中声明一次
# Common JSON Paths:
# Create: .Resource.{Id,Status}
# Describe: .Resources[0].{Id,Status}
```

**节约**: ~30 Token/文件

## TE-5: YAML anchors 消除重复字段

```yaml
x-dev: &dev
  multi_az: false
  deletion_protection: false
x-prod: &prod
  multi_az: true
  deletion_protection: true
```

**节约**: ~300 Token/文件

## TE-6: 消除跨文件重复流程

- SKILL.md 已有完整 Pre-flight → Execute → Validate → Recover
- `example-config.yaml` 中的 Complete Workflow Example 和 `boto3-sdk-usage.md` 中的 Complete Create Flow Example 是重复内容 → 删除
- 各函数 try/except pattern 在文件头部声明一次即可，不需每个函数重复

## TE Side Effects — 不可牺牲的内容

| 可压缩 | 不可压缩 |
|--------|---------|
| DocStrings、静态表格、重复流程 | Agent 可执行命令本身（参数、JSON paths） |
| 长篇描述、百科全书式概念 | 错误恢复逻辑、安全门、Credential 规则 |
| 多个示例变体（保留 1-2 个核心） | 跨技能编排链、AIOps 场景定义 |
