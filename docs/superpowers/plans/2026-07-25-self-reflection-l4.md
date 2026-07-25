# Self-Reflection Protocol — Implementation Plan (P3.4)

- **Date**: 2026-07-25
- **Spec**: `docs/superpowers/specs/2026-07-25-self-reflection-l4-design.md`
- **Strategy**: TDD per AGENTS.md §13 CADL, 8 tests (RED → GREEN verified)

## Tasks

- [x] NW10.1 Spec + Plan (this document)
- [x] NW10.2 RED: `scripts/tests/test_self_review.py` (8 tests, FAIL with ModuleNotFoundError)
- [x] NW10.3 GREEN: `scripts/self_review.py` (~210 行, 8/8 pass)
- [x] NW10.4 Codify 4 real findings (F-001 ~ F-004) in `docs/superpowers/findings/`
- [x] NW10.5 CLI e2e: list / verify / report all green; verify → stale_p0=0
- [x] NW10.6 AGENTS.md §21 Self-Reflection Protocol
- [x] NW10.7 Real e2e + regression: full suite 98 passed (was 90 + 8 new)
- [x] NW10.8 ruff clean
- [ ] NW10.9 Generate `/tmp/aws-patches/p3-4.patch`
