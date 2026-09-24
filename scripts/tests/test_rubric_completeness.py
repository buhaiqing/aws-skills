"""Rubric completeness gate.

Regression guard for the `aws-aurora-ops` defect (2026-09-10): the skill was
declared `gcl.class = required` while its `references/rubric.md` was still the
raw `_gen_rubric.py` template — both service-specific sections carried the
`<!-- LLM_FILL ... -->` markers, so the GCL Critic had no operation overrides
and no auto-fail list to score against. `--llm-fill` silently degrades to the
bare template when no LLM credential is present (`_llm_rubric_fill.call_llm`
returns `''`), which is how it shipped.

The gate checks the artifact, not the generator: every rubric in the repo must
be filled and carry the five mandatory dimensions from `gcl-spec.md` §3.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# gcl-spec.md §3 — the five mandatory dimensions, one table row each.
DIMENSIONS = ("Correctness", "Safety", "Idempotency", "Traceability", "Spec Compliance")

# Generator placeholders that must never reach a shipped rubric.
FILL_MARKER = re.compile(r"<!-- ?LLM_FILL|<!-- TODO")


def _rubric_files() -> list[Path]:
    return sorted(
        p for p in REPO.glob("*/references/rubric.md") if ".worktrees" not in p.parts
    )


RUBRICS = _rubric_files()


def _id(path: Path) -> str:
    return path.parent.parent.name


def test_repo_has_rubrics_to_check() -> None:
    """Guard the gate itself: a glob regression must not silently pass."""
    assert len(RUBRICS) >= 30, f"only {len(RUBRICS)} rubrics found under {REPO}"


@pytest.mark.parametrize("rubric", RUBRICS, ids=_id)
def test_rubric_is_filled(rubric: Path) -> None:
    """No shipped rubric may carry generator fill markers."""
    text = rubric.read_text(encoding="utf-8")
    hit = FILL_MARKER.search(text)
    assert hit is None, f"{rubric}: unfilled generator marker {hit.group(0)!r}"


@pytest.mark.parametrize("rubric", RUBRICS, ids=_id)
def test_rubric_declares_all_dimensions(rubric: Path) -> None:
    """Every rubric scores the five §3 dimensions on the 0 / 0.5 / 1 scale."""
    text = rubric.read_text(encoding="utf-8")
    missing = [d for d in DIMENSIONS if f"| **{d}** |" not in text]
    assert not missing, f"{rubric}: missing dimension row(s) {missing}"


def test_generator_emits_rds_namespace_for_aurora(tmp_path, monkeypatch) -> None:
    """Aurora is driven by the `rds` CLI namespace, not `aurora`.

    `_gen_rubric._aws_cli_svc` feeds the Traceability dimension's command
    template; an unlisted skill falls through to its directory name.
    """
    from _gen_rubric import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["_gen_rubric.py", "aws-aurora-ops", "Amazon Aurora"]
    )
    main()

    text = (tmp_path / "aws-aurora-ops" / "references" / "rubric.md").read_text(
        encoding="utf-8"
    )
    assert "aws rds <op>" in text
    assert "aws aurora" not in text
    assert "## Loop parameters" in text


def test_generator_refuses_to_overwrite_filled_rubric(tmp_path, monkeypatch) -> None:
    """Re-running the generator must not silently destroy a filled rubric."""
    from _gen_rubric import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["_gen_rubric.py", "aws-aurora-ops", "Amazon Aurora"]
    )
    assert main() == 0
    target = tmp_path / "aws-aurora-ops" / "references" / "rubric.md"

    target.write_text("# filled by hand\n")
    monkeypatch.setattr(
        sys, "argv", ["_gen_rubric.py", "aws-aurora-ops", "Amazon Aurora"]
    )
    assert main() == 1
    assert target.read_text() == "# filled by hand\n"

    monkeypatch.setattr(
        sys,
        "argv",
        ["_gen_rubric.py", "aws-aurora-ops", "Amazon Aurora", "--force"],
    )
    assert main() == 0
    assert "Amazon Aurora Ops Rubric" in target.read_text()
