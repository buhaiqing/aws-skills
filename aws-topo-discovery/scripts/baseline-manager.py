#!/usr/bin/env python3
"""CLI entry point for aws-topo-discovery baseline management.

Runs topo-scan.sh to collect real infrastructure data, then archives
the output into a date-stamped baseline directory for drift detection.

Usage:
    python baseline-manager.py --output-dir ./infra-baseline/
    python baseline-manager.py --output-dir ./infra-baseline/ --region us-east-1
    python baseline-manager.py --output-dir ./infra-baseline/ --retention-days 90 --apply-retention
    python baseline-manager.py --output-dir ./infra-baseline/ --diff
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from lib.baseline_local import LocalBackend


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Manage periodic infrastructure baseline snapshots",
    )
    parser.add_argument("--output-dir", default="./infra-baseline",
                        help="Root directory for all baselines")
    parser.add_argument("--region", default=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
                        help="AWS region (default: env or us-east-1)")
    parser.add_argument("--retention-days", type=int, default=90,
                        help="Days to keep (default: 90)")
    parser.add_argument("--apply-retention", action="store_true",
                        help="Apply retention expiry")
    parser.add_argument("--diff", action="store_true",
                        help="Compare current state with latest baseline")
    parser.add_argument("--compare-with", default=None, metavar="YYYY-MM-DD",
                        help="With --diff, compare against this historical baseline")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing baseline directories")
    return parser.parse_args(argv)


def _run_topo_scan(region: str, output_dir: Path) -> dict:
    script_dir = Path(__file__).resolve().parent
    topo_sh = script_dir / "topo-scan.sh"

    if not topo_sh.exists():
        print(f"[ERROR] topo-scan.sh not found at {topo_sh}", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(tempfile.mkdtemp(prefix="topo_baseline_", dir="/tmp"))
    scan_output = output_dir / ".scan_tmp"
    scan_output.mkdir(parents=True, exist_ok=True)

    env = {**os.environ}
    if "AWS_DEFAULT_REGION" not in env:
        env["AWS_DEFAULT_REGION"] = region

    print(f"[INFO] Running topo-scan.sh (region={region})...")
    result = subprocess.run(
        [str(topo_sh), "--mode", "brief", "--output-dir", str(scan_output),
         "--format", "both", "--region", region, "--tmp-dir", str(data_dir)],
        capture_output=True, text=True, timeout=120, env=env,
    )

    if result.returncode != 0:
        print(f"[WARN] topo-scan.sh exit={result.returncode}: {result.stderr[:300]}")

    resource_counts = {}
    resources = {}

    scan_files = {
        "VPC": "vpcs.json",
        "Subnet": "subnets.json",
        "ELB": "elbs.json",
        "NAT": "nats.json",
        "EIP": "eips.json",
        "EC2": "ec2.json",
        "SecurityGroup": "sgs.json",
        "RDS": "rds.json",
    }

    for rtype, fname in scan_files.items():
        fpath = data_dir / fname
        if not fpath.exists():
            continue
        try:
            data = json.loads(fpath.read_text())
        except (json.JSONDecodeError, Exception):
            continue
        items = _extract_items(data, rtype)
        if items:
            resource_counts[rtype] = len(items)
            resources[rtype] = items

    report_path = scan_output / "report.md"
    if report_path.exists():
        print(f"[INFO] Topology report generated: {report_path}")

    shutil.rmtree(str(scan_output), ignore_errors=True)
    shutil.rmtree(str(data_dir), ignore_errors=True)

    return {
        "resource_counts": resource_counts,
        "resources": resources,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _extract_items(data: dict, rtype: str) -> list:
    if rtype == "VPC":
        return data.get("Vpcs", [])
    elif rtype == "Subnet":
        return data.get("Subnets", [])
    elif rtype == "ELB":
        return data.get("LoadBalancers", [])
    elif rtype == "NAT":
        return data.get("NatGateways", [])
    elif rtype == "EIP":
        return data.get("Addresses", [])
    elif rtype == "EC2":
        instances = []
        for res in data.get("Reservations", []):
            instances.extend(res.get("Instances", []))
        return instances
    elif rtype == "SecurityGroup":
        return data.get("SecurityGroups", [])
    elif rtype == "RDS":
        return data.get("DBInstances", [])
    return []


def _get_account_id() -> str:
    try:
        r = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--output", "json"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return json.loads(r.stdout).get("Account", "unknown")
    except Exception:
        pass
    return "unknown"


def _build_manifest(inventory: dict, region: str) -> dict:
    return {
        "schema_version": "1.0",
        "generator": "aws-topo-discovery",
        "generator_version": "1.0.0",
        "generated_at": inventory["timestamp"],
        "account_id": _get_account_id(),
        "region": region,
        "scope": "all",
        "resource_count": sum(inventory["resource_counts"].values()),
        "by_type": inventory["resource_counts"],
        "resource_ids": {
            rtype: [
                item.get("InstanceId") or item.get("VpcId") or item.get("SubnetId")
                or item.get("LoadBalancerArn") or item.get("AllocationId")
                or item.get("NatGatewayId") or item.get("GroupId")
                or item.get("DBInstanceIdentifier") or ""
                for item in items
            ]
            for rtype, items in inventory["resources"].items()
        },
        "execution_time_ms": 0,
    }


def _compute_diff(current: dict, baseline: dict) -> list:
    changes = []
    current_counts = current.get("by_type", {})
    baseline_counts = baseline.get("by_type", {})

    all_types = set(list(current_counts.keys()) + list(baseline_counts.keys()))
    for rtype in sorted(all_types):
        c = current_counts.get(rtype, 0)
        b = baseline_counts.get(rtype, 0)
        if c > b:
            changes.append(f"[ADDED] {rtype}: {b} -> {c} (+{c-b})")
        elif c < b:
            changes.append(f"[REMOVED] {rtype}: {b} -> {c} (-{b-c})")

    current_ids = set()
    for ids in current.get("resource_ids", {}).values():
        current_ids.update(i for i in ids if i)
    baseline_ids = set()
    for ids in baseline.get("resource_ids", {}).values():
        baseline_ids.update(i for i in ids if i)

    added = current_ids - baseline_ids
    removed = baseline_ids - current_ids
    for rid in sorted(added):
        rtype = _guess_resource_type(rid)
        changes.append(f"[ADDED] {rtype} {rid}")
    for rid in sorted(removed):
        rtype = _guess_resource_type(rid)
        changes.append(f"[REMOVED] {rtype} {rid}")

    return changes


def _guess_resource_type(rid: str) -> str:
    if not rid:
        return "Unknown"
    type_map = {
        "vpc-": "VPC", "subnet-": "Subnet", "i-": "EC2",
        "arn:aws:elasticloadbalancing": "ELB",
        "nat-": "NAT", "eipalloc-": "EIP",
        "sg-": "SecurityGroup", "alloc-": "EIP",
    }
    for key, val in type_map.items():
        if rid.startswith(key):
            return val
    return "Unknown"


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory = _run_topo_scan(args.region, output_dir)
    total = sum(inventory["resource_counts"].values())
    print(f"[INFO] Discovered {total} resources across {len(inventory['resource_counts'])} types")
    for rtype, count in sorted(inventory["resource_counts"].items()):
        print(f"       {rtype}: {count}")

    if args.diff:
        backend = LocalBackend(root_dir=output_dir)
        compared_with_label = "latest"
        if args.compare_with:
            baseline_dir = backend.get_by_date(args.compare_with)
            if baseline_dir is None:
                print(f"[ERROR] No baseline found for date: {args.compare_with}")
                sys.exit(2)
            compared_with_label = args.compare_with
        else:
            baseline_dir = backend.get_latest()
            if baseline_dir is not None:
                compared_with_label = baseline_dir.name

        if baseline_dir is None:
            print("[INFO] No previous baseline found (this is the first one)")
        else:
            latest_manifest = baseline_dir / "manifest.json"
            if latest_manifest.exists():
                baseline_data = json.loads(latest_manifest.read_text())
                changes = _compute_diff(
                    _build_manifest(inventory, args.region),
                    baseline_data,
                )
                if changes:
                    print(f"\n=== Drift Detection: {len(changes)} changes "
                          f"(vs {compared_with_label}) ===")
                    for c in changes:
                        print(f"  {c}")
                else:
                    print(f"\n=== No drift detected (vs {compared_with_label}) ===")
        return

    snapshot_dir = output_dir / ".snapshot"
    if snapshot_dir.exists():
        shutil.rmtree(str(snapshot_dir))
    snapshot_dir.mkdir(parents=True)

    manifest = _build_manifest(inventory, args.region)
    (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (snapshot_dir / "inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False, default=str)
    )

    summary_lines = [
        f"# Infrastructure Baseline Snapshot",
        f"",
        f"**Date**: {manifest['generated_at']}",
        f"**Account**: {manifest['account_id']}",
        f"**Region**: {manifest['region']}",
        f"**Total Resources**: {manifest['resource_count']}",
        f"",
        f"## Resource Counts",
        f"",
        f"| Type | Count |",
        f"|------|:-----:|",
    ]
    for rtype, count in sorted(inventory["resource_counts"].items()):
        summary_lines.append(f"| {rtype} | {count} |")
    summary_lines.append("")
    summary_lines.append("## Resource IDs")
    summary_lines.append("")
    for rtype, ids in manifest["resource_ids"].items():
        for rid in ids:
            summary_lines.append(f"- {rtype}: `{rid}`")
    summary_lines.append("")
    summary_lines.append("---")
    summary_lines.append("*Generated by aws-topo-discovery baseline-manager*")
    (snapshot_dir / "summary.md").write_text("\n".join(summary_lines))

    for fname in ["provider.tf", "main.tf", "outputs.tf", "variables.tf"]:
        (snapshot_dir / fname).write_text(f"# {fname} - placeholder for baseline {date.today()}\n")

    backend = LocalBackend(root_dir=output_dir)
    new_baseline = backend.write_baseline(snapshot_dir)

    expired = []
    if args.apply_retention:
        expired = backend.apply_retention(retention_days=args.retention_days)

    baselines = backend.list_baselines()
    print(f"\n[SUMMARY] Baseline written: {new_baseline.name}")
    print(f"[SUMMARY] Total resources: {total}")
    print(f"[SUMMARY] Total baselines: {len(baselines)}")
    if expired:
        print(f"[SUMMARY] Expired: {len(expired)}")

    shutil.rmtree(str(snapshot_dir), ignore_errors=True)


if __name__ == "__main__":
    main()
