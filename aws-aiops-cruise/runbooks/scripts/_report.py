#!/usr/bin/env python3
"""Report builders: aiops_context envelope + markdown."""

from __future__ import annotations

from typing import Any


def build_aiops_context(
    *,
    run_id: str,
    trace_id: str,
    status: str,
    summary: str,
    incidents: list[dict[str, Any]],
    region: str,
) -> dict[str, Any]:
    facts: list[dict[str, Any]] = []
    facts_info: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    for inc in incidents:
        level = inc.get("level", "INFO")
        entry = {
            "kind": "finding",
            "subject": inc.get("resource_id"),
            "name": inc.get("rule_id"),
            "value": inc.get("current_value"),
            "window": "last_6h",
            "severity": level.lower(),
            "tags": {"resource_type": inc.get("resource_type"), "region": region},
        }
        if level == "INFO":
            facts_info.append(entry)
            continue
        facts.append(entry)
        if level in ("CRITICAL", "WARNING"):
            anomalies.append(
                {
                    "rule_id": inc.get("rule_id"),
                    "subject": inc.get("resource_id"),
                    "description": inc.get("title"),
                    "first_seen": inc.get("timestamp"),
                    "confidence": 0.85 if level == "CRITICAL" else 0.7,
                }
            )
        if inc.get("recommendation") and level in ("CRITICAL", "WARNING"):
            tier = "MANUAL" if level == "CRITICAL" else "AI_ASSIST"
            recommendations.append(
                {
                    "tier": tier,
                    "action": inc.get("recommendation"),
                    "rationale": inc.get("title"),
                    "blast_radius": [inc.get("resource_id")],
                    "estimated_cost_delta_usd": 0.0,
                    "rollback": "N/A — read-only patrol",
                }
            )
    return {
        "skill": "aws-aiops-cruise",
        "request_id": run_id,
        "trace_id": trace_id,
        "status": status,
        "summary": summary,
        "facts": facts,
        "facts_info": facts_info[:50],
        "anomalies": anomalies,
        "recommendations": recommendations,
        "next_skill": "aws-aiops-orchestrator"
        if sum(1 for i in incidents if i.get("level") == "CRITICAL") >= 3
        else None,
    }


def render_markdown_report(
    *,
    customer: str,
    region: str,
    overall: str,
    incidents: list[dict],
    inventory: dict[str, int],
    inference_lines: list[str],
    run_id: str,
    topology_dir: str = "",
) -> str:
    lines = [
        f"# AWS Health Cruise — {customer}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Grade | **{overall}** |",
        f"| Region | {region} |",
        f"| Run ID | `{run_id}` |",
        f"| Incidents | {len(incidents)} |",
        "",
    ]
    if topology_dir:
        lines.extend(
            [
                "## Topology",
                "",
                f"Health overlay render: [`{topology_dir}/report.md`]({topology_dir}/report.md)",
                "",
            ]
        )
    lines.append("## Inventory")
    lines.append("")
    for k, v in sorted(inventory.items()):
        lines.append(f"- **{k}**: {v}")
    lines.extend(["", "## Chain inference", ""])
    if inference_lines:
        lines.extend(inference_lines)
    else:
        lines.append("_No cross-layer patterns triggered._")
    lines.extend(["", "## Findings", ""])
    for inc in incidents[:100]:
        lines.append(
            f"- **[{inc['level']}]** {inc['title']} — `{inc['resource_id']}` (`{inc['rule_id']}`)"
        )
    return "\n".join(lines) + "\n"
