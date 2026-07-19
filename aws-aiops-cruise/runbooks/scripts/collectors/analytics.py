"""Analytics layer collectors (Athena)."""

from __future__ import annotations

from _shared import get_metric_data_batch, log, run_aws

def audit_athena_cost(
    region: str,
    scope_ids: set[str],
    run_id: str,
    customer: str,
) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """Read-only Athena cost collector (rule ATHENA-COST-01).

    Lists work groups (Athena is global via us-east-1) and pulls CloudWatch
    `AWS/Athena` metrics per WorkGroup over the last 6h/300s:
      - ProcessedBytes (Average + Maximum)
      - QuerySucceeded, QueryFailed (Sum)

    Returns (incidents, {"Athena": signals_dict}) with NO incidents emitted
    here — the inference rule fires ATHENA-COST-01 from `signals["Athena"]`.
    Only work groups that returned at least one datapoint are recorded.
    """
    incidents: list[dict] = []
    signals_dict: dict[str, dict[str, float]] = {}

    # Athena is a global service; list-work-groups is only served from us-east-1.
    athena_region = "us-east-1"
    wg = run_aws(["aws", "athena", "list-work-groups"], athena_region)
    if not wg:
        return incidents, {"Athena": signals_dict}

    names = [g.get("Name", "") for g in wg.get("WorkGroups", []) if g.get("Name")]
    if scope_ids:
        names = [n for n in names if any(n in s or s in n for s in scope_ids)]

    if not names:
        return incidents, {"Athena": signals_dict}

    queries: list[tuple[str, str, str, str, str]] = []
    for name in names:
        queries.append(("AWS/Athena", "ProcessedBytes", "WorkGroup", name, "Average"))
        queries.append(("AWS/Athena", "ProcessedBytes", "WorkGroup", name, "Maximum"))
        queries.append(("AWS/Athena", "QuerySucceeded", "WorkGroup", name, "Sum"))
        queries.append(("AWS/Athena", "QueryFailed", "WorkGroup", name, "Sum"))

    batch = get_metric_data_batch(athena_region, queries, hours=6)
    if not batch:
        log("WARN", "Athena metric batch returned nothing — skipping signal population")
        return incidents, {"Athena": signals_dict}

    for name in names:
        pb = batch.get(("ProcessedBytes", name)) or {}
        qs = batch.get(("QuerySucceeded", name)) or {}
        qf = batch.get(("QueryFailed", name)) or {}

        # Record only if at least one metric returned data.
        if not (pb.get("avg") is not None or pb.get("max") is not None
                or qs.get("sum") is not None or qf.get("sum") is not None):
            continue

        signals_dict[name] = {
            "ProcessedBytes": float(pb.get("max") if pb.get("max") is not None else pb.get("avg") or 0.0),
            "QuerySucceeded": float(qs.get("sum") or 0.0),
            "QueryFailed": float(qf.get("sum") or 0.0),
        }

    return incidents, {"Athena": signals_dict}
