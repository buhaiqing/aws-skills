#!/usr/bin/env python3
"""Convert cruise incidents → topo-discovery health overlay + invoke topo-scan."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from _shared import log

SEVERITY = {"CRITICAL": 3, "WARNING": 2, "INFO": 1, "PASS": 0}


def build_health_overlay(incidents: list[dict]) -> dict[str, dict]:
    """Map resource identifiers to topo-render health overlay entries."""
    overlay: dict[str, dict] = {}

    def _merge(key: str, entry: dict) -> None:
        if not key:
            return
        cur = overlay.get(key)
        if not cur or SEVERITY.get(entry["level"], 0) > SEVERITY.get(cur.get("level"), 0):
            overlay[key] = entry

    for inc in incidents:
        rid = str(inc.get("resource_id", ""))
        level = inc.get("level", "INFO")
        entry = {
            "level": level,
            "type": inc.get("resource_type", ""),
            "rule_id": inc.get("rule_id", ""),
            "title": (inc.get("title") or "")[:200],
            "z_score": 3.0 if level == "CRITICAL" else (2.0 if level == "WARNING" else 0.0),
        }
        keys = {rid}
        if "/" in rid:
            keys.add(rid.split("/")[-1])
            keys.add("/".join(rid.split("/")[-2:]))  # app/name/id for ALB
        if ":" in rid:
            keys.add(rid.split(":")[-1])
        # Load balancer name from ARN path
        if "loadbalancer/" in rid:
            parts = rid.split("/")
            if len(parts) >= 2:
                keys.add(parts[1])  # load balancer name
        _merge(rid, entry)
        for k in keys:
            _merge(k, entry)
    return overlay


def write_health_json(incidents: list[dict], path: Path) -> Path:
    overlay = build_health_overlay(incidents)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overlay, indent=2, ensure_ascii=False))
    log("INFO", f"Health overlay: {path} ({len(overlay)} keys)")
    return path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run_topo_scan(
    *,
    region: str,
    output_dir: str,
    health_json: Path,
    mode: str = "detailed",
    assume_role: str = "",
) -> int:
    topo_sh = repo_root() / "aws-topo-discovery" / "scripts" / "topo-scan.sh"
    if not topo_sh.exists():
        log("ERROR", f"topo-scan not found: {topo_sh}")
        return 2
    env = os.environ.copy()
    env["HEALTH_JSON"] = str(health_json)
    cmd = ["bash", str(topo_sh), "--mode", mode, "--region", region, "--output-dir", output_dir]
    if assume_role:
        cmd.extend(["--assume-role", assume_role])
    log("INFO", f"Invoking topo-scan with health overlay ({health_json.name})")
    return subprocess.call(cmd, env=env)


def render_from_cruise_report(
    cruise_json_path: str | Path,
    *,
    region: str = "",
    output_dir: str = "",
    mode: str = "detailed",
    assume_role: str = "",
) -> int:
    path = Path(cruise_json_path)
    if not path.exists():
        log("ERROR", f"Cruise report not found: {path}")
        return 2
    report = json.loads(path.read_text())
    incidents = report.get("incidents", [])
    regions = report.get("regions") or [report.get("region", region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))]
    reg = region or (regions[0] if isinstance(regions, list) else str(regions))
    out = output_dir or str(path.parent / "topology")
    health_path = path.parent / f"health-overlay-{report.get('run_id', 'cruise')[:8]}.json"
    write_health_json(incidents, health_path)
    rc = run_topo_scan(region=reg, output_dir=out, health_json=health_path, mode=mode, assume_role=assume_role)
    if rc == 0:
        log("INFO", f"Topology report in {out}/report.md")
    return rc


def overlay_from_latest_cruise(audit_dir: str | Path) -> Path | None:
    """Write health overlay from newest cruise-*.json in audit_dir; return path."""
    root = Path(audit_dir)
    if not root.is_dir():
        return None
    cruises = sorted(root.glob("cruise-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cruises:
        return None
    report = json.loads(cruises[0].read_text())
    run_id = report.get("run_id", cruises[0].stem.replace("cruise-", ""))[:8]
    out = root / f"health-overlay-auto-{run_id}.json"
    write_health_json(report.get("incidents", []), out)
    return out


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Cruise → topo-discovery health overlay render")
    p.add_argument("--cruise-json", default="", help="Path to cruise-*.json from daily-health-check")
    p.add_argument("--overlay-from-latest", default="", help="Audit dir — emit overlay from newest cruise JSON")
    p.add_argument("--region", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--mode", choices=("brief", "detailed"), default="detailed")
    p.add_argument("--assume-role", default="")
    args = p.parse_args()

    if args.overlay_from_latest:
        path = overlay_from_latest_cruise(args.overlay_from_latest)
        if not path:
            return 1
        print(str(path))
        return 0
    if not args.cruise_json:
        p.error("--cruise-json or --overlay-from-latest required")
    return render_from_cruise_report(
        args.cruise_json,
        region=args.region,
        output_dir=args.output_dir,
        mode=args.mode,
        assume_role=args.assume_role,
    )


if __name__ == "__main__":
    raise SystemExit(main())
