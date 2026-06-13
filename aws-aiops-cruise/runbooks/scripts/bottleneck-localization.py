#!/usr/bin/env python3
"""bottleneck-localization.py — layer-by-layer latency chain."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from pathlib import Path

from _shared import log, resolve_output_dir


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--region", default="")
    p.add_argument("--symptom", default="latency")
    p.add_argument("--output-dir", default="")
    args = p.parse_args()

    scripts = Path(__file__).parent
    out = resolve_output_dir(args.output_dir or None)
    run_id = str(uuid.uuid4())
    common = ["--region", args.region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1"), "--output-dir", str(out)]
    if args.resource_group:
        common.extend(["--resource-group", args.resource_group])
    if args.tag_key:
        common.extend(["--tag-key", args.tag_key, "--tag-value", args.tag_value])

    log("INFO", "Bottleneck chain: emergency → slow-query")
    rc1 = subprocess.call(
        [sys.executable, str(scripts / "emergency-troubleshoot.py"), *common, "--symptom", args.symptom, "--non-interactive"]
    )
    rc2 = subprocess.call([sys.executable, str(scripts / "slow-query-diagnosis.py"), *common])
    log("INFO", f"Chain complete run_id={run_id[:8]} rc=({rc1},{rc2})")
    return max(rc1, rc2)


if __name__ == "__main__":
    raise SystemExit(main())
