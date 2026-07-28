"""TDD tests for scripts/te_gate.py — TE C6 Hard Gate regex fixtures.

The te_gate.py G3 check verifies three things:
  (a) a `## Common JSON Paths` header exists when JSON paths are present,
  (b) the header block contains at least one JSON-path declaration,
  (c) declared paths are NOT re-declared as one-line command duplications
      in the body.

These tests pin the regex semantics so we can extend it safely. All
fixtures are real SKILL.md content (no mocks). The bugs under test are
the existing G3 fail modes for `aws-cloudwatch-ops` and `aws-ram-ops`.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from te_gate import (  # noqa: E402
    JSON_PATH_HEADER_RE,
    JSON_PATH_LINE_RE,
    check_g1,
    check_g3,
    check_g4,
    gate_skill,
)


def _make_skill(tmp_path: Path, body: str, lines: int | None = None) -> Path:
    """Build a minimal SKILL.md with a fixed body, returning skill dir."""
    skill = tmp_path / "aws-test-ops"
    skill.mkdir()
    skill_md = skill / "SKILL.md"
    if lines is not None:
        # pad body to exactly `lines` lines so G1 check has stable input
        body = body.rstrip("\n")
        current = len(body.splitlines())
        assert lines >= current, f"body has {current} lines, asked for {lines}"
        pad = lines - current
        body = body + "\n" + "\n".join(f"_pad_line_{i}" for i in range(pad))
    skill_md.write_text(body)
    return skill


# --- Reusable header body for "happy path" tests (1 path, simple key) ---

SIMPLE_HEADER = """\
---
name: aws-test
---

# Test Skill

## Common JSON Paths

```
Instances = .Instances[].InstanceId
Volumes = .Volumes[].VolumeId
```

## Operations

Some body text here.
"""


# --- T1: simple key = .path format (already worked; pin behaviour) ---


def test_g3_accepts_simple_key_equals_path(tmp_path):
    skill = _make_skill(tmp_path, SIMPLE_HEADER)
    ok, msg = check_g3(skill)
    assert ok, msg
    assert "2 path" in msg


# --- T2: labelled `# Label: .path.{key1,key2}` (currently fails) ---


def test_g3_accepts_label_prefixed_path(tmp_path):
    body = """\
---
name: aws-test
---

# Test Skill

## Common JSON Paths

```
# ResourceShare: .resourceShare.{resourceShareArn,name,status}
# Association:   .resourceShareAssociation.{resourceShareArn,associatedResource}
```

## Operations

Body text.
"""
    skill = _make_skill(tmp_path, body)
    ok, msg = check_g3(skill)
    assert ok, msg


# --- T3: multi-path on one line via `;` (currently fails) ---


def test_g3_accepts_multi_path_line_split_on_semicolon(tmp_path):
    body = """\
---
name: aws-test
---

# Test Skill

## Common JSON Paths

```
.DashboardEntries[] = .DashboardEntries[].DashboardName
.logGroups[] = .logGroups[].logGroupName
```

## Operations

Body text.
"""
    skill = _make_skill(tmp_path, body)
    ok, msg = check_g3(skill)
    assert ok, msg
    assert "2 path" in msg


# --- T4: cloudwatch-style header where multi-path on one line is the
#       actual problem. Currently the G3 check falsely flags the header
#       line itself as a body duplication. This is the bug. ---


def test_g3_existing_header_with_multi_path_no_self_dupe(tmp_path):
    """Pins the bug fix: header with multi-path content must not flag
    itself as a body duplication."""
    body = """\
---
name: aws-cloudwatch-ops
---

# AWS CloudWatch Operations Skill

## Common JSON Paths

```
.MetricAlarms[] / .CompositeAlarms[] → AlarmName, StateValue | .Metrics[] / .MetricDataResults[] / .Datapoints[]
.DashboardEntries[].DashboardName | .logGroups[]; start-query → .queryId; get-query-results → .status, .results
.InsightRules[] / .Canaries[].{Name,Status}
```

## Trigger & Scope

### SHOULD Use When
- CloudWatch
"""
    skill = _make_skill(tmp_path, body)
    ok, msg = check_g3(skill)
    assert ok, msg


# --- T5: body-dupe detection must still work for simple cases. ---


def test_g3_body_dupe_still_caught_for_new_format(tmp_path):
    body = """\
---
name: aws-test
---

# Test Skill

## Common JSON Paths

```
Buckets = .Buckets[].Name
```

## Operations

```
aws s3api list-buckets --output json
.Buckets[].Name is the path
```
"""
    skill = _make_skill(tmp_path, body)
    ok, msg = check_g3(skill)
    assert not ok, "expected body dupe to be detected"
    assert "re-declared" in msg


# --- T6: G1 still works (≤ 120 lines passes) ---


def test_g1_passes_under_cap(tmp_path):
    skill = _make_skill(tmp_path, SIMPLE_HEADER, lines=120)
    ok, msg = check_g1(skill)
    assert ok, msg


def test_g1_fails_over_cap(tmp_path):
    skill = _make_skill(tmp_path, SIMPLE_HEADER, lines=121)
    ok, msg = check_g1(skill)
    assert not ok, msg
    assert "121" in msg
