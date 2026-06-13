#!/usr/bin/env python3
"""emergency-troubleshoot.py — fast chain RCA (read-only, 1h focus)."""

from __future__ import annotations

import argparse
import json
import os
import uuid

from _audit import audit_alb_target_health
from _aws_native import collect_aws_native_insights
from _inference import apply_chain_inference, correlate_native_findings
from _report import build_aiops_context, render_markdown_report
from _shared import (
    COMMAND_TRACE,
    log,
    parallel_metric_scan,
    preflight,
    resolve_output_dir,
    resolve_scope_ids,
    run_aws,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--region", default="")
    p.add_argument("--symptom", default="unknown")
    p.add_argument("--output-dir", default="")
    p.add_argument("--non-interactive", action="store_true")
    args = p.parse_args()

    region = args.region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    customer = args.resource_group or f"{args.tag_key}={args.tag_value}"
    run_id = str(uuid.uuid4())
    out_dir = resolve_output_dir(args.output_dir or None)

    ident = preflight(region)
    scope_ids = resolve_scope_ids(region, args.resource_group, args.tag_key, args.tag_value)
    if not scope_ids:
        log("ERROR", "Empty scope")
        return 2

    log("INFO", f"Emergency: symptom={args.symptom} scope={customer}")

    incidents, signals, _ = parallel_metric_scan(
        region, scope_ids, run_id, customer, enable_wow=False, max_workers=12
    )
    incidents.extend(audit_alb_target_health(region, scope_ids, run_id, customer))

    sym = args.symptom.lower()
    use_xray = any(k in sym for k in ("502", "5xx", "latency", "timeout", "slow"))
    native_inc, _ = collect_aws_native_insights(
        region,
        scope_ids,
        run_id,
        customer,
        enable_pi=True,
        enable_guru=False,
        enable_cloudfront=use_xray or "502" in sym,
        enable_xray=use_xray,
        enable_rds_proxy=True,
    )
    incidents.extend(native_inc)

    # CloudTrail 1h window
    run_aws(
        [
            "aws",
            "cloudtrail",
            "lookup-events",
            "--max-results",
            "50",
        ],
        region,
    )

    chain_incidents, inference_lines = apply_chain_inference(
        signals,
        run_id=run_id,
        customer=customer,
        region=region,
        existing_rule_ids={i["rule_id"] for i in incidents},
    )
    incidents.extend(chain_incidents)
    _, native_lines = correlate_native_findings(
        incidents,
        run_id=run_id,
        customer=customer,
        region=region,
        existing_rule_ids={i["rule_id"] for i in incidents},
    )
    inference_lines.extend(native_lines)

    # Symptom-specific hint
    if "502" in args.symptom or "5xx" in args.symptom.lower():
        inference_lines.insert(0, f"- **Symptom anchor**: `{args.symptom}` → prioritize ALB target health + RDS connections")

    critical = sum(1 for i in incidents if i["level"] == "CRITICAL")
    overall = "CRITICAL" if critical else ("WARNING" if incidents else "PASS")
    aiops_ctx = build_aiops_context(
        run_id=run_id,
        trace_id=run_id[:12],
        status="partial" if incidents else "ok",
        summary=f"Emergency troubleshoot ({args.symptom}): {len(incidents)} findings",
        incidents=incidents,
        region=region,
    )
    if critical >= 3:
        aiops_ctx["next_skill"] = "aws-aiops-orchestrator"

    report = {
        "run_id": run_id,
        "scenario": "emergency",
        "symptom": args.symptom,
        "overall_grade": overall,
        "incidents": incidents,
        "chain_inference": inference_lines,
        "aiops_context": aiops_ctx,
        "trace": {"commands_executed": COMMAND_TRACE[:80], "account": ident.get("Account")},
    }
    json_path = out_dir / f"emergency-{run_id[:8]}.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    md_path = out_dir / f"emergency-{run_id[:8]}.md"
    md_path.write_text(
        render_markdown_report(
            customer=customer,
            region=region,
            overall=overall,
            incidents=incidents,
            inventory={},
            inference_lines=inference_lines,
            run_id=run_id,
        )
    )
    log("INFO", f"Emergency report: {json_path}")
    print("\naiops_context:" + json.dumps(aiops_ctx, indent=2))
    return 0 if overall != "CRITICAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
