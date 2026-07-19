# F1: aws-finops-core 设计文档

- **日期**: 2026-07-19
- **状态**: 定稿
- **对应计划**: `2026-07-19-finops-core.md`
- **目标**: 创建统一 FinOps Composite Skill，整合成本异常检测 + Idle Resource 发现 + 成本分摊

## 1. 背景与问题

当前仓库：
- EKS 有 `references/cost-optimization.md`（Spot/RI 优化）
- ELB 有 `references/cost-tracking.md`（per-LB 成本查询）
- 其他 30+ 服务 **无成本相关文档**

痛点：
1. 无统一的成本异常检测框架
2. Idle Resource（闲置 LB/快照/未挂载 EBS）发现依赖人工
3. 跨服务成本分摊（Tag 覆盖率）无自动化检查

## 2. 目标与范围

**目标**: 创建 `aws-finops-core`（Composite L2 Skill），统一管理 AWS 成本优化与监控。

**目录布局**:
```
aws-finops-core/
  SKILL.md                          # ~80-100 lines, L2 composite
  references/
    cost-api-usage.md               # Cost Explorer API + CLI 汇总
    idle-detection-rules.md          # 闲置资源检测规则
    tag-compliance.md               # Tag 覆盖率检查
    anomaly-detection.md            # 成本异常检测逻辑
    reserved-coverage.md             # RI/SP 覆盖率分析
    budget-alerts.md                # Budget + CloudWatch 告警配置
  assets/
    cost-tags.yaml                  # 必填 Tag 定义示例
    budget-thresholds.yaml          # 告警阈值配置
```

**metadata.type**: `composite`（编排型，不直接调用 AWS）

**delegate 映射**:
| Operation | Delegate Skill |
|-----------|----------------|
| EC2 idle / RI coverage | `aws-ec2-ops` |
| EBS idle / snapshot | `aws-ec2-ops` |
| RDS idle / RI coverage | `aws-rds-ops` |
| ELB idle | `aws-elb-ops` |
| S3 bucket size anomaly | `aws-s3-ops` |
| Lambda idle | `aws-lambda-ops` |

## 3. 核心能力

### 3.1 成本异常检测（Anomaly Detection）

**数据源**: `aws ce get-cost-and-usage` (DAILY granularity)

**检测逻辑**:
```bash
# 获取 EC2 每日成本趋势
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics BlendedCost UnblendedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon EC2"]}}'
```

**异常判定**: 7-day average 为 baseline，今日 cost > baseline × 1.3 (WARNING) 或 × 1.5 (CRITICAL)

### 3.2 闲置资源检测（Idle Detection）

| 资源类型 | 检测方法 | 闲置定义 |
|---------|---------|---------|
| ALB/NLB | `aws elbv2 describe-load-balancers` + CloudWatch `RequestCount=0` 持续 7 天 | 无流量 |
| EBS Volume | `aws ec2 describe-volumes` + `Status=available` 未挂载超过 30 天 | 未挂载 |
| EBS Snapshot | `aws ec2 describe-snapshots` + `SnapshotId` 关联 Volume 已删除 | 孤立快照 |
| Lambda | `aws lambda list-functions` + CloudWatch `Invocations=0` 持续 30 天 | 无调用 |
| RDS Instance | `aws rds describe-db-instances` + CloudWatch `DatabaseConnections=0` 持续 7 天 | 无连接 |

### 3.3 Tag 合规覆盖率

```bash
# Cost Explorer 按 Tag 分组
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by '[{"Type":"TAG","Key":"Environment"},{"Type":"TAG","Key":"Application"}]'
```

合规率 = 有 Environment+Application Tag 的资源数 / 总资源数 × 100%

### 3.4 RI/SP 覆盖率

```bash
# 已有 RI 覆盖的 EC2 成本
aws cost-explorer get-reservation-coverage \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --metrics CoveredHours Utilization \
  --granularity DAILY
```

## 4. 变量约定

所有 Cost Explorer API 无需 `{{env.*}}`（只读查询），但需：

| Placeholder | Source |
|-------------|--------|
| `{{user.cost_period}}` | User input, default `LAST_30_DAYS` |
| `{{user.threshold_pct}}` | Anomaly threshold, default `130` |
| `{{user.idle_days}}` | Idle threshold days, default `7` |
| `{{env.AWS_ACCOUNT_ID}}` | For ARN 构造 |

## 5. Token Efficiency

- Cost Explorer API 结果已结构化 JSON → 无硬编码成本数字
- Idle 规则用 API 而非静态列表
- RI/SP 覆盖率直接调用 API，不维护静态表

## 6. 验收标准

1. SKILL.md ≤ 100 lines，C6 通过
2. `delegate` 映射中所有目标目录存在
3. 每个 delegate operation 有对应 CLI 示例
4. Idle Detection 覆盖 ≥ 5 种资源类型
5. Anomaly Detection 有明确的 baseline 计算逻辑
