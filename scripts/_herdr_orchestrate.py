#!/usr/bin/env python3
"""Two-phase subagent orchestration: subagents plan → main agent executes.

Phase 1 (parallel): subagents read files, write plan to result files.
Phase 2 (serial):   main agent reads result files and executes file changes.

Usage:
    python3 scripts/_herdr_orchestrate.py --tasks tasks.csv --dry-run
    python3 scripts/_herdr_orchestrate.py --tasks tasks.csv --pane-prefix gap
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class SubagentTask:
    pane_label: str
    task_prompt: str
    result_file: Path
    pane_id: Optional[str] = None
    agent_name: Optional[str] = None
    status: str = "pending"     # pending | running | done | timeout | error
    output: str = ""
    duration_ms: float = 0.0
    error: str = ""


# ---------------------------------------------------------------------------
# herdr CLI wrappers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: str | None = None,
         timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True,
                          cwd=cwd, timeout=timeout)


def pane_split(label: str, workdir: str) -> str:
    r = _run([
        "herdr", "pane", "split", "--direction", "right",
        "--cwd", workdir, "--no-focus",
    ])
    if r.returncode != 0:
        raise RuntimeError(f"pane split failed: {r.stderr}")
    data = json.loads(r.stdout)
    pane_id = data["result"]["pane"]["pane_id"]
    _run(["herdr", "pane", "rename", pane_id, f"\U0001f527 {label}"])
    return pane_id


def agent_start(agent_name: str, pane_id: str) -> None:
    _run(["herdr", "agent", "start", agent_name,
          "--kind", "omp", "--pane", pane_id, "--timeout", "30000"])
    _run(["herdr", "agent", "wait", agent_name, "idle", "--timeout", "30000"])


def agent_prompt(agent_name: str, prompt: str, timeout_ms: int = 120000) -> None:
    _run([
        "herdr", "agent", "prompt", agent_name, prompt,
        "--wait", "--until", "idle", "--timeout", str(timeout_ms),
    ], timeout=max(30, timeout_ms // 1000 + 10))


def agent_read(agent_name: str) -> str:
    r = _run(["herdr", "agent", "read", agent_name])
    return r.stdout


def pane_close(pane_id: str) -> None:
    _run(["herdr", "pane", "close", pane_id])


# ---------------------------------------------------------------------------
# Orchestration engine
# ---------------------------------------------------------------------------

def orchestrate(
    tasks: list[SubagentTask],
    workdir: str,
    pane_prefix: str,
    timeout_ms: int = 120000,
    batch_size: int = 5,
) -> list[SubagentTask]:
    """Phase 1: spawn agents in parallel → Phase 2: read results → Phase 3: close."""

    # Phase 1: split panes and start all agents
    print(f"[orchestrate] spawning {len(tasks)} panes")
    for task in tasks:
        task.pane_id = pane_split(task.pane_label, workdir)
        task.agent_name = f"{pane_prefix}-{task.pane_label}"

    for task in tasks:
        print(f"[orchestrate] starting {task.agent_name}")
        agent_start(task.agent_name, task.pane_id)

    # Phase 2: send prompts in batches, collect outputs
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        print(f"[orchestrate] batch {i//batch_size + 1}: {[t.agent_name for t in batch]}")
        for task in batch:
            task.status = "running"
            t0 = time.monotonic()
            try:
                agent_prompt(task.agent_name, task.task_prompt, timeout_ms)
                task.duration_ms = (time.monotonic() - t0) * 1000
                task.status = "done"
            except subprocess.TimeoutExpired:
                task.status = "timeout"
                task.error = f"agent did not reach idle within {timeout_ms}ms"
                task.duration_ms = (time.monotonic() - t0) * 1000
            except Exception as exc:
                task.status = "error"
                task.error = str(exc)
                task.duration_ms = (time.monotonic() - t0) * 1000

    # Phase 3: read outputs and persist to result files
    for task in tasks:
        if task.status == "done":
            try:
                task.output = agent_read(task.agent_name)
                task.result_file.parent.mkdir(parents=True, exist_ok=True)
                task.result_file.write_text(task.output, encoding="utf-8")
                print(f"[orchestrate] wrote {len(task.output)} chars → {task.result_file}")
            except Exception as exc:
                task.error = f"read/write failed: {exc}"

    # Phase 4: close all panes (main agent retains control)
    for task in tasks:
        if task.pane_id:
            try:
                pane_close(task.pane_id)
                print(f"[orchestrate] closed pane {task.pane_id}")
            except Exception as exc:
                print(f"[orchestrate] close failed for {task.pane_id}: {exc}")

    return tasks


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_tasks(csv_path: Path) -> list[SubagentTask]:
    tasks = []
    with open(csv_path) as f:
        for row in csv.reader(f):
            if len(row) < 3 or row[0].startswith("#"):
                continue
            tasks.append(SubagentTask(
                pane_label=row[0].strip(),
                task_prompt=row[1],
                result_file=Path(row[2].strip()),
            ))
    return tasks


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    ap = argparse.ArgumentParser(prog="_herdr_orchestrate")
    ap.add_argument("--tasks", required=True,
                    help="CSV: pane_label,task_prompt,result_file")
    ap.add_argument("--workdir", default=str(REPO))
    ap.add_argument("--pane-prefix", default="orch")
    ap.add_argument("--timeout", type=int, default=120000,
                    help="Timeout per agent in ms")
    ap.add_argument("--batch-size", type=int, default=5,
                    help="Max concurrent agents per batch")
    ap.add_argument("--dry-run", action="store_true",
                    help="Load tasks and print plan, don't spawn agents")

    args = ap.parse_args(argv)
    tasks = load_tasks(Path(args.tasks))

    if not tasks:
        print("no tasks loaded")
        return 0

    if args.dry_run:
        for t in tasks:
            print(f"[dry-run] {t.pane_label} → {t.result_file}")
        return 0

    results = orchestrate(
        tasks=tasks,
        workdir=args.workdir,
        pane_prefix=args.pane_prefix,
        timeout_ms=args.timeout,
        batch_size=args.batch_size,
    )

    summary = {"total": len(results)}
    for key in ("done", "timeout", "error", "pending"):
        summary[key] = sum(1 for r in results if r.status == key)

    print(json.dumps({"status": "complete", **summary}, indent=2))
    return 0 if summary["error"] == 0 and summary["timeout"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
