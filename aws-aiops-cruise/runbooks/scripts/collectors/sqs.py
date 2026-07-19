"""SQS queue collectors — DLQ detection."""

from __future__ import annotations

from typing import Any

from _shared import make_incident, run_aws


def audit_sqs_dlq(
    region: str, scope_ids: set[str], run_id: str, customer: str
) -> tuple[list[dict], dict[str, dict[str, Any]]]:
    """Detect SQS Dead Letter Queues with visible messages.

    Returns (incidents, signals_dict) where signals_dict["SQS"] = {
        queue_url: {
            "QueueType": "dlq" | "regular",
            "ApproximateNumberOfMessages": int,
            "ApproximateAgeOfOldestMessage": float (seconds),
            "QueueName": str,
        }
    }
    """
    incidents: list[dict] = []
    signals: dict[str, dict[str, Any]] = {}

    data = run_aws(["aws", "sqs", "list-queues", "--max-results", 100], region)
    if not data:
        return incidents, {"SQS": signals}

    for url in data.get("QueueUrls", []):
        # Get queue attributes
        attrs = run_aws(
            [
                "aws", "sqs", "get-queue-attributes",
                "--queue-url", url,
                "--attribute-names",
                "ApproximateNumberOfMessages,ApproximateAgeOfOldestMessage,QueueArn",
            ],
            region,
        )
        if not attrs:
            continue

        attr = attrs.get("Attributes", {})
        msg_count = int(attr.get("ApproximateNumberOfMessages", 0) or 0)
        age = float(attr.get("ApproximateAgeOfOldestMessage", 0) or 0)
        queue_name = url.split("/")[-1]

        # Determine if DLQ (name contains DLQ or DeadLetter)
        is_dlq = "DLQ" in queue_name.upper() or "DEADLETTER" in queue_name.upper()

        signals[url] = {
            "QueueType": "dlq" if is_dlq else "regular",
            "ApproximateNumberOfMessages": msg_count,
            "ApproximateAgeOfOldestMessage": age,
            "QueueName": queue_name,
        }

        # Rule: SQS-DLQ-01 — DLQ messages visible > 0 for > 1h
        if is_dlq and msg_count > 0 and age > 3600:
            level = "CRITICAL" if msg_count > 10 else "WARNING"
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="SQS",
                    resource_id=queue_name,
                    rule_id="SQS-DLQ-01",
                    title=f"SQS DLQ `{queue_name}`: {msg_count} messages, oldest {age/3600:.1f}h",
                    level=level,
                    metric="ApproximateNumberOfMessages",
                    current_value=float(msg_count),
                    recommendation="Inspect message content; fix upstream consumer; delegate aws-sqs-ops",
                )
            )

    return incidents, {"SQS": signals}
