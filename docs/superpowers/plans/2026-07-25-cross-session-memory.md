# Cross-Session Memory — Implementation Plan (P3.1)

- **Date**: 2026-07-25
- **Spec**: `docs/superpowers/specs/2026-07-25-cross-session-memory-design.md`
- **Strategy**: TDD per AGENTS.md §13 CADL

## Tasks

- [x] NW8.1 Spec + Plan (this document)
- [ ] NW8.2 RED: `scripts/tests/test_session_memory.py` (7 tests)
- [ ] NW8.3 GREEN: `scripts/session_memory.py` (~250 行)
- [ ] NW8.4 Real e2e: CLI record + query + render round-trip
- [ ] NW8.5 Seed `.omc/conventions.json` with 3 initial entries
- [ ] NW8.6 AGENTS.md §19
- [ ] NW8.7 maturity-model 80 → 90% + TODO NW8
- [ ] NW8.8 Generate `/tmp/aws-patches/p3-1.patch`

## Acceptance

1. 7 RED → GREEN
2. ruff 0 issue
3. CLI `record` + `query` + `render` all green
4. seeded `.omc/conventions.json` retrievable via query
