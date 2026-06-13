"""Time helpers for AWS-native collectors."""

from __future__ import annotations

from datetime import datetime

def json_time(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

