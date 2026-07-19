# F2: Cost-Tracking 扩展设计文档

- **日期**: 2026-07-19
- **状态**: 定稿
- **对应计划**: `2026-07-19-finops-cost-tracking.md`
- **目标**: 为 EC2/RDS/Lambda/S3 四个高频计费服务补充 `references/cost-tracking.md`

## 1. 背景

ELB 已有 `aws-elb-ops/references/cost-tracking.md` 模板，定义了 per-LB 成本查询 + idle LB savings report 模式。
F2 将此模式扩展到其他 4 个高频计费服务，保持格式一致。

## 2. 目标与范围

**目标**: 为 EC2、RDS、Lambda、S3 各补充 `cost-tracking.md`，对齐 ELB 模板格式。

**文件布局**（每个服务）:
```
aws-ec2-ops/references/cost-tracking.md   # 新建
aws-rds-ops/references/cost-tracking.md   # 新建
aws-lambda-ops/references/cost-tracking.md # 新建
aws-s3-ops/references/cost-tracking.md    # 新建
```

## 3. 统一模板结构

每个 `cost-tracking.md` 遵循 4 个标准 Section：

### Section 1: Per-Resource Cost Query
使用 `aws ce get-cost-and-usage` 按 Tag/Resource 维度分组。

### Section 2: Idle Resource Detection
定义闲置标准 + CloudWatch 指标查询。

### Section 3: Savings Recommendations
Spot/RI/Spot savings plan 覆盖率 + 优化建议。

### Section 4: Anomaly Detection
成本突增判定规则（基于 baseline 倍数）。

## 4. 各服务差异

### EC2
- **成本构成**: On-Demand + RI + Spot + EBS 附加
- **Idle 检测**: `describe-instances` 状态 + CloudWatch CPU 0
- **Savings**: RI Coverage %, Savings Plans 利用率
- **Anomaly**: 突发大量新实例（instance-hours 突增）

```bash
# EC2 per-Instance-Type cost
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon EC2"]}}'
  --group-by '[{"Type":"DIMENSION","Key":"INSTANCE_TYPE"}]'

# EC2 Idle: running but CPU < 5% for 7 days
aws cloudwatch get-metric-data \
  --metric-data-queries '[{"Id":"cpu","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization"},"Period":86400,"Stat":"Average"}}]'
```

### RDS
- **成本构成**: Instance hours + Storage (GB) + I/O + Backup Storage + Multi-AZ
- **Idle 检测**: CloudWatch `DatabaseConnections=0` 持续 7 天
- **Savings**: RI Coverage（数据库实例预留）
- **Anomaly**: 存储量突增、I/O 费用异常

```bash
# RDS cost by engine
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Relational Database Service (RDS)"]}}'
  --group-by '[{"Type":"DIMENSION","Key":"DATABASE_ENGINE"}]'

# RDS Idle: no connections
aws cloudwatch get-metric-data \
  --metric-data-queries '[{"Id":"conn","MetricStat":{"Metric":{"Namespace":"AWS/RDS","MetricName":"DatabaseConnections"},"Period":3600,"Stat":"Sum"}}]'
```

### Lambda
- **成本构成**: 请求次数 (requests) + 执行时长 (GB-s)
- **Idle 检测**: `Invocations=0` 持续 30 天
- **Savings**: Provisioned Concurrency + Savings Plans
- **Anomaly**: 请求量突增 10x

```bash
# Lambda cost by function
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS Lambda"]}}'
  --group-by '[{"Type":"TAG","Key":"FunctionName"}]'

# Lambda Idle: no invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value={{user.function_name}} \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 86400 \
  --statistics Sum
```

### S3
- **成本构成**: Storage (GB) + Requests (PUT/GET) + Data Transfer + Intelligent-Tiering
- **Idle 检测**: `LastModified` 超过 1 年无变化 + 非 IA/Glacier 层
- **Savings**: 迁移至 S3 Intelligent-Tiering / Glacier / One Zone-IA
- **Anomaly**: 存储量突增 50%

```bash
# S3 cost by bucket
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Simple Storage Service"]}}'
  --group-by '[{"Type":"DIMENSION","Key":"LINKED_ACCOUNT"}]'

# S3 bucket size (via Storage Lens)
aws s3 get-storage-lens-configuration \
  --config-id default \
  --region {{env.AWS_DEFAULT_REGION}}
```

## 5. 验收标准

1. 4 个 `cost-tracking.md` 文件全部创建
2. 每个文件包含上述 4 个标准 Section
3. 所有 CLI 命令使用 `--output json`
4. ELB `cost-tracking.md` 模板保持不变（向后兼容）
5. SKILL.md line count ≤ 120（C6 通过）
