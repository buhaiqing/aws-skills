"""Data layer collectors (RDS PI, RDS Proxy / Aurora)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from _shared import make_incident, resource_in_scope, run_aws, log

from collectors._rds_helpers import _proxy_client_connection_limit, _parameter_max_connections
from collectors._time import json_time

def audit_rds_performance_insights(
    region: str, scope_ids: set[str], run_id: str, customer: str
) -> list[dict]:
    """Top wait event via Performance Insights (when enabled)."""
    incidents: list[dict] = []
    dbs = run_aws(["aws", "rds", "describe-db-instances"], region)
    if not dbs:
        return incidents
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    for db in dbs.get("DBInstances", []):
        ident = db.get("DBInstanceIdentifier", "")
        if scope_ids and not resource_in_scope(ident, scope_ids):
            continue
        if not db.get("PerformanceInsightsEnabled"):
            continue
        pi_arn = db.get("DbiResourceId", "")
        if not pi_arn:
            continue
        data = run_aws(
            [
                "aws",
                "pi",
                "get-resource-metrics",
                "--service-type",
                "RDS",
                "--identifier",
                pi_arn,
                "--metric-queries",
                '[{"Metric":"db.load.avg"}]',
                "--start-time",
                json_time(start),
                "--end-time",
                json_time(end),
                "--period-in-seconds",
                "300",
            ],
            region,
        )
        if not data:
            continue
        for mq in data.get("MetricList", []):
            points = mq.get("DataPoints", [])
            if not points:
                continue
            avg_load = sum(p.get("Value", 0) for p in points) / len(points)
            if avg_load > 2.0:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="RDS",
                        resource_id=ident,
                        rule_id="RDS-PI-01",
                        title=f"RDS PI db.load.avg elevated ({avg_load:.2f}) — investigate wait events",
                        level="WARNING" if avg_load < 4 else "CRITICAL",
                        metric="db.load.avg",
                        current_value=round(avg_load, 3),
                        threshold_warning=2.0,
                        threshold_critical=4.0,
                        recommendation="aws pi describe-dimension-keys (wait); runbook 05 slow-query",
                    )
                )
    return incidents

def audit_rds_proxy(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    """RDS Proxy connection path — ClientConnections vs pool limit, setup failures."""
    incidents: list[dict] = []
    proxies = run_aws(["aws", "rds", "describe-db-proxies"], region)
    if not proxies:
        return incidents
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    pool_warn_pct = 80.0
    pool_crit_pct = 95.0
    for proxy in proxies.get("DBProxies", []):
        name = proxy.get("DBProxyName", "")
        arn = proxy.get("DBProxyArn", "")
        if scope_ids and not resource_in_scope(name, scope_ids) and not resource_in_scope(arn, scope_ids):
            continue

        targets = run_aws(
            ["aws", "rds", "describe-db-proxy-targets", "--db-proxy-name", name],
            region,
        ) or {"Targets": []}

        pool_limit = _proxy_client_connection_limit(region, name, proxy, targets)

        stats_failed = run_aws(
            [
                "aws",
                "cloudwatch",
                "get-metric-statistics",
                "--namespace",
                "AWS/RDS",
                "--metric-name",
                "DatabaseConnectionsSetupFailed",
                "--dimensions",
                f"Name=ProxyName,Value={name}",
                "--start-time",
                json_time(start),
                "--end-time",
                json_time(end),
                "--period",
                "300",
                "--statistics",
                "Sum",
            ],
            region,
        )
        if stats_failed and stats_failed.get("Datapoints"):
            val = max(p.get("Sum", 0) for p in stats_failed["Datapoints"])
            if val >= 1:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="RDSProxy",
                        resource_id=name,
                        rule_id="RDS-PROXY-02",
                        title=f"RDS Proxy `{name}` DatabaseConnectionsSetupFailed={val:.0f}",
                        level="CRITICAL" if val >= 5 else "WARNING",
                        metric="DatabaseConnectionsSetupFailed",
                        current_value=val,
                        threshold_warning=1,
                        threshold_critical=5,
                        recommendation="Check target RDS max_connections; pool settings; SG between proxy and DB",
                    )
                )

        stats_conn = run_aws(
            [
                "aws",
                "cloudwatch",
                "get-metric-statistics",
                "--namespace",
                "AWS/RDS",
                "--metric-name",
                "ClientConnections",
                "--dimensions",
                f"Name=ProxyName,Value={name}",
                "--start-time",
                json_time(start),
                "--end-time",
                json_time(end),
                "--period",
                "300",
                "--statistics",
                "Maximum",
            ],
            region,
        )
        if stats_conn and stats_conn.get("Datapoints") and pool_limit:
            conn = max(p.get("Maximum", 0) for p in stats_conn["Datapoints"])
            pct = conn / pool_limit * 100
            if pct >= pool_warn_pct:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="RDSProxy",
                        resource_id=name,
                        rule_id="RDS-PROXY-01",
                        title=(
                            f"RDS Proxy `{name}` ClientConnections {conn:.0f}/{pool_limit} "
                            f"({pct:.0f}% of pool)"
                        ),
                        level="CRITICAL" if pct >= pool_crit_pct else "WARNING",
                        metric="ClientConnectionsPct",
                        current_value=round(pct, 1),
                        threshold_warning=pool_warn_pct,
                        threshold_critical=pool_crit_pct,
                        recommendation="Tune MaxConnectionsPercent / app pool; connection-storm runbook 06",
                    )
                )
        elif stats_conn and stats_conn.get("Datapoints") and not pool_limit:
            log("WARN", f"RDS Proxy {name}: skip ClientConnections % — max_connections unknown")

        # Proxy → Aurora / RDS target health
        if not targets.get("Targets"):
            continue
        for tgt in targets.get("Targets", []):
            tid = tgt.get("RdsResourceId") or tgt.get("TargetArn", "")
            rtype = tgt.get("Type", "")
            health = tgt.get("TargetHealth", {})
            state = health.get("State", "")
            if state and state.upper() != "AVAILABLE":
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="RDSProxy",
                        resource_id=f"{name}/{tid}",
                        rule_id="RDS-PROXY-TGT-01",
                        title=f"RDS Proxy target unhealthy: {name} → {tid} ({state})",
                        level="CRITICAL",
                        metric="TargetHealth",
                        current_value=1.0,
                        recommendation="describe-db-proxy-targets; check Aurora cluster/instance status",
                    )
                )
            if rtype != "TRACKED_CLUSTER" or not tid:
                continue
            cid = tid
            clusters = run_aws(
                ["aws", "rds", "describe-db-clusters", "--db-cluster-identifier", cid],
                region,
            )
            if not clusters or not clusters.get("DBClusters"):
                continue
            cl = clusters["DBClusters"][0]
            status = cl.get("Status", "")
            if status != "available":
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="Aurora",
                        resource_id=cid,
                        rule_id="RDS-PROXY-AURORA-01",
                        title=f"Aurora cluster `{cid}` behind proxy `{name}` status={status}",
                        level="CRITICAL",
                        metric="ClusterStatus",
                        current_value=1.0,
                        recommendation="Failover reader; check proxy target group; aws-aurora-ops",
                    )
                )
            stats = run_aws(
                [
                    "aws",
                    "cloudwatch",
                    "get-metric-statistics",
                    "--namespace",
                    "AWS/RDS",
                    "--metric-name",
                    "DatabaseConnections",
                    "--dimensions",
                    f"Name=DBClusterIdentifier,Value={cid}",
                    "--start-time",
                    json_time(start),
                    "--end-time",
                    json_time(end),
                    "--period",
                    "300",
                    "--statistics",
                    "Maximum",
                ],
                region,
            )
            if stats and stats.get("Datapoints"):
                conn = max(p.get("Maximum", 0) for p in stats["Datapoints"])
                # Compute percentage against cluster max_connections
                cl_pg = cl.get("DBClusterParameterGroup", "")
                max_conn = _parameter_max_connections(region, cl_pg, cluster=True) if cl_pg else 0
                conn_pct = (conn / max_conn * 100) if max_conn else conn
                if conn_pct >= 70:
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="Aurora",
                            resource_id=cid,
                            rule_id="RDS-PROXY-AURORA-02",
                            title=f"Aurora `{cid}` connections {conn:.0f} ({conn_pct:.0f}%) via proxy `{name}`",
                            level="CRITICAL" if conn_pct >= 85 else "WARNING",
                            metric="DatabaseConnections",
                            current_value=conn,
                            threshold_warning=70,
                            threshold_critical=85,
                            recommendation="Scale Aurora ACUs; tune proxy pool; aws-aurora-ops; runbook 06",
                        )
                    )
    return incidents

