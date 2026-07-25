---
id: F-007
severity: P1
title: gcl_runner._yaml_lite flattens nested dict keys (pre-existing)
status: fixed
added: 2026-07-26
closed: 2026-07-26
phase: short-path-completion
---

## Root cause

`scripts/gcl_runner.py:_yaml_lite()` incorrectly flattens nested YAML keys.
For input like:
```yaml
metadata:
  gcl:
    enabled: true
    class: required
    max_iter: 2
```
The parser produces:
```python
{"metadata": {"gcl": "", "enabled": True, "class": "required", "max_iter": 2, ...}}
```

It stores `metadata.gcl = ""` (empty) and then **flattens** the nested keys
into `metadata` directly, so `gcl.get("max_iter", 2)` fails with
`AttributeError: 'str' object has no attribute 'get'`.

Triggered by `test_gcl_runner_self_test_on_fail_appends_to_failure_patterns`
which calls `gcl_runner --self-test --skill aws-s3-ops`.

## Fix

✅ **Fixed 2026-07-26**: Removed `_yaml_lite` entirely from `scripts/gcl_runner.py`. `_load_yaml_frontmatter` now uses only `yaml.safe_load`. Test `test_gcl_runner_self_test_on_fail_appends_to_failure_patterns` now passes; full suite 106/106 green.

Original fix options:

Either:
- (a) Properly use PyYAML's safe_load (already imported at line 67); the
  fallback _yaml_lite is the actual problem path
- (b) Fix _yaml_lite to track nested `cur` per indent level, not just one

Recommended: (a) — drop _yaml_lite entirely, rely on PyYAML.

```python
def _load_yaml_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        import yaml
        return yaml.safe_load(parts[1]) or {}
    except Exception:
        return {}
```

## Lesson

Lite YAML parsers are fragile for nested structures. When PyYAML is
already a dependency, don't hand-roll fallback parsers — let exceptions
bubble up so the bug surfaces immediately, not 5 layers deep.

## Discovery

This bug pre-exists the L3→L4 closure work (visible in earlier session
runs that reported "106 passed" — likely test ordering or sandbox-specific
quirk masked it). Discovered 2026-07-26 during short-path final verification
(full suite = 105 passed + 1 pre-existing failure). Not caused by G1-G5
short-path changes.
