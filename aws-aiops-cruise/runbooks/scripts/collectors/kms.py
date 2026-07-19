"""KMS key rotation and age collectors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from _shared import make_incident, run_aws


def audit_kms_keys(
    region: str, scope_ids: set[str], run_id: str, customer: str
) -> tuple[list[dict], dict[str, dict[str, Any]]]:
    """Detect KMS keys with rotation disabled or older than 365 days.

    Returns (incidents, signals_dict) where signals_dict["KMS"] = {
        key_arn: {
            "KeyRotationEnabled": bool,
            "KeyManager": str,  # "CUSTOMER" or "AWS"
            "CreatedTimestamp": float (unix ts),
            "KeySpec": str,
            "DaysSinceCreation": int,
        }
    }
    """
    incidents: list[dict] = []
    signals: dict[str, dict[str, Any]] = {}

    data = run_aws(["aws", "kms", "list-keys", "--limit", 100], region)
    if not data:
        return incidents, {"KMS": signals}

    now = datetime.now(timezone.utc)
    for key in data.get("Keys", []):
        key_arn = key.get("KeyArn", "")
        key_id = key.get("KeyId", "")

        # Get key rotation status
        rot_data = run_aws(["aws", "kms", "get-key-rotation-status", "--key-id", key_id], region)
        if not rot_data:
            continue

        rot_enabled = rot_data.get("KeyRotationEnabled", False)

        # Get key metadata
        meta = run_aws(["aws", "kms", "describe-key", "--key-id", key_id], region)
        if not meta or not meta.get("KeyMetadata"):
            continue

        km = meta["KeyMetadata"]
        key_manager = km.get("KeyManager", "AWS")
        key_spec = km.get("KeySpec", "")
        created_str = km.get("CreationDate", "")

        if not created_str:
            continue

        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        days_since = (now - created).days

        signals[key_arn] = {
            "KeyRotationEnabled": rot_enabled,
            "KeyManager": key_manager,
            "CreatedTimestamp": created.timestamp(),
            "KeySpec": key_spec,
            "DaysSinceCreation": days_since,
        }

        # Skip AWS-managed keys for incident generation
        if key_manager == "AWS":
            continue

        # Rule: KMS-ROTATE-01 — CRITICAL if rotation disabled and > 365d old
        if not rot_enabled and days_since > 365:
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="KMS",
                    resource_id=key_arn,
                    rule_id="KMS-ROTATE-01",
                    title=f"KMS key rotation disabled > 365d: {key_id}",
                    level="CRITICAL",
                    metric="DaysSinceRotation",
                    current_value=float(days_since),
                    recommendation="Enable rotation: aws kms enable-key-rotation --key-id; delegate aws-kms-ops",
                )
            )

    return incidents, {"KMS": signals}
