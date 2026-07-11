#!/usr/bin/env python3
"""daily-health-check.py — AWS-native full-chain health patrol v1.8."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import uuid
from pathlib import Path

from _audit import (
    audit_acm_expiry,
    audit_alb_target_health,
    audit_guardduty,
    audit_public_sg_rules,
)
from _aws_native import collect_aws_native_insights
from _inference import apply_chain_inference, correlate_native_findings
from _report import build_aiops_context, render_markdown_report
from _shared import (
    COMMAND_TRACE,
    PRODUCTS,
    collect_inventory,
    jq_filter,
    log,
    parallel_metric_scan,
    preflight,
    resolve_output_dir,
    resolve_scope_ids,
    reverse_lookup_scope,
    run_aws,
)


def assume_role_if_needed(role_arn: str, region: str) -> None:
    if not role_arn:
        return
    data = run_aws(
        [
            "aws",
            "sts",
            "assume-role",
            "--role-arn",
            role_arn,
            "--role-session-name",
            "aws-aiops-cruise",
            "--duration-seconds",
            "3600",
        ],
        region,
    )
    if not data or "Credentials" not in data:
        raise SystemExit("[ERROR] AssumeRole failed")
    cred = data["Credentials"]
    os.environ["AWS_ACCESS_KEY_ID"] = cred["AccessKeyId"]
    os.environ["AWS_SECRET_ACCESS_KEY"] = cred["SecretAccessKey"]
    os.environ["AWS_SESSION_TOKEN"] = cred["SessionToken"]
    log("INFO", f"Assumed role {role_arn}")


def parse_regions(region_arg: str) -> list[str]:
    if not region_arg:
        return [os.environ.get("AWS_DEFAULT_REGION", "us-east-1")]
    return [r.strip() for r in region_arg.split(",") if r.strip()]


def grade(incidents: list[dict]) -> str:
    if any(i["level"] == "CRITICAL" for i in incidents):
        return "CRITICAL"
    if any(i["level"] == "WARNING" for i in incidents):
        return "WARNING"
    return "PASS"


def patrol_region(
    region: str,
    scope_ids: set[str],
    run_id: str,
    customer: str,
    args: argparse.Namespace,
) -> tuple[list[dict], dict, dict, list[dict], list[str]]:
    incidents: list[dict] = []
    inventory: dict = {}
    signals: dict = {}
    risk_evidence: list[dict] = []
    inference_lines: list[str] = []

    inv = collect_inventory(region, scope_ids)
    for k, v in inv.items():
        inventory[k] = inventory.get(k, 0) + v

    inc, sig, risk = parallel_metric_scan(
        region, scope_ids, run_id, customer, enable_wow=not args.no_wow
    )
    incidents.extend(inc)
    risk_evidence.extend(risk)
    for layer, resources in sig.items():
        signals.setdefault(layer, {}).update(resources)

    if not args.skip_security:
        incidents.extend(audit_public_sg_rules(region, scope_ids, run_id, customer))
        incidents.extend(audit_alb_target_health(region, scope_ids, run_id, customer))
        incidents.extend(audit_acm_expiry(region, 30, run_id, customer))
        incidents.extend(audit_guardduty(region, run_id, customer))

    native_inc, native_meta, native_signals = collect_aws_native_insights(
        region,
        scope_ids,
        run_id,
        customer,
        enable_pi=not args.no_pi,
        enable_guru=not args.no_guru,
        enable_cloudfront=not args.no_cloudfront,
        enable_xray=args.enable_xray,
        enable_rds_proxy=not args.no_rds_proxy,
    )
    incidents.extend(native_inc)
    for layer, resources in native_signals.items():
        signals.setdefault(layer, {}).update(resources)

    existing = {i["rule_id"] for i in incidents}
    chain_inc, lines = apply_chain_inference(
        signals, run_id=run_id, customer=customer, region=region, existing_rule_ids=existing
    )
    incidents.extend(chain_inc)
    inference_lines.extend(lines)
    existing = {i["rule_id"] for i in incidents}
    _, native_lines = correlate_native_findings(
        incidents, run_id=run_id, customer=customer, region=region, existing_rule_ids=existing
    )
    inference_lines.extend(native_lines)

    return incidents, inventory, native_meta, risk_evidence, inference_lines


def main() -> int:
    p = argparse.ArgumentParser(description="AWS-native daily health cruise")
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--resource-id", default="")
    p.add_argument("--region", default="", help="Single region or comma-separated")
    p.add_argument("--assume-role", default="", help="Cross-account role ARN")
    p.add_argument("--output-dir", default="")
    p.add_argument("--non-interactive", action="store_true")
    p.add_argument("--scope-full", action="store_true")
    p.add_argument("--skip-security", action="store_true")
    p.add_argument("--no-wow", action="store_true")
    p.add_argument("--no-pi", action="store_true", help="Skip RDS Performance Insights")
    p.add_argument("--no-guru", action="store_true", help="Skip DevOps Guru")
    p.add_argument("--no-cloudfront", action="store_true", help="Skip CloudFront edge metrics")
    p.add_argument("--no-rds-proxy", action="store_true", help="Skip RDS Proxy connection path")
    p.add_argument("--enable-xray", action="store_true", help="Include X-Ray service graph (last 1h)")
    p.add_argument(
        "--render-topology",
        action="store_true",
        help="After patrol, render aws-topo-discovery report with health overlay",
    )
    p.add_argument("--topo-mode", choices=("brief", "detailed"), default="detailed")
    args = p.parse_args()

    assume_role_if_needed(args.assume_role, os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    regions = parse_regions(args.region)

    if not args.resource_group and not (args.tag_key and args.tag_value) and not args.resource_id:
        if not args.scope_full:
            log("ERROR", "Scope required: --resource-group, tags, or --resource-id")
            return 2

    customer = args.resource_group or (
        f"{args.tag_key}={args.tag_value}" if args.tag_key else args.resource_id or "full-account"
    )
    run_id = str(uuid.uuid4())
    trace_id = run_id[:12]
    out_dir = resolve_output_dir(args.output_dir or None)

    ident = preflight(regions[0])
    log("INFO", f"Account {ident.get('Account')} | regions={regions} | scope={customer}")

    scope_ids: set[str] = set()
    for region in regions:
        scope_ids |= resolve_scope_ids(region, args.resource_group, args.tag_key, args.tag_value)

    if args.resource_id:
        tk, tv, expanded = reverse_lookup_scope(regions[0], args.resource_id)
        scope_ids |= expanded
        if tk:
            for region in regions:
                scope_ids |= resolve_scope_ids(region, "", tk, tv)

    if args.scope_full:
        log("WARN", "scope=full confirmed")
        for region in regions:
            for prod in PRODUCTS:
                data = run_aws(prod["list"], region)
                if not data:
                    continue
                if prod.get("id_flat"):
                    for n in data.get("TableNames", []):
                        scope_ids.add(n)
                else:
                    for item in jq_filter(data, prod.get("jq", ".")):
                        rid = item.get(prod["id"], "") if isinstance(item, dict) else str(item)
                        if rid:
                            scope_ids.add(rid)

    if not scope_ids:
        log("ERROR", "Empty scope")
        return 2

    all_incidents: list[dict] = []
    inventory: dict = {}
    all_risk: list[dict] = []
    all_inference: list[str] = []
    native_collectors: list[dict] = []

    for region in regions:
        log("INFO", f"Patrol region: {region}")
        inc, inv, nmeta, risk, inf = patrol_region(region, scope_ids, run_id, customer, args)
        all_incidents.extend(inc)
        for k, v in inv.items():
            inventory[k] = inventory.get(k, 0) + v
        all_risk.extend(risk)
        all_inference.extend(inf)
        native_collectors.append({"region": region, **nmeta})

    overall = grade(all_incidents)
    critical_n = sum(1 for i in all_incidents if i["level"] == "CRITICAL")
    aiops_ctx = build_aiops_context(
        run_id=run_id,
        trace_id=trace_id,
        status="ok" if overall == "PASS" else ("partial" if overall == "WARNING" else "failed"),
        summary=f"AWS cruise {overall}: {len(all_incidents)} findings across {len(regions)} region(s)",
        incidents=all_incidents,
        region=",".join(regions),
    )

    report = {
        "run_id": run_id,
        "schema_version": "2.0.0",
        "scenario": "daily_check",
        "customer": customer,
        "regions": regions,
        "overall_grade": overall,
        "inventory": inventory,
        "incident_count": len(all_incidents),
        "incidents": all_incidents,
        "risk_evidence": all_risk[:300],
        "chain_inference": all_inference,
        "aws_native_collectors": native_collectors,
        "aiops_context": aiops_ctx,
        "trace": {"commands_executed": COMMAND_TRACE[:120], "account": ident.get("Account")},
    }

    json_path = out_dir / f"cruise-{run_id[:8]}.json"
    md_path = out_dir / f"cruise-{run_id[:8]}.md"
    topo_dir = ""
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    if args.render_topology:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "cruise_topo_render",
            Path(__file__).parent / "cruise-topo-render.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        topo_dir = str(out_dir / "topology")
        topo_rc = mod.render_from_cruise_report(
            json_path,
            region=regions[0],
            output_dir=topo_dir,
            mode=args.topo_mode,
            assume_role=args.assume_role,
        )
        report["topology"] = {"output_dir": topo_dir, "exit_code": topo_rc}
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        if topo_rc != 0:
            log("WARN", f"Topology render exit {topo_rc}")

    md_path.write_text(
        render_markdown_report(
            customer=customer,
            region=",".join(regions),
            overall=overall,
            incidents=all_incidents,
            inventory=inventory,
            inference_lines=all_inference,
            run_id=run_id,
            topology_dir=topo_dir,
        )
    )

    log("INFO", f"Report: {json_path} | grade={overall}")
    if critical_n >= 3:
        log("INFO", "Escalate → aws-aiops-orchestrator (≥3 CRITICAL)")
    print("\naiops_context:" + json.dumps(aiops_ctx, indent=2))
    return 0 if overall != "CRITICAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
