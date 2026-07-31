# ADR-0001 M3 — Transactional Orchestration Design

- **Date**: 2026-07-31
- **Status**: 定稿草案（Wave C0 — **编码前仍须用户确认本 spec**）
- **ADR**: [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) §Milestone 3
- **Depends on**: M2 Shadow（`execution_plan` / `shadow_exec` / plan-bound proxy）
- **Plan**: [`../plans/2026-07-31-adr-m3-transactional-orchestration.md`](../plans/2026-07-31-adr-m3-transactional-orchestration.md)

## 1. Goal

跨服务执行具备**确定的停止与补偿**：每个节点声明前置/后置条件与补偿；补偿不得绕过 GCL + `safe_tool_proxy` + shadow。

```text
Request
  → Planner (ExecutionDAG + per-node ExecutionPlan)
  → Shadow each writable node
  → Runtime Safety + plan-bound token
  → GCL per node
  → safe_tool_proxy
  → Validate postcondition
  → on failure: Compensation (same gates) | MANUAL halt
```

## 2. Non-goals

- 扩大 `AUTO_HEAL`（仍受 M1 满窗 + 本里程碑补偿证据约束）
- 全仓任意 skill 编排（先三条链）
- 改 GCL `confirm=` 操作员字面量
- 让 Critic / Telemetry 直接 mutate AWS

## 3. Data model

### ExecutionNode

| Field | Notes |
|---|---|
| `id` | stable node id |
| `skill` / `operation` | L1 skill + op |
| `plan` | `ExecutionPlan` (M2) |
| `precondition` | list[str] machine/human checks |
| `postcondition` | list[str] |
| `compensation` | node id \| inline plan \| null |
| `non_compensable` | bool → default MANUAL |
| `on_fail` | `compensate` \| `halt` \| `manual` |

### ExecutionDAG

| Field | Notes |
|---|---|
| `dag_id` / `dag_hash` | hash over canonical node plans + edges |
| `nodes` | ordered / adjacency |
| `edges` | dependency list |
| `verify` | DAG-level post-checks |

## 4. Pilot chains (ADR)

1. **ELB target remediation** — deregister unhealthy → (compensate) re-register
2. **RDS failover + Route53** — failover → DNS cutover → compensate DNS / halt if non_compensable
3. **ECS deploy + ELB health** — update service → wait healthy → compensate rollback task def

Each chain needs fixtures: **success**, **node failure**, **compensation failure**.

## 5. Gate rules (locked)

- Writable / destructive nodes: M2 shadow + plan-bound token + proxy
- Compensation nodes: **same** gates (no bypass)
- `non_compensable=true`: stop before mutate; emit recovery handbook stub + evidence snapshot
- Outcome: reuse `COMPENSATED` / `BLOCKED` from M1 schema when applicable

## 6. Exit criteria (from ADR)

- 三条链 ×（成功 / 节点失败 / 补偿失败）测试
- 可补偿失败自动恢复率 ≥90%（fixture 度量）
- 不可补偿动作 100% 执行前 MANUAL

## 7. Phases

| Phase | Scope |
|---|---|
| **A** | `execution_dag.py` + unit tests (no live AWS) |
| **B** | Wire compensation through proxy + shadow |
| **C** | Three chain fixtures + CI |
| **D** | ADR/maturity Progress |

## 8. Acceptance commands (target)

```bash
pytest -p no:rerunfailures scripts/tests/test_execution_dag.py -q
# plus chain fixtures once added
python3 scripts/te_gate.py --all --strict
```
