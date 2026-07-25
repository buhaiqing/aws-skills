# Eval-Driven Dev — Implementation Plan (P2.2)

- **Date**: 2026-07-25
- **Spec**: `docs/superpowers/specs/2026-07-25-eval-driven-dev-design.md`
- **Strategy**: TDD (RED first per AGENTS.md §13 CADL)

## Tasks

- [x] NW5.1 Spec + Plan (this document)
- [ ] NW5.2 RED: `scripts/tests/test_golden_eval.py` (7 tests, verify fail)
- [ ] NW5.3 GREEN: `scripts/golden_eval.py` min implementation
- [ ] NW5.4 Sample fixture: `aws-ec2-ops/golden-scenarios.yaml` (≥5 scenarios)
- [ ] NW5.5 End-to-end: run on real aws-ec2-ops, all scenarios PASS
- [ ] NW5.6 e2e mutation test: introduce a deliberate fail, verify regression detected
- [ ] NW5.7 AGENTS.md §16 ("Eval-Driven Dev Protocol")
- [ ] NW5.8 REFACTOR (ruff) + Self-Reflection R1+R2
- [ ] NW5.9 Update maturity-model.md L4 55% → 65%; TODO.md
- [ ] NW5.10 Generate `/tmp/aws-patches/p2-2.patch`

## Acceptance criteria

1. `python3 -c "from golden_eval import load_scenarios, run_scenario, compare_to_baseline"` ✓
2. 7 RED tests pass GREEN
3. `ruff check` 0 issue on new files
4. CLI: `python3 scripts/golden_eval.py run --skill X --scenarios Y --out Z` → JSON file with valid `ScenarioResult` list
5. CLI: `python3 scripts/golden_eval.py diff --current C --baseline B` → Markdown regression report, exit 1 if regression detected
6. Mutation test: change a scenario's `expected_status` → diff should flag it as regression
7. AGENTS.md §16 ≥ 50 lines with decision tree + protocol
