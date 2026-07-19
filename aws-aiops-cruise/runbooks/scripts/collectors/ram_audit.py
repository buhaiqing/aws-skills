"""RAM (Resource Access Manager) collector — share status auditing."""

from __future__ import annotations

from typing import Any

from _shared import run_aws


def audit_ram_shares(
    region: str, scope_ids: set[str], run_id: str, customer: str
) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """Audit RAM resource shares owned by SELF.

    RAM-SHARE-01: a resource share is unhealthy when its status is not ACTIVE
    or any principal association was rejected (status == FAILED).

    The collector only emits signals; the orchestrator's inference rule turns
    them into incidents. Available signals:
      ram list-resource-shares --resource-owner SELF -> resourceShares[].status
      ram list-principal-associations --resource-share-arn <arn> -> associations[].status

    Out of scope: external invitee acceptance state (not available here).
    """
    incidents: list[dict] = []
    signals: dict[str, dict[str, float]] = {}

    shares = run_aws(["aws", "ram", "list-resource-shares", "--resource-owner", "SELF"], region)
    if not shares:
        return incidents, {"RAM": signals}

    for share in shares.get("resourceShares", []) or []:
        arn = share.get("resourceShareArn")
        if not arn:
            continue
        if scope_ids and not _arn_in_scope(arn, share, scope_ids):
            continue

        status = share.get("status")
        rejected = 0
        assoc = run_aws(
            ["aws", "ram", "list-principal-associations", "--resource-share-arn", arn],
            region,
        )
        for a in (assoc or {}).get("associations", []) or []:
            if a.get("status") == "FAILED":
                rejected += 1

        signals[arn] = {
            "ShareStatusActive": 1.0 if status == "ACTIVE" else 0.0,
            "RejectedAssociations": float(rejected),
        }

    return incidents, {"RAM": signals}


def _arn_in_scope(arn: str, share: dict[str, Any], scope_ids: set[str]) -> bool:
    """Best-effort scope check against share ARN and its name."""
    from _shared import resource_in_scope

    name = share.get("name", "")
    return bool(resource_in_scope(arn, scope_ids) or (name and resource_in_scope(name, scope_ids)))
