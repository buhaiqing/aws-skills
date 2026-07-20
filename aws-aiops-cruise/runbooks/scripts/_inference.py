#!/usr/bin/env python3
"""Chain inference + risk evidence for aws-aiops-cruise."""

from __future__ import annotations

from typing import Any

from _shared import make_incident

# Signals: resource_type -> resource_id -> metric -> value
Signals = dict[str, dict[str, dict[str, float | None]]]

SENSITIVE_PORTS = {22, 3389, 3306, 5432, 6379, 9200, 27017}


def _get(sig: Signals, rtype: str, rid: str, metric: str) -> float | None:
    return sig.get(rtype, {}).get(rid, {}).get(metric)


def _any_above(sig: Signals, rtype: str, metric: str, threshold: float) -> list[str]:
    out = []
    for rid, metrics in sig.get(rtype, {}).items():
        v = metrics.get(metric)
        if v is not None and v >= threshold:
            out.append(rid)
    return out


def apply_chain_inference(
    signals: Signals,
    *,
    run_id: str,
    customer: str,
    region: str,
    existing_rule_ids: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (extra incidents, inference markdown lines)."""
    incidents: list[dict] = []
    lines: list[str] = []

    unhealthy_albs = _any_above(signals, "ALB", "UnHealthyHostCount", 1)
    ec2_failed = _any_above(signals, "EC2", "StatusCheckFailed", 0.5)
    for alb in unhealthy_albs:
        rule = "ALB-EC2-01"
        if rule in existing_rule_ids:
            continue
        healthy_ec2 = [i for i in signals.get("EC2", {}) if i not in ec2_failed]
        if healthy_ec2:
            lines.append(
                f"- **{rule}**: ALB `{alb}` has unhealthy targets but EC2 status checks pass "
                "→ likely SG/NACL/listener path (see inference-rules.md)"
            )
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="ALB",
                    resource_id=alb,
                    rule_id=rule,
                    title="Unhealthy targets with healthy EC2 — network path suspicion",
                    level="WARNING",
                    metric="UnHealthyHostCount",
                    current_value=_get(signals, "ALB", alb, "UnHealthyHostCount"),
                    recommendation="Check SG ingress from ALB SG; verify target port listening (aws-ssm-ops optional)",
                )
            )

    for rid, metrics in signals.get("ALB", {}).items():
        lat = metrics.get("TargetResponseTime")
        if lat is not None and lat >= 1.0:
            ec2_cpus = [v for v in (signals.get("EC2", {}).get(i, {}).get("CPUUtilization") for i in signals.get("EC2", {})) if v is not None]
            if ec2_cpus and max(ec2_cpus) < 70:
                rule = "ALB-EC2-02"
                if rule not in existing_rule_ids:
                    lines.append(f"- **{rule}**: ALB `{rid}` high latency, EC2 CPU normal → check RDS/downstream")
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="ALB",
                            resource_id=rid,
                            rule_id=rule,
                            title="High ALB latency with normal EC2 CPU",
                            level="WARNING",
                            metric="TargetResponseTime",
                            current_value=lat,
                            recommendation="Inspect RDS ReadLatency/WriteLatency; ACM cert validity",
                        )
                    )

    for rid, metrics in signals.get("RDS", {}).items():
        conn = metrics.get("DatabaseConnections")
        max_conn = metrics.get("_max_connections", 0)
        conn_pct = (conn / max_conn * 100) if max_conn > 0 else conn
        if conn is not None and conn_pct >= 70:
            rule = "RDS-CONN-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: RDS `{rid}` connections {conn_pct:.0f}% of max → pool/leak check")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="RDS",
                        resource_id=rid,
                        rule_id=rule,
                        title="RDS connection count elevated",
                        level="CRITICAL" if conn_pct >= 85 else "WARNING",
                        metric="DatabaseConnections",
                        current_value=conn_pct,
                        threshold_warning=70,
                        threshold_critical=85,
                        recommendation="Review app connection pool; delegate aws-rds-ops for PI",
                    )
                )

    for rid, metrics in signals.get("RDS", {}).items():
        read_lat = metrics.get("ReadLatency")
        write_lat = metrics.get("WriteLatency")
        lat_max = max(
            v for v in (read_lat, write_lat) if v is not None
        ) if (read_lat is not None or write_lat is not None) else None
        if lat_max is not None and lat_max >= 0.02:
            rule = "RDS-LAT-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: RDS `{rid}` latency p95 {lat_max * 1000:.1f}ms "
                    "→ slow query or I/O bottleneck"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="RDS",
                        resource_id=rid,
                        rule_id=rule,
                        title="RDS read/write latency elevated",
                        level="CRITICAL" if lat_max >= 0.1 else "WARNING",
                        metric="ReadLatency+WriteLatency",
                        current_value=lat_max,
                        threshold_warning=0.02,
                        threshold_critical=0.1,
                        recommendation="PI top SQL via aws-rds-ops; check IOPS sizing and query patterns",
                    )
                )

    # Aurora inference rules
    for rid, metrics in signals.get("Aurora", {}).items():
        lag = metrics.get("AuroraReplicaLag")
        if lag is not None and lag > 1000:
            rule = "AURORA-LAG-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: Aurora `{rid}` replica lag {lag:.0f}ms "
                    "→ replication bottleneck"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="Aurora",
                        resource_id=rid,
                        rule_id=rule,
                        title="Aurora replica lag elevated",
                        level="CRITICAL" if lag > 30000 else "WARNING",
                        metric="AuroraReplicaLag",
                        current_value=lag,
                        threshold_warning=1000,
                        threshold_critical=30000,
                        recommendation="PI top SQL on writer; add reader or scale writer — delegate aws-aurora-ops",
                    )
                )

        slv_cap = metrics.get("ServerlessDatabaseCapacity")
        slv_max = metrics.get("_max_capacity")
        if slv_cap is not None and slv_max is not None and slv_max > 0:
            cap_pct = slv_cap / slv_max * 100
            if cap_pct >= 90:
                rule = "AURORA-SLV2-01"
                if rule not in existing_rule_ids:
                    lines.append(
                        f"- **{rule}**: Aurora `{rid}` Serverless v2 capacity "
                        f"{cap_pct:.0f}% of max → scaling pressure"
                    )
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="Aurora",
                            resource_id=rid,
                            rule_id=rule,
                            title="Aurora Serverless v2 capacity near ceiling",
                            level="CRITICAL",
                            metric="ServerlessDatabaseCapacity",
                            current_value=slv_cap,
                            recommendation="Raise MaxCapacity (≤ ceiling); delegate aws-aurora-ops modify-db-cluster",
                        )
                    )

        buf_hit = metrics.get("BufferCacheHitRatio")
        if buf_hit is not None and buf_hit < 99:
            rule = "AURORA-CACHE-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: Aurora `{rid}` buffer cache hit ratio "
                    f"{buf_hit:.1f}% → memory pressure"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="Aurora",
                        resource_id=rid,
                        rule_id=rule,
                        title="Aurora buffer cache hit ratio low",
                        level="CRITICAL" if buf_hit < 95 else "WARNING",
                        metric="BufferCacheHitRatio",
                        current_value=buf_hit,
                        threshold_warning=99,
                        threshold_critical=95,
                        recommendation="Scale instance class or tune buffer pool parameters — delegate aws-aurora-ops",
                    )
                )

    # RDS Proxy inference rules
    for rid, metrics in signals.get("RDSProxy", {}).items():
        client_conn = metrics.get("ClientConnections")
        pool_limit = metrics.get("_pool_limit")
        if client_conn is not None:
            if pool_limit is not None and pool_limit > 0:
                conn_pct = client_conn / pool_limit * 100
                if conn_pct >= 80:
                    rule = "RDS-PROXY-01"
                    if rule not in existing_rule_ids:
                        lines.append(
                            f"- **{rule}**: RDS Proxy `{rid}` client connections "
                            f"{conn_pct:.0f}% of pool limit → connection pool exhaustion"
                        )
                        incidents.append(
                            make_incident(
                                run_id=run_id,
                                customer=customer,
                                region=region,
                                resource_type="RDSProxy",
                                resource_id=rid,
                                rule_id=rule,
                                title="RDS Proxy client connections near pool limit",
                                level="CRITICAL" if conn_pct >= 95 else "WARNING",
                                metric="ClientConnections",
                                current_value=client_conn,
                                threshold_warning=pool_limit * 0.80,
                                threshold_critical=pool_limit * 0.95,
                                recommendation="Tune proxy max_connections_percent or increase target max_connections",
                            )
                        )
            elif client_conn >= 1000:
                rule = "RDS-PROXY-01"
                if rule not in existing_rule_ids:
                    lines.append(
                        f"- **{rule}**: RDS Proxy `{rid}` client connections "
                        f"{client_conn:.0f} (pool limit unknown) → connection pressure"
                    )
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="RDSProxy",
                            resource_id=rid,
                            rule_id=rule,
                            title="RDS Proxy client connections elevated",
                            level="WARNING",
                            metric="ClientConnections",
                            current_value=client_conn,
                            recommendation="Tune proxy max_connections_percent or increase target max_connections",
                        )
                    )

        setup_fail = metrics.get("DatabaseConnectionsSetupFailed")
        if setup_fail is not None and setup_fail > 0:
            rule = "RDS-PROXY-02"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: RDS Proxy `{rid}` connection setup failures "
                    f"{setup_fail:.0f} → auth or connectivity issue"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="RDSProxy",
                        resource_id=rid,
                        rule_id=rule,
                        title="RDS Proxy connection setup failures",
                        level="CRITICAL",
                        metric="DatabaseConnectionsSetupFailed",
                        current_value=setup_fail,
                        recommendation="Check auth config, SG rules, target RDS availability — aws-rds-ops",
                    )
                )

    # CloudWatch alarm inference rules
    for alarm_name, metrics in signals.get("CloudWatch", {}).items():
        state = metrics.get("StateValue")
        if state is not None and state == "ALARM":
            rule = "CW-ALARM-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: CloudWatch alarm `{alarm_name}` in ALARM state → customer signal"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="CloudWatch",
                        resource_id=alarm_name,
                        rule_id=rule,
                        title="CloudWatch alarm in ALARM state",
                        level="WARNING",
                        metric="StateValue",
                        current_value=1,
                        recommendation="Review alarm reason; correlate with other findings",
                    )
                )

    # DevOps Guru insight inference rules
    for insight_id, metrics in signals.get("DevOpsGuru", {}).items():
        status = metrics.get("Status")
        if status is not None and status == "ONGOING":
            rule = "DG-INSIGHT-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: DevOps Guru insight `{insight_id}` ONGOING → follow recommendation"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="DevOpsGuru",
                        resource_id=insight_id,
                        rule_id=rule,
                        title="DevOps Guru ONGOING insight",
                        level="WARNING",
                        metric="InsightStatus",
                        current_value=1,
                        recommendation="Follow DevOps Guru recommendation narrative",
                    )
                )

    # X-Ray fault/error rate inference rules
    for node, metrics in signals.get("XRay", {}).items():
        fault_rate = metrics.get("FaultRate")
        if fault_rate is not None and fault_rate >= 5:
            rule = "XRAY-FAULT-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: X-Ray node `{node}` fault rate {fault_rate:.1f}% → trace hot spot"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="XRay",
                        resource_id=node,
                        rule_id=rule,
                        title="X-Ray node fault rate elevated",
                        level="WARNING" if fault_rate < 10 else "CRITICAL",
                        metric="FaultRate",
                        current_value=fault_rate,
                        threshold_warning=5,
                        threshold_critical=10,
                        recommendation="Open X-Ray trace map for cold start / downstream timeout",
                    )
                )

    # EKS nodegroup scaling inference rules (EKS-NG-02)
    for ng_id, metrics in signals.get("EKS", {}).items():
        rule = "EKS-NG-02"
        if rule in existing_rule_ids:
            continue
        desired = metrics.get("NodesDesired")
        current = metrics.get("NodesCurrent")
        maxn = metrics.get("NodesMax")
        if current is None or desired is None:
            continue
        if current < desired:
            title = f"EKS nodegroup below desired size ({int(current)}/{int(desired)})"
            level = "CRITICAL"
            rec = "Nodes not ready: check ASG launch failures, insufficient capacity, or node bootstrap errors; delegate aws-eks-ops"
        elif maxn is not None and current >= maxn and desired >= maxn:
            title = f"EKS nodegroup at max capacity ({int(current)}/{int(maxn)}) with pending scale-up"
            level = "WARNING"
            rec = "Raise maxSize or add nodegroups; desired>=max blocks further scale-out; delegate aws-eks-ops"
        else:
            continue
        lines.append(f"- **{rule}**: EKS {ng_id} {title}")
        incidents.append(
            make_incident(
                run_id=run_id,
                customer=customer,
                region=region,
                resource_type="EKS",
                resource_id=ng_id,
                rule_id=rule,
                title=title,
                level=level,
                metric="NodesCurrent",
                current_value=current,
                recommendation=rec,
            )
        )

    # EKS node/Pod-level inference via CloudWatch Container Insights (EKS_NODE layer).
    for cluster, node_metrics in signals.get("EKS_NODE", {}).items():
        node_not_ready = node_metrics.get("NodeNotReadyMin")
        if node_not_ready is not None and node_not_ready < 1.0:
            rule = "EKS-NODE-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: EKS node NotReady in cluster `{cluster}` (min ready={node_not_ready:.2f})"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="EKS",
                        resource_id=cluster,
                        rule_id=rule,
                        title=f"EKS node NotReady in cluster {cluster}",
                        level="WARNING",
                        metric="NodeNotReadyMin",
                        current_value=node_not_ready,
                        threshold_warning=1.0,
                        recommendation="A node is NotReady: check kubelet, ASG launch/health, capacity, or node bootstrap; delegate aws-eks-ops",
                    )
                )
        oom = node_metrics.get("PodOOMKilledSum")
        if oom is not None and oom > 0:
            rule = "EKS-OOM-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: EKS pod OOM-killed in cluster `{cluster}` (events sum={oom:.0f})"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="EKS",
                        resource_id=cluster,
                        rule_id=rule,
                        title=f"EKS pod OOM-killed in cluster {cluster}",
                        level="CRITICAL",
                        metric="PodOOMKilledSum",
                        current_value=oom,
                        threshold_critical=0,
                        recommendation="Pod OOM-killed: inspect memory requests/limits and node memory pressure; right-size or scale; delegate aws-eks-ops",
                    )
                )

    for rid, metrics in signals.get("NAT", {}).items():
        err = metrics.get("ErrorPortAllocation")
        if err is not None and err >= 1:
            rule = "NAT-PORT-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: NAT `{rid}` port allocation errors → SNAT exhaustion risk")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="NAT",
                        resource_id=rid,
                        rule_id=rule,
                        title="NAT Gateway port allocation errors",
                        level="CRITICAL",
                        metric="ErrorPortAllocation",
                        current_value=err,
                        recommendation="Add NAT GW or reduce unique outbound destinations",
                    )
                )

    # NLB traffic inference rules
    for rid, metrics in signals.get("NLB", {}).items():
        flow = metrics.get("ActiveFlowCount")
        if flow is not None and flow >= 50000:
            rule = "NLB-TRAFFIC-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: NLB `{rid}` active flows {flow:.0f} → near connection limit")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="NLB",
                        resource_id=rid,
                        rule_id=rule,
                        title="NLB active flows near limit",
                        level="CRITICAL",
                        metric="ActiveFlowCount",
                        current_value=flow,
                        threshold_warning=10_000,
                        threshold_critical=50_000,
                        recommendation="Distribute across AZs or increase NLB count via aws-elb-ops",
                    )
                )

    for rid, metrics in signals.get("NLB", {}).items():
        bytes_proc = metrics.get("ProcessedBytes")
        if bytes_proc is not None and bytes_proc >= 5e9:
            rule = "NLB-TRAFFIC-02"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: NLB `{rid}` processed bytes {bytes_proc:.0f} → traffic surge detected")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="NLB",
                        resource_id=rid,
                        rule_id=rule,
                        title="NLB traffic surge detected",
                        level="CRITICAL",
                        metric="ProcessedBytes",
                        current_value=bytes_proc,
                        threshold_warning=1e9,
                        threshold_critical=5e9,
                        recommendation="Review traffic patterns; delegate aws-elb-ops for scaling analysis",
                    )
                )

    # ElastiCache inference rules
    for rid, metrics in signals.get("ElastiCache", {}).items():
        cpu = metrics.get("CPUUtilization")
        if cpu is not None and cpu >= 85:
            rule = "EC-CPU-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: ElastiCache `{rid}` CPU {cpu:.0f}% → compute bottleneck risk")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ElastiCache",
                        resource_id=rid,
                        rule_id=rule,
                        title="ElastiCache CPU utilization critical",
                        level="CRITICAL",
                        metric="CPUUtilization",
                        current_value=cpu,
                        threshold_warning=70,
                        threshold_critical=85,
                        recommendation="Upgrade node type; delegate aws-elasticache-ops; review Redis heavy commands",
                    )
                )

    for rid, metrics in signals.get("ElastiCache", {}).items():
        mem = metrics.get("DatabaseMemoryUsagePercentage")
        if mem is not None and mem >= 80:
            rule = "EC-MEM-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: ElastiCache `{rid}` memory {mem:.0f}% → eviction risk")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ElastiCache",
                        resource_id=rid,
                        rule_id=rule,
                        title="ElastiCache memory usage pressure",
                        level="CRITICAL" if mem >= 95 else "WARNING",
                        metric="DatabaseMemoryUsagePercentage",
                        current_value=mem,
                        threshold_warning=80,
                        threshold_critical=95,
                        recommendation="Scale up or adjust maxmemory policy; delegate aws-elasticache-ops",
                    )
                )

    for rid, metrics in signals.get("ElastiCache", {}).items():
        conn = metrics.get("CurrConnections")
        max_conn = metrics.get("_max_connections", 0)
        conn_pct = (conn / max_conn * 100) if max_conn > 0 else 0
        if conn is not None and max_conn > 0 and conn_pct >= 70:
            rule = "EC-CONN-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: ElastiCache `{rid}` connections {conn_pct:.0f}% of max ({conn:.0f}/{max_conn:.0f}) → connection leak risk")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ElastiCache",
                        resource_id=rid,
                        rule_id=rule,
                        title="ElastiCache connections near limit",
                        level="CRITICAL" if conn_pct >= 85 else "WARNING",
                        metric="CurrConnections",
                        current_value=conn_pct,
                        threshold_warning=70,
                        threshold_critical=85,
                        recommendation="Review client connection pools and idle timeouts; delegate aws-elasticache-ops",
                    )
                )
        elif conn is not None and max_conn == 0 and conn >= 5000:
            rule = "EC-CONN-FALLBACK-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: ElastiCache `{rid}` connections {conn:.0f} (no max_connections data, hardcoded threshold)")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ElastiCache",
                        resource_id=rid,
                        rule_id=rule,
                        title="ElastiCache connections critically high (hardcoded threshold)",
                        level="CRITICAL",
                        metric="CurrConnections",
                        current_value=conn,
                        threshold_warning=1000,
                        threshold_critical=5000,
                        recommendation="Add max_connections collector; check client connection pools; delegate aws-elasticache-ops",
                    )
                )

    # EC2 memory, I/O, and network chain rules
    for rid, metrics in signals.get("EC2", {}).items():
        mem = metrics.get("MemoryUtilization")
        if mem is not None and mem >= 85:
            rule = "EC2-MEM-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: EC2 `{rid}` memory > 85% sustained "
                    "→ possible memory leak or undersized instance"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="EC2",
                        resource_id=rid,
                        rule_id=rule,
                        title="EC2 memory utilization critical",
                        level="CRITICAL" if mem >= 95 else "WARNING",
                        metric="MemoryUtilization",
                        current_value=mem,
                        threshold_warning=85,
                        threshold_critical=95,
                        recommendation="Check process-level memory via `ps aux --sort=-%mem`; check `/var/log/messages` or `dmesg` for OOM kills; consider instance resize. Delegate aws-ec2-ops.",
                    )
                )

        vol_ql = metrics.get("VolumeQueueLength")
        burst = metrics.get("BurstBalance")
        if vol_ql is not None and vol_ql > 48 and burst is not None and burst < 20:
            rule = "EC2-IO-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: EC2 `{rid}` VolumeQueueLength {vol_ql:.0f} + "
                    f"BurstBalance {burst:.1f}% → EBS IOPS/throughput exhaustion"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="EC2",
                        resource_id=rid,
                        rule_id=rule,
                        title="EBS burst bucket depleted with high queue depth",
                        level="CRITICAL" if vol_ql > 64 else "WARNING",
                        metric="VolumeQueueLength",
                        current_value=vol_ql,
                        threshold_warning=48,
                        threshold_critical=64,
                        recommendation="Upgrade to gp3/io1/io2 with provisioned IOPS. Delegate aws-ec2-ops.",
                    )
                )

        read_lat = metrics.get("ReadLatency")
        write_lat = metrics.get("WriteLatency")
        lat_p95 = max(
            v for v in (read_lat, write_lat) if v is not None
        ) if (read_lat is not None or write_lat is not None) else None
        if lat_p95 is not None and lat_p95 > 0.02 and vol_ql is not None and vol_ql > 32:
            rule = "EC2-IO-02"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: EC2 `{rid}` disk latency p95 {lat_p95 * 1000:.1f}ms + "
                    f"VolumeQueueLength {vol_ql:.0f} → EBS latency from queue depth"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="EC2",
                        resource_id=rid,
                        rule_id=rule,
                        title="EBS high latency due to queue depth",
                        level="CRITICAL" if lat_p95 > 0.1 else "WARNING",
                        metric="ReadLatency",
                        current_value=lat_p95,
                        threshold_warning=0.02,
                        threshold_critical=0.1,
                        recommendation="Reduce concurrent I/O, increase EBS IOPS, or migrate to io1/io2. Delegate aws-ec2-ops.",
                    )
                )

        net_out = metrics.get("NetworkOut")
        net_limit = metrics.get("NetworkBandwidth")
        if net_out is not None:
            rule = "EC2-NET-01"
            if rule not in existing_rule_ids:
                if net_limit is not None and net_limit > 0:
                    pct = net_out / net_limit * 100
                    emit = net_out / net_limit > 0.80
                else:
                    pct = None
                    emit = True  # informational — no limit to compare against
                if emit:
                    label = (
                        f"{pct:.0f}% of instance limit" if pct is not None
                        else f"{net_out / 1e6:.1f} MB/s"
                    )
                    lines.append(
                        f"- **{rule}**: EC2 `{rid}` network out {label} "
                        "→ bandwidth saturation risk"
                    )
                    if pct is not None:
                        level = "CRITICAL" if pct >= 95 else "WARNING"
                        thr_w = net_limit * 0.80
                        thr_c = net_limit * 0.95
                    else:
                        level = "WARNING"
                        thr_w = None
                        thr_c = None
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="EC2",
                            resource_id=rid,
                            rule_id=rule,
                            title="EC2 network bandwidth saturation",
                            level=level,
                            metric="NetworkOut",
                            current_value=net_out,
                            threshold_warning=thr_w,
                            threshold_critical=thr_c,
                            recommendation="Check `describe-instance-types` for NetworkPerformance and resize if needed. Delegate aws-ec2-ops.",
                        )
                    )

        pkt_in = metrics.get("NetworkPacketsIn")
        pkt_out = metrics.get("NetworkPacketsOut")
        drop_in = metrics.get("PacketDropIn")
        drop_out = metrics.get("PacketDropOut")
        if pkt_in is not None and pkt_out is not None and (drop_in is not None or drop_out is not None):
            total_pkts = pkt_in + pkt_out
            total_drops = (drop_in or 0) + (drop_out or 0)
            if total_pkts > 0 and total_drops / total_pkts > 0.01:
                rule = "EC2-NET-02"
                if rule not in existing_rule_ids:
                    drop_pct = total_drops / total_pkts * 100
                    lines.append(
                        f"- **{rule}**: EC2 `{rid}` packet drop rate {drop_pct:.1f}% "
                        "→ SG/ENI packet drops"
                    )
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="EC2",
                            resource_id=rid,
                            rule_id=rule,
                            title="EC2 packet drops detected",
                            level="WARNING",
                            metric="PacketDropRate",
                            current_value=round(drop_pct, 2),
                            threshold_warning=1.0,
                            threshold_critical=5.0,
                            recommendation="Review SG rules; check ENI limits; check VPC Flow Logs for REJECT entries. Delegate aws-vpc-ops + aws-ec2-ops.",
                        )
                    )

    # Lambda throttles + API Gateway 5xx (serverless path)
    for fn, metrics in signals.get("Lambda", {}).items():
        if (metrics.get("Throttles") or 0) >= 1:
            rule = "LAMBDA-THROTTLE-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: Lambda `{fn}` throttled → check concurrency limits / downstream")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="Lambda",
                        resource_id=fn,
                        rule_id=rule,
                        title="Lambda function throttling",
                        level="WARNING",
                        metric="Throttles",
                        current_value=metrics.get("Throttles"),
                        recommendation="Raise reserved concurrency or fix slow downstream (RDS/API); delegate aws-lambda-ops",
                    )
                )

    for api, metrics in signals.get("ApiGateway", {}).items():
        e5 = metrics.get("5XXError") or 0
        if e5 >= 5:
            rule = "APIGW-5XX-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: API `{api}` 5xx errors → check Lambda/integration timeout")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ApiGateway",
                        resource_id=api,
                        rule_id=rule,
                        title="API Gateway 5XX elevated",
                        level="CRITICAL" if e5 >= 50 else "WARNING",
                        metric="5XXError",
                        current_value=e5,
                        recommendation="CloudWatch Logs for API GW; Lambda Errors metric correlation",
                    )
                )

    # DynamoDB throttle detection
    for rid, metrics in signals.get("DynamoDB", {}).items():
        throttled = metrics.get("ThrottledRequests") or 0
        if throttled >= 1:
            rule = "DYNAMO-THROTTLE-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: DynamoDB `{rid}` throttled requests {throttled:.0f} "
                    "→ RCU/WCU saturation or on-demand burst"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="DynamoDB",
                        resource_id=rid,
                        rule_id=rule,
                        title="DynamoDB throttled requests detected",
                        level="CRITICAL" if throttled >= 10 else "WARNING",
                        metric="ThrottledRequests",
                        current_value=throttled,
                        threshold_warning=1,
                        threshold_critical=10,
                        recommendation="Check consumed vs provisioned capacity; enable auto scaling; review hot partition keys",
                    )
                )

    # ElastiCache eviction detection
    for rid, metrics in signals.get("ElastiCache", {}).items():
        evictions = metrics.get("Evictions") or 0
        if evictions >= 100:
            rule = "CACHE-EVICT-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: ElastiCache `{rid}` evictions {evictions:.0f} "
                    "→ memory pressure, hot keys, or TTL misconfiguration"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ElastiCache",
                        resource_id=rid,
                        rule_id=rule,
                        title="ElastiCache evictions elevated",
                        level="CRITICAL" if evictions >= 1000 else "WARNING",
                        metric="Evictions",
                        current_value=evictions,
                        threshold_warning=100,
                        threshold_critical=1000,
                        recommendation="Scale node type; review key TTLs; check for hot keys; delegate aws-elasticache-ops",
                    )
                )

    # WAF-ALB-01: WAF blocked requests + ALB 5xx pattern
    waf_high = _any_above(signals, "WAF", "BlockedRequests", 1000)
    alb_elb5xx = _any_above(signals, "ALB", "HTTPCode_ELB_5XX_Count", 50)
    if waf_high and alb_elb5xx:
        rule = "WAF-ALB-01"
        if rule not in existing_rule_ids:
            waf_list = ", ".join(f"`{w}`" for w in waf_high[:3])
            alb_list = ", ".join(f"`{a}`" for a in alb_elb5xx[:3])
            lines.append(
                f"- **{rule}**: WAF blocked spike ({waf_list}) + ALB 5xx ({alb_list}) "
                "→ rate rule / geo block / false positive on API path"
            )
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="WAF",
                    resource_id=waf_high[0] if waf_high else "unknown",
                    rule_id=rule,
                    title="WAF blocks correlated with ALB 5xx",
                    level="CRITICAL" if len(waf_high) >= 3 else "WARNING",
                    metric="BlockedRequests",
                    current_value=float(sum(
                        (signals.get("WAF", {}).get(w, {}).get("BlockedRequests") or 0)
                        for w in waf_high
                    )),
                    threshold_warning=1000,
                    threshold_critical=5000,
                    recommendation="wafv2 get-sampled-requests; tune rate/geo rules; delegate aws-waf-ops",
                )
            )

    # ALB 5xx + WAF blocks (edge path) — WAF in native audit; correlate if both in report metadata
    for rid, metrics in signals.get("ALB", {}).items():
        e5 = metrics.get("HTTPCode_Target_5XX_Count") or 0
        if e5 >= 10:
            rule = "ALB-5XX-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: ALB `{rid}` target 5xx sum high → target health / app / RDS / cert"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ALB",
                        resource_id=rid,
                        rule_id=rule,
                        title="ALB target 5XX count elevated",
                        level="CRITICAL" if e5 >= 50 else "WARNING",
                        metric="HTTPCode_Target_5XX_Count",
                        current_value=e5,
                        recommendation="elbv2 describe-target-health; check WAF if 403 vs 502 pattern",
                    )
                )

    # --- Phase 1 additions: DynamoDB GSI + ElastiCache failover + OpenSearch ---
    for rid, metrics in signals.get("DynamoDB", {}).items():
        gsi_thr = metrics.get("GSIWriteThrottleEvents") or metrics.get("GSIReadThrottleEvents") or 0
        if gsi_thr >= 1:
            rule = "DYNAMO-GSI-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: DynamoDB `{rid}` GSI throttle events {gsi_thr:.0f} "
                    "→ GSI capacity saturation or hot GSI key"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="DynamoDB",
                        resource_id=rid,
                        rule_id=rule,
                        title="DynamoDB GSI throttling detected",
                        level="CRITICAL" if gsi_thr >= 10 else "WARNING",
                        metric="GSIWriteThrottleEvents",
                        current_value=float(gsi_thr),
                        threshold_warning=1,
                        threshold_critical=10,
                        recommendation="Review GSI provisioned capacity; delegate aws-dynamodb-ops",
                    )
                )

    for rid, metrics in signals.get("ElastiCache", {}).items():
        failover = metrics.get("FailoverInProgress") or 0
        if failover >= 1:
            rule = "EC-FAILOVER-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: ElastiCache `{rid}` failover in progress → replica promotion"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ElastiCache",
                        resource_id=rid,
                        rule_id=rule,
                        title="ElastiCache failover in progress",
                        level="CRITICAL",
                        metric="FailoverInProgress",
                        current_value=float(failover),
                        recommendation="Verify replica promotion; check primary health; delegate aws-elasticache-ops",
                    )
                )

    # --- Phase-2/3 closure: Athena / RAM / SecretsManager / CloudFront / OpenSearch ---
    # Each block consumes a `signals` key populated by its native collector
    # (collectors/analytics.py, ram_audit.py, secrets_audit.py,
    # cloudfront_audit.py, search_audit.py). Detect + recommend + delegate
    # only — no mutating AWS calls (GCL fail-closed).

    # ATHENA-COST-01: query cost anomaly via ProcessedBytes over 6h window.
    for wg, metrics in signals.get("Athena", {}).items():
        pb = metrics.get("ProcessedBytes")
        if pb is None:
            continue
        rule = "ATHENA-COST-01"
        if rule in existing_rule_ids:
            continue
        level = "CRITICAL" if pb >= 2e10 else ("WARNING" if pb >= 5e9 else None)
        if level:
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="Athena",
                    resource_id=wg,
                    rule_id=rule,
                    title=f"Athena workgroup `{wg}` scanned {pb / 1e9:.1f} GB in 6h",
                    level=level,
                    metric="ProcessedBytes",
                    current_value=float(pb),
                    threshold_warning=5e9,
                    threshold_critical=2e10,
                    recommendation="Tune query / partition / cache; delegate aws-athena-ops for cost review",
                )
            )

    # RAM-SHARE-01: resource share not ACTIVE or has rejected associations.
    for arn, metrics in signals.get("RAM", {}).items():
        active = metrics.get("ShareStatusActive", 1.0)
        rejected = metrics.get("RejectedAssociations", 0.0) or 0.0
        if active == 1.0 and rejected <= 0:
            continue
        rule = "RAM-SHARE-01"
        if rule in existing_rule_ids:
            continue
        incidents.append(
            make_incident(
                run_id=run_id,
                customer=customer,
                region=region,
                resource_type="RAM",
                resource_id=arn,
                rule_id=rule,
                title=f"RAM share `{arn.split('/')[-1]}` unhealthy (status={'ACTIVE' if active == 1.0 else 'NON-ACTIVE'}, rejected={int(rejected)})",
                level="WARNING",
                metric="ShareStatusActive",
                current_value=active,
                recommendation="Check share status / principal association rejections; delegate aws-ram-ops",
            )
        )

    # SEC-ROTATE-01: secret rotation stale or disabled.
    for name, metrics in signals.get("SecretsManager", {}).items():
        age = metrics.get("RotationAgeDays", 0.0) or 0.0
        enabled = metrics.get("RotationEnabled", 1.0)
        if age <= 90 and enabled == 1.0:
            continue
        rule = "SEC-ROTATE-01"
        if rule in existing_rule_ids:
            continue
        level = "CRITICAL" if (age > 180 or enabled == 0.0) else "WARNING"
        incidents.append(
            make_incident(
                run_id=run_id,
                customer=customer,
                region=region,
                resource_type="SecretsManager",
                resource_id=name,
                rule_id=rule,
                title=f"Secret `{name}` rotation age {age:.0f}d (enabled={enabled == 1.0})",
                level=level,
                metric="RotationAgeDays",
                current_value=float(age),
                threshold_warning=90,
                threshold_critical=180,
                recommendation="Rotate secret and enable rotation; delegate aws-secretsmanager-ops",
            )
        )

    # CF-ORIGIN-02 / CF-CACHE-01: origin latency/success + cache hit rate.
    for did, metrics in signals.get("CloudFront", {}).items():
        latency = metrics.get("OriginLatency")
        success = metrics.get("OriginSuccessRate")
        hit = metrics.get("CacheHitRate")
        # CF-ORIGIN-02
        if (latency is not None and latency > 1000) or (success is not None and success < 0.99):
            rule = "CF-ORIGIN-02"
            if rule not in existing_rule_ids:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="CloudFront",
                        resource_id=did,
                        rule_id=rule,
                        title=f"CloudFront {did} origin latency={latency}ms success={success}",
                        level="CRITICAL" if (latency or 0) > 3000 or (success or 1) < 0.95 else "WARNING",
                        metric="OriginLatency",
                        current_value=float(latency) if latency is not None else None,
                        threshold_warning=1000,
                        threshold_critical=3000,
                        recommendation="Inspect origin (ALB/S3) health, TLS, timeouts; delegate aws-cloudfront-ops",
                    )
                )
        # CF-CACHE-01
        if hit is not None and hit < 0.8:
            rule = "CF-CACHE-01"
            if rule not in existing_rule_ids:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="CloudFront",
                        resource_id=did,
                        rule_id=rule,
                        title=f"CloudFront {did} cache hit rate {hit:.2f}",
                        level="WARNING",
                        metric="CacheHitRate",
                        current_value=float(hit),
                        threshold_warning=0.8,
                        recommendation="Review cache policy, TTL, query strings/cookies in cache key; delegate aws-cloudfront-ops",
                    )
                )

    # OS-HEAP-01 / OS-SHARD-01: OpenSearch JVM pressure + shard health.
    for domain, metrics in signals.get("OpenSearch", {}).items():
        jvm = metrics.get("JVMMemoryPressure")
        if jvm is not None and jvm >= 80:
            rule = "OS-HEAP-01"
            if rule not in existing_rule_ids:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="OpenSearch",
                        resource_id=domain,
                        rule_id=rule,
                        title=f"OpenSearch `{domain}` JVM memory pressure {jvm:.1f}%",
                        level="CRITICAL" if jvm >= 95 else "WARNING",
                        metric="JVMMemoryPressure",
                        current_value=float(jvm),
                        threshold_warning=80,
                        threshold_critical=95,
                        recommendation="Scale nodes / adjust shard allocation / JVM heap; delegate aws-opensearch-ops",
                    )
                )
        blocked = metrics.get("ClusterIndexWritesBlocked", 0.0) or 0.0
        unassigned = metrics.get("UnassignedShards", 0.0) or 0.0
        if blocked > 0 or unassigned > 0:
            rule = "OS-SHARD-01"
            if rule not in existing_rule_ids:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="OpenSearch",
                        resource_id=domain,
                        rule_id=rule,
                        title=f"OpenSearch `{domain}` writes blocked={blocked:.0f} unassignedShards={unassigned:.0f}",
                        level="CRITICAL",
                        metric="ClusterIndexWritesBlocked",
                        current_value=float(blocked),
                        recommendation="Check disk watermark / node count / shard allocation; delegate aws-opensearch-ops",
                    )
                )

        # OS-MASTER-01: master node not reachable from the data node.
        master_reachable = metrics.get("MasterReachableFromNode", None)
        if master_reachable is not None and master_reachable == 0:
            rule = "OS-MASTER-01"
            if rule not in existing_rule_ids:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="OpenSearch",
                        resource_id=domain,
                        rule_id=rule,
                        title=f"OpenSearch `{domain}` master not reachable from node",
                        level="CRITICAL",
                        metric="MasterReachableFromNode",
                        current_value=0.0,
                        recommendation="Check cluster health / node availability / network partition; delegate aws-opensearch-ops",
                    )
                )

        # OS-SNAP-01: automated snapshot failure.
        snap_fail = metrics.get("AutomatedSnapshotFailure", 0.0) or 0.0
        if snap_fail > 0:
            rule = "OS-SNAP-01"
            if rule not in existing_rule_ids:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="OpenSearch",
                        resource_id=domain,
                        rule_id=rule,
                        title=f"OpenSearch `{domain}` automated snapshot failed (n={snap_fail:.0f})",
                        level="CRITICAL",
                        metric="AutomatedSnapshotFailure",
                        current_value=float(snap_fail),
                        recommendation="Investigate snapshot role / S3 access / domain health; delegate aws-opensearch-ops",
                    )
                )

    # EC2-IDLE-01: EC2 idle instance detection (CPU < 5%, healthy, age > 24h).
    # Signals expected from compute.py EC2 collector: CPUUtilization, StatusCheckFailed,
    # InstanceLifecycle, InstanceAgeDays.
    for rid, metrics in signals.get("EC2", {}).items():
        lifecycle = metrics.get("InstanceLifecycle")
        # Skip spot instances; absent lifecycle means on-demand (default)
        if lifecycle == "spot":
            continue

        cpu = metrics.get("CPUUtilization")
        status_failed = metrics.get("StatusCheckFailed")
        instance_age_days = metrics.get("InstanceAgeDays")

        # Guard: instance age > 24h, CPU low/absent, status check passing
        if instance_age_days is None or instance_age_days <= 1:
            continue
        if status_failed is not None and status_failed != 0:
            continue
        if cpu is not None and cpu >= 5:
            continue

        # Determine idle severity
        rule = "EC2-IDLE-01"
        if rule in existing_rule_ids:
            continue

        if instance_age_days >= 14:
            level = "CRITICAL"
            title = f"EC2 `{rid}` idle ≥14 days (CPU {'<5%' if cpu is not None else 'absent'}, healthy)"
        elif instance_age_days >= 7:
            level = "WARNING"
            title = f"EC2 `{rid}` idle ≥7 days (CPU {'<5%' if cpu is not None else 'absent'}, healthy)"
        else:
            continue

        lines.append(
            f"- **{rule}**: {title} → likely unused, consider decommission or rightsizing"
        )
        incidents.append(
            make_incident(
                run_id=run_id,
                customer=customer,
                region=region,
                resource_type="EC2",
                resource_id=rid,
                rule_id=rule,
                title=title,
                level=level,
                metric="IdleDays",
                current_value=float(instance_age_days),
                threshold_warning=7,
                threshold_critical=14,
                recommendation="Delegate aws-ec2-ops with health-check intent; consider stop/terminate or rightsizing",
            )
        )

    # ACM-CERT-01: certificate expiring in < 30 days
    for cert_arn, acm_data in signals.get("ACM", {}).items():
        domain = acm_data.get("DomainName", "")
        if ".internal" in domain.lower():
            continue
        days = acm_data.get("NotAfterDays", 999)
        if days < 30:
            rule = "ACM-CERT-01"
            if rule not in existing_rule_ids:
                level = "CRITICAL" if days < 7 else "WARNING"
                lines.append(f"- **{rule}**: ACM cert for `{domain}` expires in {days}d")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ACM",
                        resource_id=cert_arn,
                        rule_id=rule,
                        title=f"ACM certificate `{domain}` expires in {days} days",
                        level=level,
                        metric="DaysToExpiry",
                        current_value=float(days),
                        threshold_warning=30,
                        threshold_critical=7,
                        recommendation="delegate aws-acm-ops for renewal",
                    )
                )

    # GUARDDUTY-HIGH-01: GuardDuty high-severity findings
    backdoor_types = {"Backdoor:EC2", "Backdoor:S3"}
    for fid, gd_data in signals.get("GuardDuty", {}).items():
        sev = gd_data.get("Severity", 0)
        if sev < 7:
            continue
        ftype = gd_data.get("Type", "")
        svc = gd_data.get("ServiceName", "")
        # Skip backdoor types — escalate to human
        if ftype in backdoor_types:
            rule = "GUARDDUTY-HIGH-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: GuardDuty BACKDOOR finding detected — {ftype} → HUMAN ESCALATION")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="GuardDuty",
                        resource_id=fid,
                        rule_id=rule,
                        title=f"GuardDuty BACKDOOR: {ftype} — HUMAN ESCALATION REQUIRED",
                        level="CRITICAL",
                        metric="FindingSeverity",
                        current_value=float(sev),
                        recommendation="IMMEDIATE: isolate affected instance; do NOT delegate — requires human investigation",
                    )
                )
        elif svc in ("EC2", "S3", "RDS", "IAM"):
            rule = "GUARDDUTY-HIGH-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: GuardDuty {sev}+ finding on {svc}: {ftype}")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="GuardDuty",
                        resource_id=fid,
                        rule_id=rule,
                        title=f"GuardDuty HIGH+ finding: {ftype} on {svc}",
                        level="CRITICAL",
                        metric="FindingSeverity",
                        current_value=float(sev),
                        recommendation="delegate aws-guardduty-ops for RCA",
                    )
                )

    # SECHUB-FAILED-01: Security Hub compliance failed > 7d
    for fid, sh_data in signals.get("SecurityHub", {}).items():
        status = sh_data.get("ComplianceStatus", "")
        workflow = sh_data.get("WorkflowStatus", "")
        if status != "FAILED":
            continue
        if workflow == "RESOLVED":
            continue
        first_seen_str = sh_data.get("FirstObservedAt", "")
        if first_seen_str:
            from datetime import datetime
            first_seen = datetime.fromisoformat(first_seen_str.replace("Z", "+00:00"))
            age_days = (datetime.now().timestamp() - first_seen.timestamp()) / 86400
            if age_days > 7:
                rule = "SECHUB-FAILED-01"
                if rule not in existing_rule_ids:
                    level = "CRITICAL" if age_days > 30 else "WARNING"
                    title = sh_data.get("Title", fid)
                    lines.append(f"- **{rule}**: Security Hub compliance FAILED for {age_days:.0f}d: {title}")
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="SecurityHub",
                            resource_id=fid,
                            rule_id=rule,
                            title=f"Security Hub FAILED: {title} ({age_days:.0f}d unresolved)",
                            level=level,
                            metric="UnresolvedDays",
                            current_value=float(age_days),
                            threshold_warning=7,
                            threshold_critical=30,
                            recommendation="delegate aws-securityhub-ops for compliance remediation",
                        )
                    )

    # KMS-ROTATE-01: KMS key rotation disabled > 365 days
    for key_arn, km_data in signals.get("KMS", {}).items():
        if km_data.get("KeyManager") == "AWS":
            continue  # skip AWS-managed keys
        if not km_data.get("KeyRotationEnabled", True) and km_data.get("DaysSinceCreation", 0) > 365:
            rule = "KMS-ROTATE-01"
            if rule not in existing_rule_ids:
                days = km_data["DaysSinceCreation"]
                lines.append(f"- **{rule}**: KMS key rotation disabled for {days}d → enable rotation")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="KMS",
                        resource_id=key_arn,
                        rule_id=rule,
                        title=f"KMS key rotation disabled > 365d: {key_arn.split('/')[-1]}",
                        level="CRITICAL",
                        metric="DaysSinceRotation",
                        current_value=float(days),
                        recommendation="delegate aws-kms-ops",
                    )
                )

    # SQS-DLQ-01: SQS Dead Letter Queue messages visible > 1h
    for q_url, sqs_data in signals.get("SQS", {}).items():
        if sqs_data.get("QueueType") != "dlq":
            continue
        msg_count = sqs_data.get("ApproximateNumberOfMessages", 0)
        age_sec = sqs_data.get("ApproximateAgeOfOldestMessage", 0)
        if msg_count > 0 and age_sec > 3600:
            rule = "SQS-DLQ-01"
            if rule not in existing_rule_ids:
                q_name = sqs_data.get("QueueName", q_url)
                level = "CRITICAL" if msg_count > 10 else "WARNING"
                lines.append(f"- **{rule}**: SQS DLQ `{q_name}` has {msg_count} msgs (oldest {age_sec/3600:.1f}h)")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="SQS",
                        resource_id=q_name,
                        rule_id=rule,
                        title=f"SQS DLQ `{q_name}`: {msg_count} messages, oldest {age_sec/3600:.1f}h",
                        level=level,
                        metric="ApproximateNumberOfMessages",
                        current_value=float(msg_count),
                        recommendation="delegate aws-sqs-ops",
                    )
                )

        # === Application Auto Scaling detection (v1.3.0, per-namespace inference rules) ===
        incidents.extend(detect_app_autoscaling_lambda(
            signals, run_id=run_id, customer=customer, region=region,
            existing_rule_ids=existing_rule_ids))
        incidents.extend(detect_app_autoscaling_dynamodb(
            signals, run_id=run_id, customer=customer, region=region,
            existing_rule_ids=existing_rule_ids))
        incidents.extend(detect_app_autoscaling_spot_fleet(
            signals, run_id=run_id, customer=customer, region=region,
            existing_rule_ids=existing_rule_ids))
        incidents.extend(detect_app_autoscaling_emr(
            signals, run_id=run_id, customer=customer, region=region,
            existing_rule_ids=existing_rule_ids))
        incidents.extend(detect_app_autoscaling_sagemaker(
            signals, run_id=run_id, customer=customer, region=region,
            existing_rule_ids=existing_rule_ids))
        incidents.extend(detect_app_autoscaling_comprehend(
            signals, run_id=run_id, customer=customer, region=region,
            existing_rule_ids=existing_rule_ids))
        incidents.extend(detect_app_autoscaling_cassandra(
            signals, run_id=run_id, customer=customer, region=region,
            existing_rule_ids=existing_rule_ids))

    return incidents, lines


def detect_app_autoscaling_lambda(signals, *, run_id, customer, region, existing_rule_ids):
    out = []
    for rid, m in signals.get("Lambda", {}).items():
        throttled = m.get("Throttles") or 0
        util = m.get("ProvisionedConcurrencyUtilization")
        if throttled >= 1 and "FD-AUTO-LAMBDA-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Lambda", resource_id=rid, rule_id="FD-AUTO-LAMBDA-01",
                title=f"Lambda `{rid}` PC throttled {throttled:.0f}/hr",
                level="WARNING", metric="Throttles", current_value=float(throttled),
                recommendation="register_scalable_target Lambda PC MaxCapacity raise"))
        if util is not None and util > 80 and "PD-AUTO-LAMBDA-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Lambda", resource_id=rid, rule_id="PD-AUTO-LAMBDA-01",
                title=f"Lambda `{rid}` PC util {util:.1f}%",
                level="WARNING", metric="ProvisionedConcurrencyUtilization",
                current_value=float(util),
                recommendation="register_scalable_target Lambda PC MaxCapacity raise"))
        if util is not None and util < 20 and "CO-AUTO-LAMBDA-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Lambda", resource_id=rid, rule_id="CO-AUTO-LAMBDA-01",
                title=f"Lambda `{rid}` PC util {util:.1f}% low",
                level="INFO", metric="ProvisionedConcurrencyUtilization",
                current_value=float(util),
                recommendation="register_scalable_target Lambda PC MinCapacity lower"))
    return out


def detect_app_autoscaling_dynamodb(signals, *, run_id, customer, region, existing_rule_ids):
    out = []
    for rid, m in signals.get("DynamoDB", {}).items():
        throttled = m.get("ThrottledRequests") or 0
        util_r = m.get("ProvisionedReadCapacityUtilization")
        if throttled >= 1 and "FD-AUTO-DYNAMODB-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="DynamoDB", resource_id=rid, rule_id="FD-AUTO-DYNAMODB-01",
                title=f"DynamoDB `{rid}` throttled {throttled:.0f}",
                level="CRITICAL" if throttled >= 10 else "WARNING",
                metric="ThrottledRequests", current_value=float(throttled),
                recommendation="register_scalable_target DynamoDB MaxCapacity raise"))
        if util_r is not None and util_r > 80 and "PD-AUTO-DYNAMODB-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="DynamoDB", resource_id=rid, rule_id="PD-AUTO-DYNAMODB-01",
                title=f"DynamoDB `{rid}` read util {util_r:.1f}%",
                level="WARNING", metric="ProvisionedReadCapacityUtilization",
                current_value=float(util_r),
                recommendation="register_scalable_target read MaxCapacity raise"))
        if util_r is not None and util_r < 20 and "CO-AUTO-DYNAMODB-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="DynamoDB", resource_id=rid, rule_id="CO-AUTO-DYNAMODB-01",
                title=f"DynamoDB `{rid}` read util {util_r:.1f}% low",
                level="INFO", metric="ProvisionedReadCapacityUtilization",
                current_value=float(util_r),
                recommendation="register_scalable_target read MinCapacity lower"))
    return out


def detect_app_autoscaling_spot_fleet(signals, *, run_id, customer, region, existing_rule_ids):
    out = []
    for rid, m in signals.get("EC2SpotFleetRequest", {}).items():
        actual = m.get("ActualCapacity")
        target = m.get("TargetCapacity")
        if actual is None or target is None:
            continue
        if actual < target and "PD-AUTO-SPOT-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="EC2SpotFleetRequest", resource_id=rid,
                rule_id="PD-AUTO-SPOT-01",
                title=f"Spot Fleet `{rid}` Actual {actual:.0f} < Target {target:.0f}",
                level="WARNING", metric="ActualCapacity",
                current_value=float(actual),
                recommendation="register_scalable_target raise MaxCapacity"))
        if 0 < target and actual > target * 0.8 and "CO-AUTO-SPOT-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="EC2SpotFleetRequest", resource_id=rid,
                rule_id="CO-AUTO-SPOT-01",
                title=f"Spot Fleet `{rid}` Actual {actual:.0f} > 80% Target",
                level="INFO", metric="ActualCapacity",
                current_value=float(actual),
                recommendation="register_scalable_target lower MaxCapacity"))
    return out


def detect_app_autoscaling_emr(signals, *, run_id, customer, region, existing_rule_ids):
    out = []
    for rid, m in signals.get("ElasticMapReduce", {}).items():
        idle = m.get("IsIdle")
        cpu = m.get("JobFlowCPUUtilization")
        if idle == 1 and "FD-AUTO-EMR-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="ElasticMapReduce", resource_id=rid,
                rule_id="FD-AUTO-EMR-01",
                title=f"EMR `{rid}` idle ≥30m",
                level="WARNING", metric="IsIdle", current_value=1.0,
                recommendation="terminate cluster via EMR console if no jobs"))
        if cpu is not None and cpu > 85 and "PD-AUTO-EMR-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="ElasticMapReduce", resource_id=rid,
                rule_id="PD-AUTO-EMR-01",
                title=f"EMR `{rid}` JobFlowCPU {cpu:.1f}%",
                level="CRITICAL", metric="JobFlowCPUUtilization",
                current_value=float(cpu),
                recommendation="register_scalable_target InstanceGroup MaxCapacity raise"))
        if cpu is not None and cpu < 20 and "CO-AUTO-EMR-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="ElasticMapReduce", resource_id=rid,
                rule_id="CO-AUTO-EMR-01",
                title=f"EMR `{rid}` JobFlowCPU {cpu:.1f}% low",
                level="INFO", metric="JobFlowCPUUtilization",
                current_value=float(cpu),
                recommendation="register_scalable_target MinCapacity lower"))
    return out


def detect_app_autoscaling_sagemaker(signals, *, run_id, customer, region, existing_rule_ids):
    out = []
    for rid, m in signals.get("SageMaker", {}).items():
        inv_5xx = m.get("Invocation5XXErrors")
        per_inst = m.get("InvocationsPerInstance")
        if inv_5xx is not None and inv_5xx >= 5 and "FD-AUTO-SAGEMAKER-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="SageMaker", resource_id=rid,
                rule_id="FD-AUTO-SAGEMAKER-01",
                title=f"SageMaker `{rid}` invocation 5XX {inv_5xx:.0f}",
                level="CRITICAL", metric="Invocation5XXErrors",
                current_value=float(inv_5xx),
                recommendation="deregister then register_scalable_target; or rollback model artifact"))
        if per_inst is not None and per_inst > 0.8 and "PD-AUTO-SAGEMAKER-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="SageMaker", resource_id=rid,
                rule_id="PD-AUTO-SAGEMAKER-01",
                title=f"SageMaker `{rid}` InvPerInst {per_inst:.2f}",
                level="WARNING", metric="InvocationsPerInstance",
                current_value=float(per_inst),
                recommendation="register_scalable_target variant MaxCapacity raise"))
        if per_inst is not None and per_inst < 0.3 and "CO-AUTO-SAGEMAKER-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="SageMaker", resource_id=rid,
                rule_id="CO-AUTO-SAGEMAKER-01",
                title=f"SageMaker `{rid}` InvPerInst {per_inst:.2f} low",
                level="INFO", metric="InvocationsPerInstance",
                current_value=float(per_inst),
                recommendation="register_scalable_target variant MinCapacity lower"))
    return out


def detect_app_autoscaling_comprehend(signals, *, run_id, customer, region, existing_rule_ids):
    out = []
    for rid, m in signals.get("Comprehend", {}).items():
        throttle = m.get("ThrottledException") or 0
        util = m.get("InferenceRequestCount")
        if throttle >= 1 and "FD-AUTO-COMPREHEND-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Comprehend", resource_id=rid,
                rule_id="FD-AUTO-COMPREHEND-01",
                title=f"Comprehend `{rid}` throttled {throttle:.0f}",
                level="WARNING", metric="ThrottledException",
                current_value=float(throttle),
                recommendation="register_scalable_target raise MaxCapacity"))
        if util is not None and util > 16 and "PD-AUTO-COMPREHEND-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Comprehend", resource_id=rid,
                rule_id="PD-AUTO-COMPREHEND-01",
                title=f"Comprehend `{rid}` InferenceReq {util:.0f}",
                level="WARNING", metric="InferenceRequestCount",
                current_value=float(util),
                recommendation="register_scalable_target InferenceUnits raise"))
        if util is not None and util < 4 and "CO-AUTO-COMPREHEND-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Comprehend", resource_id=rid,
                rule_id="CO-AUTO-COMPREHEND-01",
                title=f"Comprehend `{rid}` InferenceReq {util:.0f} low",
                level="INFO", metric="InferenceRequestCount",
                current_value=float(util),
                recommendation="register_scalable_target InferenceUnits lower"))
    return out


def detect_app_autoscaling_cassandra(signals, *, run_id, customer, region, existing_rule_ids):
    out = []
    for rid, m in signals.get("Cassandra", {}).items():
        throttle = m.get("ProvisionedThroughputExceededException") or 0
        consumed = m.get("ConsumedReadCapacityUnits")
        if throttle >= 1 and "FD-AUTO-CASSANDRA-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Cassandra", resource_id=rid,
                rule_id="FD-AUTO-CASSANDRA-01",
                title=f"Keyspace `{rid}` throughput exceeded {throttle:.0f}",
                level="CRITICAL", metric="ProvisionedThroughputExceededException",
                current_value=float(throttle),
                recommendation="register_scalable_target raise MaxCapacity"))
        if consumed is not None and consumed > 80 and "PD-AUTO-CASSANDRA-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Cassandra", resource_id=rid,
                rule_id="PD-AUTO-CASSANDRA-01",
                title=f"Keyspace `{rid}` consumed {consumed:.0f}/prov",
                level="WARNING", metric="ConsumedReadCapacityUnits",
                current_value=float(consumed),
                recommendation="register_scalable_target raise MaxCapacity"))
        if consumed is not None and consumed < 20 and "CO-AUTO-CASSANDRA-01" not in existing_rule_ids:
            out.append(make_incident(
                run_id=run_id, customer=customer, region=region,
                resource_type="Cassandra", resource_id=rid,
                rule_id="CO-AUTO-CASSANDRA-01",
                title=f"Keyspace `{rid}` consumed {consumed:.0f}/prov low",
                level="INFO", metric="ConsumedReadCapacityUnits",
                current_value=float(consumed),
                recommendation="register_scalable_target lower MinCapacity"))
    return out


def correlate_native_findings(
    incidents: list[dict],
    *,
    run_id: str,
    customer: str,
    region: str,
    existing_rule_ids: set[str],
) -> tuple[list[dict], list[str]]:
    """Cross-link CloudFront / RDS Proxy / X-Ray findings with metric incidents."""
    extra: list[dict] = []
    lines: list[str] = []
    rules = {i["rule_id"] for i in incidents}

    if "CF-ORIGIN-01" in rules and any(i["resource_type"] == "Lambda" for i in incidents):
        lines.append(
            "- **CF-LAMBDA-URL-01**: CloudFront origin latency + Lambda errors "
            "→ check Function URL auth, timeout, and downstream RDS"
        )
    if "CF-ORIGIN-01" in rules and any("execute-api" in i.get("resource_id", "") for i in incidents):
        lines.append(
            "- **CF-APIGW-01**: CloudFront + API Gateway path "
            "→ verify stage deployment, integration timeout, WAF on edge"
        )

    if "CF-ORIGIN-01" in rules and any(i["rule_id"].startswith("METRIC-ALB") for i in incidents):
        rid = "CF-ORIGIN-01"
        if rid not in existing_rule_ids:
            lines.append(
                "- **CF-ALB-01**: CloudFront origin latency + ALB metrics abnormal "
                "→ debug origin (ALB target health) not edge cache"
            )

    if "S3-METRICS-01" in rules:
        lines.append(
            "- **S3-METRICS-01**: S3 request metrics not published "
            "→ rely on CloudFront CF-EDGE-01 or enable S3 CloudWatch request metrics"
        )

    if "CF-S3-01" in rules or "S3-PAB-01" in rules or "S3-4XX-01" in rules or "S3-5XX-01" in rules:
        if "CF-EDGE-01" in rules or "CF-ORIGIN-01" in rules or "S3-4XX-01" in rules:
            lines.append(
                "- **CF-S3-01**: CloudFront errors + S3 origin misconfig "
                "→ verify OAC/OAI, bucket policy, Block Public Access, S3 4xx/5xx metrics"
            )

    if "RDS-PROXY-AURORA-01" in rules or "RDS-PROXY-AURORA-02" in rules:
        lines.append(
            "- **RDS-PROXY-AURORA-01**: Proxy targets Aurora cluster under stress "
            "→ failover, scale ACUs, connection-storm runbook 06"
        )

    if "RDS-PROXY-01" in rules or "RDS-PROXY-02" in rules:
        if "RDS-CONN-01" in rules or any("METRIC-RDS-DatabaseConnections" in i["rule_id"] for i in incidents):
            lines.append(
                "- **RDS-PROXY-CONN-01**: Proxy + DB connection pressure "
                "→ tune max_connections percent, pool size, or RDS Proxy target group"
            )

    if "XRAY-FAULT-01" in rules:
        xray_nodes = [i for i in incidents if i["rule_id"] == "XRAY-FAULT-01"]
        if any(i["resource_type"] == "Lambda" for i in incidents):
            lines.append(
                "- **XRAY-LAMBDA-01**: X-Ray fault node + Lambda errors "
                "→ open trace map for cold start / downstream timeout"
            )
        for x in xray_nodes[:3]:
            lines.append(f"  - Hot node: `{x['resource_id']}` rate={x.get('current_value')}%")

    if ("CF-EDGE-01" in rules or "CF-ORIGIN-01" in rules) and ("S3-4XX-01" in rules or "S3-5XX-01" in rules):
        lines.append(
            "- **CF-S3-COMPOSITE**: CloudFront errors + S3 origin issues → verify OAC/bucket policy/path"
        )

    acm_exp = [i for i in incidents if i["rule_id"] == "ACM-EXP-01"]
    if acm_exp:
        expiry_days = min((i.get("current_value") or 30) for i in acm_exp)
        level_tag = "CRITICAL" if any(i["level"] == "CRITICAL" for i in acm_exp) else "WARNING"
        domains = ", ".join(i["title"].split(": ")[-1] for i in acm_exp[:3])
        lines.append(
            f"- **ACM-EXP-01** [{level_tag}]: {len(acm_exp)} certificate(s) expiring "
            f"(earliest in {expiry_days:.0f}d) — {domains}"
        )

    # R53-ALB-01: Route53 HC failing, ALB targets healthy.
    if "R53-ALB-01" in rules and not any(i["resource_type"] == "ALB" for i in incidents):
        lines.append(
            "- **R53-ALB-01**: Route53 health check failing but ALB targets healthy"
            " → DNS mispoint, CloudFront cert mismatch, or regional endpoint issue"
        )

    # WAF-ALB-01: WAF blocking + ALB 5XX.
    if any(i["rule_id"].startswith("WAF") for i in incidents) and "ALB-5XX-01" in rules:
        lines.append(
            "- **WAF-ALB-01**: WAF blocking requests and ALB returning 5XX"
            " → rate rule / geo block / false positive on API path;"
            " check `wafv2 get-sampled-requests`"
        )

    # LAMBDA-THROTTLE-APIGW-01: Lambda throttles + API Gateway 5XX.
    if "LAMBDA-THROTTLE-01" in rules and "APIGW-5XX-01" in rules:
        lines.append(
            "- **LAMBDA-THROTTLE-APIGW-01**: Lambda throttling and API Gateway 5XX"
            " → concurrency limit hit; downstream integration timeout"
        )

    # CF-EDGE-CACHE-01: CloudFront edge errors + origin latency.
    if "CF-EDGE-01" in rules and "CF-ORIGIN-02" in rules:
        lines.append(
            "- **CF-EDGE-CACHE-01**: CloudFront edge errors AND origin latency elevated"
            " → check both cache behavior AND origin health; cache miss amplification risk"
        )

    return extra, lines


def build_risk_evidence(
    resource_type: str,
    resource_id: str,
    metric: str,
    current: float | None,
    *,
    threshold_w: float | None,
    threshold_c: float | None,
    wow_pct: float | None = None,
    trend_daily: float | None = None,
    consecutive: int = 0,
) -> dict[str, Any]:
    """Unified risk evidence (ML off by default)."""
    static_level = "NORMAL"
    if current is not None and threshold_c is not None and current >= threshold_c:
        static_level = "CRITICAL"
    elif current is not None and threshold_w is not None and current >= threshold_w:
        static_level = "WARNING"

    risk_score = 0.0
    if static_level == "CRITICAL":
        risk_score = 0.85
    elif static_level == "WARNING":
        risk_score = 0.55
    if wow_pct is not None and wow_pct > 50:
        risk_score = min(1.0, risk_score + 0.15)
    if trend_daily is not None and trend_daily > 0 and threshold_c and current is not None:
        days_to_crit = (threshold_c - current) / trend_daily if trend_daily > 0 else None
        if days_to_crit is not None and days_to_crit <= 3:
            risk_score = max(risk_score, 0.75)

    if risk_score >= 0.75:
        risk_level = "CRITICAL"
    elif risk_score >= 0.50:
        risk_level = "WARNING"
    elif risk_score >= 0.25:
        risk_level = "INFO"
    else:
        risk_level = "NORMAL"

    ml_mode = __import__("os").environ.get("AIOPS_ML_MODE", "off")
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "metric": metric,
        "current_value": current,
        "risk_level": risk_level,
        "risk_score": round(risk_score, 3),
        "confidence": 0.9 if static_level != "NORMAL" else 0.7,
        "static_level": static_level,
        "duration": {"consecutive_points": consecutive, "duration_minutes": consecutive * 5},
        "trend": {
            "direction": "rising" if (wow_pct or 0) > 10 else "flat",
            "wow_percent": wow_pct,
            "daily_growth": trend_daily,
        },
        "ml_shadow_result": None if ml_mode == "off" else {"mode": ml_mode, "skipped": True},
        "detection_methods": ["static_threshold", "wow"] if wow_pct else ["static_threshold"],
    }
