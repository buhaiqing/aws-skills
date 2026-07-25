# Telemetry Dashboard — 设计 (L4 #8)

- **日期**: 2026-07-25
- **状态**: 定稿 (待实施)
- **优先级**: P2.3 (生产遥测面板)
- **关联**: `docs/agentic-maturity-model.md` §6.3 (Planned) + `gcl_metrics.py` (早期 L4 #5)

## 1. 背景

L4 #5 (`scripts/gcl_metrics.py`) 已 ship,可对 `audit-results/gcl-trace-*.json` 出
Markdown 报告 (per-skill pass-rate / fail-mode / 耗时)。但缺三件:
1. **趋势检测** — 当前 vs 30 天前,pass-rate 涨跌幅
2. **遥测面板集成** — 把 per-skill / per-fail-mode / golden_eval 数据都沉淀
   到统一 dashboard; 30 天滚动窗
3. **CI 告警** — 当 pass-rate 跌幅 ≥ threshold 时,`--alert` 模式 exit 1

P2.2 golden_eval 已经奠定 baseline 格式,P2.3 在此基础上做"统一 dashboard + 告警"。

## 2. 目标

新增 `scripts/telemetry_dashboard.py`:
1. **库函数** `load_signals(audit_dir)` 提取 (gcl traces + golden results + reflexion patterns) 单源
2. **库函数** `compute_dashboard(signals, window_days=30)` 出 per-skill 多维度指标
3. **库函数** `detect_regressions(dashboard, prior_window)` — 当 prior vs recent 跌幅 ≥ threshold 标红
4. **CLI**:
   - `dashboard` — 出 Markdown dashboard to stdout/file
   - `alert` — exit 1 if regression detected (CI gate)

## 3. 契约

```python
@dataclass
class SignalSlice:
    skill: str
    status: str              # PASS | SAFETY_FAIL | MAX_ITER
    timestamp: datetime
    source: str              # "gcl-trace" | "golden" | "reflexion"
    scenario_id: str | None  # for golden scenarios

@dataclass
class SkillMetric:
    skill: str
    pass_count: int
    fail_count: int
    total: int
    pass_rate: float          # 0..1
    prior_pass_rate: float    # 0..1 (for delta computation)
    delta: float              # pass_rate - prior_pass_rate
    regression: bool          # delta < -threshold

@dataclass
class Dashboard:
    window_days: int
    generated_at: datetime
    by_skill: list[SkillMetric]
    by_fail_mode: dict[str, int]   # dimension -> count
    total_signals: int

def load_signals(audit_dir: Path) -> list[SignalSlice]: ...
def compute_dashboard(signals: list[SignalSlice], window_days: int = 30,
                     prior_window_days: int = 7) -> Dashboard: ...
def detect_regressions(d: Dashboard, drop_threshold: float = 0.05) -> list[str]: ...
def render_markdown(d: Dashboard) -> str: ...

# Alert decision
def alert_exit_code(d: Dashboard, drop_threshold: float = 0.05) -> int:
    return 1 if detect_regressions(d, drop_threshold) else 0
```

## 4. 时间窗算法

- 30-day rolling: include signal if `(now - signal.timestamp).days <= window_days`
- Prior window: signal if `window_days < (now - sig) <= window_days + prior_window_days`
- 用于 delta 计算; 不足数据的 skill 标 `pass_rate = None`

## 5. CLI

```bash
# 1. 生成 dashboard
python3 scripts/telemetry_dashboard.py dashboard \
  --audit-dir audit-results/ \
  --window-days 30 \
  --out docs/telemetry/dashboard-2026-07-25.md

# 2. CI 告警
python3 scripts/telemetry_dashboard.py alert \
  --audit-dir audit-results/ \
  --drop-threshold 0.05
# stdout: ## Alerts
#         - aws-ec2-ops: pass_rate 0.85 -> 0.70 (Δ-0.15)
# exit 0 = no regression, 1 = regression detected
```

## 6. 验收

1. `python3 -c "from telemetry_dashboard import compute_dashboard"` 可导入
2. RED → GREEN: 7 测试 (load + 3 compute + 2 regression + 1 CLI)
3. ruff 0 issue
4. 真跑: 当前 audit-results/ 加载 → dashboard 包含 ≥ 3 个 skill 行的真实数据
5. alert 模式: 模拟 pass-rate drop → exit 1
6. AGENTS.md §17 "Telemetry Dashboard Protocol"

## 7. 风险

| 风险 | 缓解 |
|---|---|
| audit-results/ 时间戳分布不均 | 30 天窗 window 处理空数据 |
| plan artifact 混入真实 metrics | `gcl_metrics.py` 已有 filter, 复用 |
| Signal source mix (gcl-trace + golden + reflexion) | 单一 SignalSlice 抽象,每 source 独立 loader |
| Alert threshold 难定 | default 0.05 (5pp), user 可调 |

## 8. Token budget

预估 ~300 行 production + ~150 行 tests + ~50 行 AGENTS.md = **~500 行**.
