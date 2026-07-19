"""Secrets Manager collector (rotation hygiene, read-only)."""

from __future__ import annotations

from datetime import UTC, datetime

from _shared import resource_in_scope, run_aws

# Never-rotated sentinel: trips CRITICAL via the inference rule (> 180d).
_NEVER_ROTATED_DAYS = 9999.0


def audit_secrets_rotation(
    region: str, scope_ids: set[str], run_id: str, customer: str
) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """Audit Secrets Manager secret rotation age (read-only).

    Emits no incidents — the orchestrator's inference rule (SEC-ROTATE-01)
    fires WARNING when RotationAgeDays > 90 and CRITICAL when > 180 or
    RotationEnabled == 0. This collector only produces signals.
    """
    incidents: list[dict] = []
    signals_dict: dict[str, dict[str, float]] = {}

    data = run_aws(["aws", "secretsmanager", "list-secrets"], region)
    if not data:
        return incidents, {"SecretsManager": signals_dict}

    for secret in data.get("SecretList", []) or []:
        name = secret.get("Name")
        arn = secret.get("ARN")
        if not name:
            continue
        if scope_ids and not resource_in_scope(name, scope_ids) and not resource_in_scope(arn or "", scope_ids):
            continue

        desc = run_aws(["aws", "secretsmanager", "describe-secret", "--secret-id", name], region)
        if not desc:
            continue

        last_rotated_str = desc.get("LastRotated")
        if last_rotated_str:
            last_rotated = datetime.fromisoformat(last_rotated_str.replace("Z", "+00:00"))
            age_days = (datetime.now(UTC) - last_rotated).total_seconds() / 86400
        else:
            age_days = _NEVER_ROTATED_DAYS

        signals_dict[name] = {
            "RotationAgeDays": float(age_days),
            "RotationEnabled": 1.0 if desc.get("RotationEnabled") else 0.0,
        }

    return incidents, {"SecretsManager": signals_dict}
