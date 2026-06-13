#!/usr/bin/env python3
"""Collect CloudFront distribution origins for Mermaid edge linking (read-only)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable


def run_aws(args: list[str]) -> dict | None:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def load_apigw_v2_ids(region: str, *, run_aws_fn: Callable[[list[str]], dict | None] = run_aws) -> set[str]:
    data = run_aws_fn(["aws", "apigatewayv2", "get-apis", "--region", region, "--output", "json"])
    if not data:
        return set()
    return {item.get("ApiId", "") for item in data.get("Items", []) if item.get("ApiId")}


def origin_kind(domain: str, apigw_v2_ids: set[str]) -> str:
    d = domain.lower()
    if ".execute-api." in d:
        api_id = domain.split(".")[0]
        if api_id in apigw_v2_ids:
            return "apigw_v2"
        return "apigw"
    if ".lambda-url." in d:
        return "lambda_url"
    if ".s3." in d:
        return "s3"
    if ".elb." in d:
        return "alb"
    return "custom"


def parse_distribution_config(
    item: dict[str, Any],
    cfg: dict[str, Any] | None,
    apigw_v2_ids: set[str],
) -> dict[str, Any] | None:
    """Build one distribution entry from list item + get-distribution-config response."""
    did = item.get("Id", "")
    if not did or not cfg:
        return None
    dist = cfg.get("DistributionConfig", {})
    default_origin_id = dist.get("DefaultCacheBehavior", {}).get("TargetOriginId", "")
    cache_behaviors = []
    for cb in dist.get("CacheBehaviors", {}).get("Items", []):
        cache_behaviors.append(
            {
                "pathPattern": cb.get("PathPattern", ""),
                "targetOriginId": cb.get("TargetOriginId", ""),
            }
        )

    origin_groups: list[dict] = []
    origin_group_by_member: dict[str, dict] = {}
    for og in dist.get("OriginGroups", {}).get("Items", []):
        gid = og.get("Id", "")
        members = [m.get("OriginId", "") for m in og.get("Members", {}).get("Items", [])]
        codes = og.get("FailoverCriteria", {}).get("StatusCodes", {}).get("Items", [])
        origin_groups.append(
            {
                "id": gid,
                "members": members,
                "failoverStatusCodes": codes,
            }
        )
        for idx, mid in enumerate(members):
            if not mid:
                continue
            origin_group_by_member[mid] = {
                "groupId": gid,
                "role": "primary" if idx == 0 else "failover",
                "memberIndex": idx,
                "failoverStatusCodes": codes,
            }

    origins = []
    group_ids = {g["id"] for g in origin_groups}
    for o in dist.get("Origins", {}).get("Items", []):
        oid = o.get("Id", "")
        domain = o.get("DomainName", "")
        used_by = [
            b["pathPattern"]
            for b in cache_behaviors
            if b.get("targetOriginId") == oid and b.get("pathPattern")
        ]
        for b in cache_behaviors:
            tid = b.get("targetOriginId", "")
            if tid in group_ids:
                for g in origin_groups:
                    if g["id"] == tid and oid in g.get("members", []):
                        used_by.append(b.get("pathPattern", ""))
        used_by = [p for p in used_by if p]
        entry: dict[str, Any] = {
            "id": oid,
            "domain": domain,
            "kind": origin_kind(domain, apigw_v2_ids),
            "isDefault": oid == default_origin_id,
            "usedByPaths": used_by,
        }
        if oid in origin_group_by_member:
            entry["originGroup"] = origin_group_by_member[oid]
        origins.append(entry)

    default_targets_group = default_origin_id in group_ids
    return {
        "distributionId": did,
        "domainName": item.get("DomainName", did),
        "defaultOriginId": default_origin_id,
        "defaultTargetsOriginGroup": default_targets_group,
        "cacheBehaviors": cache_behaviors,
        "originGroups": origin_groups,
        "origins": origins,
    }


def collect_distributions(
    listed: dict[str, Any],
    *,
    apigw_v2_ids: set[str],
    fetch_config: Callable[[str], dict[str, Any] | None],
    workers: int = 1,
) -> list[dict[str, Any]]:
    items = [i for i in listed.get("DistributionList", {}).get("Items", []) if i.get("Id")]
    if not items:
        return []

    def _one(item: dict[str, Any]) -> dict[str, Any] | None:
        did = item["Id"]
        cfg = fetch_config(did)
        return parse_distribution_config(item, cfg, apigw_v2_ids)

    if workers <= 1 or len(items) == 1:
        return [r for item in items if (r := _one(item))]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        futures = {pool.submit(_one, item): item for item in items}
        for fut in as_completed(futures):
            parsed = fut.result()
            if parsed:
                results.append(parsed)
    results.sort(key=lambda x: x.get("distributionId", ""))
    return results


def fetch_distribution_config(distribution_id: str) -> dict[str, Any] | None:
    return run_aws(
        [
            "aws",
            "cloudfront",
            "get-distribution-config",
            "--id",
            distribution_id,
            "--output",
            "json",
        ]
    )


def main() -> int:
    p = argparse.ArgumentParser(description="CloudFront origin collector for topo-render Mermaid edges")
    p.add_argument("list_path", help="cloudfront.json from list-distributions")
    p.add_argument("out_path", help="Output cloudfront_origins.json")
    p.add_argument("region", nargs="?", default=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    p.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("CF_ORIGINS_WORKERS", "5")),
        help="Parallel get-distribution-config workers (default 5)",
    )
    args = p.parse_args()

    with open(args.list_path, encoding="utf-8") as f:
        listed = json.load(f)

    apigw_v2_ids = load_apigw_v2_ids(args.region)
    workers = max(1, min(args.workers, 10))
    results = collect_distributions(
        listed,
        apigw_v2_ids=apigw_v2_ids,
        fetch_config=fetch_distribution_config,
        workers=workers,
    )

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump({"distributions": results}, f, indent=2)
    print(f"CloudFront origins: {len(results)} distribution(s) -> {args.out_path} (workers={workers})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
