#!/usr/bin/env python3
"""Skill generation gate — ADR O10 D2.

Machine gate for scaffolded aws-*-ops skills before human PR approval.
Auto-merge rate is always 0% (no merge API).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent

REQUIRED_REFS = (
    "aws-cli-usage.md",
    "boto3-sdk-usage.md",
    "core-concepts.md",
    "troubleshooting.md",
)
ALLOWED_DOC_HOSTS = frozenset({"docs.aws.amazon.com", "aws.amazon.com"})
AUTO_HEAL_ENABLED_RE = re.compile(
    r"AUTO_HEAL:\s*enabled\s+by\s+default",
    re.IGNORECASE,
)
AUTO_HEAL_EXPAND_RE = re.compile(r"expand\s+AUTO_HEAL", re.IGNORECASE)
AUTO_HEAL_NEGATED_RE = re.compile(
    r"\b(?:do\s+not|don't|never)\s+expand\s+AUTO_HEAL",
    re.IGNORECASE,
)


@dataclass
class GateReport:
    ok: bool
    checks: list[dict]
    auto_merge_rate: float = 0.0


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def _check_layout(skill_dir: Path) -> dict:
    missing: list[str] = []
    if not (skill_dir / "SKILL.md").is_file():
        missing.append("SKILL.md")
    refs = skill_dir / "references"
    for fn in REQUIRED_REFS:
        if not (refs / fn).is_file():
            missing.append(f"references/{fn}")
    if not (skill_dir / "golden-scenarios.yaml").is_file():
        missing.append("golden-scenarios.yaml")
    if missing:
        return _check("layout", False, f"missing: {', '.join(missing)}")
    return _check("layout", True, "required files present")


def _check_frontmatter_c2(skill_dir: Path) -> dict:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return _check("frontmatter_c2", False, "SKILL.md missing")
    text = skill_md.read_text(encoding="utf-8")
    has_should = "### SHOULD Use When" in text
    has_should_not = "### SHOULD NOT Use When" in text
    if has_should and has_should_not:
        return _check("frontmatter_c2", True, "C2 sub-headers present")
    missing = []
    if not has_should:
        missing.append("### SHOULD Use When")
    if not has_should_not:
        missing.append("### SHOULD NOT Use When")
    return _check("frontmatter_c2", False, f"missing: {', '.join(missing)}")


def _check_docs_url_evidence(skill_dir: Path) -> dict:
    spec_path = skill_dir / "service-spec.json"
    if not spec_path.is_file():
        return _check(
            "docs_url_evidence",
            False,
            "service-spec.json required for scaffold gate",
        )
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _check("docs_url_evidence", False, f"invalid JSON: {exc}")
    docs_url = spec.get("docs_url", "")
    if not docs_url:
        return _check("docs_url_evidence", False, "docs_url missing or empty")
    host = urlparse(docs_url).hostname or ""
    if host in ALLOWED_DOC_HOSTS:
        return _check("docs_url_evidence", True, f"docs_url host {host!r}")
    return _check("docs_url_evidence", False, f"docs_url host {host!r} not allowed")


def _check_golden_load(skill_dir: Path) -> dict:
    path = skill_dir / "golden-scenarios.yaml"
    if not path.is_file():
        return _check("golden_load", False, "golden-scenarios.yaml missing")
    try:
        from golden_eval import load_scenarios

        scenarios = load_scenarios(path)
    except Exception as exc:
        return _check("golden_load", False, str(exc))
    if len(scenarios) < 5:
        return _check("golden_load", False, f"{len(scenarios)} scenarios (< 5)")
    return _check("golden_load", True, f"{len(scenarios)} scenarios loaded")


def _skill_under_repo(skill_dir: Path) -> bool:
    try:
        skill_dir.resolve().relative_to(REPO.resolve())
        return True
    except ValueError:
        return False


def _inline_te_gate(skill_dir: Path) -> dict:
    """Run te_gate checks in-process (works for tmp_path outside repo)."""
    from te_gate import gate_skill

    results = gate_skill(skill_dir)
    failures = []
    for gate in ("G1", "G3", "G4"):
        ok, msg = results[gate]
        if not ok:
            failures.append(f"{gate}: {msg}")
    if failures:
        return _check("te_gate", False, "; ".join(failures))
    detail = "te_gate passed (inline)"
    if not _skill_under_repo(skill_dir):
        detail = "te_gate passed (inline, outside repo)"
    return _check("te_gate", True, detail)


def _check_te_gate(skill_dir: Path, *, strict: bool) -> dict:
    if _skill_under_repo(skill_dir):
        cmd = [sys.executable, str(SCRIPTS / "te_gate.py"), skill_dir.name]
        if strict:
            cmd.append("--strict")
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if proc.returncode == 0:
            return _check("te_gate", True, "te_gate passed")
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        detail = tail[-1] if tail else "te_gate failed"
        return _check("te_gate", False, detail)
    return _inline_te_gate(skill_dir)


def _auto_heal_line_suspicious(line: str) -> bool:
    if AUTO_HEAL_ENABLED_RE.search(line):
        return True
    if AUTO_HEAL_EXPAND_RE.search(line) and not AUTO_HEAL_NEGATED_RE.search(line):
        return True
    return False


def _check_no_auto_heal_expand(skill_dir: Path) -> dict:
    hits: list[str] = []
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".md", ".yaml", ".yml", ".json", ".txt"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if _auto_heal_line_suspicious(line):
                hits.append(f"{path.relative_to(skill_dir)}:{i}")
    if hits:
        sample = ", ".join(hits[:3])
        return _check(
            "no_auto_heal_expand",
            False,
            f"suspicious AUTO_HEAL expansion: {sample}",
        )
    return _check("no_auto_heal_expand", True, "no AUTO_HEAL expansion language")


def run_gate(skill_dir: Path, *, strict: bool = True) -> GateReport:
    skill_dir = skill_dir.resolve()
    checks = [
        _check_layout(skill_dir),
        _check_frontmatter_c2(skill_dir),
        _check_docs_url_evidence(skill_dir),
        _check_golden_load(skill_dir),
        _check_te_gate(skill_dir, strict=strict),
        _check_no_auto_heal_expand(skill_dir),
        _check("auto_merge_rate", True, "auto_merge_rate=0.0 (no auto-merge API)"),
    ]
    ok = all(c["ok"] for c in checks)
    return GateReport(ok=ok, checks=checks, auto_merge_rate=0.0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Skill generation gate (O10 D2)")
    parser.add_argument("--skill", required=True, type=Path, help="Skill directory")
    parser.add_argument(
        "--strict",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    report = run_gate(args.skill, strict=args.strict)
    exit_code = 0 if report.ok else 1
    if args.as_json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(f"=== skill_gen_gate: {args.skill.name} ===")
        for chk in report.checks:
            status = "PASS" if chk["ok"] else "FAIL"
            print(f"  [{status}] {chk['name']}: {chk['detail']}")
        print(f"  auto_merge_rate: {report.auto_merge_rate}")
        print("PASS" if report.ok else "FAIL")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
