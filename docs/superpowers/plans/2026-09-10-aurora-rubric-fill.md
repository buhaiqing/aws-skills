# Plan — `aws-aurora-ops` rubric fill (+ generator CLI-namespace defect)

Spec: `docs/superpowers/specs/2026-09-10-aurora-rubric-fill-design.md`
Branch: `main` (working tree; no worktree — single-file artifact change)

| # | Slice | Blocked by | DoD | Verify |
|---|-------|-----------|-----|--------|
| 1 | **Namespace map** — add `aws-aurora-ops → rds` to `_gen_rubric._aws_cli_svc()` overrides and to `_sync_prompt_skeletons.CLI_OVERRIDES`, and repoint the stale `mirrors scripts/gcl_runner.py` comment (`_sync_prompt_skeletons.py:42` — `_gen_rubric.py` is where that map actually lives; `gcl_runner.py` has none) | — | `_aws_cli_svc("aws-aurora-ops") == "rds"` in both scripts | `python3 -c "..."` prints `rds` |
| 2 | **Regenerate** — `python3 scripts/_gen_rubric.py aws-aurora-ops "Amazon Aurora" --llm-fill` | 1 | Template written; Traceability row reads `aws rds <op>`; stderr records the LLM-fill skip | `git diff --stat aws-aurora-ops/references/rubric.md` |
| 3 | **Fill** — replace both `LLM_FILL`/`TODO` markers with the ops × dims table and the auto-fail list; add changelog row | 2 | No `LLM_FILL`/`TODO` marker anywhere in the file; every A-rule the SKILL.md Quality Gate names (A14, A7, A8, A9, A10) is cited by id | `grep -n 'LLM_FILL\|TODO' aws-aurora-ops/references/rubric.md` → empty |
| 4 | **Prompt metadata** — `{{skill.aws_cli_svc}}` `aurora` → `rds` | 1 | Row matches `_sync_prompt_skeletons.CLI_OVERRIDES` output | idempotent re-read of the row |
| 5 | **Regression test** — `scripts/tests/test_rubric_completeness.py`: every `aws-*-ops/references/rubric.md` carries the 5 §3 dimensions and zero fill markers; generator emits `aws rds` for aurora | 3 | Red before slice 3 (marker present), green after | `pytest scripts/tests/test_rubric_completeness.py -q` |
| 6 | **GCL loop** — Generator (agent edits) → blind Critic (isolated subagent, no user request) → §5 verdict; persist §6 trace | 3, 4 | `PASS` or an explicit `MAX_ITER` with residual items listed; trace in `audit-results/` | trace JSON `final.status` |

## Cross-slice gates

- `pytest scripts/tests/ -q` → green (repo pre-commit gate).
- `python3 scripts/gcl_runner.py --skill aws-aurora-ops --print-critic` → non-empty render.
- `python3 scripts/links_lint.py` → no new broken links (repo gate).
- No commit: the change is handed over as a working-tree diff.

## Status

| # | State | Evidence |
|---|-------|----------|
| 1 | done | `_aws_cli_svc("aws-aurora-ops") == "rds"` in both scripts |
| 2 | done | generator recorded `WARNING: LLM fill returned empty (check API key)`; Traceability row now `aws rds <op>` |
| 3 | done | 121-line rubric, 0 fill markers; AIOps delegate row added in round 2 |
| 4 | done | `--dry-run --skill aws-aurora-ops` reproduces the metadata block |
| 5 | done | 85/85 green; red against HEAD (verified by restoring the HEAD rubric) |
| 6 | done (2 Critic rounds) | round 1 → 6 applied fixes, 1 rejected with evidence; round 2 verdict in the closing report |
| 7 | done (round 2) | `--force` guard + test; Global DB preconditions corrected; Confirmation Strings completed |
