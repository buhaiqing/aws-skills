# ADR-0001 M1 Phase A — Evidence Foundation 实施计划

- **Date**: 2026-07-31
- **Spec**: [`2026-07-31-adr-m1-evidence-foundation-design.md`](../specs/2026-07-31-adr-m1-evidence-foundation-design.md)
- **ADR**: [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) §M1

## Wave 1（本 PR — 仅文档）

- [x] W1.1 Spec
- [x] W1.2 Plan（本文）

## Wave 2 任务

- [x] **T1** — `evals/scenarios/schema.md` + 五 skill skeleton
  - `evals/scenarios/{ec2,s3,iam,rds,kms}-ops/scenarios.yaml`（每文件 ≥2 占位，含 `risk`）
  - thin `golden-scenarios.yaml` 与 rich 按 `id` 对齐

- [x] **T2** — 扩展 `Scenario` + 双读 load + `--all-high-risk`
  - 6 optional 字段；merge 逻辑；`HIGH_RISK_SKILLS` 常量；CLI `--all-high-risk --out-dir`

- [x] **T3** — 五高风险 golden 扩至 ≥10 / skill（合计 ≥50）
  - 五类 `risk` 全覆盖；同步 rich + thin；基线 JSON → `audit-results/golden/`

- [x] **T4** — 测试：`test_golden_eval.py` 覆盖 merge、optional 字段、`--all-high-risk`、计数断言

- [x] **T5** — 运行 §Acceptance 全部命令

依赖：`T1 → T2 → T3 → T4 → T5`

## Acceptance（Wave 2 完成后）

### A1 — 场景深度

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
SKILLS = ["aws-ec2-ops","aws-s3-ops","aws-iam-ops","aws-rds-ops","aws-kms-ops"]
RISKS = {"read-only","write","destructive","recovery","secret-redaction"}
total = 0
for skill in SKILLS:
    rich = Path(f"evals/scenarios/{skill}/scenarios.yaml")
    thin = Path(f"{skill}/golden-scenarios.yaml")
    data = yaml.safe_load((rich if rich.exists() else thin).read_text())
    scns = data["scenarios"]; n = len(scns); total += n
    risks = {s.get("risk","") for s in scns if s.get("risk")}
    assert n >= 10, f"{skill}: {n} < 10"
    assert not (RISKS - risks), f"{skill} missing: {RISKS - risks}"
    print(f"OK {skill}: {n}")
assert total >= 50; print(f"OK total={total}")
PY
```

### A2 — batch runner

```bash
python3 scripts/golden_eval.py run --all-high-risk --out-dir audit-results/golden/
```

### A3 — 单元测试

```bash
pytest scripts/tests/test_golden_eval.py -q
```

### A4 — Bootstrap 不退化

```bash
python3 scripts/te_gate.py --all --strict
python3 -c "
from pathlib import Path; import yaml
fs = list(Path('.').rglob('golden-scenarios.yaml'))
t = sum(len(yaml.safe_load(p.read_text())['scenarios']) for p in fs)
print(len(fs), t); assert len(fs)>=45 and t>=274
"
```

### A5 — schema 文件存在

```bash
test -f evals/scenarios/schema.md
for s in aws-ec2-ops aws-s3-ops aws-iam-ops aws-rds-ops aws-kms-ops; do
  test -f "evals/scenarios/$s/scenarios.yaml"
done && echo OK
```

## Phase B 预览（不在范围）

- trace `BLOCKED` / `COMPENSATED`
- mutation-test CI（移除安全门 → 100% 检出）
- 30-day dashboard warm-up
- `expected_plan` runtime 断言（M2 Shadow）

## 完成定义

- [x] Wave 1：spec + plan 合并 → T1 可开始。
- [x] Wave 2：A1–A5 全 exit 0；mutation CI + outcome 五态已合入（`d338b9b`）；dashboard warm-up started。
- **Status**: **DONE**（M1 工程闭环）。剩余仅 30 天满窗基线（见 ADR Progress STILL OPEN）。
