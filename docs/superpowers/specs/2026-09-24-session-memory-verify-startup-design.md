# Session Memory `verify-startup` — make missing/empty state observable

> Spec. Date: 2026-09-24. Branch: `feature/smem-verify-startup`.
> Motivation: RSI audit (2026-09-24) found `scripts/session_memory.py verify-startup` returns exit code 1 (or 2 with `--required`) on every non-current memory condition but prints NOTHING to stdout. The agent gets a silent failure and assumes memory is OK. Disk evidence: `.omc/conventions.json` has `records: []`; `verify-startup` exits 1 with empty stdout; `memory-eval` later returns `"error": "no records"`. Mechanism is empty-running.

## 1. Problem (disk-verified)

```bash
$ rm -f .omc/conventions.json && python3 scripts/session_memory.py verify-startup
$ echo "exit=$?"
exit=1
# stdout: EMPTY — agent has no signal that memory is absent

$ echo '{"version":"1.0.0","records":[]}' > .omc/conventions.json
$ python3 scripts/session_memory.py verify-startup
$ echo "exit=$?"
exit=1
# stdout: EMPTY — same silent fail with empty file

$ python3 scripts/session_memory.py memory-eval
{"error": "no records in /Users/.../omc/conventions.json"}
# memory-eval IS observable; verify-startup is not.
```

Three failure modes all silent:
1. **File missing** (`p.exists() == False`)
2. **File exists but empty** (`records == []`)
3. **Records exist but none from current session** (loop falls through)

`--required` mode is the only path that exits 2 (still silent).

## 2. Goal / Non-goals

**Goal**
- G1: Every non-zero return emits a single-line stderr message that explains what is wrong and how to fix it (the path + the action).
- G2: Exit codes preserved (1 for non-required failure, 2 for required-missing).
- G3: The 4 pre-existing tests (`test_verify_startup_*`) keep passing with no semantic change.

**Non-goals**
- Not changing the semantics of `memory-eval` (it already prints a structured error).
- Not adding a new mode flag — keep the existing CLI.
- Not adding automatic memory seeding (separate concern; would mask whether seeding was ever run).

## 3. Contract

- **C1** (scope): only modify `scripts/session_memory.py::main` `verify-startup` branch + `scripts/tests/test_session_memory.py` (add 3 RED tests).
- **C2** (no breaking change): existing 4 tests pass unchanged; their assertions on exit code remain valid.
- **C3** (stderr vs stdout): error messages go to stderr (so they don't pollute `render` / `query` stdout streams). Successful match (exit 0) keeps silent stdout (caller didn't ask for a verdict).

## 4. Implementation

In `main()` `verify-startup` branch (around line 315-318):

```python
if args.cmd == "verify-startup":
    p = Path(args.path)
    current_session = os.environ.get("OMC_SESSION_ID", "")
    if not current_session:
        last_session_file = Path(".omc/.last_session")
        if last_session_file.exists():
            current_session = last_session_file.read_text().strip()
    if not p.exists():
        msg = (f"memory file not found at {p}; "
               f"run 'session_memory.py record --scope ... --summary ...' to seed")
        print(msg, file=sys.stderr)
        if args.required:
            return 2
        return 1
    records = load_memory(p)
    if not records:
        print(f"memory file at {p} is empty (0 records); "
              f"run 'session_memory.py record' to seed", file=sys.stderr)
        return 1
    for rec in records:
        if rec.source_session == current_session:
            return 0
    print(f"memory file at {p} has {len(records)} {'record' if len(records) == 1 else 'records'} but none from "
          f"current session ({current_session or 'unset'}); stale; "
          f"run 'session_memory.py record' to refresh", file=sys.stderr)
    return 1
```

Exit codes unchanged: 0 (match) / 1 (non-required failure) / 2 (`--required` and missing).

## 5. Verification

- Gate 1: `python3 scripts/session_memory.py verify-startup` on missing file → exit 1 + stderr "memory file not found at ...; run 'session_memory.py record ...' to seed".
- Gate 2: same on empty file → exit 1 + stderr "memory file at ... is empty (0 records); ...".
- Gate 3: same on stale records → exit 1 + stderr "memory file at ... has N records but none from current session (unset); ...".
- Gate 4: `--required` on missing → exit 2 + stderr.
- Gate 5: 4 existing tests + 3 new = 7 passed; ruff clean.

## 6. Tests

Three new RED tests in `scripts/tests/test_session_memory.py`:

1. `test_verify_startup_missing_file_prints_to_stderr` — missing file → exit 1, stderr contains "memory file not found".
2. `test_verify_startup_empty_records_prints_to_stderr` — empty file → exit 1, stderr contains "is empty".
3. `test_verify_startup_stale_records_prints_to_stderr` — records exist but none from current session → exit 1, stderr contains "stale".

Each must fail before the fix and pass after.