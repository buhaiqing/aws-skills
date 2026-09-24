# P0-2 CLI Resilience — `report --dwell-stats` handles missing queue

> Spec. Date: 2026-09-24. Branch: `feature/p0-2-cli`.
> Motivation: P0-2 (commit `094ca79`) ships `dwell_stats()` + `report --dwell-stats` CLI, but the CLI crashes with `FileNotFoundError` when the queue file is absent (the queue lives in gitignored `audit-results/governed-learning/`, which doesn't exist on a fresh checkout or in CI before the first `harvest` run). The CLI is the only observable surface for the "168h dwell really accumulates" claim — when it crashes, the auto-promotion gate is invisible to operators.

## 1. Problem (disk-verified)

```
$ python3 scripts/governed_learning.py report --dwell-stats
FileNotFoundError: [Errno 2] No such file or directory:
  '/Users/.../audit-results/governed-learning/queue.json'
  at scripts/governed_learning.py:977 in main
```

The default queue path is `audit-results/governed-learning/queue.json` (governed_learning.py:30). On a clean checkout that directory doesn't exist, and the user (or `make ci`) never runs `harvest` first. The CLI surfaces the raw traceback instead of an empty-state response.

## 2. Goal / Non-goals

**Goal**
- G1: `report --dwell-stats` (and `report` without `--dwell-stats`) return an empty-state JSON when queue file is absent — no traceback.
- G2: When queue file is absent, the response makes the empty state explicit (`"pending": 0`, `"histogram": {}`, `"note": "no candidates; run 'harvest' first"`).
- G3: Existing behavior preserved when queue file is present (regression suite green).

**Non-goals**
- Not auto-triggering `harvest` from `report` (separate concern; would mask whether harvesting was ever run).
- Not changing the queue file location (the gitignored path is the canonical design).
- Not adding a new subcommand — keep the existing `report --dwell-stats` API.

## 3. Contract

- **C1** (scope): only modify `scripts/governed_learning.py` (`main()` `report` branch) + `scripts/tests/test_governed_learning.py`. No other files.
- **C2** (regression): the 56 existing `test_governed_learning.py` cases must remain green; their fixtures write a queue file explicitly, so they exercise the "queue present" path.
- **C3** (idempotent): the empty-state output is a fixed shape — operators / dashboards can rely on the schema whether the queue is empty or populated.

## 4. Implementation

In `main()` `report` branch (around line 977):

```python
if args.cmd == "report":
    qpath = Path(args.queue)
    if not qpath.exists():
        # Empty-state response (queue not yet produced by `harvest`).
        # Return exit 0 — absence of data is a legitimate state, not an error.
        # Keys mirror `dwell_stats()` populated output (lines 785-798) so
        # downstream consumers (dashboards, CI scripts) can read a fixed
        # schema whether the queue is empty or populated (C3).
        empty = {
            "generated_at": _now(),
            "pending_total": 0,
            "age_histogram_hours": {},
            "blocked_by_gate": {},
            "dwell_blocked_count": 0,
            "terminal_gate_ids": sorted(TERMINAL_GATES),
            "terminal_blocked_count": 0,
            "min_dwell_hours": MIN_DWELL_HOURS,
            "note": f"queue not found at {qpath}; run 'harvest' first",
        }
        print(json.dumps(empty, indent=2, ensure_ascii=False))
        return 0
    meta = json.loads(qpath.read_text(encoding="utf-8"))
    ...
```

Return code 0 (success, not an error — the absence of data is a legitimate state).

## 5. Verification

- Gate 1: `python3 scripts/governed_learning.py report --dwell-stats` on fresh checkout → empty-state JSON, exit 0.
- Gate 2: same command after `python3 scripts/governed_learning.py harvest` → populated JSON, exit 0.
- Gate 3: `pytest scripts/tests/test_governed_learning.py -q` → 56 + 2 new = 58 passed.
- Gate 4: `ruff check scripts/governed_learning.py` → 0 error.

## 6. Tests

Two new RED tests in `test_governed_learning.py`:

1. `test_report_dwell_stats_handles_missing_queue_file` — invoke `main(["report", "--dwell-stats", "--queue", str(tmp_path/"missing.json")])`, assert exit 0 + `note` key in JSON output.
2. `test_report_default_handles_missing_queue_file` — same but without `--dwell-stats` (the plain `report` path also crashes today).

Both must fail before the fix and pass after.