# ADR-0001 M2 — Shadow Execution Design

- **Date**: 2026-07-31
- **Status**: 已实施（M2 code + tests landed）
- **ADR**: [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) §Milestone 2
- **Depends on**: M1 Evidence Foundation（`evals/`, `--all-high-risk`, mutation CI, outcome 五态）
- **Plan**: [`../plans/2026-07-31-adr-m2-shadow-execution.md`](../plans/2026-07-31-adr-m2-shadow-execution.md)

## 1. Goal

写操作执行前必须可证明：**计划、范围、预期变化**。缺 shadow evidence 或 plan 与调用漂移 → **不得**进入真实 mutation。

```text
Request
  → Planner (ExecutionPlan + plan_hash)
  → Shadow Executor (dry-run | describe/simulator) → ShadowEvidence (redacted)
  → Runtime Safety (failure patterns + plan-bound token)
  → GCL (Generator / Critic)  # confirm= literals unchanged
  → safe_tool_proxy            # hard gate: shadow + token
  → AWS
```

## 2. Non-goals

- M3 补偿执行 / DAG orchestration
- 扩大 `AUTO_HEAL`
- 全仓 45 skill 一律 shadow（M2 先五高风险 destructive 100%）
- 改变技能文档里的 GCL `confirm=<OP> <id>` 操作员体验
- 以「30 天 dashboard 满窗」作为库代码开工前提（仅阻塞 AUTO_HEAL 放宽）

## 3. Reuse

| Asset | Use |
|---|---|
| `scripts/runtime_safety.py` | `ToolCall`, pattern gate; add plan-bound token helper |
| `scripts/safe_tool_proxy.py` | Sole write path; add shadow/plan_hash check before ALLOW exec |
| `scripts/gcl_runner.py` | Trace may record `shadow` + `BLOCKED` on pre-GCL block |
| `evals/scenarios/*` | `expected_plan` / `expected_gate` become assertable in W4 |
| High-risk: ec2 / s3 / iam / rds / kms | First coverage set |

## 4. Data model

### ExecutionPlan

| Field | Type | Notes |
|---|---|---|
| `plan_id` | str | uuid4 or ulid |
| `skill` | str | e.g. `aws-ec2-ops` |
| `operation` | str | normalized, e.g. `ec2 terminate-instances` |
| `resource_ids` | list[str] | canonical ids |
| `region` | str | A7 |
| `risk` | str | read-only \| write \| destructive \| … |
| `preconditions` | list[str] | human/machine checks |
| `expected_diff` | dict | structured intent (before→after) |
| `confirmation_op` | str | maps to GCL Confirmation Strings op label |
| `verify` | list[str] | post-conditions |
| `compensation` | str \| null | **placeholder for M3 only** |
| `plan_hash` | str | sha256 of canonical JSON (no hash field inside) |

### ShadowEvidence

| Field | Type | Notes |
|---|---|---|
| `plan_hash` | str | must match plan |
| `strategy` | `dry-run` \| `describe` \| `simulate` | |
| `ok` | bool | shadow succeeded |
| `redacted_payload` | dict | A9-masked |
| `timestamp` | ISO8601 | |
| `path` | str | `audit-results/shadow/shadow-…json` |

## 5. Token binding (locked)

- **GCL Critic** continues to require skill `confirm=` literals in trace (unchanged).
- **Runtime / proxy** uses a **new** helper:

```text
build_plan_bound_token(call, plan_hash) -> "CONFIRM <op> <digest16>"
digest = sha256(canonical_call_json + plan_hash)[:16]
```

- Existing `build_confirmation_token(call)` remains for backward-compat tests; destructive proxy path **requires** plan-bound token + matching on-disk ShadowEvidence for `plan_hash`.
- Drift (resource / region / op change after plan) → token mismatch or `assert_plan_matches_call` fail → **BLOCK**.

## 6. Shadow strategies

1. **Native dry-run** — when AWS CLI/API documents dry-run for the op (allowlist in code).
2. **Describe / read-back** — snapshot current resource state; no writes.
3. **Local simulate** — for ops with no dry-run; produce structured expected_diff check only (no AWS).

Shadow Executor **must not** call mutating APIs.

## 7. Exit criteria (ADR M2)

| Criterion | Measure |
|---|---|
| 100% destructive high-risk scenarios produce plan_hash + shadow evidence | eval/unit + mocked integration |
| Parameter / region / resource drift blocked | dedicated tests; 0 escapes |
| False-block rate &lt; 5% on eval set | fixture suite; document formula |
| Safety leak = 0 | no plaintext secrets in shadow JSON fixtures |

## 8. Phases

| Phase | Scope |
|---|---|
| **A** | `execution_plan.py` + `shadow_exec.py` + unit tests (no live AWS) |
| **B** | `safe_tool_proxy` hard gate + plan-bound token |
| **C** | High-risk destructive eval hooks + CI; ADR/maturity progress |

## 9. Acceptance commands (target)

```bash
pytest -p no:rerunfailures scripts/tests/test_execution_plan.py \
  scripts/tests/test_shadow_exec.py scripts/tests/test_safe_tool_proxy.py \
  scripts/tests/test_shadow_coverage.py -q
python3 scripts/shadow_coverage.py check --all-high-risk
```
