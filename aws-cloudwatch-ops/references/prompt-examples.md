# CloudWatch Skill — Prompt Examples

_Latest update: 2026-05-28_

This document provides concrete user prompts that activate the `aws-cloudwatch-ops` skill. Copy and adapt these for your use cases.

> **双向链接**: SKILL.md → [prompt-examples.md](prompt-examples.md)
> **双向链接**: prompt-examples.md → [SKILL.md](../SKILL.md)

---

## 场景 1：基础告警创建 + 通知

### Prompt
```
帮我给 EC2 实例 i-0abc123def456 创建一个 CPU 告警，当 CPU 连续 3 次超过 80% 时，
通过 SNS 通知我。SNS Topic 叫 ops-alerts。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 发现需求 → 加载 `aws-cloudwatch-ops` |
| 2. Pre-flight → 检查 AWS CLI + 凭证 |
| 3. 确认 metric 存在 | `aws cloudwatch list-metrics --namespace AWS/EC2 --metric-name CPUUtilization` |
| 4. 创建告警 | `aws cloudwatch put-metric-alarm --alarm-name HighCPU-i-0abc123def456 ... --alarm-actions arn:aws:sns:us-east-1:123456789:ops-alerts` |
| 5. Validate | `aws cloudwatch describe-alarms --alarm-names HighCPU-i-0abc123def456` |

---

## 场景 2：Lambda 错误率告警（Metric Math）

### Prompt
```
帮我监控 Lambda 函数 my-order-processor 的错误率。
如果错误率超过 5% 并且持续 2 个周期，发告警。
用 Metric Math 计算 (Errors / Invocations) * 100 作为错误率。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 发现需要 Metric Math → `aws-cloudwatch-ops` 的 `PutMetricAlarm` + Metric Math |
| 2. 构建 metrics 数组 | `errors + invocations → error_rate = (errors/invocations)*100` |
| 3. 创建告警 | `put-metric-alarm` with `--metrics` + `--threshold 5` |
| 4. 通知绑定 SNS | `--alarm-actions arn:aws:sns:region:account:ops-alerts` |

---

## 场景 3：异常检测告警（AIOps / ML 动态阈值）

### Prompt
```
我的 EC2 实例的网络流量有周期性波动，白天高晚上低，
静态阈值老是误报。帮我创建一个异常检测告警，偏差因子设为 2。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 发现需要 Anomaly Detection → `aws-cloudwatch-ops` |
| 2. Pre-flight | 查询 30 天数据，确认 ≥ 2 周历史 |
| 3. 创建告警 | `put-metric-alarm` with `ANOMALY_DETECTION_BAND(m1, 2)` + `LessThanLowerOrGreaterThanUpperThreshold` |
| 4. 通知绑定 SNS | `--alarm-actions` |

---

## 场景 4：成本异常根因分析（FinOps + AIOps 交叉）

### Prompt
```
这个月的 AWS 账单比上个月多了 20%。帮我查一下怎么回事。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 查询账单 | `get-metric-statistics --namespace AWS/Billing --metric-name EstimatedCharges` |
| 2. 对比上月 | 提取最近 30 天 vs 上个月数据 |
| 3. 关联资源指标 | 对每个高消耗服务查对应指标（EC2 CPU, Lambda Invocations, DynamoDB ConsumedCapacity） |
| 4. 定位异常 | 找到资源使用率突增的服务和时间点 |
| 5. 建议 | 降配、清理闲置资源、预留实例建议 |

---

## 场景 5：Dashboard 成本评估（FinOps）

### Prompt
```
帮我看看我当前 CloudWatch 的告警和 Dashboard 花了多少钱。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 统计告警数 | `aws cloudwatch describe-alarms \| jq '.MetricAlarms \| length'` |
| 2. 统计 Dashboard | `aws cloudwatch list-dashboards \| jq '.DashboardEntries \| length'` |
| 3. 成本计算 | `(N-10)×$0.10 + max(0, M-3)×$3.00 = $X.XX/mo` |
| 4. 优化建议 | Composite Alarm 合并、冗余 Dashboard 删除 |

---

## 场景 6：查询 Lambda 错误日志（Logs Insights）

### Prompt
```
帮我查一下过去 1 小时的 Lambda my-order-processor 的日志，
把错误信息按 5 分钟分桶统计。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Pre-flight | `aws logs describe-log-groups --log-group-name-prefix /aws/lambda/my-order-processor` |
| 2. Start Query | `aws logs start-query --log-group-names /aws/lambda/my-order-processor --query-string 'filter @message like /ERROR/ \| stats count() by bin(5m)'` |
| 3. Get Results | Poll `get-query-results` 直到 `status=Complete` |
| 4. 展现结果 | 输出 5 分钟分桶的错误计数 |

---

## 场景 7：预测 CPU 趋势辅助扩容（AIOps + FinOps）

### Prompt
```
帮我预测一下 EC2 实例 i-0abc123def456 接下来 7 天的 CPU 使用率趋势，
看看要不要扩容。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Verify metric | `list-metrics` 确认 EC2 CPUUtilization |
| 2. Forecast | `get-metric-data` with `FORECAST(m1, "linear", 168)` |
| 3. 分析结果 | 比较预测值与安全阈值 |
| 4. 建议 | 扩容、调整实例类型、或保持现状 |

---

## 场景 8：Composite Alarm 合并告警省钱（FinOps）

### Prompt
```
我有两个告警 HighCPU 和 HighMemory，帮我合并成一个复合告警，
只要任何一个触发就发通知。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Pre-flight | 检查 HighCPU 和 HighMemory 是否存在 |
| 2. 创建 | `put-composite-alarm --alarm-rule '(ALARM("HighCPU") OR ALARM("HighMemory"))'` |
| 3. FinOps 提醒 | "合并后每月节省 $0.10" |
| 4. Validate | `describe-alarms` |

---

## 场景 9：排查告警未触发问题

### Prompt
```
我的告警 HighCPU 一直没有触发，检查一下怎么回事。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 查状态 | `describe-alarms --alarm-names HighCPU` → 确认 `StateValue` |
| 2. 查数据 | `get-metric-statistics` → 检查是否有数据点 |
| 3. 查阈值 | 比较 `Threshold` 与实际值 |
| 4. 查 Action | 确认 `--alarm-actions` 是否设置 |
| 5. 报告原因 | 阈值过高 / 无数据点 / 缺少通知目标 / 维度不匹配 |

---

## 场景 10：批量摘要（AIOps: Contributor Insights）

### Prompt
```
帮我分析一下 CloudTrail 日志中哪些用户访问被拒绝最多。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 创建规则 | `put-insight-rule` 匹配 `$.errorCode` starts-with "Access" |
| 2. 等待 | 规则运行需要时间收集数据 |
| 3. 查询结果 | `list-insight-rules` 获取贡献者 |
| 4. 报告 | 展示 Top-N 被拒用户及次数 |

---

## 场景 11（跨技能编排）：三层分层巡检 —— 网络层 → 云资源层 → 应用层

> **详细模板见**: [layered-inspection-template.md](layered-inspection-template.md) — 包含根因分析、决策类型、自治愈闭环的完整版本

这是一个**跨技能编排**的综合巡检场景，Agent 需依次加载多个 AWS 技能，按自底向上三层逻辑执行巡检并生成层次化报告。

### Prompt

```
帮我做一次全面的运维巡检，包含根因分析和自治愈建议
```

### 一句话激活

| 触发词 | 执行范围 | 决策类型覆盖 |
|--------|----------|-------------|
| "帮我做一次全面运维巡检，包含根因分析和自治愈建议" | 三层全量 | AUTO_HEAL / AI_ASSIST / MANUAL |
| "帮我巡检网络层并做 RCA" | 仅网络层 | 同全量 |
| "帮我看看 EKS 为什么有问题" | 仅应用层 + 根因诊断 | AI_ASSIST 为主 |
| "自治愈巡检" | 三层全量 | 仅 AUTO_HEAL 项执行 |

### 跨技能依赖链

```
┌─────────────────────────────────────────────────────┐
│  场景 11：三层分层巡检                               │
├─────────┬───────────────────────────────────────────┤
│ 发起层  │ aws-cloudwatch-ops (CloudWatch 指标查询)   │
├─────────┼───────────────────────────────────────────┤
│ 网络层  │ aws-elb-ops + aws-vpc-ops                 │
│ 资源层  │ aws-ec2-ops + aws-rds-ops                 │
│         │ + aws-elasticache-ops + aws-dynamodb-ops  │
│ 应用层  │ aws-eks-ops                               │
└─────────┴───────────────────────────────────────────┘
```

> **详细执行步骤、检查命令、输出格式、根因分析、决策建议、自治愈闭环请见**: [layered-inspection-template.md](layered-inspection-template.md)

---

## 设计原则

1. **每个 Prompt 对应一个具体的** Operation 或组合 —— Agent 可以准确匹配到 SKILL.md 中的执行流
2. **日常语言 → Agent 解析** —— 用户不需要知道 CloudWatch 术语，Agent 负责翻译
3. **FinOps 和 AIOps 场景交叉** —— 成本优化、异常检测、趋势预测覆盖多种需求
4. **按复杂度分级**—— 从单步操作到多步编排