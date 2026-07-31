"""Tests for scripts/skill_scaffold.py — ADR O10 D1."""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import skill_scaffold  # noqa: E402
from golden_eval import load_scenarios  # noqa: E402
from te_gate import JSON_PATH_LINE_RE, check_g3  # noqa: E402


def _minimal_spec(**overrides) -> dict:
    base = {
        "service_id": "glue",
        "product_name": "AWS Glue",
        "primary_resource": "Job",
        "docs_url": "https://docs.aws.amazon.com/glue/latest/dg/welcome.html",
        "cli_namespace": "glue",
        "boto3_module": "glue",
        "destructive_ops": ["delete-job"],
    }
    base.update(overrides)
    return base


def _write_spec(tmp_path: Path, spec: dict) -> Path:
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    return p


def test_happy_path_creates_tree_and_golden_at_least_five(tmp_path):
    spec = _minimal_spec()
    created = skill_scaffold.init(spec, tmp_path)

    assert created == tmp_path / "aws-glue-ops"
    assert (created / "SKILL.md").is_file()
    assert (created / "references" / "aws-cli-usage.md").is_file()
    assert (created / "references" / "boto3-sdk-usage.md").is_file()
    assert (created / "references" / "core-concepts.md").is_file()
    assert (created / "references" / "troubleshooting.md").is_file()
    assert (created / "assets" / "example-config.yaml").is_file()
    assert (created / "service-spec.json").is_file()

    scenarios = load_scenarios(created / "golden-scenarios.yaml")
    assert len(scenarios) >= 5


def test_refuse_missing_docs_url(tmp_path):
    spec = _minimal_spec()
    del spec["docs_url"]
    with pytest.raises(skill_scaffold.SpecValidationError, match="docs_url"):
        skill_scaffold.init(spec, tmp_path)


def test_refuse_bad_docs_host(tmp_path):
    spec = _minimal_spec(docs_url="http://evil.example/bad")
    with pytest.raises(skill_scaffold.SpecValidationError, match="host not allowed"):
        skill_scaffold.init(spec, tmp_path)


def test_destructive_ops_creates_rubric_and_prompt_templates(tmp_path):
    created = skill_scaffold.init(_minimal_spec(), tmp_path)
    assert (created / "references" / "rubric.md").is_file()
    assert (created / "references" / "prompt-templates.md").is_file()
    text = (created / "references" / "prompt-templates.md").read_text()
    assert "aws-glue-ops" in text
    assert "<SKILL_NAME>" not in text


def test_empty_destructive_skips_rubric(tmp_path):
    created = skill_scaffold.init(
        _minimal_spec(destructive_ops=[]),
        tmp_path,
    )
    assert not (created / "references" / "rubric.md").exists()
    assert not (created / "references" / "prompt-templates.md").exists()
    scenarios = load_scenarios(created / "golden-scenarios.yaml")
    assert len(scenarios) >= 5


def test_skill_md_has_should_use_when_subheader(tmp_path):
    created = skill_scaffold.init(_minimal_spec(destructive_ops=[]), tmp_path)
    skill_md = (created / "SKILL.md").read_text()
    assert "### SHOULD Use When" in skill_md
    assert "### SHOULD NOT Use When" in skill_md


def test_no_auto_heal_in_generated_tree(tmp_path):
    created = skill_scaffold.init(_minimal_spec(), tmp_path)
    for path in created.rglob("*"):
        if path.is_file():
            assert "AUTO_HEAL" not in path.read_text()


def test_no_merge_or_auto_merge_functions_in_module():
    for name, obj in inspect.getmembers(skill_scaffold):
        if inspect.isfunction(obj) and obj.__module__ == skill_scaffold.__name__:
            assert not name.startswith("merge_")
            assert name != "auto_merge"


def test_cli_init_success(tmp_path):
    spec_path = _write_spec(tmp_path, _minimal_spec(destructive_ops=[]))
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "skill_scaffold.py"),
            "init",
            "--spec",
            str(spec_path),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert (out_dir / "aws-glue-ops").is_dir()
    assert proc.stdout.strip().endswith("aws-glue-ops")


def test_cli_validation_error_exit_2(tmp_path):
    spec_path = _write_spec(
        tmp_path,
        _minimal_spec(docs_url="http://evil.example/x"),
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "skill_scaffold.py"),
            "init",
            "--spec",
            str(spec_path),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "host not allowed" in proc.stderr


def test_skill_md_line_count_at_most_120(tmp_path):
    created = skill_scaffold.init(_minimal_spec(), tmp_path)
    lines = (created / "SKILL.md").read_text().splitlines()
    assert len(lines) <= 120


def _json_paths_fence_lines(skill_md: str) -> list[str]:
    lines = skill_md.splitlines()
    header_idx = next(
        i for i, ln in enumerate(lines) if "## Common JSON Paths" in ln
    )
    in_fence = False
    fenced: list[str] = []
    for ln in lines[header_idx + 1:]:
        if ln.strip() == "```":
            if in_fence:
                break
            in_fence = True
            continue
        if in_fence:
            fenced.append(ln)
    return fenced


def test_skill_md_json_paths_block_non_empty(tmp_path):
    created = skill_scaffold.init(_minimal_spec(), tmp_path)
    skill_md = (created / "SKILL.md").read_text()
    fenced = _json_paths_fence_lines(skill_md)
    path_comments = [ln for ln in fenced if ln.lstrip().startswith("#")]
    assert path_comments, "Common JSON Paths fence must include a # comment line"
    assert any(JSON_PATH_LINE_RE.match(ln) for ln in fenced), (
        "fence must declare at least one TE-4 JSON path"
    )
    ok, msg = check_g3(created)
    assert ok, msg
