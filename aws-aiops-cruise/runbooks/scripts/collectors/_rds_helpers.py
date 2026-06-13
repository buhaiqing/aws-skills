"""RDS Proxy pool limit helpers."""

from __future__ import annotations

from typing import Any

from _shared import run_aws

def _parameter_max_connections(
    region: str, group_name: str, *, cluster: bool
) -> int | None:
    if not group_name:
        return None
    if cluster:
        data = run_aws(
            [
                "aws",
                "rds",
                "describe-db-cluster-parameters",
                "--db-cluster-parameter-group-name",
                group_name,
            ],
            region,
        )
    else:
        data = run_aws(
            ["aws", "rds", "describe-db-parameters", "--db-parameter-group-name", group_name],
            region,
        )
    if not data:
        return None
    for p in data.get("Parameters", []):
        if p.get("ParameterName") != "max_connections":
            continue
        raw = p.get("AppliedValue") or p.get("ParameterValue")
        if raw is None:
            return None
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None
    return None

def _target_max_connections(region: str, target: dict[str, Any]) -> int | None:
    rid = target.get("RdsResourceId", "")
    rtype = target.get("Type", "")
    if not rid:
        return None
    if rtype == "TRACKED_CLUSTER":
        cl = run_aws(
            ["aws", "rds", "describe-db-clusters", "--db-cluster-identifier", rid],
            region,
        )
        if not cl or not cl.get("DBClusters"):
            return None
        pg = cl["DBClusters"][0].get("DBClusterParameterGroup", "")
        return _parameter_max_connections(region, pg, cluster=True)
    inst = run_aws(
        ["aws", "rds", "describe-db-instances", "--db-instance-identifier", rid],
        region,
    )
    if not inst or not inst.get("DBInstances"):
        return None
    pgs = inst["DBInstances"][0].get("DBParameterGroups", [])
    pg = pgs[0].get("DBParameterGroupName", "") if pgs else ""
    return _parameter_max_connections(region, pg, cluster=False)

def _proxy_client_connection_limit(
    region: str, proxy_name: str, proxy: dict[str, Any], targets: dict[str, Any]
) -> int | None:
    max_pct = proxy.get("MaxConnectionsPercent") or 100
    tg = run_aws(
        ["aws", "rds", "describe-db-proxy-target-groups", "--db-proxy-name", proxy_name],
        region,
    )
    if tg and tg.get("TargetGroups"):
        cfg = tg["TargetGroups"][0].get("ConnectionPoolConfig", {}) or {}
        max_pct = cfg.get("MaxConnectionsPercent") or max_pct
    db_max: int | None = None
    for tgt in targets.get("Targets", []):
        db_max = _target_max_connections(region, tgt)
        if db_max:
            break
    if not db_max or db_max <= 0:
        return None
    return max(1, int(db_max * int(max_pct) / 100))

