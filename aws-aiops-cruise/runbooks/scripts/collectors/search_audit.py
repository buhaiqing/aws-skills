"""Search layer collector (OpenSearch / Amazon ES domains)."""

from __future__ import annotations

from _shared import get_metric_data_batch, resource_in_scope, run_aws

_NS = "AWS/ES"
_DIM = "DomainName"


def audit_opensearch_health(
    region: str,
    scope_ids: set[str],
    run_id: str,
    customer: str,
) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """Collect OpenSearch health signals (read-only; emits no incidents).

    Returns (incidents, {"OpenSearch": {domain_name: {...}}}).
    The orchestrator's inference rule turns these signals into OS-HEAP-01 /
    OS-SHARD-01 incidents, so this collector keeps `incidents` empty.
    """
    incidents: list[dict] = []
    signals: dict[str, dict[str, float]] = {}

    data = run_aws(["aws", "es", "list-domain-names"], region)
    if not data or not data.get("DomainNames"):
        return incidents, {"OpenSearch": signals}

    batch: list[tuple[str, str, str, str, str]] = []
    names: list[str] = []
    for entry in data["DomainNames"]:
        name = entry.get("DomainName")
        if not name:
            continue
        if scope_ids and not resource_in_scope(name, scope_ids):
            continue
        names.append(name)
        batch.append((_NS, "JVMMemoryPressure", _DIM, name, "Maximum"))
        batch.append((_NS, "ClusterIndexWritesBlocked", _DIM, name, "Maximum"))
        batch.append((_NS, "UnassignedShards", _DIM, name, "Maximum"))

    if not batch:
        return incidents, {"OpenSearch": signals}

    results = get_metric_data_batch(region, batch, hours=6)

    for name in names:
        jvm = results.get(("JVMMemoryPressure", name))
        blocked = results.get(("ClusterIndexWritesBlocked", name))
        unassigned = results.get(("UnassignedShards", name))
        signals[name] = {
            # None when absent so the inference rule can skip missing pressure data
            "JVMMemoryPressure": (jvm or {}).get("max"),
            # 0.0 default so the boolean/count rules still evaluate
            "ClusterIndexWritesBlocked": (blocked or {}).get("max") or 0.0,
            "UnassignedShards": (unassigned or {}).get("max") or 0.0,
        }

    return incidents, {"OpenSearch": signals}
