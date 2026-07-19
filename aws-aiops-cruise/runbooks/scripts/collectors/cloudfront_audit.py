"""CloudFront origin & cache signal collector (read-only).

Populates ``signals["CloudFront"]`` for inference rules CF-ORIGIN-02 and
CF-CACHE-01. Emits NO incidents itself — the orchestrator's inference layer
fires the rules from these signals.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from _shared import resource_in_scope, run_aws

from collectors._time import json_time

_CF_REGION = "us-east-1"
_CF_NS = "AWS/CloudFront"
_CF_METRICS = ("OriginLatency", "OriginSuccessRate", "CacheHitRate")


def _metric_avg(did: str, metric: str) -> float | None:
    """Average of a CloudFront metric over the last hour (two dimensions).

    CloudFront metrics require both ``DistributionId`` and ``Region=Global``
    dimensions. The shared helpers (``get_metric_stats`` / ``get_metric_data_batch``)
    only accept a single dimension per query, so we call ``get-metric-statistics``
    directly here — mirroring the proven pattern in ``edge.audit_cloudfront``.
    """
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    data = run_aws(
        [
            "aws",
            "cloudwatch",
            "get-metric-statistics",
            "--namespace",
            _CF_NS,
            "--metric-name",
            metric,
            "--dimensions",
            f"Name=DistributionId,Value={did} Name=Region,Value=Global",
            "--start-time",
            json_time(start),
            "--end-time",
            json_time(end),
            "--period",
            "300",
            "--statistics",
            "Average",
        ],
        _CF_REGION,
    )
    if not data or not data.get("Datapoints"):
        return None
    avgs = [p["Average"] for p in data["Datapoints"] if "Average" in p]
    return sum(avgs) / len(avgs) if avgs else None


def audit_cloudfront_signals(
    scope_ids: set[str], run_id: str, customer: str
) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """Collect CloudFront origin/cache signals for in-scope distributions.

    Returns ``(incidents, {"CloudFront": {did: {metric: value|None}}})``.
    ``incidents`` is always empty; the inference layer generates findings.
    """
    incidents: list[dict] = []
    signals: dict[str, float] = {}

    data = run_aws(["aws", "cloudfront", "list-distributions"], _CF_REGION)
    if not data:
        return incidents, {"CloudFront": {}}

    for dist in data.get("DistributionList", {}).get("Items", []):
        did = dist.get("Id", "")
        if not did:
            continue
        domain = dist.get("DomainName", did)
        if scope_ids and not resource_in_scope(did, scope_ids) and not resource_in_scope(domain, scope_ids):
            aliases = dist.get("Aliases", {}).get("Items", [])
            if not any(resource_in_scope(a, scope_ids) for a in aliases):
                continue

        dist_signals: dict[str, float | None] = {}
        for metric in _CF_METRICS:
            dist_signals[metric] = _metric_avg(did, metric)
        signals[did] = dist_signals

    return incidents, {"CloudFront": signals}
