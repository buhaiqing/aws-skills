# Telemetry Dashboard — Implementation Plan (P2.3)

- **Date**: 2026-07-25
- **Spec**: `docs/superpowers/specs/2026-07-25-telemetry-dashboard-design.md`
- **Strategy**: TDD per AGENTS.md §13 CADL

## Tasks

- [x] NW6.1 Spec + Plan (this document)
- [ ] NW6.2 RED: `scripts/tests/test_telemetry_dashboard.py` (7 tests)
- [ ] NW6.3 GREEN: `scripts/telemetry_dashboard.py` (~300 行)
- [ ] NW6.4 Real run: dashboard against current `audit-results/`
- [ ] NW6.5 Mutation: simulate regression → alert exits 1
- [ ] NW6.6 AGENTS.md §17 (Telemetry Dashboard Protocol)
- [ ] NW6.7 maturity-model 65 → 75% + TODO NW6
- [ ] NW6.8 Generate `/tmp/aws-patches/p2-3.patch`

## Acceptance

1. 7 RED → GREEN
2. ruff 0 issue
3. `python3 scripts/telemetry_dashboard.py dashboard --out /tmp/dash.md` produces valid Markdown
4. `python3 scripts/telemetry_dashboard.py alert --drop-threshold 0.05` exit 0/1 随真实数据
