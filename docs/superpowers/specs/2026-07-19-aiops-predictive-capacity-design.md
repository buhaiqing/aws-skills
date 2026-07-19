# A1: 预测性容量预警设计文档

- **日期**: 2026-07-19
- **状态**: 定稿
- **对应计划**: `2026-07-19-aiops-predictive-capacity.md`
- **目标**: 扩展 `aws-cloudwatch-ops`，集成 `get_metric_forecast` API，实现基于趋势预测的主动容量预警

## 1. 背景

当前 `aws-cloudwatch-ops` 只处理实时指标和历史统计。
A1 新增 **预测性能力**：
- 基于 14-day 历史趋势预测未来 7-day 容量
- CPU/内存/连接数等关键指标预测
- 生成扩容/缩容建议（主动预防 SLA 降级）

## 2. 目标与范围

**修改范围**:
```
aws-cloudwatch-ops/
  SKILL.md                           # 扩展 + Predictive Operations section
  references/
    aws-cli-usage.md                 # 补充 get-metric-forecast CLI
    boto3-sdk-usage.md               # 补充 boto3 forecast_metric_data
    capacity-forecast-rules.md        # 新建：预测规则定义
    capacity-alert-thresholds.md      # 新建：阈值配置
```

**预测覆盖服务**: EC2、ECS、RDS、ElastiCache、ALB

## 3. 核心能力

### 3.1 CloudWatch Metric Forecast API

```bash
# 预测 EC2 CPU 未来 7 天
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {
      "Id": "cpu_forecast",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/EC2",
          "MetricName": "CPUUtilization"
        },
        "Period": 3600,
        "Stat": "Average"
      },
      "AccountId": "{{env.AWS_ACCOUNT_ID}}"
    }
  ]' \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z

# 注意：Forecast API 需要 CloudWatch Contributor Insights 或单独启用
# 替代方案：使用 get-metric-statistics 手动计算趋势
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxx \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 3600 \
  --statistics Average \
  --output json
```

### 3.2 预测算法（Python 实现）

使用线性回归或移动平均计算趋势：

```python
import boto3
import statistics

def predict_capacity(metric_data: list, forecast_days: int = 7) -> dict:
    """
    基于历史数据预测未来容量。
    metric_data: CloudWatch get_metric_statistics 返回的 datapoints
    forecast_days: 预测天数
    """
    values = [float(p['Average']) for p in metric_data if 'Average' in p]
    if len(values) < 2:
        return {"predictable": False, "reason": "insufficient_data"}

    # 简单线性回归
    n = len(values)
    x_mean = sum(range(n)) / n
    y_mean = sum(values) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in enumerate(values))
    den = sum((x - x_mean) ** 2 for x in range(n))
    slope = num / den if den != 0 else 0
    intercept = y_mean - slope * x_mean

    # 预测未来
    predictions = []
    for i in range(forecast_days):
        predicted = intercept + slope * (n + i)
        predictions.append(max(0, min(100, predicted)))  # clamp to [0, 100]

    avg_prediction = statistics.mean(predictions)
    max_prediction = max(predictions)

    return {
        "predictable": True,
        "current_avg": round(y_mean, 2),
        "forecast_avg_7d": round(avg_prediction, 2),
        "forecast_max_7d": round(max_prediction, 2),
        "trend": "increasing" if slope > 0.5 else "decreasing" if slope < -0.5 else "stable",
        "threshold_warning": 80.0,
        "threshold_critical": 90.0,
        "will_exceed_warning": any(p > 80 for p in predictions),
        "will_exceed_critical": any(p > 90 for p in predictions),
    }
```

### 3.3 预测规则

| Rule ID | 服务 | 指标 | Warning | Critical | 行动 |
|---------|------|------|---------|----------|------|
| CAP-FC-01 | EC2 | CPUUtilization | 7d avg > 70% | 7d avg > 85% | Proactive resize |
| CAP-FC-02 | ECS | CPUUtilization | cluster avg > 70% | > 85% | Scale out ASG |
| CAP-FC-03 | RDS | DatabaseConnections | > 80% of max_conn | > 95% | Scale DB instance |
| CAP-FC-04 | ElastiCache | DatabaseMemoryUsagePercentage | > 75% | > 90% | Scale cluster |
| CAP-FC-05 | ALB | ActiveConnectionCount | 7d trend + 30% | > 80% capacity | Scale ASG |
| CAP-FC-06 | Lambda | ProvisionedConcurrencyUtilization | > 70% | > 90% | Increase provisioned |

### 3.4 与 aws-aiops-cruise 的集成

在 `aws-aiops-cruise` 的 HealthCruise 中增加预测性检查：

```
Perceive Layer (扩展):
  HealthCruise: 实时健康检查
  CapacityForecast: [NEW] 预测性容量检查 → 发现未来风险
```

**集成方式**: `aws-cloudwatch-ops` 提供 `get-capacity-forecast` 操作 → `aws-aiops-cruise` 调用

## 4. 输出格式

```json
{
  "capacity_forecast": {
    "resource_id": "i-xxx",
    "resource_type": "EC2",
    "metric": "CPUUtilization",
    "current_value": 65.5,
    "forecast_7d_avg": 78.3,
    "forecast_7d_max": 92.1,
    "trend": "increasing",
    "alert_level": "WARNING",
    "recommendation": "Proactive resize: t3.medium → t3.large",
    "confidence": "medium",
    "data_points_analyzed": 336,
    "forecast_generated_at": "2026-07-19T00:00:00Z"
  }
}
```

## 5. 验收标准

1. `get-capacity-forecast` 操作覆盖 ≥ 5 种资源类型
2. 预测算法使用真实 14-day 历史数据
3. Warning/Critical 阈值可配置（非硬编码）
4. 输出格式与 incident-schema 对齐
5. SKILL.md ≤ 120 lines（C6 通过）
6. 预测结果正确性有量化置信度
