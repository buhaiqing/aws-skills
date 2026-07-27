"""Generate a machine-checked harness-health evidence snapshot.

Closes root cause #3 (maturity doc claims were hand-maintained, not gate-derived):
this script runs the real gates (pytest / ruff / composite_lint / self_review verify)
and emits a dated, reproducible evidence file that the maturity doc references instead
of asserting static numbers like "L4 99% / tests green".

Usage:
    python3 scripts/status_snapshot.py [--json] [--out docs/status-snapshot.md]

Exit code is 0 when all gates are green, 1 otherwise (so it can act as a CI signal
without duplicating the blocking behavior of `make lint`/`make test`).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


@dataclass
class Snapshot:
    generated_at: str
    pytest: dict
    ruff: dict
    composite_lint: dict
    self_review: dict

    @property
    def all_ok(self) -> bool:
        return bool(
            self.pytest["ok"]
            and self.ruff["ok"]
            and self.composite_lint["ok"]
            and self.self_review["ok"]
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    def to_markdown(self) -> str:
        p = self.pytest
        r = self.ruff
        c = self.composite_lint
        s = self.self_review
        badge = "🟢 ALL GREEN" if self.all_ok else "🔴 GATE RED"
        return (
            "# Harness Health Snapshot (auto-generated)\n\n"
            f"> Generated: **{self.generated_at}** · {badge}\n"
            "> This file is produced by `make snapshot` (`scripts/status_snapshot.py`).\n"
            "> Do not edit by hand — it is overwritten on every run.\n\n"
            "## Live Evidence\n\n"
            "| Gate | Result |\n"
            "|------|--------|\n"
            f"| pytest | {p['passed']} passed, {p['failed']} failed, {p['error']} error "
            f"({'OK' if p['ok'] else 'RED'}) |\n"
            f"| ruff | {r['errors']} error(s) ({'OK' if r['ok'] else 'RED'}) |\n"
            f"| composite_lint | {'OK' if c['ok'] else 'RED'} |\n"
            f"| self_review verify | stale P0 = {s['stale_p0']} ({'OK' if s['ok'] else 'RED'}) |\n\n"
            "## Note\n\n"
            "Capability maturity percentages (L1–L4) in `agentic-maturity-model.md` are a\n"
            "**human assessment**. This snapshot only proves the harness gates are currently\n"
            "green. The two are intentionally separate so drift in either is independently checkable.\n"
        )


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO), timeout=300)


def collect_pytest() -> dict:
    """Run pytest on scripts/tests; parse the summary line for pass/fail/error."""
    result = _run(
        [sys.executable, "-m", "pytest", "-p", "no:rerunfailures",
         str(SCRIPTS / "tests"), "-q"]
    )
    out = result.stdout + result.stderr
    # lines like: "111 passed in 2.60s" or "1 failed, 110 passed in 2.76s"
    passed = failed = error = 0
    if m := re.search(r"(\d+) passed", out):
        passed = int(m.group(1))
    if m := re.search(r"(\d+) failed", out):
        failed = int(m.group(1))
    if m := re.search(r"(\d+) error", out):
        error = int(m.group(1))
    ok = result.returncode == 0
    return {"passed": passed, "failed": failed, "error": error, "ok": ok}


def collect_ruff() -> dict:
    """Run ruff on scripts/; count errors from the summary line."""
    result = _run([sys.executable, "-m", "ruff", "check", str(SCRIPTS)])
    out = result.stdout + result.stderr
    errors = 0
    if m := re.search(r"Found (\d+) error", out):
        errors = int(m.group(1))
    elif result.returncode == 0:
        errors = 0
    else:
        # ruff may phrase it differently; fall back to non-zero returncode
        errors = errors or 1
    return {"errors": errors, "ok": errors == 0}


def collect_composite_lint() -> dict:
    result = _run([sys.executable, str(SCRIPTS / "composite_lint.py"), "lint", "--all"])
    return {"ok": result.returncode == 0}


def collect_self_review() -> dict:
    result = _run([sys.executable, str(SCRIPTS / "self_review.py"), "verify"])
    stale = 0
    if m := re.search(r"stale_p0=(\d+)", result.stdout + result.stderr):
        stale = int(m.group(1))
    return {"stale_p0": stale, "ok": stale == 0}


def build_snapshot() -> Snapshot:
    return Snapshot(
        generated_at=date.today().isoformat(),
        pytest=collect_pytest(),
        ruff=collect_ruff(),
        composite_lint=collect_composite_lint(),
        self_review=collect_self_review(),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Harness health evidence snapshot")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout")
    ap.add_argument("--out", type=str, default=None,
                    help="write Markdown evidence to this path")
    args = ap.parse_args(argv)

    snap = build_snapshot()

    if args.out:
        Path(args.out).write_text(snap.to_markdown(), encoding="utf-8")
        print(f"wrote {args.out} (all_ok={snap.all_ok})")
    if args.json:
        print(snap.to_json())
    elif not args.out:
        # default: human-readable markdown to stdout
        print(snap.to_markdown())

    return 0 if snap.all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
