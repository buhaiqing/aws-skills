# Plan: ADR-0001 M2 Shadow Execution

**Spec:** [`../specs/2026-07-31-adr-m2-shadow-execution-design.md`](../specs/2026-07-31-adr-m2-shadow-execution-design.md)  
**ADR:** [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) §M2

## Status

- [x] **W0** Spec + Plan 落盘（本文 + design）
- [x] **W1** `scripts/execution_plan.py` + tests
- [x] **W2** `scripts/shadow_exec.py` + redaction + audit persist + tests
- [x] **W3** `build_plan_bound_token` + `safe_tool_proxy` hard gate
- [x] **W4** High-risk destructive shadow coverage + CI
- [x] **W5** ADR M2 Progress + maturity §6.3/§8

## W1 — ExecutionPlan

- [x] Add `scripts/execution_plan.py`: dataclass, `compute_plan_hash`, `assert_plan_matches_call`
- [x] Tests: hash stability; drift on region / resource_ids / operation → fail
- [x] `codegraph sync .` before edit; explore callers of `build_confirmation_token` before changing tokens

## W2 — Shadow executor

- [x] Add `scripts/shadow_exec.py`: strategies dry-run | describe | simulate
- [x] Persist `audit-results/shadow/*.json` (gitignored); A9 redaction
- [x] Tests with mocks only (no live AWS in unit suite)

## W3 — Proxy gate

- [x] Add `build_plan_bound_token(call, plan_hash)` in `runtime_safety.py` (keep old token helper)
- [x] `safe_tool_proxy`: destructive → require `plan_hash` + ShadowEvidence file + matching plan-bound `safety_confirm`
- [x] Missing/mismatched → `decision=BLOCK`, `executed=False`
- [x] Extend `test_safe_tool_proxy.py` / `test_runtime_safety.py`

## W4 — Eval + CI

- [x] For high-risk **destructive** scenarios: generate plan + shadow in test harness (or `--require-shadow` path)
- [x] Drift / false-block fixtures documented
- [x] Extend `.github/workflows/golden-high-risk.yml` or add `shadow.yml` for new unit tests
- [x] Keep `--all-high-risk` 58/58 green (no GCL confirm= breakage)

## W5 — Docs

- [x] ADR §M2 Progress: DONE / STILL OPEN
- [x] `docs/agentic-maturity-model.md`: M2 🔧→✅ when W4 green; next = M3
- [x] Optional one-line in AGENTS.md design docs

## Acceptance

```bash
pytest -p no:rerunfailures scripts/tests/test_execution_plan.py \
  scripts/tests/test_shadow_exec.py scripts/tests/test_safe_tool_proxy.py \
  scripts/tests/test_shadow_coverage.py -q
python3 scripts/shadow_coverage.py check --all-high-risk --shadow-dir /tmp/shadow-m2
python3 scripts/golden_eval.py run --all-high-risk --out audit-results/golden/high-risk.json
python3 scripts/te_gate.py --all --strict
```

## Explicit non-goals

- M3 compensation execution
- AUTO_HEAL expansion
- Shadow all 45 skills in this milestone
