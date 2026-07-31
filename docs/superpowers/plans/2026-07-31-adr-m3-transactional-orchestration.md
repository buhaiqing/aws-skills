# Plan: ADR-0001 M3 Transactional Orchestration

**Spec:** [`../specs/2026-07-31-adr-m3-transactional-design.md`](../specs/2026-07-31-adr-m3-transactional-design.md)  
**ADR:** [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) §M3  
**Status:** 📋 C0 SPEC/PLAN LANDED — **等待确认后再写 C1–C4 代码**

## Waves

- [x] **C0** Spec + Plan 落盘（本文）
- [ ] **C1** `scripts/execution_dag.py` — nodes, edges, `dag_hash`, fail policy
- [ ] **C2** Compensation path → `run_shadow` + `safe_tool_proxy` (reuse M2)
- [ ] **C3** Three chain fixtures (ELB / RDS+R53 / ECS+ELB) × success|node-fail|comp-fail
- [ ] **C4** ADR §M3 Progress + maturity next=M4

## Non-goals

- AUTO_HEAL expansion
- Bypass gates on compensation
- Live AWS in unit suite

## Acceptance

```bash
pytest -p no:rerunfailures scripts/tests/test_execution_dag.py -q
# chain tests once present
python3 scripts/te_gate.py --all --strict
```
