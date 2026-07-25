# L4 Quick-Wins: 可观测 + 反思 + 硬门禁 — 设计文档

- **日期**: 2026-07-25
- **状态**: 定稿
- **对应计划**: `docs/superpowers/plans/2026-07-25-l4-quickwins.md`
- **优先级**: P0 (本 Spec 是 P1–P3 L4 路线的奠基; 3 项 quick win < 400 行代码)
- **先例**: `2026-07-11-level3-coverage-design.md` (3 期并行 fan-out 模式)、
  `2026-07-19-codegraph-ab-experiment-design.md` (A/B 数据驱动决策)。

## 1. 背景与基线（已核磁盘）

仓库 L4 Agentic AI 成熟度评估（2026-07-25）— 详见
[`docs/agentic-maturity-model.md`](../../agentic-maturity-model.md)：

| L4 维度 | 当前状态 |
|---|---|
| **可观测 / 遥测** | **4 条 GCL trace 散落, 无聚合** → 本 Spec Task-1 解决 |
| **反思 / Reflexion** | **静态 `docs/failure-patterns.md` (129 行, 手工)** → 本 Spec Task-2 解决 |
| **持续自校准 A/B** | Spec 已写, 未落地 → 本 Spec Task-3 解决 (硬门禁化) |

**判定**: 仓库架构上已在 L4 门槛; 差"持续度量 / 持续沉淀 / 持续校准"这条运营闭环。
本次 Spec 落地 3 个 quick win 直接覆盖这 3 个维度, 为后续 P2/P3 提供可复用基线。

## 2. 三件事（精确契约）

### 2.1 Task-1 — `scripts/gcl_metrics.py`（L4 维度 #5 可观测）

**问题**: `audit-results/` 中 4 条 GCL trace 是 JSON 散落文件, 无聚合、无统计、无报表。
任何"系统化的 L4 自进化"都需要先有"过去 30 天发生了什么"的可量化视图。

**目标**: 独立脚本, 从 `audit-results/gcl-trace-*.json` 提取:
1. **Pass-rate** (按 skill、按整体)
2. **Per-skill failure-mode 直方图** (safety=0 / blocking / SPEC dimension fail)
3. **耗时** (用文件 mtime 作粗粒度替代; trace 缺 `started_at` 字段)
4. **跳过非 GCL trace** (`strategy`/`agents` 键存在 → 是 plan artifact, 不是 trace)

输出 → `docs/gcl-metrics-report.md` (含时间戳 + SHA256 摘要, 30 日滚动窗口)。

**关键约束** (来自 `.agents/design.md`):
- "Core stays small, extend at edges" — 新增独立脚本, 不改 gcl_runner.py 核心循环
- "Minimal change that solves the real problem" — 报表只覆盖真实有数据的维度
- 不引入新依赖 (只用 stdlib + PyYAML, 已是 repo 通用依赖)

**契约**:

```python
# scripts/gcl_metrics.py
def classify_trace(trace: dict) -> Literal["gcl", "plan_artifact"]: ...
def collect_traces(audit_dir: Path, days: int = 30) -> list[TraceRow]: ...
def aggregate(rows: list[TraceRow]) -> dict[str, Any]: ...
def render_markdown(rows: list[TraceRow]) -> str: ...
def main(argv: list[str] | None = None) -> int: ...

# CLI:
#   python3 scripts/gcl_metrics.py                  # 默认 30 天
#   python3 scripts/gcl_metrics.py --days 7          # 窗口可调
#   python3 scripts/gcl_metrics.py --json            # 机器可读
#   python3 scripts/gcl_metrics.py --out PATH        # 自定义输出
```

**验收** (硬指标):
1. 对当前 4 条 trace 运行零异常
2. 输出含 3 张表: 总览 / per-skill pass-rate / 维度 fail 直方图
3. 至少正确识别 `aws-s3-ops` 2 条 + 标记 2 条 plan artifact 不混入
4. `--json` 输出能被 `json.loads` 解析
5. `docs/gcl-metrics-report.md` 在 git status 中可见

### 2.2 Task-2 — `scripts/_reflexion.py` + `gcl_runner.py --on-fail`（L4 维度 #3 反思）

**问题**: `docs/failure-patterns.md` 当前 129 行, 由 Self-Review R3 手工 append。
**没有任何自动化钩子**把 GCL SAFETY_FAIL 落到这个文件 — L4 反思记忆的"自动沉淀"是 0。

**目标**: 当 GCL 真实终止为 `SAFETY_FAIL` 或 `MAX_ITER` 且某维度 < 1.0 时,
自动追加一条失败模式到 `docs/failure-patterns.md`, **dedup by (skill, command, error_signature)**,
counter 自增。

**关键约束**:
- "Extend at the edges" — 新增 `scripts/_reflexion.py` (独立模块, ~80 行),
  gcl_runner.py 只加 `--on-fail` flag + 1 行调用
- "Minimal change" — 不改 gcl_runner.py 核心 loop; 不改 trace schema
- "Explicit over magical" — append 操作是**显式 CLI flag 控制**,
  默认 False (避免在 `--self-test` 噪声测试中污染 failure-patterns)
- 失败模式格式**严格对齐** `failure-patterns.md` §1 的 Markdown table 风格

**契约**:

```python
# scripts/_reflexion.py
@dataclass
class FailurePattern:
    skill: str
    command: str
    error: str
    root_cause: str
    fix: str
    timestamp: str  # ISO 8601

def derive_from_trace(trace: dict) -> list[FailurePattern]: ...
    # 仅当 final.status in {SAFETY_FAIL, MAX_ITER} 且最低维度 < 1.0
    # MAX_ITER 时取 best-so-far 的 critic 报错维度

def append_or_increment(path: Path, pattern: FailurePattern) -> str:
    # 返回 "appended" | "incremented" | "no-op"
    # dedup key = (skill, command, error_signature)
    # atomic write: tmp → rename

def prune_low_frequency(path: Path, min_count: int = 3, max_lines: int = 200) -> int:
    # 返回被剪枝条目数

# gcl_runner.py 新增 CLI flag:
#   --on-fail               append failure pattern on SAFETY_FAIL / MAX_ITER (default: false)
#   --failure-patterns PATH  override docs/failure-patterns.md location
```

**验收** (硬指标):
1. `python3 -c "from scripts._reflexion import ..."` 可导入, 零异常
2. 模拟 1 条 SAFETY_FAIL trace → `append_or_increment` 返回 `appended`,
   `failure-patterns.md` 行数 +1
3. 再喂相同 trace → 返回 `incremented`, 行数不变, 原行 count 列 +1
4. 喂不同 trace (skill 或 error 不同) → 返回 `appended`, 行数 +1
5. `gcl_runner.py --self-test --on-fail` 跑完后 `failure-patterns.md` 末尾新增 ≥1 行
6. **回归**: 原 Self-Review R3 流程仍可手工 append (不破坏现有用法)

### 2.3 Task-3 — AGENTS.md §12 升级 + `scripts/hooks/pre-commit`（L4 维度 #4 硬门禁）

**问题**: AGENTS.md §12 已用 "Must" 措辞, 但**无自动化执行**。
te_gate.py 已能 exit 1, 但只在手工跑 `--strict` 时生效; 没有任何
pre-commit / CI 强制触发。SKILL.md 改动后 cross_skill_deps 指向的目录是否真实
存在也只靠 GCL R2 手工 grep — 没有自动化兜底。

**目标**: 两件事并行:
1. **新增 `scripts/hooks/pre-commit`** (committed) + `scripts/install-hooks.sh`
   (committed, one-shot) — 当 staged 变更包含 `aws-*-ops/*/SKILL.md` 或
   `scripts/gcl_runner.py` / `te_gate.py` 时:
   - 自动跑 `codegraph sync .` (AGENTS.md §12 已要求, 这里机械化)
   - 对每个变更 SKILL.md, **验证 `cross_skill_deps` / `delegate` 块**指向的目录真实存在
   - 跑 `python3 scripts/te_gate.py <skill-dir> --strict`
   - 任意失败 → exit 1, 阻止 commit
2. **AGENTS.md §12 措辞升级**:
   - 新增一节"**Pre-commit Hard Gate**"明确这是**硬门禁不是建议**
   - 新增一行 Rule: "SKILL.md 改动必须 pre-commit 验证 cross_skill_deps 目录存在性"
   - 不动 §12 现有"Boundary of applicability"主体 (已很扎实)

**关键约束**:
- "Core stays small" — 不改 te_gate.py 核心; hook 是独立脚本
- "Explicit over magical" — hook 必须显式 print 每一步通过/失败原因
- "Keep PRs reviewable" — 本次 PR 只动 4 文件:
  `scripts/hooks/pre-commit` (new), `scripts/install-hooks.sh` (new),
  `scripts/tests/test_precommit_hook.py` (new),
  `AGENTS.md` (§12 局部追加)
- 不引入新依赖 (用 git/python3 已存在的工具)

**契约**:

```bash
# scripts/hooks/pre-commit
# 1. 列 changed files (git diff --cached --name-only --diff-filter=ACM)
# 2. 若含 scripts/gcl_runner.py 或 scripts/te_gate.py → 跑 --self-test / --all --strict
# 3. 若含 aws-*-ops/*/SKILL.md →
#    a. 对每个, grep frontmatter 中的 cross_skill_deps / delegate 行
#    b. 对每个 dep 名, 验证目录存在 (test -d)
#    c. 跑 python3 scripts/te_gate.py <skill-dir> --strict
# 4. 任意 step 失败 → exit 1 + 打印失败原因
```

```bash
# scripts/install-hooks.sh
git config core.hooksPath scripts/hooks
# 可重复运行, idempotent
```

**AGENTS.md §12 新增段落** (精确措辞, 落地后 verbatim):

```markdown
### Pre-commit Hard Gate (硬门禁 — automation, not suggestion)

The rules above are **enforced**, not advisory. `scripts/hooks/pre-commit` runs
automatically on `git commit` (after one-time `bash scripts/install-hooks.sh`).
Three triggers, all blocking:

1. `aws-*-ops/*/SKILL.md` staged → for each changed skill, verify every name in
   `metadata.cross_skill_deps` / `metadata.delegate` keys points to an existing
   directory in this repo (`test -d`); fail commit if any miss.
2. `scripts/gcl_runner.py` or `scripts/te_gate.py` staged → run their
   `--self-test` / `--all --strict` modes respectively; fail commit on regression.
3. Code files (`.py`/`.ts`/...) staged → `codegraph sync .` runs as part of the
   hook (mandatory pre-flight per §12 above).

**Bypass**: only for emergency hotfixes, with `git commit --no-verify`; the
bypass event MUST be logged in the commit body.
```

**验收** (硬指标):
1. `bash scripts/install-hooks.sh` 后 `git config core.hooksPath` 显示 `scripts/hooks`
2. 故意构造一个 cross_skill_deps 指向不存在目录的 SKILL.md → `git commit` 被拒
3. 恢复后正常 commit → 通过
4. AGENTS.md §12 含新 "Pre-commit Hard Gate" 段落, 含上述 3 条 trigger
5. te_gate.py 现有 `--strict` 行为不被破坏 (回归测试)

## 3. Scope 边界

**In scope**:
- 4 个独立模块文件 + 1 个 hook + 1 个 install + 1 份 AGENTS.md 局部修改 + 1 份 spec/plan
- 配套最小验证脚本 (每个 Task 自带 pytest 测试)

**Out of scope**:
- GCL trace schema 升级 (保留 v1; 扩展留待 Phase 2)
- te_gate.py 新增 G2/G5/G6 机器检查 (AGENTS.md §14.2 明确留给 LLM+人)
- 跨 runtime A/B 测试 (属 L4 维度 #7, 本 Spec 不覆盖)
- AIOps 业务脚本改动
- README_cn.md / CHANGELOG.md 同步 (不在本次 PR scope)

## 4. 开发顺序与并行策略

| 步骤 | 内容 | 并行 | 验证 |
|---|---|---|---|
| **T1.1** | `scripts/gcl_metrics.py` + tests | 独立 | smoke + 报表生成 |
| **T2.1** | `scripts/_reflexion.py` + tests | 独立 | dedup smoke |
| **T3.1** | `scripts/hooks/pre-commit` + tests | 独立 | 故意破坏 → 阻断 |
| **T2.2** | `gcl_runner.py --on-fail` 钩子 | 串行 (T2.1 后) | 跑 `--self-test --on-fail` |
| **T3.2** | `scripts/install-hooks.sh` | 串行 (T3.1 后) | `bash install-hooks.sh` |
| **T3.3** | AGENTS.md §12 段落追加 | 串行 (T3.1 后) | grep 验证新段落存在 |
| **P1** | Token Efficiency Monitor 评审 | 串行 | OPTIMAL / REFACTOR-NOW / ACCEPT-SUBOPTIMAL |
| **P2** | Self-Reflection R1 + R2 | 串行 | 2 轮全绿 |
| **P3** | 主 Agent 验证 + commit | 最后 | 全脚本可跑 |

**Fan-out 模式**: T1.1 / T2.1 / T3.1 三件**无共享写集** (不同文件, 零合并冲突),
可在同一 message 内发起 3 个 sub-agent **并行**实现。
T2.2 / T3.2 / T3.3 分别为 T2.1 / T3.1 的串联依赖, 由主 Agent 串行落地。

## 5. 度量与验收

| 维度 | 度量 | 胜出判据 |
|---|---|---|
| 完整性 | 6 个脚本 + 1 个 hook + AGENTS.md 改动全部交付 | 文件全部存在 + 可执行 |
| 可观测 | `gcl_metrics.py` 输出含 ≥3 张表 + 0 异常 | smoke test 通过 |
| 自动反思 | `--on-fail` 真实把 trace 落地到 failure-patterns | 文件内容 diff ≥1 行 |
| 硬门禁 | 故意破坏 SKILL.md → 阻断 commit | hook exit code = 1 |
| TE 通过 | Monitor 判 OPTIMAL / ACCEPT-SUBOPTIMAL | Monitor 不判 REFACTOR-NOW |

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Hook 误阻断合法 commit | hook exit code + 清晰失败原因; 提供 `--no-verify` 兜底 |
| Reflexion append 污染真实数据 | `--on-fail` 默认 False; append 前 dedup; 不破坏现有手工流程 |
| gcl_metrics.py 误把 plan artifact 当 trace | 显式 type 判定 (`iterations` vs `agents` 键) |
| AGENTS.md §12 已超 500 行 soft cap | 本次仅追加 ~15 行; 不重排现有段落 |
| Pre-commit 跑 codegraph sync 增加 commit 延迟 | sync 已是 incremental (实测 < 1s); 可接受 |

## 7. 预期产出 (Deliverable)

1. `scripts/gcl_metrics.py` (新, ~150 行) + `docs/gcl-metrics-report.md` (新, 自动生成)
2. `scripts/_reflexion.py` (新, ~80 行) + `scripts/gcl_runner.py` (追加 2 flag + 1 调用)
3. `scripts/hooks/pre-commit` (新, ~80 行) + `scripts/install-hooks.sh` (新, ~10 行)
   + `AGENTS.md` §12 追加 ~15 行
4. 一份 `docs/superpowers/plans/2026-07-25-l4-quickwins.md` (含每 Task 复选框 + 验收)
5. 验证快照: 4 条 trace 通过 gcl_metrics、failure-patterns 新增 ≥1 行、hook 阻断故意破坏

**Token budget 估计**: 总新增代码 + 文档 < 700 行, 1 个 commit 闭环。
