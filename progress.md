# Progress

## Status
Completed

## Sprint B — P0-B Lessons 归档 (2026-08-25)

**Goal**: Structure散落在 maturity changelog v16-v24 的 28 条 lessons，建立可导航的索引 + 统一的 Problem/Lesson/Evidence 格式。

**Deliverable**: `docs/superpowers/learnings.md` (restructured with index table + 28 lessons in Problem/Lesson/Evidence format, ~450 lines)

**Evidence**:
- Index table: 28 lessons across 4 categories (TE Gate, Process, P0-B)
- All 28 lessons expanded from bullet list to Problem/Lesson/Evidence format
- Key patterns: batch by security domain (L27), service-specific hard gates (L28), TDD step size (L6)
- Changelog v16-v24 lessons captured; no orphan references

**Validation** (2026-08-25):
- pytest 343/343 ✅
- ruff: E501 ignores apply (docs file)
- status_snapshot: ALL GREEN ✅
