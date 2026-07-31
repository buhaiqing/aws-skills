# ADR-0001 M1 Phase A — Evidence Foundation 设计

- **日期**: 2026-07-31
- **状态**: 定稿 (Wave 1 — spec/plan only)
- **关联**: [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md), [`AGENTS.md`](../../../AGENTS.md) §16, [`2026-07-25-eval-driven-dev-design.md`](2026-07-25-eval-driven-dev-design.md)

## 1. 目的

ADR-0001 M1 从 bootstrap golden（45 skill × ≥5）升级到**高风险服务深度证据集**。Phase A：

1. 定义 `evals/scenarios/` rich schema
2. 扩展 `golden_eval.py` 双读 + `--all-high-risk`
3. 五高风险 skill 各 ≥10 场景（合计 ≥50）

Phase B 才做 `BLOCKED`/`COMPENSATED`、mutation CI、dashboard warm-up。

## 2. 现状差距（2026-07-31）

| Skill | 当前 | 目标 |
|---|---:|---:|
| aws-ec2-ops | 7 | ≥10 |
| aws-s3-ops / iam / rds / kms | 各 6 | 各 ≥10 |
| **合计** | **31** | **≥50** |

## 3. Rich schema

权威文档：`evals/scenarios/schema.md`（T1）。

### 3.1 新增 optional 字段（向后兼容）

| 字段 | 类型 | 说明 |
|---|---|---|
| `risk` | enum | `read-only` \| `write` \| `destructive` \| `recovery` \| `secret-redaction` |
| `preconditions` | `list[str]` | 执行前 describe/配额条件 |
| `expected_plan` | `str` | 期望 Planner 动作摘要（Phase A 不断言） |
| `expected_gate` | `str` | 期望 safety/GCL 门行为 |
| `expected_outcome` | `str` | 人类可读结果语义 |
| `forbidden_actions` | `list[str]` | 禁止 CLI 子命令/参数 |

### 3.2 保留字段（Phase A 不变）

`id`, `description`, `request` 必填；`expected_status` 仅 `PASS` \| `SAFETY_FAIL` \| `MAX_ITER`；`user_region`, `safety_confirm` 可选。

## 4. 双读架构

```text
evals/scenarios/<skill>/scenarios.yaml   ← rich source
        ↓ merge by id
aws-<skill>-ops/golden-scenarios.yaml    ← thin L4 §16 entry
        ↓
golden_eval.load_scenarios() → Scenario → gcl_runner --self-test
```

合并：rich 优先；thin 按 `id` 补 rich 缺失项，不覆盖 rich 已有键；仅 thin 时行为不变。

## 5. Scenario dataclass 映射

现有（`scripts/golden_eval.py`）：

```python
@dataclass
class Scenario:
    id: str; description: str; request: str
    expected_status: str          # PASS | SAFETY_FAIL | MAX_ITER
    user_region: str = ""; safety_confirm: str = ""
```

Phase A 扩展（optional，默认空）：

```python
    risk: str = ""
    preconditions: list[str] = field(default_factory=list)
    expected_plan: str = ""; expected_gate: str = ""
    expected_outcome: str = ""
    forbidden_actions: list[str] = field(default_factory=list)
```

Runner Phase A **只断言** `expected_status`；rich 字段供文档与未来 shadow 断言。

## 6. 高风险服务集

`aws-ec2-ops`, `aws-s3-ops`, `aws-iam-ops`, `aws-rds-ops`, `aws-kms-ops` — 各 ≥10，五类 `risk` 均 ≥1，合计 ≥50。

## 7. CLI

```bash
python3 scripts/golden_eval.py run --all-high-risk --out-dir audit-results/golden/
```

依次跑 §6 五 skill，双读加载，输出 5 JSON。

## 8. Phase A 范围外

| 项 | 归属 |
|---|---|
| `BLOCKED` / `COMPENSATED` | Phase B + trace schema |
| mutation-test CI | Phase B |
| 30-day dashboard warm-up | Phase B |
| `expected_plan` runtime 断言 | M2 Shadow |

## 9. Wave 1 验收

1. 本 spec + plan 存在且交叉引用。
2. Wave 2：五 skill 各 ≥10，合计 ≥50。
3. Wave 2：`run --all-high-risk` exit 0；pytest 全绿；45-skill bootstrap 不退化。
