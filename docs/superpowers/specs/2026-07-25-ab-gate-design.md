# A/B Test Hard Gate — 设计 (L4 #9)

- **日期**: 2026-07-25
- **状态**: 定稿 (待实施)
- **优先级**: P2.4 (A/B Hard Gate)
- **关联**: `docs/agentic-maturity-model.md` §6.3 (Planned)

## 1. 背景

P2.2 `golden_eval.py` 已经能跑 scenarios + diff baseline。但当前是**手动两步**:
1. 写 baseline
2. 写改动
3. run + diff

P2.4 把这三步自动化,并加入**跨 skill cascade** — 当改 L2 composite
(`aws-aiops-copilot`),所有 `metadata.cross_skill_deps` 里的 skills 也要一并回归跑。

任何 PR 涉及 `aws-*-ops/SKILL.md` 或 `references/` 必须通过 `ab_gate.py` 才合,否则
CI 失败。

## 2. 目标

新增 `scripts/ab_gate.py`:
1. **库** `run_ab_gate(baseline_path, candidate_path, drop_threshold=0.05) -> ABReport`
2. **库** `cascaded_skills(skill_name) -> list[str]` 从 frontmatter 提取 `cross_skill_deps`
3. **CLI** 子命令:
   - `gate` — 比较 baseline vs candidate, exit 1 if regression
   - `cascade` — 列出 cross_skill_deps (dry-run)
4. **JSON output** — 给 CI 消费

## 3. 契约

```python
@dataclass
class ABReport:
    baseline_path: Path
    candidate_path: Path
    regressions: list[str]
    fixed: list[str]
    unchanged: list[str]
    cascaded_regressions: list[str]  # cross_skill_deps with own regressions
    @property
    def has_regression(self) -> bool: ...
    @property
    def exit_code(self) -> int: ...   # 0 or 1

def run_ab_gate(
    baseline_path: Path,
    candidate_path: Path,
    drop_threshold: float = 0.05,
) -> ABReport: ...

def cascaded_skills(skill_name: str, repo: Path = REPO) -> list[str]:
    """Read SKILL.md frontmatter; return list of cross_skill_deps (skill dir names)."""
```

## 4. CLI 协议

```bash
# 1. 比较 baseline vs candidate
python3 scripts/ab_gate.py gate \
  --baseline audit-results/baseline/aws-ec2-ops.json \
  --candidate audit-results/golden/aws-ec2-ops.json
# stdout: ## A/B Gate Report
#         regressions: 0
#         fixed: 1
#         cascaded_regressions: 0
# exit 0 = pass, 1 = regression

# 2. Dry-run: cascade 列表
python3 scripts/ab_gate.py cascade --skill aws-aiops-copilot
# stdout: cascaded skills for aws-aiops-copilot:
#         - aws-aiops-cruise
#         - aws-aiops-orchestrator

# 3. CI JSON 输出
python3 scripts/ab_gate.py gate ... --json
# stdout: {"regressions": [...], "fixed": [...], "exit_code": 0}
```

## 5. 验收

1. `python3 -c "from ab_gate import run_ab_gate, ABReport"` 可导入
2. RED → GREEN: 5 测试 (gate + cascade + JSON + 2 CLI)
3. ruff 0 issue
4. 真跑: 创建 baseline.json + candidate.json (mutated one) → gate exit 1
5. AGENTS.md §18 "A/B Test Hard Gate Protocol"

## 6. 风险

| 风险 | 缓解 |
|---|---|
| 两份 JSON schema 不一致 (旧版缺 `skill` 字段) | gate 加载时校验, 缺失报错 |
| 跨 skill cascade 跟用户期望不符 | cascade 是 advisory,不参与 gate decision |
| CI 调用端无 baseline.json | gate 退出码 2 + 明确提示 "no baseline" |

## 7. Out of scope

- 自动生成 baseline (P3; 当前是手动)
- 多 variant 多臂老虎机 (P3)
- 统计显著性检验 (P4; 当前用 delta threshold)

## 8. Token budget

预估 ~250 行 production + ~150 行 tests + ~70 行 AGENTS.md = **~470 行**.
