# CloudWatch Skill — Prompt Examples

_Latest update: 2026-07-30_

Concrete user prompts for `aws-cloudwatch-ops`. Full routing: [operation-index.md](operation-index.md) · CLI: [aws-cli-usage.md](aws-cli-usage.md).

## 场景 1：EC2 CPU 告警 + SNS

**Prompt**: 给 EC2 i-0abc123def456 创建 CPU 告警，连续 3 次超 80% 时通过 SNS ops-alerts 通知。

| 步骤 | 操作 |
|------|------|
| Pre-flight | CLI + 凭证；`list-metrics --namespace AWS/EC2 --metric-name CPUUtilization --output json` |
| Execute | `put-metric-alarm --alarm-name HighCPU-i-0abc123def456 ... --alarm-actions arn:aws:sns:...:ops-alerts --output json` |
| Validate | `describe-alarms --alarm-names HighCPU-i-0abc123def456 --output json` |

## 场景 2：Lambda 错误率（Metric Math）

**Prompt**: 监控 Lambda my-order-processor，错误率 >5% 持续 2 周期告警；用 (Errors/Invocations)*100。

| 步骤 | 操作 |
|------|------|
| Execute | `put-metric-alarm --metrics '[errors, invocations, error_rate expr]' --threshold 5 --output json` |
| Validate | `describe-alarms --alarm-names <name> --output json` |

## 场景 3：异常检测告警（AIOps）

**Prompt**: EC2 网络流量周期性波动，静态阈值误报；创建异常检测告警，偏差因子 2。

| 步骤 | 操作 |
|------|------|
| Pre-flight | 确认 ≥14 天历史数据 |
| Execute | `put-metric-alarm` + `ANOMALY_DETECTION_BAND(m1, 2)` + `LessThanLowerOrGreaterThanUpperThreshold --output json` |

## 场景 4：成本异常根因（FinOps）

**Prompt**: 本月账单比上月多 20%，帮我查原因。

| 步骤 | 操作 |
|------|------|
| Execute | `get-metric-statistics --namespace AWS/Billing --metric-name EstimatedCharges --output json` |
| Correlate | EC2 CPU / Lambda Invocations / DynamoDB ConsumedCapacity 等指标对比 |

## 场景 5：Dashboard / 告警成本（FinOps）

**Prompt**: 当前 CloudWatch 告警和 Dashboard 花了多少钱？

| 步骤 | 操作 |
|------|------|
| Count | `describe-alarms --output json` · `list-dashboards --output json` |
| Estimate | `(N-10)×$0.10 + max(0,M-3)×$3.00/mo` |

## 场景 6：Lambda 错误日志（Logs Insights）

**Prompt**: 查过去 1 小时 Lambda my-order-processor 错误，按 5 分钟分桶。

| 步骤 | 操作 |
|------|------|
| Pre-flight | `describe-log-groups --log-group-name-prefix /aws/lambda/my-order-processor --output json` |
| Execute | `start-query` → poll `get-query-results` until Complete |

## 场景 7：CPU 趋势预测（AIOps）

**Prompt**: 预测 EC2 i-0abc123def456 未来 7 天 CPU，判断要不要扩容。

| 步骤 | 操作 |
|------|------|
| Execute | `get-metric-data` + `FORECAST(m1, "linear", 168) --output json` |

## 场景 8：Composite Alarm 合并（FinOps）

**Prompt**: 合并 HighCPU 和 HighMemory 为复合告警，任一触发即通知。

| 步骤 | 操作 |
|------|------|
| Execute | `put-composite-alarm --alarm-rule '(ALARM("HighCPU") OR ALARM("HighMemory"))' --output json` |

## 场景 9：告警未触发排查

**Prompt**: 告警 HighCPU 一直不触发，检查原因。

| 步骤 | 操作 |
|------|------|
| Diagnose | `describe-alarms` → `get-metric-statistics` → 核对 threshold / actions / dimensions |

## 场景 10：Contributor Insights

**Prompt**: 分析 CloudTrail 哪些用户访问被拒绝最多。

| 步骤 | 操作 |
|------|------|
| Execute | `put-insight-rule` → `list-insight-rules --output json` |

## 场景 11：三层分层巡检（跨技能）

**Prompt**: 全面运维巡检，含根因分析和自治愈建议。

→ 完整模板：[layered-inspection-template.md](layered-inspection-template.md)（网络层 `aws-elb-ops`/`aws-vpc-ops` · 资源层 `aws-ec2-ops`/`aws-rds-ops` · 应用层 `aws-eks-ops`）

## 设计原则

1. 每个 Prompt 映射 [operation-index.md](operation-index.md) 中的 Operation
2. 日常语言 → Agent 解析 CloudWatch 术语
3. FinOps / AIOps 场景交叉覆盖
4. 破坏性操作须 `confirm=` 前缀 — 见 [SKILL.md](../SKILL.md) Safety Gates
