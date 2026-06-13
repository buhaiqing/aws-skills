---
runbook_id: "07"
scenario: "Bottleneck localization"
version: "1.0.0"
---

# Bottleneck Localization

End-to-end latency chain: ALB `TargetResponseTime` → EC2 CPU → RDS latency → NAT errors.

> **Script**: [`runbooks/scripts/bottleneck-localization.py`](../scripts/bottleneck-localization.py)

Run emergency troubleshoot with `--symptom latency`, then apply inference rules ALB-EC2-02, EC2-01, RDS-CONN-01.
