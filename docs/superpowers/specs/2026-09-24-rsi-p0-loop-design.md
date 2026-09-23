# RSI P0 — 闭合「度量 / 晋升 / 回写」三段环

> Spec (Spec+Plan First 铁律). Date: 2026-09-24. Branch: `feature/rsi-p0-loop`.
> Motivation: RSI 审计报告（2026-09-24）发现三段环断裂，修复后改进优劣才可判定。

## 1. 问题与根因（已验证）

| ID | 症状 | 根因（证据） |
|---|---|---|
| P0-1 | 238 条 GCL trace 落盘但无时间序列；dashboard 47 skill 的 Δ 全 `+0.00` | `gcl_metrics.py` 无持久化输出、零 CI 接线；`telemetry_dashboard.py:248` 无 prior 时 `prior_pass = pass_rate` → delta 恒 0，把「无数据」伪装成「持平」 |
| P0-2 | `auto_promote` 恒返回 0 promoted | Gate 5 要求 `age >= 168h`（`governed_learning.py:47,471-477`），但 `DEFAULT_QUEUE = audit-results/governed-learning/queue.json`（`:30`）位于 **git-ignored 且会被 prune** 的目录，且 CI 每次 `harvest --fixtures` 重建队列（`.github/workflows/golden-high-risk.yml:13`）；`candidate_from_parts:131` 无条件 `created_at=_now()` → 候选 age 恒为 0 |
| P0-3 | `docs/failure-patterns.jsonl` 26 条 **全部 `source=manual`、`last_seen=2026-08-22`** | `gcl_runner.py:731-732` 与 `golden_eval.py:565` 的默认库路径是 `.md`（legacy 6 段表），而 `runtime_safety.py:218-220` 只 load `.jsonl` → 运行时失败写进 md、读取走 jsonl，双存储分叉 |

## 2. 目标 / 非目标

**目标**
- G1：指标有 append-only 持久时间序列，可看出变好/变差。
- G2：dashboard 的 Δ 在无 prior 数据时显式 `n/a`，不再伪造 0。
- G3：候选 age 可跨运行累积（durable candidate-state），Gate 5 有真实语义。
- G4：死门禁可观测——能列出「被 Gate 5 挡住」的候选及其 age。
- G5：runtime/gcl/golden 产生的失败写入 canonical `.jsonl`，且 `source != manual`。

**非目标**
- 不新建数据库/服务/第三方依赖（stdlib only）。
- 不改变 Gate 1-7 的阈值语义（只修 age 来源）。
- 不在 CI 里 commit（避免 push 触发回环，`.github/workflows/golden-high-risk.yml:1` 是 `on: [push, pull_request]`）。
- 不把 governed-learning 队列搬进 git（保持 transient）。
- 不做 A/B baseline、模板同步钩子（属 P1，本批次不做）。

## 3. 契约（跨子任务硬约束）

- **C1**：canonical 失败库 = `docs/failure-patterns.jsonl`；`.md` 永远是 jsonl 的渲染产物（`_render_failure_patterns.py`）。
- **C2**：`governed_learning._library_signatures()` 必须同时支持 `.md` 与 `.jsonl` 输入（P0-2 负责），否则 P0-3 把默认路径切到 jsonl 后 Gate 2/7 会误判（当前 `:283` 只做 markdown 表解析）。
- **C3**：P0-3 **禁止**改 `scripts/governed_learning.py`；P0-2 **禁止**改 gcl_runner/golden_eval/_reflexion/failure_kb。文件所有权互斥。
- **C4**：新写入 jsonl 的记录 `source` 必须取 `failure_kb.SOURCES` 内的非 `manual` 值；禁止新增枚举值以外的自由字符串。
- **C5**：所有新 CLI 必须 `--help` 可见、可 `--dry-run` 或幂等；重复执行同一输入不得产生重复 CSV 行 / 重复 first-seen 覆盖。

## 4. 子任务规格

### P0-1 指标时间序列（owner: subtask A）
- `gcl_metrics.py` 新增 `--timeseries PATH`：append-only CSV，schema `timestamp,window_days,skill,total,pass,fail,pass_rate`；缺文件则写表头；同一 `timestamp`(UTC 日期) + `skill` 覆盖而非追加（幂等）。
- `telemetry_dashboard.py`：prior 缺失时 `delta=None`，渲染为 `n/a`（改 `:248` 附近 + 渲染层）；若提供 `--timeseries` 则以 CSV 为 prior 真值来源。
- 新增 `gcl_metrics.py --staleness-check --max-age-days N`：无数据/超龄 → exit 1；被 `status_snapshot.py` 复用展示 🟢/🔴。
- CI：在 `golden-high-risk.yml` 末尾（upload-artifact 之前）加一步 append 到 `audit-results/metrics/timeseries.csv`（**不 commit**，随 artifact 留存）。
- 仓库内 durable CSV：`docs/metrics/timeseries.csv` + `Makefile` 目标 `metrics`（调用 append），首次提交含表头。
- 测试：`test_gcl_metrics.py` 覆盖 append/幂等/表头/缺数据；`test_telemetry_dashboard.py` 覆盖 `delta=None → n/a` 与有 prior 时真实 Δ。

### P0-2 晋升 dwell 门禁（owner: subtask B）
- `candidate_from_parts` / harvest：按 `signature` 幂等 upsert —— 已存在则**保留最早 `created_at`**、`attempt_count += 1`、合并 `sources`（不重置时间戳）。
- 引入 durable candidate state：`docs/governed-learning/candidate-state.json`（`{signature: {first_seen: ISO8601, attempt_count: int}}`，受 git 跟踪，两字段同一次原子写落盘）。harvest 时：候选 `created_at = state.first_seen.get(sig, now)`，`attempt_count` 读累计值 +1 后写回（Gate 4 恒挡的根因）；队列仍留在 `audit-results/`（transient）。
- `confidence` 按证据计算（Gate 1 恒挡的根因）：`min(1.0, 0.30*min(attempt_count,3) + W_source + 0.05*min(distinct_sources-1,2))`，`W_source={SAFETY_FAIL:0.65, MAX_ITER:0.10, BLOCKED:0.05, COMPENSATION_FAIL:0.05}`。单次 sighting 不得满分；`MIN_CONFIDENCE` 保持 0.95 不变。
- `auto_promote` 新增 `blocked_by` 统计：返回/记录每个未晋升候选被哪个 Gate 挡住。
- 新增 `--dwell-stats`（`report` 子命令或独立子命令）：输出 pending 候选的 age 直方图 + 被 Gate 5 挡住的数量。
- `_library_signatures` 支持 `.jsonl`（C2）。
- 测试：`test_governed_learning.py` 覆盖 ①二次 harvest 不重置 created_at ②first_seen 跨进程持久化 ③age≥168h 时 Gate 5 放行（用可注入的 `now`）④Gate 5 拦截时出现在 `--dwell-stats`。

### P0-3 运行时回写（owner: subtask C）
- `gcl_runner.py:` `REFLEXION_PATTERNS_PATH`(`:52`) 与 `--failure-patterns` 默认(`:731-732`) 改为 `docs/failure-patterns.jsonl`。
- `golden_eval.py:565` 默认库路径改为 `.jsonl`。
- `_reflexion.append_or_increment` 的 jsonl 分支：透传 `source`（映射到 `failure_kb.SOURCES`：`gcl`→`gcl_trace`、`runtime_safety`→`runtime_block`、`golden_eval`→`governed_learning`；如需新值须在 `failure_kb.SOURCES` 内显式添加并说明）。`derive_from_trace` 支持 `source=` 入参，gcl_runner 传 `"gcl"`。
- 回归 md：`_render_failure_patterns.py` 重新渲染 `docs/failure-patterns.md` 并提交。
- 测试（**测试保真硬要求**）：round-trip 断言 —— 经 `gcl_runner --on-fail` 写入后，用**真实读取方** `runtime_safety.load_failure_patterns()` 能读到该记录，且 `source != "manual"`。禁止用自造解析断言。

## 5. 验收（DoD）

- `ruff check scripts/` 0 error；`pytest scripts/tests/ -q` 全绿（含新增用例）。
- P0-1：`docs/metrics/timeseries.csv` 存在且 schema 正确；无 prior 时 dashboard Δ 显示 `n/a`。
- P0-2：同一 signature 二次 harvest 后 `created_at` 不变；first-seen 跨进程保留。
- P0-3：round-trip 测试通过（`gcl_runner` 写 → `runtime_safety` 读），新记录 `source != manual`。
- 三个子任务各自原子 commit；`git status` 干净。
