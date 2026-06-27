#!/usr/bin/env python3
"""
Sync GCL prompt skeletons across all `aws-<svc>-ops` skills.

Idempotent migration: extracts the service-specific Hard rules +
Confirmation strings + Variable deltas from each skill's existing
`references/prompt-templates.md`, and rewrites the file as a thin
specialization of `aws-skill-generator/references/prompt-skeletons.md`.

Usage:
    # Dry-run: print the proposed new file content for one skill.
    python3 scripts/_sync_prompt_skeletons.py --skill aws-rds-ops --dry-run

    # Apply across all 31 skills. Writes a `.bak` next to each modified file.
    python3 scripts/_sync_prompt_skeletons.py --all

    # Roll back a single skill from its `.bak`:
    python3 scripts/_sync_prompt_skeletons.py --skill aws-rds-ops --restore

Why this exists (TE-3 / TE-6): without this script, any change to the
canonical Generator/Critic/Orchestrator templates would have to be
copy-pasted into 31 places. With it, the per-skill files become a thin
delta over the shared skeleton, and a single edit to
`prompt-skeletons.md` is enough to update the boilerplate across all skills.

Reference:
- aws-skill-generator/references/gcl-spec.md §7 (Prompt Templates contract)
- aws-skill-generator/references/prompt-skeletons.md (canonical templates)
- AGENTS.md §11 (GCL rollout)
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKELETON = REPO / "aws-skill-generator" / "references" / "prompt-skeletons.md"

# aws-<svc>-ops -> aws <svc> cli namespace (mirrors scripts/gcl_runner.py overrides)
CLI_OVERRIDES = {
    "aws-vpc-ops": "ec2",
    "aws-elb-ops": "elbv2",
    "aws-waf-ops": "wafv2",
}


def _aws_cli_svc(skill: str) -> str:
    if skill in CLI_OVERRIDES:
        return CLI_OVERRIDES[skill]
    return skill.replace("aws-", "").replace("-ops", "")


# ---------------------------------------------------------------------------
# Extraction (parse existing per-skill files)
# ---------------------------------------------------------------------------


# Marker lines that signal the end of the "service-specific" Hard rules
# inside a Critic section. Everything from "# Hard rules" up to (but not
# including) the first marker is considered skill-specific content.
HARD_RULES_END_MARKERS = (
    "Never invent values",          # canonical skeleton closing line
    "Correctness = 0 if `--region` does not match",  # generic A7 (in skeleton)
    "Correctness = 0 if the resource id was not echoed",
    "Traceability = 0 if `aws sts get-caller-identity`",
    "Safety = 0 if any plaintext secret",
)


def split_sections(txt: str) -> dict[str, str]:
    """Split by `## <header>` lines. Returns {header -> body}."""
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in txt.splitlines(keepends=True):
        m = re.match(r"^(##\s+.*?)\s*$", line)
        if m:
            if current is not None:
                sections[current] = "".join(buf)
            current = m.group(1)
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "".join(buf)
    return sections


def extract_hard_rules(critic_body: str, full_txt: str = "") -> str:
    """Pull the service-specific Hard rules out of a Critic section, OR
    from a post-migration `## Hard rules (Critic template injection)`
    block (which is the current format after `_sync_prompt_skeletons.py`
    ran).
    """
    # Path 1: legacy format with a Critic section that has a "# Hard rules" anchor.
    if critic_body:
        m = re.search(r"# Hard rules[^\n]*\n(.*?)(?=\n```|\Z)", critic_body, re.DOTALL)
        if m:
            block = m.group(1)
            lines = block.splitlines()
            cut = len(lines)
            for i, line in enumerate(lines):
                for marker in HARD_RULES_END_MARKERS:
                    if marker in line:
                        cut = min(cut, i)
                        break
            return "\n".join(lines[:cut]).rstrip()

    # Path 2: post-migration format with a dedicated Hard rules block.
    m2 = re.search(
        r"## Hard rules \(Critic template injection\).*?```text\n(.*?)\n```",
        full_txt, re.DOTALL,
    )
    if m2:
        return m2.group(1).rstrip()

    return ""


def extract_confirmation_strings(txt: str) -> str | None:
    """Pull a `## Confirmation Strings` table if present."""
    sections = split_sections(txt)
    for header, body in sections.items():
        if "Confirmation" in header:
            return body.strip()
    return None


def extract_supported_ops(txt: str) -> str | None:
    """Pull a `## Supported Operations` block if present (e.g. guardduty)."""
    sections = split_sections(txt)
    for header, body in sections.items():
        if "Supported Op" in header:
            return body.strip()
    return None


def extract_variable_convention(txt: str) -> str:
    """Return the Variable Convention table body, stripping ALL
    introductory prose blocks ('> Common placeholders are defined
    once...') that the script itself inserts. Without this, re-running
    on an already-migrated file accumulates the intro block N times.
    """
    sections = split_sections(txt)
    for header, body in sections.items():
        if "Variable Convention" in header:
            body = body.strip()
            # Strip every leading contiguous `> ...` block (each is
            # terminated by a blank line or non-`>` line).
            while True:
                stripped = re.sub(
                    r"(?:^>.*\n)+\n*",
                    "",
                    body,
                    count=1,
                )
                if stripped == body:
                    break
                body = stripped
            return body.strip()
    return ""


def extract_changelog(txt: str) -> str:
    """Return the Changelog section body, stopping at any trailing
    horizontal rule (`---`) and reference block (so re-running on an
    already-migrated file doesn't duplicate them).
    """
    sections = split_sections(txt)
    for header, body in sections.items():
        if "Changelog" in header:
            body = body.strip()
            # Cut off at the first trailing `---` separator.
            cut = body.find("\n---")
            if cut != -1:
                body = body[:cut].rstrip()
            return body
    return ""


def strip_trailing_references(txt: str) -> str:
    """Remove any trailing `\\n---\\n\\n> See [prompt-skeletons.md]...`
    block (the boilerplate this script emits). Idempotent re-runs
    otherwise accumulate one extra copy per run.
    """
    # Repeat until no more trailing reference blocks remain.
    pattern = r"\n*---\s*\n+>\s*See\s*\[`prompt-skeletons\.md`\].*$"
    prev = None
    while prev != txt:
        prev = txt
        txt = re.sub(pattern, "", txt, flags=re.DOTALL).rstrip() + "\n"
    return txt


# ---------------------------------------------------------------------------
# Render (produce the new thin file)
# ---------------------------------------------------------------------------


HEADER_TMPL = """# GCL Prompt Templates — `{skill}`

> Specialization of the shared skeleton:
> [`aws-skill-generator/references/prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
>
> This file contains only the **service-specific deltas** for `{skill}`:
> Hard rules (substituted into the Critic template's `{{skill.hard_rules}}`),
> Confirmation strings, and Variable Convention deltas. The three canonical
> templates (Generator / Critic / Orchestrator) are referenced from the
> skeleton file; do not duplicate them here.

## Skill metadata (used by skeleton `{{skill.*}}` placeholders)

| Placeholder | Value |
|---|---|
| `{{{{skill.name}}}}` | `{skill}` |
| `{{{{skill.service}}}}` | `{service}` |
| `{{{{skill.aws_cli_svc}}}}` | `{aws_cli_svc}` |
| `{{{{skill.max_iter}}}}` | `{max_iter}` (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |
"""

DELTA_HEADER = """
## Hard rules (Critic template injection)

> These bullets are substituted into the Critic template's
> `{{skill.hard_rules}}` slot in `prompt-skeletons.md` §2.
> They run BEFORE the canonical generic Hard rules (A7 / A8 / A9 / A10).

```text
{hard_rules}
```
"""


def render(skill: str, src_txt: str) -> str:
    # Strip any accumulated trailing reference blocks from a previous run
    # (idempotency: re-running on already-migrated files must NOT
    # duplicate the trailing `---` + See prompt-skeletons.md block).
    src_txt = strip_trailing_references(src_txt)
    sections = split_sections(src_txt)
    critic_body = ""
    for header, body in sections.items():
        if "Critic" in header:
            critic_body = body
            break

    hard_rules = extract_hard_rules(critic_body, src_txt)
    confirmations = extract_confirmation_strings(src_txt)
    supported_ops = extract_supported_ops(src_txt)
    var_conv = extract_variable_convention(src_txt)
    changelog = extract_changelog(src_txt)

    # Read max_iter from SKILL.md frontmatter
    skill_md = (REPO / skill / "SKILL.md").read_text()
    fm_max_iter = "2"
    m = re.search(r"max_iter:\s*(\d+)", skill_md)
    if m:
        fm_max_iter = m.group(1)

    parts: list[str] = []
    parts.append(HEADER_TMPL.format(
        skill=skill,
        service=skill.replace("aws-", "").replace("-ops", ""),
        aws_cli_svc=_aws_cli_svc(skill),
        max_iter=fm_max_iter,
    ))

    if hard_rules:
        parts.append(DELTA_HEADER.format(hard_rules=hard_rules))

    if supported_ops:
        parts.append("\n## Supported Operations (Generator reference)\n")
        parts.append(supported_ops)
        parts.append("\n")

    if confirmations:
        parts.append("\n## Confirmation Strings\n")
        parts.append(confirmations)
        parts.append("\n")

    if var_conv:
        parts.append("\n## Variable Convention (skill-specific deltas)\n")
        parts.append("> Common placeholders (`{{user.*}}`, `{{env.*}}`, `{{output.*}}`)\n")
        parts.append("> are defined once in `prompt-skeletons.md` §Variable convention.\n")
        parts.append("> Only entries unique to this skill are listed below.\n\n")
        parts.append(var_conv)
        parts.append("\n")

    if changelog:
        parts.append("\n## Changelog\n")
        parts.append(changelog)
        parts.append("\n")

    parts.append("""
---

> See [`prompt-skeletons.md`](../../aws-skill-generator/references/prompt-skeletons.md)
> for the canonical Generator / Critic / Orchestrator templates and the
> shared Variable Convention table.
""")

    return "".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--skill", help="e.g. aws-rds-ops")
    ap.add_argument("--all", action="store_true",
                    help="Sync every aws-<svc>-ops skill")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print proposed new file content to stdout")
    ap.add_argument("--restore", action="store_true",
                    help="Restore from <skill>/references/prompt-templates.md.bak")
    args = ap.parse_args(argv)

    if not SKELETON.is_file():
        print(f"error: skeleton not found: {SKELETON}", file=sys.stderr)
        return 2

    if args.restore:
        if not args.skill:
            print("--restore requires --skill", file=sys.stderr); return 2
        bak = REPO / args.skill / "references" / "prompt-templates.md.bak"
        if not bak.is_file():
            print(f"no backup: {bak}", file=sys.stderr); return 1
        shutil.move(str(bak), str(bak.with_suffix("")))
        print(f"restored: {bak.with_suffix('')}")
        return 0

    if args.all:
        skills = sorted(
            p.parent.parent.name
            for p in REPO.glob("aws-*-ops/references/prompt-templates.md")
        )
        for s in skills:
            target = REPO / s / "references" / "prompt-templates.md"
            backup = target.with_suffix(".md.bak")
            if not backup.is_file():
                shutil.copy2(target, backup)
            new_txt = render(s, target.read_text())
            target.write_text(new_txt)
            old_lines = len(target.read_text().splitlines()) if False else 0
            new_lines = new_txt.count("\n") + 1
            old_lines = sum(1 for _ in backup.open()) if backup.is_file() else 0
            print(f"  {s}: {old_lines} -> {new_lines} lines")
        print(f"sync complete: {len(skills)} skills (backups at *.bak)")
        return 0

    if not args.skill:
        ap.error("provide --skill or --all")
    target = REPO / args.skill / "references" / "prompt-templates.md"
    if not target.is_file():
        print(f"skill not found: {target}", file=sys.stderr); return 1
    new_txt = render(args.skill, target.read_text())
    if args.dry_run:
        print(new_txt)
        return 0
    backup = target.with_suffix(".md.bak")
    if not backup.is_file():
        shutil.copy2(target, backup)
    target.write_text(new_txt)
    print(f"wrote {target} (backup at {backup})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
