# Self-Reflection Protocol — Design (L4 #12, final)

- **Date**: 2026-07-25
- **Status**: 定稿 (待实施)
- **Priority**: P3.4 (Self-Reflection 闭环, L4 自进化维度最后一里)
- **Source signal**: 用户原始诉求 "复盘王东提出的优化改进建议" → 把 self-review
  流程从"一次性动作"升级为"可复用协议", 防止 F-1~F-23 重犯.
- **关联**: `docs/agentic-maturity-model.md` §6.4 (Gap → ✅ In-progress)

## 1. 背景

L3 闭环 + P0~P3.2 改造期间, 主 Agent 跑了多轮 self-review (R1 Structural /
R2 Content / R3 Cross-cutting), 发现 **23 个 finding**:

- **F-1**: critical-state-desync bug — 多 assert-then-replace 串, Python 无
  partial execution, assert 失败时前面所有 replace 都未生效 (process bug, 不能
  code-fix, 只能 convention-fix).
- **F-2**: pre-commit awk markdown-link 解析错误 → 抽 `scripts/_frontmatter.py`
  (109 行 + 8 测试, 已在 P0 修复).
- **F-3**: `runtime_safety.py` 的 destructive-op 检测用 substring 匹配
  (`aws<svc><op>` 拼接), 会误命中 (e.g. "describe-instances" 中包含
  "terminate-instances" 字符串) → 改为 token-level regex matcher
  (P0 修复 + 4 测试).
- **F-4** ~ **F-22**: 在不同阶段发现, 但**没有结构化记录**, 下次同类问题
  重犯风险高.
- **F-23**: `_reflexion.append_or_increment` 当目标文件存在但为空 (e.g.
  0-byte) 时静默数据丢失 → 抽 `_FRESH_HEADER` 常量 + `_needs_fresh_init()`
  helper, P0 修复 + 9 测试.

**核心痛点**: 23 个 finding 大部分**只留在对话上下文**, 没有落到磁盘. 一旦
session 结束, 经验就消失. 这违反 CADL 精神 (经验必须沉淀).

P3.4 把 self-review **从"一次性动作"升级为"协议"**:

1. **结构化 finding 库** (`docs/superpowers/findings/F-NNN-*.md`) — 每个
   finding 一个文件, 包含 root_cause / fix / lesson / status, **机器可读 +
   人类可读**.
2. **Self-review orchestrator** (`scripts/self_review.py`) — 提供 CLI:
   - `record` — 把新 finding 落盘 (auto-increment id)
   - `list` — 按严重度查 finding
   - `verify` — 反向验证 stale finding 是否清零 (per AGENTS.md §11.7
     "末尾 grep 反向验证" 约定)
   - `report` — 生成当前 phase 的 self-review Markdown 报告
3. **触发契约** — 任何 P0/P1/P2/P3 phase 完成**必须**触发, 否则算 phase
   未闭环.

## 2. 目标

`scripts/self_review.py`:
1. **库** `record_finding(repo, severity, title, root_cause, fix, lesson)` —
   返回 finding id (`F-NNN` 格式, 3 位 zero-padded).
2. **库** `list_findings(repo, severity=None)` — 列出 finding, 可按 severity
   过滤.
3. **库** `verify_findings(repo)` — 反向验证: P0 finding 必须有对应的测试
   或修复 commit, 否则返回 `stale_p0`.
4. **库** `generate_report(repo, phase_id)` — 输出 phase-level Markdown.
5. **CLI** `record / list / verify / report` 子命令.

## 3. 契约

```python
@dataclass(frozen=True)
class Finding:
    id: str                    # "F-001" ... "F-999"
    severity: str              # "P0" | "P1" | "P2"
    title: str                 # ≤80 chars
    root_cause: str            # why it happened
    fix: str                   # what was done
    lesson: str                # what to do differently next time
    status: str                # "open" | "fixed" | "accepted"
    added_date: str            # ISO date (YYYY-MM-DD)
    closed_date: str | None    # ISO date when status -> fixed/accepted

    def to_markdown(self) -> str: ...


@dataclass(frozen=True)
class VerifyReport:
    open_count: int
    fixed_count: int
    accepted_count: int
    stale_p0: list[Finding]    # P0 findings still open


def record_finding(
    repo: Path,
    severity: str,
    title: str,
    root_cause: str,
    fix: str,
    lesson: str,
) -> str: ...

def list_findings(repo: Path, severity: str | None = None) -> list[Finding]: ...

def verify_findings(repo: Path) -> VerifyReport: ...

def generate_report(repo: Path, phase_id: str) -> str: ...

KNOBS = {
    "findings_dir": "docs/superpowers/findings",
    "max_id": 999,
    "valid_severities": ("P0", "P1", "P2"),
    "valid_statuses": ("open", "fixed", "accepted"),
}
```

## 4. Finding 文件格式 (one Markdown file per finding)

`docs/superpowers/findings/F-001-multi-replace-state-desync.md`:

```markdown
---
id: F-001
severity: P1
title: multi-replace state desync
status: accepted
added: 2026-07-25
closed: 2026-07-25
phase: l3-closure
---

## Root cause

Python 没有 partial execution. 当 `python3 << EOF` 脚本中
先做 assert 检查, 再做 file replace, assert 失败时前面所有
replace 都没生效, 但 session 上下文可能仍认为它们生效了.

## Fix

无 code fix (process bug). Convention fix:
1. 每个 update 跑独立 `exec_command` session
2. 末尾 grep 反向验证 stale marker 是否清零

## Lesson

任何批量 update 必须**反向验证** (grep / read-back), 不能信 assert.
```

Frontmatter 是 single `---` block, 与 SKILL.md 同结构 (consistent with
`_frontmatter.py` parser).

## 5. CLI

```bash
# 记录新 finding (auto-increment id)
python3 scripts/self_review.py record \
    --severity P0 \
    --title "runtime_safety token-level matcher regression" \
    --root-cause "substring 匹配把 describe-instances 误命中为 terminate" \
    --fix "改为 token-level regex `^aws <svc> terminate-instances$`" \
    --lesson "任何 destructive-op 检测必须用 token boundary, 不能用 substr"

# 按 severity 列 finding
python3 scripts/self_review.py list --severity P0

# 反向验证: P0 是否都 fixed?
python3 scripts/self_review.py verify

# 生成 phase-level report
python3 scripts/self_review.py report --phase l4-closure --out docs/superpowers/reports/l4-closure.md
```

## 6. 验收

1. `from self_review import Finding, record_finding` 可导入
2. RED → GREEN: **≥6 effective tests** (record × 2, list × 1, verify × 2,
   report × 1, edge × 1) — **测试有效性优先于覆盖率**
3. ruff 0 issue
4. 真跑: `record` 4 个 finding (F-1 / F-2 / F-3 / F-23) → 4 个 .md 文件
   落盘, 每个含正确 frontmatter
5. `verify` 在 P0 已修复情况下应返回 `stale_p0 == []`
6. `report --phase l4-closure` 输出 Markdown 含 4 finding + counts
7. AGENTS.md §21 "Self-Reflection Protocol"
8. `docs/superpowers/findings/` 目录在 git status 中出现

## 7. Token budget

预估 ~200 行 production + ~180 行 tests + ~80 行 AGENTS.md §21 + 4 个 finding
文件 (~50 行 each) = **~660 行**.
