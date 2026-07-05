"""Block storage layer collectors (EBS volumes)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from _shared import make_incident, resource_in_scope, run_aws, log

from collectors._time import json_time


def audit_ebs_volumes(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    """Check for orphan available volumes and queue-depth saturation."""
    incidents: list[dict] = []
    volumes = run_aws(["aws", "ec2", "describe-volumes"], region)
    if not volumes:
        return incidents

    now = datetime.now(UTC)
    for vol in volumes.get("Volumes", []):
        vol_id = vol.get("VolumeId", "")
        if scope_ids and not resource_in_scope(vol_id, scope_ids):
            continue

        state = vol.get("State", "")
        vol_type = vol.get("VolumeType", "")

        # EBS-VOL-01: orphan available volume (> 30 days)
        if state == "available":
            create_time = vol.get("CreateTime", "")
            if create_time:
                try:
                    created = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
                    age_days = (now - created).days
                    if age_days > 30:
                        incidents.append(
                            make_incident(
                                run_id=run_id,
                                customer=customer,
                                region=region,
                                resource_type="EBS",
                                resource_id=vol_id,
                                rule_id="EBS-VOL-01",
                                title=f"Orphan EBS volume available > {age_days} days",
                                level="WARNING",
                                metric="AvailableVolumeAge",
                                current_value=float(age_days),
                                threshold_warning=30,
                                recommendation="Delete if unintended, or attach to instance",
                            )
                        )
                except (ValueError, TypeError):
                    pass

        # EBS-VOL-02: io1/io2 with low provisioned IOPS (queue pressure)
        if state == "in-use" and vol_type in ("io1", "io2"):
            iops = vol.get("Iops", 0)
            # GP3 baseline is 3k IOPS; if provisioned IOPS < 3k, may saturate queue
            if iops > 0 and iops < 3000:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="EBS",
                        resource_id=vol_id,
                        rule_id="EBS-VOL-02",
                        title=f"EBS {vol_type} provisioned IOPS {iops} below GP3 baseline (3k)",
                        level="INFO",
                        metric="ProvisionedIops",
                        current_value=float(iops),
                        threshold_warning=3000,
                        recommendation="Review workload IOPS; consider gp3 with auto scaling or io2 with provisioned IOPS matching workload",
                    )
                )

    return incidents
