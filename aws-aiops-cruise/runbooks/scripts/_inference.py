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
                        recommendation="PI top SQL on writer; add reader or scale writer — aws-aurora-ops",
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
                            recommendation="Raise MaxCapacity (≤ ceiling); aws-aurora-ops modify-db-cluster",
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
                        recommendation="Scale instance class or tune buffer pool parameters — aws-aurora-ops",
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
                        recommendation="Upgrade node type via aws-elasticache-ops; review Redis heavy commands",
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
                        recommendation="Scale up or adjust maxmemory policy via aws-elasticache-ops",
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
                        recommendation="Review client connection pools and idle timeouts via aws-elasticache-ops",
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
                        recommendation="Add max_connections collector; check client connection pools via aws-elasticache-ops",
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
                        recommendation="Raise reserved concurrency or fix slow downstream (RDS/API)",
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
                        recommendation="Scale node type; review key TTLs; check for hot keys via aws-elasticache-ops",
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
                        recommendation="Verify replica promotion; check primary health via aws-elasticache-ops",
                    )
                )

    return incidents, lines


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
