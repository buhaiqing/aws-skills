from __future__ import annotations

import datetime as _dt
import json
import subprocess
import sys
import tempfile
import time
import uuid as _uuid
from pathlib import Path
from typing import Any

import pytest
import yaml

import gcl_runner
import parallel_gcl_runner as pgr
from parallel_gcl_runner import (
    _build_parallel_trace,
    _parallel_trace_path,
    _self_test,
    CommandTimeout,
    CompositeTaskSchema,
    run_parallel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_reflexion(tmp_path, monkeypatch):
    """Keep reflexion writes out of the real docs/failure-patterns.md.

    parallel_gcl_runner calls gcl_runner._run_loop in-process; any
    trust-boundary failure would otherwise append (and via _needs_fresh_init
    potentially rewrite) the real docs/failure-patterns.md.
    """
    monkeypatch.setattr(
        gcl_runner, "REFLEXION_PATTERNS_PATH", tmp_path / "failure-patterns.md",
    )


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def two_subtask_yaml(temp_dir):
    path = temp_dir / "task.yaml"
    path.write_text(
        yaml.dump({
            "task_id": "test-task",
            "request": "composite test",
            "subtasks": [
                {"skill": "aws-s3-ops", "request": "list buckets"},
                {"skill": "aws-ec2-ops", "request": "describe instances"},
            ],
        })
    )
    return path


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_schema_loads_valid_yaml(temp_dir):
    path = temp_dir / "task.yaml"
    path.write_text(yaml.dump({
        "task_id": "x",
        "request": "y",
        "subtasks": [{"skill": "aws-s3-ops", "request": "list buckets"}],
    }))
    data = CompositeTaskSchema.load(path)
    assert data["task_id"] == "x"
    assert len(data["subtasks"]) == 1


def test_schema_rejects_missing_task_id(temp_dir):
    path = temp_dir / "task.yaml"
    path.write_text(yaml.dump({"subtasks": []}))
    with pytest.raises(ValueError, match="task_id"):
        CompositeTaskSchema.load(path)


def test_schema_rejects_empty_subtasks(temp_dir):
    path = temp_dir / "task.yaml"
    path.write_text(yaml.dump({"task_id": "x", "subtasks": []}))
    with pytest.raises(ValueError, match="non-empty"):
        CompositeTaskSchema.load(path)


def test_schema_rejects_subtask_missing_skill(temp_dir):
    path = temp_dir / "task.yaml"
    path.write_text(yaml.dump({
        "task_id": "x",
        "subtasks": [{"request": "do it"}],
    }))
    with pytest.raises(ValueError, match="skill"):
        CompositeTaskSchema.load(path)


# ---------------------------------------------------------------------------
# Trace building
# ---------------------------------------------------------------------------

def test_build_parallel_trace_includes_all_fields(temp_dir):
    trace = _build_parallel_trace(
        task_id="t1",
        request="composite request",
        subtask_traces=[
            {"subtask_index": 0, "skill": "aws-s3-ops", "status": "PASS", "iter": 1},
            {"subtask_index": 1, "skill": "aws-ec2-ops", "status": "PASS", "iter": 1},
        ],
        final_status="PASS",
        plan_hash="abc123",
    )
    assert trace["task_id"] == "t1"
    assert trace["parallel"] is True
    assert trace["final"]["status"] == "PASS"
    assert len(trace["subtasks"]) == 2
    assert trace["plan_hash"] == "abc123"
    # request is sanitized (not stored verbatim)
    assert trace["request"].startswith("<request-sha256:")


def test_parallel_trace_path_unique():
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = _parallel_trace_path(Path(tmpdir), "t1")
        time.sleep(0.01)
        p2 = _parallel_trace_path(Path(tmpdir), "t1")
    assert p1 != p2
    assert p1.name.startswith("gcl-parallel-trace-")


# ---------------------------------------------------------------------------
# Aggregation — overall status
# ---------------------------------------------------------------------------

def test_aggregation_all_pass_is_pass(temp_dir):
    trace = _build_parallel_trace(
        task_id="x",
        request="",
        subtask_traces=[
            {"subtask_index": 0, "status": "PASS", "iter": 1},
            {"subtask_index": 1, "status": "PASS", "iter": 1},
        ],
        final_status="PASS",
    )
    assert trace["final"]["status"] == "PASS"


def test_aggregation_one_fail_is_safety_fail(temp_dir):
    trace = _build_parallel_trace(
        task_id="x",
        request="",
        subtask_traces=[
            {"subtask_index": 0, "status": "PASS", "iter": 1},
            {"subtask_index": 1, "status": "SAFETY_FAIL", "iter": 0},
        ],
        final_status="SAFETY_FAIL",
    )
    assert trace["final"]["status"] == "SAFETY_FAIL"


def test_aggregation_mixed_is_max_iter(temp_dir):
    trace = _build_parallel_trace(
        task_id="x",
        request="",
        subtask_traces=[
            {"subtask_index": 0, "status": "PASS", "iter": 1},
            {"subtask_index": 1, "status": "MAX_ITER", "iter": 2},
        ],
        final_status="MAX_ITER",
    )
    assert trace["final"]["status"] == "MAX_ITER"


# ---------------------------------------------------------------------------
# Mock generators — verify aggregation with injected callables
# ---------------------------------------------------------------------------

def test_aggregation_all_pass_via_run_parallel(temp_dir, monkeypatch):
    """run_parallel reports PASS when every subtask generator + critic pass."""
    pass_gen_count = [0]

    def counting_gen(ctx: dict[str, Any]) -> dict[str, Any]:
        pass_gen_count[0] += 1
        return {
            "command": "mock",
            "args": {},
            "exit_code": 0,
            "result_excerpt": '{"ok": true}',
            "safety_confirm_token": "",
        }

    def pass_critic(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "correctness": 1.0,
                "safety": 1.0,
                "idempotency": 1.0,
                "traceability": 1.0,
                "spec_compliance": 1.0,
            },
            "suggestions": [],
            "blocking": False,
        }

    task_yaml = temp_dir / "task.yaml"
    task_yaml.write_text(yaml.dump({
        "task_id": "agg-test",
        "request": "test aggregation",
        "subtasks": [
            {"skill": "aws-s3-ops", "request": "task 1"},
            {"skill": "aws-ec2-ops", "request": "task 2"},
        ],
    }))

    patched = pgr._make_patched_subtask_runner(
        {0: counting_gen, 1: counting_gen}, pass_critic
    )
    trace = run_parallel(task_yaml, temp_dir, _subtask_runner=patched, flaky_critic=False)

    assert trace["final"]["status"] == "PASS"
    assert pass_gen_count[0] == 2  # both generators ran


def test_aggregation_one_fail_via_run_parallel(temp_dir):
    """run_parallel reports SAFETY_FAIL when one subtask fails."""
    fail_trace = _build_parallel_trace(
        task_id="one-fail",
        request="",
        subtask_traces=[
            {
                "subtask_index": 0,
                "skill": "aws-s3-ops",
                "request": "<request-sha256:a>",
                "status": "PASS",
                "iter": 1,
                "output": {"ok": True},
                "reason": None,
                "generator_outputs": [],
                "critic_outputs": [],
            },
            {
                "subtask_index": 1,
                "skill": "aws-ec2-ops",
                "request": "<request-sha256:b>",
                "status": "SAFETY_FAIL",
                "iter": 0,
                "output": None,
                "reason": "trust boundary failure: command exceeded 60s",
                "generator_outputs": [],
                "critic_outputs": [],
            },
        ],
        final_status="SAFETY_FAIL",
    )

    statuses = [t["status"] for t in fail_trace["subtasks"]]
    if any(s == "SAFETY_FAIL" for s in statuses):
        result = "SAFETY_FAIL"
    elif all(s == "PASS" for s in statuses):
        result = "PASS"
    else:
        result = "MAX_ITER"

    assert result == "SAFETY_FAIL"


# ---------------------------------------------------------------------------
# Isolation — no shared state between generators
# ---------------------------------------------------------------------------

def test_generators_are_isolated_per_worker_ctx(temp_dir):
    """Each worker gets its own ctx dict — verify no trace/request cross-contamination."""
    ctx_snapshots: dict[int, dict[str, Any]] = {}

    def gen_a(ctx: dict[str, Any]) -> dict[str, Any]:
        ctx_snapshots[0] = dict(ctx)  # capture worker's local copy of ctx
        return {
            "command": "gen-a", "args": {}, "exit_code": 0,
            "result_excerpt": "a", "safety_confirm_token": "",
        }

    def gen_b(ctx: dict[str, Any]) -> dict[str, Any]:
        ctx_snapshots[1] = dict(ctx)
        return {
            "command": "gen-b", "args": {}, "exit_code": 0,
            "result_excerpt": "b", "safety_confirm_token": "",
        }

    def crit(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "correctness": 1.0, "safety": 1.0,
                "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
            },
            "suggestions": [],
            "blocking": False,
        }

    task_yaml = temp_dir / "task.yaml"
    task_yaml.write_text(yaml.dump({
        "task_id": "isolation-test",
        "request": "isolation check",
        "subtasks": [
            {"skill": "aws-s3-ops", "request": "task a"},
            {"skill": "aws-ec2-ops", "request": "task b"},
        ],
    }))

    patched = pgr._make_patched_subtask_runner({0: gen_a, 1: gen_b}, crit)
    trace = run_parallel(task_yaml, temp_dir, _subtask_runner=patched, flaky_critic=False)

    # Both tasks completed with PASS
    assert trace["final"]["status"] == "PASS"

    # Each generator got its own independent ctx (not a shared reference)
    assert 0 in ctx_snapshots and 1 in ctx_snapshots
    assert ctx_snapshots[0]["user"]["request"] == "task a"
    assert ctx_snapshots[1]["user"]["request"] == "task b"

    # Per-subtask trace outputs are distinct — no cross-contamination
    gen_outputs = {
        t["subtask_index"]: t.get("generator_outputs", [])
        for t in trace["subtasks"]
    }
    # subtask 0 ran gen-a, subtask 1 ran gen-b
    assert any("gen-a" in str(gen_outputs.get(0, [])) for _ in [1])
    assert any("gen-b" in str(gen_outputs.get(1, [])) for _ in [1])


# ---------------------------------------------------------------------------
# Parallel execution — timing check
# ---------------------------------------------------------------------------

def test_parallel_faster_than_serial(temp_dir):
    """With 4 workers and 4 tasks × 0.2s each, parallel should be < 0.5s."""
    DELAY = 0.2
    TASKS = 4
    WORKERS = 4
    SERIAL_EXPECTED = DELAY * TASKS  # 0.8s
    PARALLEL_BUDGET = 0.5

    def slow_gen(ctx: dict[str, Any]) -> dict[str, Any]:
        time.sleep(DELAY)
        return {
            "command": "slow", "args": {}, "exit_code": 0,
            "result_excerpt": "slow", "safety_confirm_token": "",
        }

    def crit(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "correctness": 1.0, "safety": 1.0,
                "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
            },
            "suggestions": [],
            "blocking": False,
        }

    task_yaml = temp_dir / "task.yaml"
    task_yaml.write_text(yaml.dump({
        "task_id": "timing-test",
        "request": "timing check",
        "subtasks": [{"skill": "aws-s3-ops", "request": f"task {i}"} for i in range(TASKS)],
    }))

    patched = pgr._make_patched_subtask_runner(
        {i: slow_gen for i in range(TASKS)}, crit
    )
    t0 = time.time()
    trace = run_parallel(task_yaml, temp_dir, _subtask_runner=patched, max_workers=WORKERS, flaky_critic=False)
    elapsed = time.time() - t0

    assert trace["final"]["status"] == "PASS"
    assert elapsed < PARALLEL_BUDGET, \
        f"parallel took {elapsed:.2f}s (expected < {PARALLEL_BUDGET}s; serial would be ~{SERIAL_EXPECTED}s)"
    # Sanity: serial would actually be slower
    assert elapsed < SERIAL_EXPECTED * 0.75


def test_max_workers_configurable(temp_dir):
    """max_workers=1 forces serial execution (still correct, just slower)."""
    DELAY = 0.1
    TASKS = 2

    def slow_gen(ctx: dict[str, Any]) -> dict[str, Any]:
        time.sleep(DELAY)
        return {
            "command": "slow", "args": {}, "exit_code": 0,
            "result_excerpt": "slow", "safety_confirm_token": "",
        }

    def crit(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "correctness": 1.0, "safety": 1.0,
                "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
            },
            "suggestions": [],
            "blocking": False,
        }

    task_yaml = temp_dir / "task.yaml"
    task_yaml.write_text(yaml.dump({
        "task_id": "max-workers-test",
        "request": "workers check",
        "subtasks": [{"skill": "aws-s3-ops", "request": f"task {i}"} for i in range(TASKS)],
    }))

    patched = pgr._make_patched_subtask_runner(
        {i: slow_gen for i in range(TASKS)}, crit
    )
    t0 = time.time()
    trace = run_parallel(task_yaml, temp_dir, _subtask_runner=patched, max_workers=1, flaky_critic=False)
    elapsed = time.time() - t0

    # With max_workers=1 and 2 tasks × 0.1s, should take ≥ 0.2s (serial)
    assert elapsed >= DELAY * TASKS * 0.8  # at least 80% of serial time
    assert trace["final"]["status"] == "PASS"


# ---------------------------------------------------------------------------
# Trace persistence
# ---------------------------------------------------------------------------

def test_trace_persisted_to_output_dir(temp_dir):
    """run_parallel writes the trace JSON to output_dir."""
    def gen(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "command": "mock", "args": {}, "exit_code": 0,
            "result_excerpt": "ok", "safety_confirm_token": "",
        }

    def crit(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "correctness": 1.0, "safety": 1.0,
                "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
            },
            "suggestions": [],
            "blocking": False,
        }

    task_yaml = temp_dir / "task.yaml"
    task_yaml.write_text(yaml.dump({
        "task_id": "persist-test",
        "request": "trace persistence",
        "subtasks": [{"skill": "aws-s3-ops", "request": "task"}],
    }))

    patched = pgr._make_patched_subtask_runner({0: gen}, crit)
    trace = run_parallel(task_yaml, temp_dir, _subtask_runner=patched, flaky_critic=False)

    # A parallel trace file should exist in temp_dir
    traces = list(temp_dir.glob("gcl-parallel-trace-*.json"))
    assert len(traces) == 1

    # And its content should match the returned trace
    loaded = json.loads(traces[0].read_text())
    assert loaded["task_id"] == "persist-test"
    assert loaded["parallel"] is True
    assert loaded["final"]["status"] == trace["final"]["status"]


# ---------------------------------------------------------------------------
# Self-test entry point
# ---------------------------------------------------------------------------

def test_self_test_runs_successfully(temp_dir, monkeypatch, capsys):
    """--self-test exits 0 and prints passing tests."""
    monkeypatch.chdir(temp_dir)
    rc = pgr._self_test()
    assert rc == 0
    captured = capsys.readouterr().out
    assert "PASS" in captured
    assert "All parallel GCL self-tests passed" in captured


def test_self_test_aggregation_all_pass():
    """_self_test's internal all-PASS aggregation check passes."""
    trace = _build_parallel_trace(
        task_id="x", request="",
        subtask_traces=[
            {"status": "PASS", "iter": 1},
            {"status": "PASS", "iter": 1},
        ],
        final_status="PASS",
    )
    assert trace["final"]["status"] == "PASS"


def test_self_test_aggregation_one_fail():
    """_self_test's internal one-FAIL aggregation returns SAFETY_FAIL."""
    trace = _build_parallel_trace(
        task_id="x", request="",
        subtask_traces=[
            {"status": "PASS", "iter": 1},
            {"status": "SAFETY_FAIL", "iter": 0},
        ],
        final_status="SAFETY_FAIL",
    )
    assert trace["final"]["status"] == "SAFETY_FAIL"


def test_self_test_passes_when_run_as_script():
    """RED test: subprocess --self-test MUST exit 0 even in script mode.

    This catches the module-identity bug where monkey-patching `_run_subtask_gcl`
    inside `_self_test` mutates a *different* module object than the one whose
    globals `run_parallel` reads.  In pytest, `import parallel_gcl_runner`
    resolves to the same object the test imports; in `python3 scripts/
    parallel_gcl_runner.py`, the script is loaded as `__main__` and a fresh
    `parallel_gcl_runner` module is created on `import` inside
    `_swap_subtask_runner`.  Only subprocess exercises the buggy path.
    """
    script_path = Path(__file__).resolve().parent.parent / "parallel_gcl_runner.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--self-test"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"--self-test exited {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "All parallel GCL self-tests passed" in result.stdout
    assert "isolation: per-worker ctx ... PASS" in result.stdout


def test_run_parallel_accepts_subtask_runner_kwarg():
    """RED test: run_parallel accepts `_subtask_runner` for DI.

    Without DI, the only way to inject a fake runner is monkey-patching the
    module-global `_run_subtask_gcl`, which fails in `python3 script.py`
    mode (two module objects).  DI is the surgical fix.
    """
    seen: list[int] = []

    def fake_runner(subtask_index, subtask, generator_cmd, critic_cmd, flaky_critic):
        seen.append(subtask_index)
        return {
            "subtask_index": subtask_index,
            "skill": subtask["skill"],
            "request": subtask["request"],
            "status": "PASS",
            "iter": 1,
            "output": {"stub": True},
            "reason": None,
            "generator_outputs": [],
            "critic_outputs": [],
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        task_yaml = Path(tmpdir) / "task.yaml"
        task_yaml.write_text(yaml.dump({
            "task_id": "di-test",
            "request": "x",
            "subtasks": [
                {"skill": "aws-s3-ops", "request": "a"},
                {"skill": "aws-ec2-ops", "request": "b"},
            ],
        }))
        _ = run_parallel(task_yaml, Path(tmpdir), _subtask_runner=fake_runner)
    assert sorted(seen) == [0, 1]


# ---------------------------------------------------------------------------
# §22 testability improvements
# ---------------------------------------------------------------------------

def test_parallel_trace_path_deterministic(temp_dir):
    """_parallel_trace_path produces deterministic filenames when clock/uuid are injected."""
    def fixed_clock():
        return _dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=_dt.timezone.utc)

    def fixed_uuid():
        return _uuid.UUID("00000000-0000-0000-0000-000000000000")
    path = _parallel_trace_path(
        Path(temp_dir),
        "my-task-id",
        clock=fixed_clock,
        uuid_factory=fixed_uuid,
    )
    expected_name = "gcl-parallel-trace-20260101-120000-my-task-id-00000000.json"
    assert path.name == expected_name
    assert path.parent == Path(temp_dir)


def test_parallel_trace_path_uniqueness_without_injection(temp_dir):
    """Without injection, two calls return different paths (uuid-based)."""
    p1 = _parallel_trace_path(Path(temp_dir), "t1")
    p2 = _parallel_trace_path(Path(temp_dir), "t1")
    assert p1 != p2


def test_build_parallel_trace_empty_subtasks():
    """empty subtask list → iter=0, status=PASS (boundary condition)."""
    trace = _build_parallel_trace(
        task_id="empty",
        request="",
        subtask_traces=[],
        final_status="PASS",
    )
    assert trace["final"]["iter"] == 0
    assert trace["final"]["status"] == "PASS"
    assert trace["subtasks"] == []


def test_run_parallel_dry_run_skips_persistence(temp_dir):
    """dry_run=True returns trace without writing to output_dir."""
    def gen(ctx):
        return {"command": "x", "args": {}, "exit_code": 0,
                "result_excerpt": "ok", "safety_confirm_token": ""}

    def crit(ctx):
        return {"scores": {"correctness": 1.0, "safety": 1.0,
                           "idempotency": 1.0, "traceability": 1.0,
                           "spec_compliance": 1.0},
                "suggestions": [], "blocking": False}

    task_yaml = temp_dir / "task.yaml"
    task_yaml.write_text(yaml.dump({
        "task_id": "dry-run-test",
        "request": "test dry_run",
        "subtasks": [{"skill": "aws-s3-ops", "request": "list buckets"}],
    }))

    patched = pgr._make_patched_subtask_runner({0: gen}, crit)
    trace = run_parallel(task_yaml, temp_dir, _subtask_runner=patched,
                         flaky_critic=False, dry_run=True)

    # Trace returned
    assert trace["task_id"] == "dry-run-test"
    # Nothing written
    assert list(temp_dir.glob("gcl-parallel-trace-*.json")) == []


def test_main_self_test_routes_correctly():
    """main(['--self-test']) exits 0 and prints passing tests."""
    rc = pgr.main(["--self-test"])
    assert rc == 0


def test_composite_task_schema_from_dict_valid():
    """from_dict validates and returns data without IO."""
    data = {
        "task_id": "x",
        "request": "y",
        "subtasks": [{"skill": "s3", "request": "list buckets"}],
    }
    result = CompositeTaskSchema.from_dict(data)
    assert result["task_id"] == "x"
    assert len(result["subtasks"]) == 1


def test_composite_task_schema_from_dict_rejects_missing_field():
    """from_dict raises ValueError on missing required field."""
    data = {"request": "y", "subtasks": []}
    with pytest.raises(ValueError, match="task_id"):
        CompositeTaskSchema.from_dict(data)


def test_composite_task_schema_from_dict_rejects_empty_subtasks():
    """from_dict raises ValueError on empty subtasks list."""
    data = {"task_id": "x", "request": "y", "subtasks": []}
    with pytest.raises(ValueError, match="non-empty"):
        CompositeTaskSchema.from_dict(data)


def test_composite_task_schema_load_is_from_dict_plus_yaml(temp_dir):
    """load() is a thin wrapper around from_dict() parsing YAML."""
    path = temp_dir / "task.yaml"
    path.write_text(yaml.dump({
        "task_id": "x",
        "request": "y",
        "subtasks": [{"skill": "s3", "request": "list"}],
    }))
    direct = CompositeTaskSchema.from_dict(yaml.safe_load(path.read_text()))
    loaded = CompositeTaskSchema.load(path)
    assert loaded == direct


def test_subtask_runner_sets_safety_fail_on_trust_boundary_error():
    """Exception in generator → status=SAFETY_FAIL, reason set."""
    def bad_gen(ctx):
        raise CommandTimeout("simulated timeout")

    def crit(ctx):
        return {"scores": {"correctness": 1.0, "safety": 1.0,
                           "idempotency": 1.0, "traceability": 1.0,
                           "spec_compliance": 1.0},
                "suggestions": [], "blocking": False}

    patched = pgr._make_patched_subtask_runner({0: bad_gen}, crit)
    result = patched(
        subtask_index=0,
        subtask={"skill": "aws-s3-ops", "request": "list buckets"},
        generator_cmd=None,
        critic_cmd=None,
        flaky_critic=False,
    )
    assert result["status"] == "SAFETY_FAIL"
    assert result["reason"] is not None
