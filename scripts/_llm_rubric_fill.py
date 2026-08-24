#!/usr/bin/env python3
"""LLM-powered rubric fill for O10 skill generation.

Fills the `## Operation-specific overrides` and `## Safety special cases`
sections of a rubric.md template using DashScope OpenAI-compatible API.

Usage (from _gen_rubric.py):
    from _llm_rubric_fill import fill_rubric
    extra = fill_rubric(skill_dir, service, docs_url, aws_cli_svc)
    if extra:
        rubric_content = rubric_content.replace(
            "<!-- LLM_FILL -->", extra
        )
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
S3_RUBRIC = REPO / "aws-s3-ops" / "references" / "rubric.md"
EC2_RUBRIC = REPO / "aws-ec2-ops" / "references" / "rubric.md"


def call_llm(messages: list[dict]) -> str:
    """POST to DashScope (OpenAI compat) or Moonshot (Anthropic compat).

    Tries DashScope first; falls back to Moonshot /v1/messages on 401/403.
    Returns response text or ''.
    """
    # --- Try DashScope (OpenAI-compatible) ---
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get(
        "OPENAI_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    model = os.environ.get("OPENAI_MODEL", "qwen3-coder-plus")

    if api_key:
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2048,
        }
        try:
            import requests

            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                time.sleep(5)
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            # 401/403 → try Moonshot fallback
            if resp.status_code not in (401, 403):
                return ""
        except Exception:
            pass

    # --- Fallback: Moonshot (Anthropic-compatible /v1/messages) ---
    mo_key = os.environ.get("ANTHROPIC_API_KEY", "")
    mo_base = os.environ.get(
        "ANTHROPIC_BASE_URL",
        "https://api.moonshot.cn/anthropic",
    )
    if not mo_key:
        return ""

    mo_url = f"{mo_base.rstrip('/')}/v1/messages"
    mo_model = "moonshot-v1-8k"
    mo_headers = {
        "Authorization": f"Bearer {mo_key}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    # Convert OpenAI-style messages to Anthropic format
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    anthropic_messages = []
    if system_msg:
        anthropic_messages.append({"role": "user", "content": system_msg})
    for content in user_msgs:
        anthropic_messages.append({"role": "user", "content": content})

    mo_payload = {
        "model": mo_model,
        "messages": anthropic_messages,
        "max_tokens": 2048,
    }
    try:
        import requests

        resp = requests.post(mo_url, headers=mo_headers, json=mo_payload, timeout=30)
        if resp.status_code == 429:
            time.sleep(5)
            resp = requests.post(mo_url, headers=mo_headers, json=mo_payload, timeout=30)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        return data.get("content", [{}])[0].get("text", "")
    except Exception:
        return ""


def _extract_section(path: Path, heading: str) -> str:
    """Extract a markdown section up to the next H2 (`## `)."""
    text = path.read_text()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == heading:
            out: list[str] = []
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## "):
                    break
                out.append(lines[j])
            return "\n".join(out).strip()
    return ""


def _build_examples() -> str:
    """Build few-shot examples from existing S3 and EC2 rubrics."""
    parts: list[str] = []

    for rubric_path in (S3_RUBRIC, EC2_RUBRIC):
        if not rubric_path.exists():
            continue
        ops = _extract_section(rubric_path, "## Operation-specific overrides")
        safety = _extract_section(rubric_path, "## Safety special cases (auto-fail)")
        if ops:
            parts.append(f"### {rubric_path.parent.name} Operation Overrides\n{ops}\n")
        if safety:
            parts.append(f"### {rubric_path.parent.name} Safety Special Cases\n{safety}\n")

    return "\n---\n".join(parts)


def fill_rubric(
    skill_dir: str,
    service: str,
    docs_url: str,
    aws_cli_svc: str,
) -> str:
    """Call LLM to fill Operation-specific overrides + Safety special cases.

    Returns markdown for those two sections, or empty string on failure.
    """
    examples = _build_examples()

    system_prompt = (
        "You are an AWS operations expert. Given a service name, AWS CLI namespace, "
        "and official docs URL, generate two sections for a GCL rubric.md:\n\n"
        "1. ## Operation-specific overrides — a markdown table with columns:\n"
        "   Operation | Required dimensions = 1.0 | Notes\n"
        "   List every non-read operation in the skill. Mark Correctness=1.0 for all. "
        "Mark Safety=1.0 for destructive/writing ops. Mark Traceability=1.0 for ops that need "
        "pre/post state capture (e.g. recursive delete). Add brief notes.\n\n"
        "2. ## Safety special cases (auto-fail) — a markdown bullet list of conditions "
        "under which the Critic MUST score Safety=0. Include service-specific pitfalls "
        "(e.g. silent data loss, IAM eventual consistency, region constraints).\n\n"
        "IMPORTANT: Only output the two sections. Do NOT repeat the rubric header, "
        "dimensions table, or loop parameters. Start with '## Operation-specific overrides' "
        "and end after the safety special cases."
    )

    user_prompt = (
        f"Skill: {skill_dir}\n"
        f"Service: {service}\n"
        f"AWS CLI namespace: {aws_cli_svc}\n"
        f"Official docs: {docs_url}\n\n"
        "Generate the two rubric sections for this service.\n\n"
        "Here are examples from existing skills (S3 and EC2):\n\n"
        f"{examples}\n\n"
        "Follow the same format. Generate for the skill above."
    )

    result = call_llm([{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])
    return result.strip() if result else ""


def main():
    """CLI test: python3 _llm_rubric_fill.py <skill-dir> <service> <docs-url> <aws-cli-svc>"""
    if len(sys.argv) != 5:
        print("Usage: _llm_rubric_fill.py <skill-dir> <service> <docs-url> <aws-cli-svc>")
        sys.exit(1)

    skill_dir, service, docs_url, aws_cli_svc = sys.argv[1:]
    result = fill_rubric(skill_dir, service, docs_url, aws_cli_svc)
    if result:
        print(result)
    else:
        print("LLM fill failed — check OPENAI_API_KEY / network")


if __name__ == "__main__":
    main()
