---
runbook_id: "07"
scenario: "Bottleneck localization"
version: "2.1.0"
---

# Bottleneck Localization

End-to-end latency chain: ALB `TargetResponseTime` → EC2 CPU/Memory/IO/Network → RDS latency → NAT errors.

> **Script**: [`runbooks/scripts/bottleneck-localization.py`](../scripts/bottleneck-localization.py)

## 1. Symptom Collection

Run emergency troubleshoot with `--symptom latency`, then apply inference rules ALB-EC2-02, EC2-01, RDS-CONN-01.

## 2. EC2 Bottleneck Diagnosis

Diagnose in order: **CPU → Memory → EBS I/O → Network**. Each phase: check metric → check cross-signal → classify root cause.

| Phase | Metric (FD rule) | Threshold | Cross-signal | Root cause |
|-------|-------------------|-----------|--------------|------------|
| **CPU** | FD-07 `CPUUtilization` | avg > 90% PT15M | + ASG at max | Scale ceiling → resize or increase max |
| | FD-07 | avg > 90% PT15M | + RDS CPU > 85% | DB query CPU-bound → optimize SQL or add read replicas |
| **Memory** | FD-07a `CWAgent.Memory % Used` | avg > 85% PT15M | + OOM in dmesg | Memory leak → find leaking process via `ps aux --sort=-%mem` |
| | FD-07a | avg > 85% PT15M | + swap > 50% | Thrashing → resize or fix leak |
| **EBS I/O** | FD-07b `VolumeQueueLength` | avg > 64 PT10M | + FD-07c `BurstBalance` < 20% | Burst depleted → upgrade to gp3/io1/io2 |
| | FD-07d `ReadLatency`/`WriteLatency` | p95 > 20ms PT15M | + VolumeQueueLength > 32 | Queue depth latency → increase IOPS or reduce I/O threads |
| **Network** | FD-07e `NetworkOut` | > 80% type limit PT15M | + TCP retransmits | Bandwidth saturation → resize to higher network instance |
| | FD-07f `NetworkPacketsIn/Out` drop rate | > 1% PT15M | + VPC Flow Logs REJECT | Packet drops → review SG rules or ENI limits |

> **Instance type network/EBS limits**: Fetch via `aws ec2 describe-instance-types --instance-types <type>` — do not hardcode (TE-1).

> **Diagnostic commands**: See [`aws-ec2-ops/references/aws-cli-usage.md`](../../aws-ec2-ops/references/aws-cli-usage.md) §AIOps — `top`, `free -h`, `iostat`, `ss -s`, `netstat -s`.

## 3. Cross-Layer Correlation

| Symptom pattern | Root cause | Fix path |
|-----------------|-----------|----------|
| ALB latency + EC2 CPU high + RDS CPU high | App CPU-bound (DB queries) | Optimize SQL, add read replicas, or resize EC2 |
| ALB latency + EC2 CPU high + RDS normal | App CPU-bound (business logic) | Resize EC2 or optimize code |
| ALB latency + EC2 CPU normal + memory high | Memory pressure / swap | Resize EC2 or fix memory leak |
| ALB latency + EC2 normal + EBS queue high | I/O bottleneck | Upgrade EBS type or add IOPS |
| ALB latency + EC2 normal + network high | Network bottleneck | Resize EC2 or check SG/ENI |
| ALB latency + EC2 normal + NAT errors | NAT port exhaustion | Add NAT Gateway per AZ |

## 4. Diagnostic Flowchart

```
ALB TargetResponseTime > 1s
  ├─ EC2 CPU > 90%? → YES → top processes → resize or optimize SQL
  ├─ EC2 Memory > 85%? → YES → OOM in dmesg? → resize or fix leak
  ├─ EBS VolumeQueueLength > 64? → YES → BurstBalance < 20%? → upgrade EBS
  ├─ NetworkOut > 80% limit? → YES → resize to higher network instance
  └─ All normal → Check RDS latency / connection pool
```
