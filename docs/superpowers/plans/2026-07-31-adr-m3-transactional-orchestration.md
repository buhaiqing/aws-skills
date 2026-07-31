# Plan: ADR-0001 M3 Transactional Orchestration

**Spec:** [`../specs/2026-07-31-adr-m3-transactional-design.md`](../specs/2026-07-31-adr-m3-transactional-design.md)  
**ADR:** [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) §M3  
**Status:** ✅ C0–C4 DONE — M3 engineering closed; next = M4 Governed Learning

## Waves

- [x] **C0** Spec + Plan 落盘（本文）
- [x] **C1** `scripts/execution_dag.py` — nodes, edges, `dag_hash`, fail policy
- [x] **C2** Compensation path → `run_shadow` + `safe_tool_proxy` (reuse M2) — `scripts/compensation_runner.py`
- [x] **C3** Three chain fixtures (ELB / RDS+R53 / ECS+ELB) × success|node-fail|comp-fail — `scripts/chain_fixtures.py`
- [x] **C4** ADR §M3 Progress + maturity next=M4

## Acceptance

```bash
pytest -p no:rerunfailures scripts/tests/test_execution_dag.py \
  scripts/tests/test_compensation_runner.py scripts/tests/test_m3_chain_fixtures.py -q
python3 scripts/chain_fixtures.py run --all --shadow-root /tmp/m3-chains
python3 scripts/te_gate.py --all --strict
```

## Non-goals

- AUTO_HEAL expansion
- Bypass gates on compensation
- Live AWS in unit suite
