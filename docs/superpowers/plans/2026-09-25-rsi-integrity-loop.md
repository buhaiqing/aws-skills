# RSI Integrity Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and `spec-to-ship-gcl` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 闭合可信的 trace → eval artifact → candidate → shadow outcome → promotion/rollback 证据链。

**Architecture:** 三个文件所有权互斥的 Generator 并行实现 Signal Integrity、Evidence Contract、Shadow Learning；主 Agent 串行完成 ADR/spec/plan 同步和跨切片集成。只读 Critic 并行盲审，deterministic graders 与完整测试套件决定是否通过。

**Tech Stack:** Python 3.12 stdlib、pytest、ruff、GitHub Actions YAML、JSON/JSONL/SHA256。

**Spec:** `docs/superpowers/specs/2026-09-25-rsi-integrity-loop-design.md`

**Execution status (2026-09-25):** Tasks 1–4 implemented and integrated; Task 5 final contract sync and GCL verification in progress. Critic harness returned empty output, so the main Agent performed the evidence-based review and fixed the discovered blockers before final verification.

## Global Constraints

- 不执行或修改 AWS 资源。
- 不扩大 `AUTO_HEAL`、destructive approval 或 runtime 权限。
- Scheduled loop 只生成 shadow artifacts，不写长期规则，不 push。
- Artifact hash 基于原始文件 bytes。
- 无真实 eval artifact、无独立 labeled cases、metrics stale 时必须 fail closed。
- 禁止 broad `except Exception: pass` 掩盖学习链失败。
- 所有行为变更执行 RED → GREEN TDD。

## Review Focus

1. 混合 real/stub trace 时 Dashboard 不得把 stub 计入生产指标。
2. Golden current/baseline 与重复 scenario 不得重复进入分母。
3. Artifact bytes 被篡改但 JSON 仍合法时，SHA256 校验必须拒绝。
4. Memory cases 从被测 memory 自动生成时必须拒绝，而不是自证通过。
5. Scheduled workflow 重跑不得重复 ledger event，也不得修改长期 failure KB。

---

### Task 1: Signal Integrity

**Files:**
- Modify: `scripts/telemetry_dashboard.py`
- Modify: `scripts/status_snapshot.py`
- Test: `scripts/tests/test_telemetry_dashboard.py`
- Test: `scripts/tests/test_status_snapshot.py`

**Interfaces:**
- Consumes: `gcl_metrics.is_real_trace(trace: dict) -> bool`
- Produces: `load_signals(audit_dir: Path, golden_files: Sequence[Path] | None = None) -> list[SignalSlice]`
- Produces: `Snapshot.harness_ok` 与 `Snapshot.rsi_ready`

- [ ] **Step 1: RED — trace 真实性**

在 `test_telemetry_dashboard.py` 构造一个 real trace 和一个 `generator.command == "aws --self-test"` 的 stub，断言 `load_signals()` 只产生 real trace 信号。

- [ ] **Step 2: RED — Golden 选择与去重**

构造 `aws-x-ops-current.json`、`aws-x-ops-baseline.json` 及重复 scenario，断言未显式提供 `golden_files` 时不混合 baseline/current；显式提供文件时按 `(skill, scenario_id, run_id)` 去重，无 run_id 时按稳定内容 hash 去重。

- [ ] **Step 3: RED — readiness**

在 `test_status_snapshot.py` 令 `collect_metrics()` 返回 false，断言 `harness_ok is True` 但 `rsi_ready is False`，Markdown 不得出现完整 `ALL GREEN`。

- [ ] **Step 4: GREEN — 最小实现**

Telemetry 导入并复用 `gcl_metrics.is_real_trace`；CLI 新增 `--golden-file` 可重复参数。`Snapshot.all_ok` 保留 harness 语义，新增 `rsi_ready = harness_ok && metrics.ok`，状态徽章分别显示 `HARNESS GREEN` 与 `RSI NOT READY`。

- [ ] **Step 5: 验证**

```bash
pytest -v scripts/tests/test_telemetry_dashboard.py scripts/tests/test_status_snapshot.py
ruff check scripts/telemetry_dashboard.py scripts/status_snapshot.py
```

- [ ] **Step 6: Commit**

```bash
git add scripts/telemetry_dashboard.py scripts/status_snapshot.py scripts/tests/test_telemetry_dashboard.py scripts/tests/test_status_snapshot.py
git commit -m "fix(rsi): enforce signal integrity readiness"
```

### Task 2: Evidence Contract

**Files:**
- Modify: `scripts/governed_learning.py`
- Modify: `scripts/golden_eval.py`
- Test: `scripts/tests/test_governed_learning.py`
- Test: `scripts/tests/test_golden_eval.py`

**Interfaces:**
- Produces: `file_sha256(path: Path) -> str`
- Produces: `build_eval_evidence(path: Path, producer: str, run_id: str) -> dict`
- Produces: `validate_eval_evidence(candidate: CandidateRule) -> bool`
- Changes: `evaluate_candidate(..., regression_fixture: list[dict] | None = None)` 无默认真实 fixture

- [ ] **Step 1: RED — artifact round-trip**

测试真实 JSON artifact 写入后，`build_eval_evidence()` 返回 raw-bytes SHA256，`validate_eval_evidence()` 为 true。

- [ ] **Step 2: RED — tamper/missing fail closed**

覆盖 artifact 不存在、hash 格式错误、修改 artifact bytes 后 hash 不匹配、producer/run_id 缺失；每种情况 candidate 必须为 `needs_eval`。

- [ ] **Step 3: RED — regression fixture required**

不传 `regression_fixture` 时不得默认 `no_regression=true`；传入失败 fixture 时 evidence 明确包含 regression id。

- [ ] **Step 4: RED — auto-promote error propagation**

注入 `build_eval_evidence` 异常，断言 `golden_eval --auto-promote` 返回非零并输出结构化 error，不静默成功。

- [ ] **Step 5: GREEN — 最小实现**

使用 `hashlib.sha256(path.read_bytes()).hexdigest()`；evidence 保存 producer/run_id/artifact metadata；`blocking_gate()` 增加 evidence validation。`golden_eval` 捕获具体异常、打印 JSON error 并返回 1。

- [ ] **Step 6: 验证**

```bash
pytest -v scripts/tests/test_governed_learning.py scripts/tests/test_golden_eval.py
ruff check scripts/governed_learning.py scripts/golden_eval.py
```

- [ ] **Step 7: Commit**

```bash
git add scripts/governed_learning.py scripts/golden_eval.py scripts/tests/test_governed_learning.py scripts/tests/test_golden_eval.py
git commit -m "fix(rsi): bind promotion evidence to artifacts"
```

### Task 3: Labeled Memory Golden

**Files:**
- Create: `evals/memory-retrieval-golden.json`
- Create: `scripts/tests/fixtures/memory-conventions.json`
- Modify: `scripts/memory_eval.py`
- Test: `scripts/tests/test_memory_eval.py`

**Interfaces:**
- Changes: `EvalCase` 增加 `id` 与 `irrelevant_ids`
- Produces: `load_eval_cases(path: Path, minimum: int = MIN_CASES) -> list[EvalCase]`
- Changes: `--cases` 改为生产模式必填；缺失/非法/样本不足 exit 2

- [ ] **Step 1: RED — independent cases**

测试缺失 `--cases` 返回 exit 2，stderr 明确 `labeled cases required`；禁止从 memory summary 自动生成 cases。

- [ ] **Step 2: RED — irrelevant precision**

构造 top-k 包含 relevant 与 irrelevant 的 case，断言 retrieval report 单独计算 irrelevant leakage，错误相关项不能计为 relevant。

- [ ] **Step 3: RED — minimum sample**

少于最小样本、重复 case id、空 relevant_ids、未知 schema 字段均 fail closed。

- [ ] **Step 4: GREEN — 数据与 loader**

创建独立 `evals/memory-retrieval-golden.json` 与稳定的 `scripts/tests/fixtures/memory-conventions.json`，至少 8 个跨 scope cases，包含 relevant 与 irrelevant expectations。实现 strict loader 和 report 字段 `irrelevant_leakage_rate`。

- [ ] **Step 5: 验证**

```bash
pytest -v scripts/tests/test_memory_eval.py
python3 scripts/memory_eval.py eval --cases evals/memory-retrieval-golden.json --memory scripts/tests/fixtures/memory-conventions.json
ruff check scripts/memory_eval.py
```

- [ ] **Step 6: Commit**

```bash
git add scripts/memory_eval.py scripts/tests/test_memory_eval.py scripts/tests/fixtures/memory-conventions.json evals/memory-retrieval-golden.json
git commit -m "feat(rsi): add labeled memory retrieval golden"
```

### Task 4: Scheduled Shadow Loop And Outcome Ledger

**Files:**
- Create: `scripts/learning_outcomes.py`
- Create: `.github/workflows/rsi-shadow-loop.yml`
- Test: `scripts/tests/test_learning_outcomes.py`
- Test: `scripts/tests/test_rsi_shadow_workflow.py`

**Interfaces:**
- Produces: `append_event(path: Path, event: dict) -> bool`
- Produces: `build_report(events: list[dict]) -> dict`
- Event types: `candidate_proposed`, `candidate_evaluated`, `promotion_recorded`, `deployment_observed`, `post_deploy_measured`, `rollback_recorded`
- Artifact root: `audit-results/rsi-shadow-loop/`

- [ ] **Step 1: RED — idempotent append-only ledger**

相同 `event_id` 重跑只保留一条；不同事件保持 append-only；malformed event fail closed。

- [ ] **Step 2: RED — chain report**

构造完整链与断链，断言 report 输出每类事件数、完整 candidate 数、post-deploy delta、rollback rate；未知 candidate 不计入 completed chain。

- [ ] **Step 3: RED — workflow safety**

解析 YAML，断言仅 `schedule`/`workflow_dispatch` 触发；包含 real trace filter、memory cases、ledger artifact upload；不包含 `git push`、`approve --approver`、`auto_promote`、failure KB 写入。

- [ ] **Step 4: GREEN — minimal CLI**

实现 `record`、`report`、`verify` 三个子命令；仅 stdlib；默认 ledger 位于 `audit-results/rsi-shadow-loop/outcomes.jsonl`。

- [ ] **Step 5: GREEN — workflow**

Workflow 运行 targeted tests、real trace harvest/evaluate 的 shadow 模式和 outcome artifact upload；权限最小化为 `contents: read`。

- [ ] **Step 6: 验证**

```bash
pytest -v scripts/tests/test_learning_outcomes.py scripts/tests/test_rsi_shadow_workflow.py
python3 scripts/learning_outcomes.py --help
python3 scripts/learning_outcomes.py verify --ledger /tmp/outcomes.jsonl
ruff check scripts/learning_outcomes.py
```

- [ ] **Step 7: Commit**

```bash
git add scripts/learning_outcomes.py scripts/tests/test_learning_outcomes.py scripts/tests/test_rsi_shadow_workflow.py .github/workflows/rsi-shadow-loop.yml
git commit -m "feat(rsi): add scheduled shadow learning ledger"
```

### Task 5: Integration, Contract Sync And Final GCL

**Files:**
- Modify: `docs/adr/0001-l4-production-evidence-loop.md`
- Modify: `docs/superpowers/specs/2026-09-25-rsi-integrity-loop-design.md`
- Modify: `docs/superpowers/plans/2026-09-25-rsi-integrity-loop.md`
- Modify: `AGENTS.md` only if a durable new rule is not already present

- [ ] **Step 1: Parallel Critic review**

三个只读 Critic 分别审查 Signal Integrity、Evidence Contract、Shadow Learning，输出 `[BLOCKER|MAJOR|MINOR]`、文件行号、Spec↔Plan↔Code 结论。

- [ ] **Step 2: Fix loop**

仅修复 BLOCKER/MAJOR；每轮后重跑对应 targeted tests，最多 3 轮。

- [ ] **Step 3: Contract sync**

ADR 明确 scheduled shadow 不自动写回；artifact hash 为强制 promotion evidence；readiness stale 时不得声明 RSI ready。

- [ ] **Step 4: Deterministic gates**

```bash
ruff check scripts/
pytest -v scripts/tests/
bash scripts/hooks/pre-commit
python3 - <<'PY'
import pathlib, yaml
for p in pathlib.Path('.github/workflows').glob('*.yml'):
    yaml.safe_load(p.read_text())
print('workflow yaml ok')
PY
```

- [ ] **Step 5: Vertical integration probes**

```bash
python3 scripts/telemetry_dashboard.py dashboard --audit-dir audit-results --golden-file audit-results/golden/aws-ec2-ops-current.json --out /tmp/rsi-dashboard.md
python3 scripts/gcl_metrics.py --staleness-check --max-age-days 7; test $? -eq 1
python3 scripts/memory_eval.py eval --cases evals/memory-retrieval-golden.json --memory /tmp/memory-fixture.json
python3 scripts/learning_outcomes.py report --ledger /tmp/outcomes.jsonl
```

- [ ] **Step 6: Final Critic and commit**

Final Critic 验证无 stub 假绿、无 broad catch、无长期规则自动写入、完整测试通过；更新 plan checkboxes 和 GCL verdict。
