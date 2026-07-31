"""Tests for scripts/skill_gen_gate.py — ADR O10 D2."""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import skill_gen_gate  # noqa: E402
from skill_gen_gate import run_gate  # noqa: E402

MINIMAL_SKILL = """\
---
name: aws-test-ops
description: test skill
---

# AWS Test Operations Skill

## Trigger & Scope

### SHOULD Use When
- test operations

### SHOULD NOT Use When
- do not expand AUTO_HEAL by default
- unrelated work

## Operations

Body text.
"""

GOLDEN_HEADER = """\
---
skill: aws-test-ops
description: minimal golden suite
scenarios:
"""

GOLDEN_SCENARIO = """\
  - id: {sid}
    description: scenario {sid}
    request: list resources
    expected_status: PASS
"""


def _write_golden(skill: Path, count: int = 5) -> None:
    lines = [GOLDEN_HEADER]
    for i in range(count):
        lines.append(GOLDEN_SCENARIO.format(sid=f"scn-{i}"))
    (skill / "golden-scenarios.yaml").write_text("".join(lines))


def _write_refs(skill: Path) -> None:
    refs = skill / "references"
    refs.mkdir(exist_ok=True)
    for name in skill_gen_gate.REQUIRED_REFS:
        (refs / name).write_text(f"# {name}\n")


def _write_service_spec(skill: Path, docs_url: str = "https://docs.aws.amazon.com/test/") -> None:
    spec = {
        "service_id": "test",
        "product_name": "Test",
        "primary_resource": "Thing",
        "docs_url": docs_url,
        "cli_namespace": "test",
        "boto3_module": "test",
        "destructive_ops": [],
    }
    (skill / "service-spec.json").write_text(json.dumps(spec))


def build_minimal_skill(
    tmp_path: Path,
    *,
    skill_body: str | None = None,
    golden_count: int = 5,
    docs_url: str = "https://docs.aws.amazon.com/test/",
    include_spec: bool = True,
) -> Path:
    skill = tmp_path / "aws-test-ops"
    skill.mkdir()
    (skill / "SKILL.md").write_text(skill_body or MINIMAL_SKILL)
    _write_refs(skill)
    _write_golden(skill, golden_count)
    if include_spec:
        _write_service_spec(skill, docs_url=docs_url)
    return skill


def _check(report, name: str) -> dict:
    return next(c for c in report.checks if c["name"] == name)


def test_gate_passes_minimal_skill(tmp_path):
    skill = build_minimal_skill(tmp_path)
    report = run_gate(skill)
    assert report.ok is True
    assert report.auto_merge_rate == 0.0
    assert all(c["ok"] for c in report.checks)


def test_missing_should_use_when_fails(tmp_path):
    body = MINIMAL_SKILL.replace("### SHOULD Use When\n", "")
    skill = build_minimal_skill(tmp_path, skill_body=body)
    report = run_gate(skill)
    assert report.ok is False
    assert _check(report, "frontmatter_c2")["ok"] is False


def test_skill_md_over_120_lines_fails(tmp_path):
    pad = "\n".join(f"_pad_{i}" for i in range(130))
    body = MINIMAL_SKILL + "\n" + pad
    skill = build_minimal_skill(tmp_path, skill_body=body)
    report = run_gate(skill)
    assert report.ok is False
    te = _check(report, "te_gate")
    assert te["ok"] is False
    assert "121" in te["detail"] or "> 120" in te["detail"] or "G1" in te["detail"]


def test_missing_service_spec_fails(tmp_path):
    skill = build_minimal_skill(tmp_path, include_spec=False)
    report = run_gate(skill)
    assert report.ok is False
    docs = _check(report, "docs_url_evidence")
    assert docs["ok"] is False
    assert "service-spec.json required" in docs["detail"]


def test_bad_docs_url_host_fails(tmp_path):
    skill = build_minimal_skill(
        tmp_path,
        docs_url="https://example.com/not-aws",
    )
    report = run_gate(skill)
    assert report.ok is False
    docs = _check(report, "docs_url_evidence")
    assert docs["ok"] is False
    assert "not allowed" in docs["detail"]


def test_golden_fewer_than_five_fails(tmp_path):
    skill = build_minimal_skill(tmp_path, golden_count=4)
    report = run_gate(skill)
    assert report.ok is False
    golden = _check(report, "golden_load")
    assert golden["ok"] is False
    assert "< 5" in golden["detail"]


def test_auto_merge_rate_always_zero(tmp_path):
    skill = build_minimal_skill(tmp_path)
    report = run_gate(skill)
    assert report.auto_merge_rate == 0.0
    merge_chk = _check(report, "auto_merge_rate")
    assert merge_chk["ok"] is True


def test_module_has_no_auto_merge_helpers():
    public = {
        name
        for name, obj in inspect.getmembers(skill_gen_gate)
        if not name.startswith("_") and callable(obj)
    }
    assert "auto_merge" not in public
    assert "merge_to_main" not in public


def test_auto_heal_expansion_language_fails(tmp_path):
    body = MINIMAL_SKILL + "\n\nexpand AUTO_HEAL to all skills\n"
    skill = build_minimal_skill(tmp_path, skill_body=body)
    report = run_gate(skill)
    assert report.ok is False
    heal = _check(report, "no_auto_heal_expand")
    assert heal["ok"] is False


def _run_gate_cli(skill: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "skill_gen_gate.py"),
            "--skill",
            str(skill),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_subprocess_exit_code_pass_and_fail(tmp_path):
    skill = build_minimal_skill(tmp_path)
    ok_plain = _run_gate_cli(skill)
    assert ok_plain.returncode == 0
    assert "PASS" in ok_plain.stdout

    ok_json = _run_gate_cli(skill, "--json")
    assert ok_json.returncode == 0
    payload = json.loads(ok_json.stdout)
    assert payload["ok"] is True
    assert payload["auto_merge_rate"] == 0.0

    body = MINIMAL_SKILL.replace("### SHOULD Use When\n", "")
    fail_root = tmp_path / "fail"
    fail_root.mkdir()
    failing = build_minimal_skill(fail_root, skill_body=body)

    fail_plain = _run_gate_cli(failing)
    assert fail_plain.returncode == 1
    assert "FAIL" in fail_plain.stdout

    fail_json = _run_gate_cli(failing, "--json")
    assert fail_json.returncode == 1
    fail_payload = json.loads(fail_json.stdout)
    assert fail_payload["ok"] is False


def test_cli_main_return_matches_subprocess(tmp_path):
    """In-process main() must agree with script exit code."""
    skill = build_minimal_skill(tmp_path)
    assert skill_gen_gate.main(["--skill", str(skill), "--json"]) == 0

    body = MINIMAL_SKILL.replace("### SHOULD Use When\n", "")
    bad_root = tmp_path / "bad"
    bad_root.mkdir()
    bad = build_minimal_skill(bad_root, skill_body=body)
    assert skill_gen_gate.main(["--skill", str(bad), "--json"]) == 1
    assert _run_gate_cli(bad, "--json").returncode == 1
