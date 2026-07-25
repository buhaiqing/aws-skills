# L4 Quick-Wins 执行计划（TDD 强制）

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:test-driven-development`
> （r4 / r6 根下）。任何代码改动前必须 **RED → GREEN → REFACTOR**；测试有效性 > 覆盖率。

**Goal**: 落地 Spec `2026-07-25-l4-quickwins-design.md` 三个 quick win，用 TDD 保证
每个脚本/hook 都经过"先写失败测试 → 看到正确失败原因 → 最小实现 → 全绿"循环。

**Architecture**:
- T1: 新增 `scripts/gcl_metrics.py` + `scripts/tests/test_gcl_metrics.py` + 自动生成 `docs/gcl-metrics-report.md`
- T2: 新增 `scripts/_reflexion.py` + `scripts/tests/test_reflexion.py` + 给 `scripts/gcl_runner.py` 加 `--on-fail` flag
- T3: 新增 `scripts/hooks/pre-commit` + `scripts/install-hooks.sh` + `scripts/tests/test_precommit_hook.py` + AGENTS.md §12 新段落

**Tech Stack**: Python 3.12 (stdlib + PyYAML), pytest 9.0.3, ruff 0.11.8, bash。

---

## 通用 TDD 纪律（每个 sub-agent 都必须遵守）

1. **RED**: 在 `scripts/tests/test_<module>.py` 写至少 5 个测试，**针对真实 fixture**
   （不要 mock 掉被测对象本身）。常见 fixture：
   - 4 条真实 trace: `audit-results/gcl-trace-*.json`
   - 真实 `docs/failure-patterns.md` 副本（测试用 `tmp_path` 隔离）
2. **VERIFY RED**: 跑 `pytest scripts/tests/test_<module>.py -x`，确认每个测试因
   "feature missing / NotImplementedError" 失败（不是 import error 或 typo）。
3. **GREEN**: 写**最小**实现让测试过；不动 gcl_runner.py 核心 loop。
4. **VERIFY GREEN**: 跑全量 `pytest scripts/tests/`，所有测试绿，无 warning。
5. **REFACTOR**: 在保持绿的前提下消除重复，提取 helper。**不允许加新行为**。
6. **禁止的反模式**（来自 `superpowers:test-driven-development/testing-anti-patterns.md`）:
   - 不要 mock 你要测的函数本身（用真实函数）
   - 不要为了测试加 test-only 方法到生产代码
   - 不要"我先写完再补测试"——违反 Iron Law，删除重写
   - 不要把"行覆盖率"当目标——目标是**测试能抓到真实 bug**

每个 sub-agent 必须在最终汇报里包含：
- RED 阶段输出（验证失败的 pytest 截屏）
- GREEN 阶段输出（全绿 pytest 截屏）
- 真实 fixture 用例（不是 mock）
- 改动文件清单 + 行数

---

## Task T1 — `scripts/gcl_metrics.py`（L4 维度 #5）

**Files**:
- NEW `scripts/tests/test_gcl_metrics.py`
- NEW `scripts/gcl_metrics.py`
- NEW `docs/gcl-metrics-report.md`（自动生成, 首次 commit 后存在）

### T1.1 RED: 写 6 个失败测试

- [ ] **Step 1** — 创建 `scripts/tests/__init__.py`（空文件, 让 pytest 识别）
- [ ] **Step 2** — `test_real_gcl_trace_is_parsed_as_trace_not_plan`:
  加载 `audit-results/gcl-trace-20260627-031257.json`（SAFETY_FAIL），调用
  `classify_trace(trace) == "gcl"`，**且** `extract_final_status(trace) == "SAFETY_FAIL"`
- [ ] **Step 3** — `test_plan_artifact_is_excluded_from_metrics`:
  加载 `audit-results/gcl-trace-20260705-181751.json`（含 `strategy`/`agents` 键），
  调用 `classify_trace(trace) == "plan_artifact"`，**且** `collect_traces()` 不返回它
- [ ] **Step 4** — `test_pass_rate_per_skill`:
  对 4 条 trace 跑 `collect_traces()`，断言 `aws-s3-ops` 的 pass_rate 在 [0, 1] 区间，
  且 total = len(iterations) 时每条 iter 真实分母正确（s3 有 2 条, 0 PASS / 2 FAIL）
- [ ] **Step 5** — `test_failure_dimensions_are_aggregated`:
  SAFETY_FAIL trace (s3 iter=1) critic.scores.safety == 0 → 维度直方图
  `dimension_fail_counts["safety"] >= 1`，且 command 是 `aws --self-test`
- [ ] **Step 6** — `test_markdown_render_contains_three_tables`:
  对 4 条 fixture 跑 `render_markdown(rows)`，断言 markdown 字符串含至少 3 个
  `| ` 起头的表格行 + 1 个 `## Pass-rate by skill` 段标题
- [ ] **Step 7** — `test_json_output_is_machine_readable`:
  跑 `main(["--json", "--days", "30"])`, 捕获 stdout, `json.loads(stdout)` 不抛异常，
  且 result 是 `dict` 且含 `"rows"` 键
- [ ] **Step 8** — `pytest scripts/tests/test_gcl_metrics.py -x` 全红，截屏 RED

### T1.2 GREEN: 最小实现

- [ ] **Step 1** — `scripts/gcl_metrics.py`:
  - `classify_trace(trace: dict) -> Literal["gcl","plan_artifact"]`: 含 `iterations`→gcl, 含 `agents`→plan_artifact
  - `collect_traces(audit_dir: Path, days: int = 30) -> list[TraceRow]`: glob `gcl-trace-*.json`,
    mtime < cutoff 排除, 调用 `classify_trace` 过滤
  - `extract_final_status(trace) -> str`: `trace["final"]["status"]`
  - `aggregate(rows) -> dict`: per-skill pass-rate + dimension fail 直方图
  - `render_markdown(rows) -> str`: 3 张表（总览 / per-skill / 维度 fail）
  - `main(argv)`：argparse `--days/--json/--out`
- [ ] **Step 2** — 跑 `pytest scripts/tests/test_gcl_metrics.py -v`, 全绿
- [ ] **Step 3** — 跑 `python3 scripts/gcl_metrics.py`, 生成
  `docs/gcl-metrics-report.md`, 截屏 GREEN

### T1.3 REFACTOR

- [ ] **Step 1** — 提取 `TraceRow` dataclass（如必要），消除重复字典访问
- [ ] **Step 2** — 跑 `ruff check scripts/gcl_metrics.py scripts/tests/test_gcl_metrics.py`, 0 issue
- [ ] **Step 3** — 跑 `pytest scripts/tests/test_gcl_metrics.py -v`, 仍绿

### T1 验收

- [ ] RED 截屏存在（每个测试 FAIL 因 NotImplementedError）
- [ ] GREEN 截屏存在（6 测试全绿, 0 warning）
- [ ] `docs/gcl-metrics-report.md` 在 git status
- [ ] ruff 0 issue

---

## Task T2 — `scripts/_reflexion.py` + gcl_runner.py hook（L4 维度 #3）

**Files**:
- NEW `scripts/tests/test_reflexion.py`
- NEW `scripts/_reflexion.py`
- MODIFY `scripts/gcl_runner.py`（追加 `--on-fail` flag + 1 行 hook 调用）

### T2.1 RED: 写 7 个失败测试

- [ ] **Step 1** — `test_derive_from_pass_trace_returns_empty`:
  给一个 final.status=PASS trace, `derive_from_trace(trace) == []`
- [ ] **Step 2** — `test_derive_from_safety_fail_returns_one_pattern`:
  给 gcl-trace-20260627-031257.json（safety=0）→ `len(derive_from_trace(trace)) == 1`,
  且 pattern.skill == "aws-s3-ops", pattern.error 含 "safety=0"
- [ ] **Step 3** — `test_derive_from_max_iter_returns_one_pattern`:
  给 gcl-trace-20260627-031303.json（MAX_ITER, idempotency=0）→ `len == 1`,
  且 pattern.error 含 "idempotency=0"
- [ ] **Step 4** — `test_append_or_increment_adds_new_row`:
  tmp_path/failure-patterns.md 初始空, append 一个 pattern → 文件含 1 行表格行,
  count 列 == 1, timestamp 列是 ISO 8601
- [ ] **Step 5** — `test_append_or_increment_dedups_and_increments`:
  同一 pattern 连续 append 3 次 → 文件仍 1 行, count 列 == 3
- [ ] **Step 6** — `test_prune_removes_low_frequency`:
  构造 5 行 count=1 + 1 行 count=5, 跑 `prune_low_frequency(min_count=3)` →
  文件只剩 count=5 那一行
- [ ] **Step 7** — `test_gcl_runner_self_test_on_fail_appends_to_failure_patterns`:
  `tmp_path` 复制 `docs/failure-patterns.md`, 跑
  `python3 scripts/gcl_runner.py --self-test --no-prune --on-fail
  --failure-patterns <tmp>/failure-patterns.md`, 验证临时文件末尾新增 ≥1 行
  （**这是集成测试, 不是 mock**）
- [ ] **Step 8** — RED 截屏

### T2.2 GREEN: 最小实现

- [ ] **Step 1** — `scripts/_reflexion.py`:
  - `@dataclass class FailurePattern`: skill/command/error/root_cause/fix/timestamp
  - `derive_from_trace(trace: dict) -> list[FailurePattern]`: 只看 SAFETY_FAIL / MAX_ITER,
    提取最低分维度的 error 描述
  - `append_or_increment(path: Path, pattern: FailurePattern) -> str`: dedup key =
    `(skill, command, error_signature)`, atomic write tmp→rename
  - `prune_low_frequency(path, min_count=3, max_lines=200) -> int`
- [ ] **Step 2** — 修改 `scripts/gcl_runner.py`:
  - 添加 `--on-fail` flag (default False)
  - 添加 `--failure-patterns PATH` flag (default REPO/docs/failure-patterns.md)
  - 在 `_prune_old_traces()` 后或 trace write 前, 调用
    `from scripts._reflexion import derive_from_trace, append_or_increment`,
    仅当 `--on-fail` 且 final.status in {SAFETY_FAIL, MAX_ITER}
  - **不动** 核心 loop / 终止 / trace schema
- [ ] **Step 3** — `pytest scripts/tests/test_reflexion.py -v`, 全绿, 截屏 GREEN

### T2.3 REFACTOR

- [ ] **Step 1** — 把 error_signature 抽成 helper（如 `f"{dim}={value}"`）
- [ ] **Step 2** — ruff 0 issue
- [ ] **Step 3** — 再跑一次 T2.1 的所有测试, 仍绿

### T2 验收

- [ ] gcl_runner.py 核心 loop **未变**（`git diff` 确认只追加 CLI flag + 1 调用）
- [ ] RED 截屏 + GREEN 截屏
- [ ] 集成测试 (T2.1 step 7) 真跑 `--self-test`, 不 mock
- [ ] ruff 0 issue

---

## Task T3 — `scripts/hooks/pre-commit` + AGENTS.md §12（L4 维度 #4）

**Files**:
- NEW `scripts/tests/test_precommit_hook.py`
- NEW `scripts/hooks/pre-commit`
- NEW `scripts/install-hooks.sh`
- MODIFY `AGENTS.md`（§12 末尾追加 "Pre-commit Hard Gate" 段落）

### T3.1 RED: 写 6 个失败测试

- [ ] **Step 1** — `test_hook_exits_zero_when_no_relevant_files_staged`:
  `subprocess.run(["bash", "scripts/hooks/pre-commit"], env=...)` + fake
  `git diff --cached --name-only` 返回空 → exit code 0
- [ ] **Step 2** — `test_hook_exits_one_when_skill_md_has_missing_cross_skill_dep`:
  临时 SKILL.md 含 `cross_skill_deps: [aws-nonexistent-ops]` → exit code 1,
  stderr 含 "missing dir" 字样
- [ ] **Step 3** — `test_hook_exits_zero_when_cross_skill_deps_exist`:
  临时 SKILL.md 含 `cross_skill_deps: [aws-s3-ops]`（真实存在）→ exit code 0
- [ ] **Step 4** — `test_hook_runs_te_gate_when_skill_md_staged`:
  临时 SKILL.md 行数 200（>120）→ exit code 1, stderr 含 "G1" 字样
- [ ] **Step 5** — `test_install_hooks_sh_sets_core_hooks_path`:
  `subprocess.run(["bash", "scripts/install-hooks.sh"])` + 后续
  `git config core.hooksPath` → 输出 `scripts/hooks`
- [ ] **Step 6** — `test_agents_md_section_12_contains_precommit_hard_gate`:
  读 AGENTS.md, 断言含 `Pre-commit Hard Gate` 段标题 + `scripts/hooks/pre-commit` 字符串
- [ ] **Step 7** — RED 截屏

### T3.2 GREEN: 最小实现

- [ ] **Step 1** — `scripts/hooks/pre-commit`（bash）:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  REPO=$(git rev-parse --show-toplevel)
  CHANGED=$(git diff --cached --name-only --diff-filter=ACM)
  FAIL=0
  # 检测 SKILL.md cross_skill_deps
  for f in $CHANGED; do
    [[ "$f" =~ ^aws-.*-ops/.*/SKILL\.md$ ]] || continue
    # grep frontmatter 中的 cross_skill_deps / delegate 值
    deps=$(awk '/^cross_skill_deps:/,/^[a-z]/' "$f" | grep -E '^\s+- ' | awk '{print $2}' || true)
    for d in $deps; do
      [[ -d "$REPO/$d" || -d "$REPO/aws-$d-ops" ]] || {
        echo "✗ missing dir: $d (referenced from $f)"; FAIL=1;
      }
    done
    # 跑 te_gate
    skill_dir=$(dirname "$f")
    python3 "$REPO/scripts/te_gate.py" "$skill_dir" --strict || FAIL=1
  done
  exit $FAIL
  ```
- [ ] **Step 2** — `scripts/install-hooks.sh`（bash, 3 行）:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  git config core.hooksPath scripts/hooks
  echo "✓ hooks path → scripts/hooks"
  ```
- [ ] **Step 3** — AGENTS.md §12 末尾追加（**verbatim**）:
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
- [ ] **Step 4** — `pytest scripts/tests/test_precommit_hook.py -v`, 全绿, 截屏

### T3.3 REFACTOR

- [ ] **Step 1** — pre-commit 里提取 helper 函数（避免长 if-for 嵌套）
- [ ] **Step 2** — shellcheck `scripts/hooks/pre-commit scripts/install-hooks.sh`（如有）
- [ ] **Step 3** — 再跑所有测试, 仍绿

### T3 验收

- [ ] RED + GREEN 截屏
- [ ] AGENTS.md §12 新段落存在, 字数 ≤ 200 行追加
- [ ] `bash scripts/install-hooks.sh` 真跑通, `git config core.hooksPath` 显示 `scripts/hooks`
- [ ] 故意构造的 `cross_skill_deps: [aws-bogus-ops]` SKILL.md → hook exit 1
- [ ] 真实 commit `aws-skill-generator/SKILL.md` → hook exit 0

---

## 串行收尾（主 Agent 责任）

- [ ] **P1 — 集成验证**: 跑 `pytest scripts/tests/ -v`, 全部绿; 跑
  `python3 scripts/gcl_metrics.py`, 生成报表; 跑
  `python3 scripts/gcl_runner.py --self-test --on-fail`, 验证 failure-patterns.md
  新增 ≥1 行; 跑 `bash scripts/install-hooks.sh` + 故意构造坏 SKILL.md,
  hook 退出 1
- [ ] **P2 — Token Efficiency Monitor**: 派 sub-agent 评审本次新增 3 文件 + 测试,
  判 OPTIMAL / REFACTOR-NOW / ACCEPT-SUBOPTIMAL
- [ ] **P3 — Self-Reflection R1 (结构)**: AGENTS.md "Self-reflection rule" 表:
  R1 范围, 跑 Charter C1–C6 + TE-1…TE-6 + frontmatter 单 --- 块校验 + delegation
  引用存在性 + 破坏性操作人工确认 + JSON 路径对齐 + README sync + TE post-change audit
- [ ] **P4 — Self-Reflection R2 (内容)**: CLI 验证 / 错误码 / 安全门禁 / 链接完整 /
  dedup / TODO.md sync (本 PR 不动 TODO, 记录在 PR body)
- [ ] **P5 — commit & push**: 单个 commit, message:
  `feat(l4-quickwins): gcl metrics + reflexion + pre-commit hard gate (#L4 #5/#3/#4)`

## Token budget

总新增 < 600 行（生产 + 测试 + AGENTS.md 追加 + docs 报表）。3 个独立 sub-agent
并行 → 主串行收尾。预计 wall-time < 30 分钟（含 fixture 解析）。
