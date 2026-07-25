r"""Self-Reflection Protocol — L4 #12.

Codifies the post-implementation self-review process so that L3 / P0~P3.2 era
findings (F-1 / F-2 / F-3 / F-23 et al.) do not vanish when the session ends.

Public API:
    Finding            — frozen dataclass; one finding, one .md file
    VerifyReport       — counts + stale_p0 list
    record_finding()   — append a new finding (auto-increment id)
    list_findings()    — read all findings (optional severity filter)
    verify_findings()  — flag stale P0 findings (regression guard)
    generate_report()  — produce phase-level Markdown

CLI:
    python3 scripts/self_review.py {record, list, verify, report}
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

KNOBS = {
    "findings_dir": "docs/superpowers/findings",
    "max_id": 999,
    "valid_severities": ("P0", "P1", "P2"),
    "valid_statuses": ("open", "fixed", "accepted"),
}

_ID_PATTERN = re.compile(r"^F-(\d{3})-")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    title: str
    root_cause: str
    fix: str
    lesson: str
    status: str
    added_date: str
    closed_date: Optional[str]
    phase: str = ""

    def to_markdown(self) -> str:
        closed = self.closed_date or ""
        return (
            f"---\n"
            f"id: {self.id}\n"
            f"severity: {self.severity}\n"
            f"title: {self.title}\n"
            f"status: {self.status}\n"
            f"added: {self.added_date}\n"
            f"closed: {closed}\n"
            f"phase: {self.phase}\n"
            f"---\n\n"
            f"## Root cause\n\n{self.root_cause}\n\n"
            f"## Fix\n\n{self.fix}\n\n"
            f"## Lesson\n\n{self.lesson}\n"
        )


@dataclass(frozen=True)
class VerifyReport:
    open_count: int
    fixed_count: int
    accepted_count: int
    stale_p0: list[Finding] = field(default_factory=list)


def _findings_path(repo: Path) -> Path:
    p = repo / KNOBS["findings_dir"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def _next_id(findings: Path) -> str:
    """Auto-increment to next available F-NNN."""
    existing = sorted(
        int(m.group(1))
        for f in findings.iterdir()
        if (m := _ID_PATTERN.match(f.name)) is not None
    )
    nxt = (existing[-1] + 1) if existing else 1
    if nxt > KNOBS["max_id"]:
        raise RuntimeError(f"finding id space exhausted (max={KNOBS['max_id']})")
    return f"F-{nxt:03d}"


def _parse_finding_file(path: Path) -> Optional[Finding]:
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    # Body extraction — sections after frontmatter
    body = text[m.end():]
    rc_match = re.search(r"## Root cause\n+(.*?)(?=\n##|\Z)", body, re.DOTALL)
    fix_match = re.search(r"## Fix\n+(.*?)(?=\n##|\Z)", body, re.DOTALL)
    lesson_match = re.search(r"## Lesson\n+(.*?)(?=\n##|\Z)", body, re.DOTALL)
    return Finding(
        id=fm.get("id", path.stem),
        severity=fm.get("severity", "P2"),
        title=fm.get("title", path.stem),
        root_cause=(rc_match.group(1).strip() if rc_match else ""),
        fix=(fix_match.group(1).strip() if fix_match else ""),
        lesson=(lesson_match.group(1).strip() if lesson_match else ""),
        status=fm.get("status", "open"),
        added_date=fm.get("added", ""),
        closed_date=fm.get("closed") or None,
        phase=fm.get("phase", ""),
    )


def record_finding(
    repo: Path,
    severity: str,
    title: str,
    root_cause: str,
    fix: str,
    lesson: str,
    phase: str = "",
) -> str:
    if severity not in KNOBS["valid_severities"]:
        raise ValueError(
            f"severity must be one of {KNOBS['valid_severities']}, got {severity!r}"
        )
    findings = _findings_path(repo)
    fid = _next_id(findings)
    slug = re.sub(r"[^a-z0-9-]+", "-", title.lower()).strip("-")[:60]
    f = Finding(
        id=fid,
        severity=severity,
        title=title,
        root_cause=root_cause,
        fix=fix,
        lesson=lesson,
        status="open",
        added_date=date.today().isoformat(),
        closed_date=None,
        phase=phase,
    )
    out = findings / f"{fid}-{slug}.md"
    out.write_text(f.to_markdown(), encoding="utf-8")
    return fid


def list_findings(repo: Path, severity: Optional[str] = None) -> list[Finding]:
    findings = _findings_path(repo)
    out: list[Finding] = []
    for path in sorted(findings.iterdir()):
        if not _ID_PATTERN.match(path.name):
            continue
        parsed = _parse_finding_file(path)
        if parsed is None:
            continue
        if severity is None or parsed.severity == severity:
            out.append(parsed)
    return out


def verify_findings(repo: Path) -> VerifyReport:
    findings = list_findings(repo)
    open_n = fixed_n = acc_n = 0
    stale_p0: list[Finding] = []
    for f in findings:
        if f.status == "open":
            open_n += 1
            if f.severity == "P0":
                stale_p0.append(f)
        elif f.status == "fixed":
            fixed_n += 1
        elif f.status == "accepted":
            acc_n += 1
    return VerifyReport(
        open_count=open_n,
        fixed_count=fixed_n,
        accepted_count=acc_n,
        stale_p0=stale_p0,
    )


def generate_report(repo: Path, phase_id: str) -> str:
    findings = list_findings(repo)
    sev_counts = {"P0": 0, "P1": 0, "P2": 0}
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
    lines: list[str] = [f"# Self-Review Report — {phase_id}\n"]
    lines.append(f"- Generated: {date.today().isoformat()}")
    lines.append(f"- Total: {len(findings)}")
    for sev in ("P0", "P1", "P2"):
        lines.append(f"- {sev}: {sev_counts.get(sev, 0)}")
    lines.append("")
    lines.append("| ID | Severity | Status | Title | Phase |")
    lines.append("|----|----------|--------|-------|-------|")
    for f in findings:
        lines.append(f"| {f.id} | {f.severity} | {f.status} | {f.title} | {f.phase} |")
    lines.append("")
    return "\n".join(lines)


# ---------- CLI ----------
def _cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="self_review")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--repo", default=".")
    p_rec.add_argument("--severity", required=True)
    p_rec.add_argument("--title", required=True)
    p_rec.add_argument("--root-cause", required=True)
    p_rec.add_argument("--fix", required=True)
    p_rec.add_argument("--lesson", required=True)
    p_rec.add_argument("--phase", default="")

    p_list = sub.add_parser("list")
    p_list.add_argument("--repo", default=".")
    p_list.add_argument("--severity", default=None)

    p_ver = sub.add_parser("verify")
    p_ver.add_argument("--repo", default=".")

    p_rep = sub.add_parser("report")
    p_rep.add_argument("--repo", default=".")
    p_rep.add_argument("--phase", required=True)
    p_rep.add_argument("--out", default=None)

    args = p.parse_args(argv)
    repo = Path(args.repo).resolve()
    if args.cmd == "record":
        fid = record_finding(
            repo=repo,
            severity=args.severity,
            title=args.title,
            root_cause=args.root_cause,
            fix=args.fix,
            lesson=args.lesson,
            phase=args.phase,
        )
        print(fid)
        return 0
    if args.cmd == "list":
        findings = list_findings(repo, severity=args.severity)
        if not findings:
            print("no findings yet — record some via `record` subcommand")
            return 0
        print("| ID | Severity | Status | Title | Phase |")
        print("|----|----------|--------|-------|-------|")
        for f in findings:
            print(f"| {f.id} | {f.severity} | {f.status} | {f.title} | {f.phase} |")
        return 0
    if args.cmd == "verify":
        rep = verify_findings(repo)
        print(f"open={rep.open_count} fixed={rep.fixed_count} "
              f"accepted={rep.accepted_count} stale_p0={len(rep.stale_p0)}")
        if rep.stale_p0:
            for f in rep.stale_p0:
                print(f"  STALE: {f.id} {f.title}")
            return 1
        return 0
    if args.cmd == "report":
        md = generate_report(repo, args.phase)
        if args.out:
            Path(args.out).write_text(md, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(md)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
