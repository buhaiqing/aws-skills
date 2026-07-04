"""ElastiCache maxclients (max_connections) helper."""

from __future__ import annotations

from _shared import run_aws


def _elasticache_max_connections(region: str, cluster_id: str) -> int | None:
    """Query ElastiCache maxclients from the cache parameter group.

    Mirrors RDS _parameter_max_connections pattern: looks up the cluster's
    parameter group, then reads the ``maxclients`` parameter value.
    """
    cluster = run_aws(
        ["aws", "elasticache", "describe-cache-clusters", "--cache-cluster-id", cluster_id],
        region,
    )
    if not cluster or not cluster.get("CacheClusters"):
        return None

    c = cluster["CacheClusters"][0]
    # Only Redis uses the maxclients parameter approach
    if c.get("Engine", "").startswith("memcached"):
        return None

    pgs = c.get("CacheParameterGroup", {})
    pg_name = pgs.get("CacheParameterGroupName", "") if isinstance(pgs, dict) else ""
    if not pg_name:
        return None

    params = run_aws(
        [
            "aws",
            "elasticache",
            "describe-cache-parameters",
            "--cache-parameter-group-name",
            pg_name,
        ],
        region,
    )
    if not params or not params.get("Parameters"):
        return None

    for p in params["Parameters"]:
        if p.get("ParameterName") != "maxclients":
            continue
        raw = p.get("ParameterValue", "")
        if not raw:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return None