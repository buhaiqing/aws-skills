# Plan — Inference Latency SLA (aws-aiops-cruise)

Spec: `docs/superpowers/specs/2026-09-06-infer-latency-sla-design.md`
Branch: `feature/infer-latency-sla` (worktree `.worktrees/infer-latency-sla`)

Slices are vertical: each one is independently demoable end-to-end
(signal → rule → report → test).

| # | Slice | Blocked by | DoD | Verify |
|---|-------|-----------|-----|--------|
| 1 | **Percentile core** — `percentile_from_buckets()` + `extract_xray_latency_signals()`; wire `signals["XRay"]` through `audit_xray_service_graph()` → `patrol_region()` → `daily-health-check.py` | — | X-Ray histogram → `{p50,p95,p99,n,fault_rate}` in ms; `signals["XRay"]` non-empty on real graph | `pytest tests/test_inference.py -k Percentile or ExtractXray -q` |
| 2 | **SLA rule** — `infer_latency_p95_rule()` → `INFER-LAT-P95-01`, env `INFER_P95_SLA_MS` (default 1500 ms), CRITICAL at 1.5×, skip `n<10` | 1 | Incident emitted at/above SLA, level escalates at critical, env override honoured | `pytest tests/test_inference.py -k InferLatencyP95Rule -q` |
| 3 | **Report surface** — `build_inference_latency_table()` + `_report.py` section | 1, 2 | `## Inference Latency SLA` table with status column; omitted when no X-Ray signals | `pytest tests/test_inference.py -k BuildInferenceLatencyTable -q` |
| 4 | **Capacity decay** — `infer_p95_wow_change()` + `inference_p95_wow` in `capacity-planning.py` report | 1 | Endpoints with >30% WoW P95 drift listed; X-Ray failure → `WARN` + `[]`, run still exits 0 | `python3 capacity-planning.py --help` (import smoke) + slice-1/3 tests |

## Cross-slice gates

- `ruff check aws-aiops-cruise/runbooks/scripts` → 0 errors.
- `pytest aws-aiops-cruise/tests/ -q` → all green (was 126 at ship time).
- `pytest scripts/tests/ -q` → 426 green (repo pre-commit gate).
- No uncommitted files besides the slice under work; commit per slice.

## Status

| # | State | Commit |
|---|-------|--------|
| 1–3 | done | `d10ebda` |
| 4 | done | `c9a4882` |
| spec/plan | backfilled 2026-09-06 | `c9a4882` |
| branch → main | merged (HEAD = main HEAD) | `c9a4882` |
| worktree cleanup | `.worktrees/infer-latency-sla` removed | `2026-09-24` |

## Closure (2026-09-24)

- Branch `feature/infer-latency-sla` is at `c9a4882` = `main` HEAD → no merge action needed.
- Worktree removed; accidentally-staged `D aws-topo-discovery/references/gcl-rubric.md` restored in worktree before removal.
- Branch ref retained in repo for history (`git branch --list feature/infer-latency-sla` still resolves).
- `rsi-p0-loop` worktree remains active for the in-flight P0-4 stub-filter work.

## Known gaps

- Slice 4 has no unit test: `infer_p95_wow_change()` calls X-Ray twice and
  the current suite has no X-Ray mock for the two-window path. Best-effort
  wrapper in `capacity-planning.py` is covered indirectly by import smoke
  only. Add a mock when a second WoW consumer appears (YAGNI until then).
