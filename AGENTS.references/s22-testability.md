# §22 — Testability Discipline

> 见 [AGENTS.md §22](../AGENTS.md) 索引

## §22.0 TDD 是开发规范（hard rule）

For any non-trivial change to a core function — and core means any
function that anchors the spec (GCL loop, parallel runner, schema
loader, trace builder, safety gates, CLI entry) — the workflow is:

1. **Red**: write the failing test FIRST.  The test must exercise
   the actual failure path you observed, not a unit branch.
2. **Green**: minimal change to make it pass.
3. **Refactor**: clean up without breaking the test.

Do not skip step 1 by reasoning about why the bug "should" be
fixed.  The test pins the regression so future changes cannot
reintroduce it.  A fix without a test is a fix that will rot.

A "branch is covered" is NOT a test.  A test pins an observable
contract: return value, side effect, persisted artifact, exit
code.  If you cannot phrase the regression as "given X input,
the system does Y", you have not written a test — you have
written a probe.

## §22.1 核心功能必须有专门测试（hard rule）

For each core function (§22.0), the test file MUST contain at
least one test that:

1. Sets up the canonical pre-condition from the spec.
2. Drives the function through the success path end-to-end.
3. Asserts the observable contract (return value, side effect,
   trace).
4. Has a counterpart that drives the failure path and asserts
   the termination status matches the spec's §5 rule.

If a PR changes a core function and the corresponding test does
not change, the PR MUST add or update a test in the same diff.
No "covered by existing test" without re-running that test and
showing it exercises the new code path.

A test that uses `assert 1 + 1 == 2` does not satisfy this rule.
The test must reference the function under test by name and
exercise at least one path the function takes in production.

## §22.2 Subprocess + import both required for CLI scripts

For any script with both `python3 scripts/<name>.py --self-test`
and `pytest scripts/tests/test_<name>.py`:

- pytest exercises the module-import path: `import <name>`
  resolves to the SAME module object the test imports.
- `python3 scripts/<name>.py` runs the file as `__main__`, and any
  internal `import <name>` creates a SECOND module object.

Tests that only exercise the import path hide bugs that only fire
in the script path.  Every CLI script with `--self-test` MUST
have a subprocess test:

```python
def test_self_test_passes_when_run_as_script():
    script_path = Path(__file__).resolve().parent.parent / "<name>.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--self-test"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"--self-test exited {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
```

This catches the 2026-08-25 parallel-gcl-runner bug where
monkey-patching module globals silently failed in script mode.

## §22.3 禁止 module-global monkey-patch（hard rule）

Production code MUST NOT rely on `module.attr = patched_fn` to
inject test doubles.  This pattern fails silently in
`python3 script.py` mode because the script loads as `__main__`
while the patched module is a second object the `import` inside
the test helper creates.

Use **dependency injection** instead:

```python
def runner(..., _subtask_runner=None):     # kwarg-injected
    run = _subtask_runner or _run_subtask_gcl
    ...
```

Or pass the test double as a callable parameter.  Forbidden:

- `pgr._run_subtask_gcl = stub` (any `module.fn = stub`)
- `import X; X.fn = stub`
- `global _original_fn; _original_fn = ...`

These leave module state dirty across tests in a single process.
`--self-test` runs N cases in one Python invocation; a patched
stub leaks into the next case.

## §22.4 模块顶层 import 是规范（hard rule）

`from foo import bar` inside a function body is forbidden for any
import the function depends on in normal operation.  Imports MUST
appear at the top of the module.

Why: in-function imports hide coupling.  Tests cannot stub the
imported name without patching the source module.  Top-level
imports let `monkeypatch.setattr(target_module, 'name', stub)`
work uniformly across all test runners.

Exception: imports that are legitimately optional and absent in
some environments (e.g. `from typing import Annotated` on
Python <3.9) MAY live inside a function.  Document the exception
inline.

## §22.5 时间 / 随机性 / IO 必须可注入（hard rule）

Functions that call `datetime.now()`, `uuid.uuid4()`, `time.sleep()`,
`subprocess.run()`, or open files MUST accept injectable parameters
for those operations:

```python
def _parallel_trace_path(
    output_dir: Path, task_id: str,
    *, clock: Callable[[], datetime] = _dt.datetime.now,
    uuid_factory: Callable[[], uuid.UUID] = uuid.uuid4,
) -> Path:
    ...
```

Tests pass `clock=lambda: datetime(2026,1,1,...)` and
`uuid_factory=lambda: uuid.UUID('00000000-0000-...')` to get
deterministic outputs.  Production callers use defaults.

Functions that write to disk MUST accept a `dry_run` flag that
returns the would-be-written content without touching the
filesystem.  This lets tests assert content shape without tmpdir
boilerplate.

## §22.6 Schema loader 必须有 in-memory 入口（hard rule）

A `XSchema.load(path)` MUST also expose `XSchema.from_dict(data)`.
The path variant is a thin wrapper:

```python
@classmethod
def load(cls, path: Path) -> dict[str, Any]:
    return cls.from_dict(yaml.safe_load(path.read_text()))

@classmethod
def from_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
    # validation only — no IO
    ...
```

Why: tests of `load()` end up writing tmpfiles and parsing YAML
to test validation logic.  Tests of `from_dict()` exercise the
validation directly.  A test that writes YAML to a tmpdir to
test "missing field raises ValueError" is testing the wrong
thing.

## §22.7 --self-test 各 case 必须相互隔离（hard rule）

`--self-test` runs N cases in one process.  Each case MUST NOT
mutate module state visible to the next.  Forbidden in test code:

- `module.attr = X` (covered by §22.3)
- `os.environ[...] = X` without `try/finally: restore`
- File / process / socket lifetime > one test case
- Generator / critic callables defined at module scope (each
  case MUST define its own; never share)

Each case wraps its setup in `try/finally` covering all side
effects introduced at entry.  When DI (§22.3) is used, this
becomes a non-issue — DI is the structural fix.

## §22.8 异常处理必须显式设 status（hard rule）

Any function that catches an exception and falls back to a
"safe" return value MUST set ALL status fields explicitly.  A
`try/except` that sets `reason` but leaves `status` to its
default silent failure is a bug.  Tests must cover the
exception path:

```python
def test_subtask_runner_sets_safety_fail_on_timeout():
    def hanging_gen(ctx):
        raise CommandTimeout("simulated")
    patched = _make_patched_subtask_runner({0: hanging_gen}, crit)
    result = patched(0, {"skill": "x", "request": "y"}, None, None, False)
    assert result["status"] == "SAFETY_FAIL"
    assert result["reason"] is not None
```

## §22.9 Debug print 必须在 diff 中消失（hard rule）

Any `print(f"DEBUG ...", flush=True)` added during debugging
MUST be removed in the SAME diff that fixes the bug.  CI greps
for the literal `DEBUG ` (case-sensitive, 1+ space after) in
`scripts/*.py` and fails the commit if found outside of
`scripts/tests/`.

## §22.10 编辑手术的最小动作单元（hard rule）

Forbidden edit patterns (each caused real damage in the 2026-08
sessions):

- `sed -i` for multi-line replacement (loses signature / global
  declarations)
- `str.replace()` for non-idempotent edits (lost a function
  signature when the pattern matched twice)
- Single-line `PUT N.=M` that crosses function boundaries
- `write` overwrites a file you have not fully `read` in this
  session

Required:

- Re-`read` the section before every edit; the tag is fresh or
  the edit is rejected.
- Multi-line changes → `PUT N*` (whole block) or rewrite the
  whole file.  When the file has been damaged by 3+ prior bad
  edits, do NOT keep patching — `read` the whole file, `write`
  it whole.
- Add new helpers as new functions, never inline-monkey-patch
  globals.
- When in doubt, prefer the larger diff over the smaller one;
  small diffs to broken files produce broken files.