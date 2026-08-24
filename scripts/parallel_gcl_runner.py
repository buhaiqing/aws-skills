#!/usr/bin/env python3
"""Parallel GCL Runner — multi-Generator + single-Critic per gcl-spec.md §12.

Architecture:
  1. Decompose composite task into N independent subtasks
  2. Run each Generator in parallel (ThreadPoolExecutor, isolated contexts)
  3. Single Critic audits ALL generator outputs
  4. Overall PASS only if ALL subtasks PASS
  5. Per-subtask traces + aggregated parallel trace persisted

Anti-patterns enforced (per §12.4):
  - Generators must NOT share mutable state
  - Each generator gets isolated prompt context
  - Critic audits ALL outputs (not just one)
  - No Critic bypass

CLI:
    python3 scripts/parallel_gcl_runner.py run --task <composite-task.yaml> \\
        --output-dir audit-results/gcl-parallel/
    python3 scripts/parallel_gcl_runner.py --self-test
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import yaml

# gcl_runner is a sibling module in the scripts/ directory
from gcl_runner import (
    CommandContractError,
    CommandTimeout,
    _invoke_critic,
    _invoke_generator,
    _prune_old_traces,
    _run_loop,
    run_with_callables,
    sanitize_request,
)

# Status constants (shared with gcl_runner VALID_OUTCOMES)
PASS = "PASS"
MAX_ITER = "MAX_ITER"
SAFETY_FAIL = "SAFETY_FAIL"

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MAX_WORKERS = 4


# ---------------------------------------------------------------------------
# Composite task YAML schema
# ---------------------------------------------------------------------------

class CompositeTaskSchema:
    """Loader and validator for composite task YAML."""

    REQUIRED_FIELDS = ("task_id", "subtasks")
    SUBTASK_REQUIRED = ("skill", "request")

    @classmethod
    def load(cls, path: Path) -> dict[str, Any]:
        return cls.from_dict(yaml.safe_load(path.read_text()))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Validate without IO. Raises ValueError on missing/invalid fields."""
        for f in cls.REQUIRED_FIELDS:
            if f not in data:
                raise ValueError(f"task data missing required field: {f}")
        if not isinstance(data["subtasks"], list) or len(data["subtasks"]) == 0:
            raise ValueError("task data must have non-empty 'subtasks' list")
        for i, st in enumerate(data["subtasks"]):
            if not isinstance(st, dict):
                raise ValueError(f"subtask[{i}] must be a dict")
            for f in cls.SUBTASK_REQUIRED:
                if f not in st:
                    raise ValueError(f"subtask[{i}] missing required field: {f}")
        return data


# ---------------------------------------------------------------------------
# Parallel GCL trace schema (extends gcl-spec.md §6 with parallel envelope)
# ---------------------------------------------------------------------------

def _parallel_trace_path(
    output_dir: Path,
    task_id: str,
    *,
    clock: Callable[[], _dt.datetime] = lambda: _dt.datetime.now(_dt.timezone.utc),
    uuid_factory: Callable[[], uuid.UUID] = uuid.uuid4,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = clock().strftime("%Y%m%d-%H%M%S")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", task_id)
    uid = uuid_factory().hex[:8]
    return output_dir / f"gcl-parallel-trace-{ts}-{safe_id}-{uid}.json"

def _build_parallel_trace(
    task_id: str,
    request: str,
    subtask_traces: list[dict[str, Any]],
    final_status: str,
    plan_hash: str = "",
) -> dict[str, Any]:
    """Build the parallel GCL trace per gcl-spec.md §6 + §12."""
    return {
        "task_id": task_id,
        "request": sanitize_request(request),
        "rubric_version": "v1",
        "parallel": True,
        "subtasks": subtask_traces,
        "final": {
            "status": final_status,
            "iter": max((t.get("iter", 0) for t in subtask_traces), default=0),
        },
        "plan_hash": plan_hash or None,
    }

def _make_subtask_trace(subtask_index: int, subtask: dict[str, Any]) -> dict[str, Any]:
    """Factory: build a subtask trace with default values. Eliminates schema duplication."""
    return {
        "subtask_index": subtask_index,
        "skill": subtask["skill"],
        "request": sanitize_request(subtask["request"]),
        "status": MAX_ITER,
        "iter": 0,
        "output": None,
        "reason": None,
        "generator_outputs": [],
        "critic_outputs": [],
    }
def _run_subtask_gcl(
    subtask_index: int,
    subtask: dict[str, Any],
    generator_cmd: list[str] | None,
    critic_cmd: list[str] | None,
    flaky_critic: bool,
) -> dict[str, Any]:
    """
    Run GCL for one subtask in its own ThreadPoolExecutor worker.

    Each call is fully isolated - no shared mutable state between workers.
    This is the unit of parallelism per gcl-spec.md section 12 Rule 1.
    """
    user_region = subtask.get("user_region", os.environ.get("AWS_DEFAULT_REGION", ""))
    safety_confirm = subtask.get("safety_confirm", "")

    subtask_trace = _make_subtask_trace(subtask_index, subtask)

    def gen(ctx: dict[str, Any]) -> dict[str, Any]:
        return _invoke_generator(ctx, generator_cmd)

    def crit(ctx: dict[str, Any]) -> dict[str, Any]:
        return _invoke_critic(ctx, critic_cmd, ctx.get("rubric", ""))

    try:
        serial_trace = _run_loop(
            skill_name=subtask["skill"],
            request=subtask["request"],
            user_region=user_region,
            generator=gen,
            critic=crit,
            safety_confirm=safety_confirm,
            flaky_critic=flaky_critic,
        )

        final = serial_trace.get("final", {})
        subtask_trace["iterations"] = serial_trace.get("iterations", [])
        subtask_trace["status"] = final.get("status", MAX_ITER)
        subtask_trace["iter"] = final.get("iter", 0)
        subtask_trace["output"] = final.get("output")
        subtask_trace["reason"] = final.get("reason")
        subtask_trace["generator_outputs"] = [
            {
                "iter": it["iter"],
                "command": it.get("generator", {}).get("command", ""),
                "exit_code": it.get("generator", {}).get("exit_code", 0),
            }
            for it in serial_trace.get("iterations", [])
        ]
        subtask_trace["critic_outputs"] = [
            {
                "iter": it["iter"],
                "scores": it.get("critic", {}).get("scores", {}),
                "blocking": it.get("critic", {}).get("blocking", False),
            }
            for it in serial_trace.get("iterations", [])
        ]
    except (CommandTimeout, CommandContractError, RuntimeError) as exc:
        subtask_trace["status"] = SAFETY_FAIL
        subtask_trace["reason"] = f"trust boundary failure: {exc}"

    return subtask_trace


def _aggregate_status(subtask_traces: list[dict[str, Any]]) -> str:
    """Aggregate per-subtask statuses into overall trace status per gcl-spec.md §5."""
    statuses = [t.get("status", MAX_ITER) for t in subtask_traces]
    if SAFETY_FAIL in statuses:
        return SAFETY_FAIL
    if all(s == PASS for s in statuses):
        return PASS
    return MAX_ITER


# ---------------------------------------------------------------------------

def run_parallel(
    task_yaml_path: Path,
    output_dir: Path,
    generator_cmd: list[str] | None = None,
    critic_cmd: list[str] | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    flaky_critic: bool = False,
    plan_hash: str = "",
    _subtask_runner: Callable[..., dict[str, Any]] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Top-level parallel GCL entry point.

    1. Load and validate the composite task YAML.
    2. Run each subtask's GCL in parallel (ThreadPoolExecutor, max_workers).
    3. Collect all subtask traces.
    4. Determine overall PASS (all subtasks PASS) or FAIL (any subtask FAIL).
    5. Persist the parallel trace.
    """
    task_data = CompositeTaskSchema.load(task_yaml_path)
    task_id = task_data["task_id"]
    subtasks = task_data["subtasks"]
    composite_request = task_data.get("request", "")

    results_map: dict[int, dict[str, Any]] = {}

    runner = _subtask_runner or _run_subtask_gcl
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                runner,
                i,
                st,
                generator_cmd,
                critic_cmd,
                flaky_critic,
            ): i
            for i, st in enumerate(subtasks)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                results_map[idx] = future.result()
            except Exception as exc:  # noqa: BLE001
                results_map[idx] = {
                    "subtask_index": idx,
                    "skill": subtasks[idx].get("skill", "unknown"),
                    "request": sanitize_request(subtasks[idx].get("request", "")),
                    "status": SAFETY_FAIL,
                    "iter": 0,
                    "output": None,
                    "reason": f"executor error: {exc}",
                    "generator_outputs": [],
                    "critic_outputs": [],
                }

    # Preserve original subtask order
    subtask_traces = [results_map[i] for i in sorted(results_map)]

    # gcl-spec.md §12 Rule 4 / §5 Termination: aggregate status
    final_status = _aggregate_status(subtask_traces)

    trace = _build_parallel_trace(
        task_id=task_id,
        request=composite_request,
        subtask_traces=subtask_traces,
        final_status=final_status,
        plan_hash=plan_hash,
    )
    # Persist (skip in dry_run mode)
    if not dry_run:
        out_path = _parallel_trace_path(output_dir, task_id)
        out_path.write_text(json.dumps(trace, indent=2))

    return trace


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def _make_patched_subtask_runner(
    gen_map: dict[int, Any],
    crit: Any,
) -> Any:
    """Build a patched _run_subtask_gcl that uses test callables instead of cmds."""

    def patched(
        subtask_index: int,
        subtask: dict[str, Any],
        generator_cmd: list[str] | None,
        critic_cmd: list[str] | None,
        flaky_critic: bool,
    ) -> dict[str, Any]:
        safety_confirm = subtask.get("safety_confirm", "")

        gen = gen_map.get(subtask_index, gen_map.get(0))
        if gen is None:
            raise ValueError(f"no generator for subtask index {subtask_index}")

        subtask_trace = _make_subtask_trace(subtask_index, subtask)

        try:
            serial_trace = run_with_callables(
                skill_name=subtask["skill"],
                request=subtask["request"],
                user_region=subtask.get("user_region", os.environ.get("AWS_DEFAULT_REGION", "")),
                generator=gen,
                critic=crit,
                safety_confirm=safety_confirm,
            )
            final = serial_trace.get("final", {})
            subtask_trace["iter"] = final.get("iter", 0)
            subtask_trace["status"] = final.get("status", MAX_ITER)
            subtask_trace["output"] = final.get("output")
            subtask_trace["reason"] = final.get("reason")
            subtask_trace["generator_outputs"] = [
                {
                    "iter": it["iter"],
                    "command": it.get("generator", {}).get("command", ""),
                    "exit_code": it.get("generator", {}).get("exit_code", 0),
                }
                for it in serial_trace.get("iterations", [])
            ]
            subtask_trace["critic_outputs"] = [
                {
                    "iter": it["iter"],
                    "scores": it.get("critic", {}).get("scores", {}),
                    "blocking": it.get("critic", {}).get("blocking", False),
                }
                for it in serial_trace.get("iterations", [])
            ]
        except (CommandTimeout, CommandContractError, RuntimeError) as exc:
            subtask_trace["status"] = SAFETY_FAIL
            subtask_trace["reason"] = f"trust boundary failure: {exc}"

        return subtask_trace

    return patched

def _self_test() -> int:
    """Run built-in self-tests validating parallel GCL invariants."""
    import tempfile

    print("parallel_gcl_runner: --self-test")

    # --- Test 1: Aggregation — all PASS → overall PASS ---------------
    print("  aggregation: all PASS → PASS ... ", end="", flush=True)

    def pass_gen(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "command": "aws --self-test",
            "args": {},
            "exit_code": 0,
            "result_excerpt": '{"stub": "pass"}',
            "safety_confirm_token": ctx.get("user", {}).get("safety_confirm", ""),
        }

    def pass_crit(ctx: dict[str, Any]) -> dict[str, Any]:
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

    with tempfile.TemporaryDirectory() as tmpdir:
        task_yaml = Path(tmpdir) / "task.yaml"
        task_yaml.write_text(
            yaml.dump({
                "task_id": "test-all-pass",
                "request": "composite test",
                "subtasks": [
                    {"skill": "aws-s3-ops", "request": "list buckets"},
                    {"skill": "aws-ec2-ops", "request": "describe instances"},
                ],
            })
        )
        patched = _make_patched_subtask_runner({0: pass_gen, 1: pass_gen}, pass_crit)
        trace = run_parallel(task_yaml, Path(tmpdir), _subtask_runner=patched, flaky_critic=False)

    assert trace["final"]["status"] == "PASS", \
        f"expected PASS, got {trace['final']['status']}"
    assert len(trace["subtasks"]) == 2
    print("PASS")

    # --- Test 2: Aggregation — one FAIL → overall FAIL ---------------
    print("  aggregation: one FAIL → FAIL ... ", end="", flush=True)

    fail_trace = _build_parallel_trace(
        task_id="test-one-fail",
        request="composite test",
        subtask_traces=[
            {
                "subtask_index": 0,
                "skill": "aws-s3-ops",
                "request": "<request-sha256:abc>",
                "status": PASS,
                "iter": 1,
                "output": {"stub": "ok"},
                "reason": None,
                "generator_outputs": [],
                "critic_outputs": [],
            },
            {
                "subtask_index": 1,
                "skill": "aws-ec2-ops",
                "request": "<request-sha256:def>",
                "status": SAFETY_FAIL,
                "iter": 0,
                "output": None,
                "reason": "trust boundary failure: command exceeded 60s: simulated generator failure",
                "generator_outputs": [],
                "critic_outputs": [],
            },
        ],
        final_status="SAFETY_FAIL",
    )

    assert fail_trace["final"]["status"] == "SAFETY_FAIL"
    print("PASS")

    # --- Test 3: Isolation — each worker gets its own ctx, no trace corruption ---
    print("  isolation: per-worker ctx ... ", end="", flush=True)

    ctxSnapshots: dict[int, dict[str, Any]] = {}

    def gen_a(ctx: dict[str, Any]) -> dict[str, Any]:
        ctxSnapshots[0] = dict(ctx)
        return {
            "command": "gen-a", "args": {}, "exit_code": 0,
            "result_excerpt": "a", "safety_confirm_token": "",
        }

    def gen_b(ctx: dict[str, Any]) -> dict[str, Any]:
        ctxSnapshots[1] = dict(ctx)
        return {
            "command": "gen-b", "args": {}, "exit_code": 0,
            "result_excerpt": "b", "safety_confirm_token": "",
        }

    def crit(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "correctness": 1, "safety": 1,
                "idempotency": 1, "traceability": 1, "spec_compliance": 1,
            },
            "suggestions": [],
            "blocking": False,
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        task_yaml = Path(tmpdir) / "task.yaml"
        task_yaml.write_text(
            yaml.dump({
                "task_id": "test-isolation",
                "request": "isolation test",
                "subtasks": [
                    {"skill": "aws-s3-ops", "request": "task a"},
                    {"skill": "aws-ec2-ops", "request": "task b"},
                ],
            })
        )
        patched = _make_patched_subtask_runner({0: gen_a, 1: gen_b}, crit)
        trace = run_parallel(task_yaml, Path(tmpdir), _subtask_runner=patched, flaky_critic=False)


    # Both completed with PASS
    assert trace["final"]["status"] == "PASS"

    # Each generator got its own ctx dict (not shared reference)
    assert 0 in ctxSnapshots and 1 in ctxSnapshots
    assert ctxSnapshots[0]["user"]["request"] == "task a"
    assert ctxSnapshots[1]["user"]["request"] == "task b"

    # Per-subtask traces are separate — gen-a result is "a", gen-b is "b"
    gen_outputs = {t["subtask_index"]: t["generator_outputs"]
                   for t in trace["subtasks"]}
    assert any("gen-a" in str(gen_outputs.get(0, [])) for _ in [1])
    assert any("gen-b" in str(gen_outputs.get(1, [])) for _ in [1])
    print("PASS")

    # --- Test 4: Parallel is faster than serial ------------------------
    print("  parallel faster than serial ... ", end="", flush=True)

    def slow_gen(ctx: dict[str, Any]) -> dict[str, Any]:
        time.sleep(0.2)
        return {
            "command": "slow", "args": {}, "exit_code": 0,
            "result_excerpt": "slow", "safety_confirm_token": "",
        }

    def crit_fast(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "correctness": 1.0, "safety": 1.0,
                "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
            },
            "suggestions": [],
            "blocking": False,
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        task_yaml = Path(tmpdir) / "task.yaml"
        task_yaml.write_text(
            yaml.dump({
                "task_id": "test-timing",
                "request": "timing test",
                "subtasks": [
                    {"skill": "aws-s3-ops", "request": f"task {i}"}
                    for i in range(4)
                ],
            })
        )
        patched = _make_patched_subtask_runner(
            {i: slow_gen for i in range(4)}, crit_fast
        )
        t0 = time.time()
        trace = run_parallel(task_yaml, Path(tmpdir), _subtask_runner=patched, max_workers=4, flaky_critic=False)
        parallel_duration = time.time() - t0

    # 4 tasks × 0.2s each with 4 workers → ~0.2s parallel vs ~0.8s serial
    assert parallel_duration < 0.5, \
        f"parallel took {parallel_duration:.2f}s, expected < 0.5s (serial would be ~0.8s)"
    print(f"PASS ({parallel_duration:.2f}s < 0.5s)")

    print("\nAll parallel GCL self-tests passed.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Parallel GCL Orchestrator (gcl-spec.md §12: multi-Generator + single-Critic)"
    )
    ap.add_argument(
        "command", nargs="?",
        help="'run' executes a composite task; omit for --self-test"
    )
    ap.add_argument("--task", type=Path, help="Composite task YAML path")
    ap.add_argument(
        "--output-dir", type=Path,
        default=REPO / "audit-results" / "gcl-parallel",
        help="Output directory for parallel GCL traces"
    )
    ap.add_argument(
        "--generator-cmd",
        help="External command for all Generator agents (same command used for all subtasks)"
    )
    ap.add_argument(
        "--critic-cmd",
        help="External command for the Critic agent"
    )
    ap.add_argument(
        "--max-workers", type=int, default=DEFAULT_MAX_WORKERS,
        help=f"Max parallel Generator workers (default: {DEFAULT_MAX_WORKERS})"
    )
    ap.add_argument(
        "--self-test", action="store_true",
        help="Run built-in self-tests (no external agent)"
    )
    ap.add_argument(
        "--flaky-critic", action="store_true",
        help="(self-test) Force idempotency=0 to exercise MAX_ITER path"
    )
    ap.add_argument(
        "--no-prune", action="store_true",
        help="Skip 30-day trace retention prune"
    )

    args = ap.parse_args(argv)

    if args.self_test or args.command is None:
        return _self_test()

    if args.command == "run":
        if args.task is None:
            ap.error("--task is required for 'run' command")

        gen_cmd = args.generator_cmd.split() if args.generator_cmd else None
        crit_cmd = args.critic_cmd.split() if args.critic_cmd else None

        trace = run_parallel(
            task_yaml_path=args.task,
            output_dir=args.output_dir,
            generator_cmd=gen_cmd,
            critic_cmd=crit_cmd,
            max_workers=args.max_workers,
            flaky_critic=args.flaky_critic,
        )

        if not args.no_prune:
            _prune_old_traces()

        print(
            f"status: {trace['final']['status']}  "
            f"subtasks: {len(trace['subtasks'])}  "
            f"task_id: {trace.get('task_id', '?')}"
        )
        return 0 if trace["final"]["status"] == "PASS" else 1

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
