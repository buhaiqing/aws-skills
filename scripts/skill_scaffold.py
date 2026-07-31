#!/usr/bin/env python3
"""Mechanical AWS skill scaffold — ADR O10 D1.

Creates directory layout + placeholder stubs from a ServiceSpec JSON.
No LLM fill, no merge helpers, no AUTO_HEAL expansion.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
PROMPT_TEMPLATE = (
    REPO / "aws-skill-generator/assets/new-skill-template/prompt-templates.md"
)

REQUIRED_FIELDS = (
    "service_id",
    "product_name",
    "primary_resource",
    "docs_url",
    "cli_namespace",
    "boto3_module",
    "destructive_ops",
)

ALLOWED_DOC_HOSTS = frozenset({"docs.aws.amazon.com", "aws.amazon.com"})

CADL_HOOK = (
    '> After completing a task, review and distill reusable assets per the root '
    'AGENTS.md "Compound-Asset Distillation Loop (CADL)".'
)


class SpecValidationError(ValueError):
    """ServiceSpec failed validation."""


def validate_spec(spec: dict) -> None:
    for field in REQUIRED_FIELDS:
        if field not in spec:
            raise SpecValidationError(f"missing required field: {field}")
    if not isinstance(spec["destructive_ops"], list):
        raise SpecValidationError("destructive_ops must be a list")

    parsed = urlparse(spec["docs_url"])
    host = parsed.hostname or ""
    if host not in ALLOWED_DOC_HOSTS:
        raise SpecValidationError(f"docs_url host not allowed: {host!r}")


def skill_dir_name(service_id: str) -> str:
    return f"aws-{service_id}-ops"


def _primary_resource_json_path(resource: str) -> str:
    """One TE-4-compliant path comment derived from primary_resource."""
    base = resource[0].lower() + resource[1:] if resource else "resource"
    plural = base if base.endswith("s") else f"{base}s"
    return f"# {resource}: .{plural}[].{{{base}Name,{base}Arn,state,status}}"


def _write_skill_md(skill_path: Path, spec: dict) -> None:
    skill_name = skill_path.name
    product = spec["product_name"]
    resource = spec["primary_resource"]
    cli_ns = spec["cli_namespace"]
    destructive = spec["destructive_ops"]
    docs_url = spec["docs_url"]

    metadata_lines = [
        "  author: aws",
        '  version: "0.0.0-scaffold"',
        '  last_updated: "2026-08-01"',
        "  runtime: Harness AI Agent",
        "  cli_applicability: dual-path",
        "  type: base",
        "  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, AWS_DEFAULT_REGION, AWS_PROFILE]",
    ]
    cross_deps = spec.get("cross_skill_deps") or []
    if cross_deps:
        metadata_lines.append(
            f"  cross_skill_deps: [{', '.join(cross_deps)}]"
        )
    if destructive:
        metadata_lines.extend([
            "  destructive_ops_require_confirm: true",
            "  gcl: {enabled: true, class: required, max_iter: 2, "
            "rubric_ref: references/rubric.md, prompts_ref: references/prompt-templates.md}",
        ])

    destructive_note = ""
    if destructive:
        ops = ", ".join(destructive)
        destructive_note = (
            f"\n\nDestructive operations ({ops}) require explicit human "
            "confirmation before Execute."
        )

    content = f"""---
name: {skill_name}
description: >-
  Use when operating AWS {product} {resource} resources via AWS CLI or boto3;
  user mentions {product} or {resource}.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
{chr(10).join(metadata_lines)}
---

# AWS {product} Operations Skill

## Common JSON Paths (Centralized)

```
{_primary_resource_json_path(resource)}
# Verify against {docs_url} and `aws {cli_ns} help`
```

## Overview

AWS {product} operational runbook (scaffold). Fill references from official docs.

## Trigger & Scope

### SHOULD Use When
- User mentions "{product}" or "{resource}"
- Task involves CRUD on **{resource}** via `aws {cli_ns}` or boto3 `{spec['boto3_module']}`

### SHOULD NOT Use When
- IAM-only tasks → delegate to `aws-iam-ops`
- Unrelated AWS services → delegate to the appropriate `aws-*-ops` skill

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{{{env.AWS_ACCESS_KEY_ID}}}}` | Runtime env | NEVER ask user; fail if unset |
| `{{{{env.AWS_SECRET_ACCESS_KEY}}}}` | Runtime env | NEVER ask user; fail if unset |
| `{{{{env.AWS_DEFAULT_REGION}}}}` | Runtime env | Use default only if skill allows |
| `{{{{user.region}}}}` | User input | Ask once; reuse |
| `{{{{user.resource_id}}}}` | User input | Ask once; reuse |
| `{{{{output.resource_id}}}}` | Last API response | Parse per AWS API docs |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**.{destructive_note}

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Per-operation CLI/SDK detail belongs in `references/aws-cli-usage.md` and
`references/boto3-sdk-usage.md`.

## Operations Index

| Operation | Detail |
|-----------|--------|
| List {resource} | references/aws-cli-usage.md |
| Describe {resource} | references/aws-cli-usage.md |

{CADL_HOOK}
"""
    (skill_path / "SKILL.md").write_text(content)


def _write_references(skill_path: Path, spec: dict) -> None:
    refs = skill_path / "references"
    product = spec["product_name"]
    cli_ns = spec["cli_namespace"]
    boto3_mod = spec["boto3_module"]
    docs_url = spec["docs_url"]
    resource = spec["primary_resource"]

    (refs / "aws-cli-usage.md").write_text(f"""# AWS CLI Usage — {product}

Official docs: {docs_url}

## Command Map (scaffold)

| Goal | CLI Command |
|------|-------------|
| List {resource} | `aws {cli_ns} list-* --output json` |
| Describe {resource} | `aws {cli_ns} describe-* --output json` |

Verify subcommands with `aws {cli_ns} help` before filling this file.
""")

    (refs / "boto3-sdk-usage.md").write_text(f"""# boto3 SDK Usage — {product}

Module: `{boto3_mod}`

```python
import boto3

client = boto3.client("{boto3_mod}", region_name="{{{{user.region}}}}")
# Fill methods from {docs_url}
```
""")

    (refs / "core-concepts.md").write_text(f"""# Core Concepts — {product}

Primary resource: **{resource}**

Reference: {docs_url}

<!-- Fill architecture, quotas, and IAM prerequisites from official docs. -->
""")

    (refs / "troubleshooting.md").write_text(f"""# Troubleshooting — {product}

| Error | Action |
|-------|--------|
| InvalidParameter (400) | Fix args; retry once |
| QuotaExceeded | HALT |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |
""")


def _write_example_config(skill_path: Path, spec: dict) -> None:
    resource = spec["primary_resource"]
    (skill_path / "assets" / "example-config.yaml").write_text(f"""# AWS {spec['product_name']} — Example Configuration (scaffold)

defaults:
  region: "{{{{env.AWS_DEFAULT_REGION}}}}"

{resource.lower()}:
  name: "{{{{user.resource_name}}}}"
  id: "{{{{user.resource_id}}}}"
""")


def _write_golden_scenarios(skill_path: Path, spec: dict) -> None:
    skill_name = skill_path.name
    resource = spec["primary_resource"]
    destructive = spec["destructive_ops"]
    lines = [
        "---",
        f"skill: {skill_name}",
        "description: |",
        f"  Golden evaluation suite (scaffold) for {skill_name} v0.0.0-scaffold.",
        "",
        "scenarios:",
    ]

    def add_scenario(
        sid: str,
        desc: str,
        request: str,
        status: str,
        *,
        confirm: str | None = None,
    ) -> None:
        lines.extend([
            f"  - id: {sid}",
            f"    description: {desc}",
            f"    request: {request}",
            f"    expected_status: {status}",
            "    user_region: us-east-1",
        ])
        if confirm is not None:
            lines.append(f'    safety_confirm: "{confirm}"')

    add_scenario(
        f"{spec['service_id']}-list",
        f"read-only list {resource}",
        f"list {resource} resources",
        "PASS",
    )
    add_scenario(
        f"{spec['service_id']}-describe",
        f"read-only describe {resource}",
        f"describe {resource} example-id",
        "PASS",
    )

    if destructive:
        op1 = destructive[0]
        op2 = destructive[1] if len(destructive) > 1 else destructive[0]
        add_scenario(
            f"{spec['service_id']}-destructive-confirmed-1",
            f"destructive {op1} with confirm token",
            f"{op1} example-id",
            "PASS",
            confirm=f"confirm={op1} example-id",
        )
        add_scenario(
            f"{spec['service_id']}-destructive-confirmed-2",
            f"destructive {op2} with confirm token",
            f"{op2} example-id-2",
            "PASS",
            confirm=f"confirm={op2} example-id-2",
        )
        add_scenario(
            f"{spec['service_id']}-destructive-no-confirm",
            f"destructive {op1} without confirm token",
            f"{op1} example-id",
            "SAFETY_FAIL",
            confirm="",
        )
    else:
        add_scenario(
            f"{spec['service_id']}-get",
            f"read-only get {resource}",
            f"get {resource} details for example-id",
            "PASS",
        )
        add_scenario(
            f"{spec['service_id']}-list-filtered",
            f"read-only filtered list {resource}",
            f"list {resource} resources in us-east-1",
            "PASS",
        )
        add_scenario(
            f"{spec['service_id']}-idempotent-list",
            f"idempotency — repeat list {resource}",
            f"list {resource} resources",
            "PASS",
        )

    (skill_path / "golden-scenarios.yaml").write_text("\n".join(lines) + "\n")


def _write_rubric(skill_path: Path, spec: dict) -> None:
    from _gen_rubric import TEMPLATE  # noqa: WPS433 — repo-local helper

    skill_name = skill_path.name
    max_iter = 3 if spec.get("gcl_tier") == "recommended" else 2
    out = skill_path / "references" / "rubric.md"
    out.write_text(
        TEMPLATE.format(
            skill=skill_name,
            service=spec["product_name"],
            aws_cli_svc=spec["cli_namespace"],
            max_iter=max_iter,
        )
    )


def _write_prompt_templates(skill_path: Path, spec: dict) -> None:
    skill_name = skill_path.name
    text = PROMPT_TEMPLATE.read_text()
    text = text.replace("<SKILL_NAME>", skill_name)
    text = text.replace("<SERVICE>", spec["boto3_module"])
    text = text.replace("<AWS_CLI_SVC>", spec["cli_namespace"])
    max_iter = "3" if spec.get("gcl_tier") == "recommended" else "2"
    text = text.replace("<2|3>", max_iter)
    text = text.replace("<YYYY-MM-DD>", "2026-08-01")
    (skill_path / "references" / "prompt-templates.md").write_text(text)


def init(spec: dict, out_dir: Path) -> Path:
    """Scaffold skill directory tree; return created skill path."""
    validate_spec(spec)
    skill_path = out_dir / skill_dir_name(spec["service_id"])
    if skill_path.exists():
        raise SpecValidationError(f"skill directory already exists: {skill_path}")

    (skill_path / "references").mkdir(parents=True)
    (skill_path / "assets").mkdir()

    _write_skill_md(skill_path, spec)
    _write_references(skill_path, spec)
    _write_example_config(skill_path, spec)
    _write_golden_scenarios(skill_path, spec)
    (skill_path / "service-spec.json").write_text(
        json.dumps(spec, indent=2) + "\n"
    )

    if spec["destructive_ops"]:
        _write_rubric(skill_path, spec)
        _write_prompt_templates(skill_path, spec)

    return skill_path


def _load_spec(path: Path) -> dict:
    return json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mechanical AWS skill scaffold")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Scaffold skill from ServiceSpec JSON")
    init_p.add_argument("--spec", type=Path, required=True, help="ServiceSpec JSON")
    init_p.add_argument("--out", type=Path, required=True, help="Output directory")

    args = parser.parse_args(argv)

    if args.command == "init":
        try:
            spec = _load_spec(args.spec)
            created = init(spec, args.out)
        except (SpecValidationError, json.JSONDecodeError, OSError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(created)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
