# RDS Skill — Prompt Examples

_Latest update: 2026-05-28_

This document provides concrete user prompts that activate the `aws-rds-ops` skill. Copy and adapt these for your use cases.

> **双向链接**: SKILL.md → [prompt-examples.md](prompt-examples.md)
> **双向链接**: prompt-examples.md → [SKILL.md](../SKILL.md)

---

## 场景 1：数据库慢查询根因诊断（AIOps）

### Prompt
```
我的 RDS MySQL 最近变慢了，帮我查一下什么问题。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 查实例状态 | `aws rds describe-db-instances --db-instance-identifier {{u.id}}` |
| 2. 查 CloudWatch 指标 | `CPUUtilization`, `DatabaseConnections`, `ReadLatency`, `WriteLatency` — 最近 1 小时趋势 |
| 3. 查 Performance Insights | `describe-performance-insights-details` → Top SQL by load |
| 4. 查慢查询日志 | `describe-db-log-files` → 最近的慢查询 |
| 5. 输出 RCA 报告 | 发现(指标偏差) → RCA(根因) → 决策(建议操作) → SLA |

### 输出格式
```
【发现】prod-mysql-orders — CPUUtilization=87%(持续30分钟), ReadLatency=12ms(正常<5ms)
【RCA】直接原因: 慢查询 `SELECT * FROM orders WHERE status='pending'` 全表扫描(rows_examined=500K)
      └─判定: Performance Insights 显示该 SQL 占 DB Load 65%
【决策】[AI_ASSIST] 建议添加索引 idx_orders_status
      ├─ CREATE INDEX idx_orders_status ON orders(status);
      └─ 失败回退: 索引创建后仍慢 → 考虑升级实例规格
【SLA】P1 (2小时) — 性能降级但可用
```

---

## 场景 2：存储自动扩容（AIOps — AUTO_HEAL）

### Prompt
```
RDS 存储快满了，帮我看看并处理。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 查存储 | `aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name FreeStorageSpace --dimensions Name=DBInstanceIdentifier,Value={{u.id}}` |
| 2. 评估 | FreeStorageSpace < 10% → 触发扩容 |
| 3. 扩容 | `aws rds modify-db-instance --db-instance-identifier {{u.id}} --allocated-storage {{new_size}} --apply-immediately` |
| 4. 验证 | `describe-db-instances` → `.AllocatedStorage` = new_size |

### 扩容计算公式
```
新存储 = max(当前存储 × 1.2, 当前存储 + 20)  # 最少扩 20%, 至少 20GB
```

---

## 场景 3：连接数异常诊断 + 自治愈（AIOps）

### Prompt
```
我的数据库连不上了，连接数太多了，帮我看下。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 查连接数 | `DatabaseConnections` + `DBInstanceIdentifier` → 最近 1 小时数据 |
| 2. 查 max_connections | 参数组中的 max_connections 当前值 |
| 3. 判断 | DatabaseConnections >= max_connections × 90% → 触发自治愈 |
| 4. 自治愈 | `modify-db-parameter-group` → `max_connections+=100`, ApplyMethod=immediate 并通知用户 |
| 5. 建议 | 检查应用层连接池 / C3P0 泄漏 |

---

## 场景 4：备份合规检查（AIOps）

### Prompt
```
帮我检查所有 RDS 实例的备份配置是否符合规范。
```

### Agent 执行流程
```bash
aws rds describe-db-instances --query "DBInstances[*].{ID:DBInstanceIdentifier,Backup:BackupRetentionPeriod,PITR:PointInTimeRecoveryEnabled,Encrypted:StorageEncrypted,DeletionProtection:DeletionProtection}" --output table
```
检查项:
- BackupRetentionPeriod >= 7 (Production) / >= 1 (Dev)
- StorageEncrypted = true (Production)
- DeletionProtection = true (Production)
- 输出合规/不合规清单

---

## 场景 5：闲置实例清理（FinOps）

### Prompt
```
帮我找一下有没有闲置的 RDS 实例可以删掉省钱。
```

### Agent 执行流程
```bash
# 1. 列出所有实例及最后修改时间
aws rds describe-db-instances --query "DBInstances[*].{ID:DBInstanceIdentifier,Status:DBInstanceStatus,Created:InstanceCreateTime,Engine:Engine,Size:DBInstanceClass}"

# 2. 检查 CloudWatch 连接数指标
aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name DatabaseConnections --statistics Maximum --period 86400 --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) --end-time $(date -u +%Y-%m-%dT00:00:00Z) --dimensions Name=DBInstanceIdentifier,Value={{u.id}}
```
**闲置判定**: DatabaseConnections = 0 (连续 14 天) + 最后修改 > 30 天 → 建议删除/停止

---

## 场景 6：灾难恢复演练 — 跨区域快照复制

### Prompt
```
帮我把 prod-mysql-orders 的快照复制到 eu-west-1 做灾备。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 查实例 | `describe-db-instances --db-instance-identifier prod-mysql-orders` → 确认 region/状态 |
| 2. 创建快照 | `create-db-snapshot` → `prod-mysql-orders-dr-$(date +%Y%m%d)` |
| 3. 等待可用 | `wait db-snapshot-available` |
| 4. 跨区域复制 | `copy-db-snapshot --source-region us-east-1 --source-db-snapshot-identifier arn:... --target-db-snapshot-identifier prod-mysql-orders-dr-eu --destination-region eu-west-1` |
| 5. 验证 | `describe-db-snapshots --region eu-west-1` |

---

## 场景 7：参数组性能调优建议（AIOps）

### Prompt
```
我的 PostgreSQL 数据库性能不佳，帮我检查参数组设置并给出优化建议。
```

### Agent 执行流程
```bash
# 1. 查看当前参数组
aws rds describe-db-parameters --db-parameter-group-name {{u.pg}}
# 2. 与推荐值对比
```
| 参数 | 推荐值 | 说明 |
|------|--------|------|
| shared_buffers | 实例内存的 25% | InnoDB/PostgreSQL 缓存 |
| effective_cache_size | 实例内存的 75% | 查询优化器估值 |
| work_mem | 25MB — 50MB | 排序操作内存 |
| max_connections | 根据实例规格 (见 example-config.yaml) | 过高会消耗内存 |

---

## 场景 8：Aurora 集群故障切换诊断

### Prompt
```
Aurora 集群 prod-aurora-catalog 的写节点好像挂了，帮我检查并做故障切换。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 查集群 | `describe-db-clusters --db-cluster-identifier prod-aurora-catalog` |
| 2. 查节点 | `.DBClusterMembers` → 哪个是 writer, 状态 |
| 3. 故障切换 | `failover-db-cluster --db-cluster-identifier prod-aurora-catalog --target-db-instance-identifier {{replica_id}}` |
| 4. 验证 | 检查新 writer 端点 (`Endpoint`) 是否可达 |
| 5. SLA | P0 (15分钟) — 写中断 = 业务不可用 |

---

## 场景 9：跨技能编排 — RDS 根因联动分析

### Prompt
```
我的 RDS 实例突然 CPU 飙升到 99%，帮我查一下是应用层还是数据库的问题。
```

### Agent 执行流程（跨技能）
```
1. [rds-ops] 查 Performance Insights → Top SQL / Wait Events
2. [cloudwatch-ops] 查近 1 小时 CPU + Connections + ReadIOPS 趋势
3. [ec2-ops] 如果 RDS CPU 高但 SQL 正常 → 查 EC2 底层
4. [lambda-ops] 如果应用连接突增 → 查 Lambda 调用量
```
**输出**: 跨层 RCA 报告

---

## 场景 10：容量预测建议（AIOps + FinOps）

### Prompt
```
看看我 RDS 实例的存储和 CPU 趋势，未来一个月需不需要扩容？
```

### Agent 执行流程
```bash
# 1. 拉 30 天数据
aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name FreeStorageSpace --statistics Average --period 86400 --start-time $(date -d '-30 days' -u +%Y-%m-%dT00:00:00Z) --end-time $(date -u +%Y-%m-%dT00:00:00Z) --dimensions Name=DBInstanceIdentifier,Value={{u.id}}
# 2. 线性拟合 → 预测到期天数
# 3. 建议: 扩容 / 清理数据 / 启用存储自动扩容
```

---

## 设计原则

1. **每个 Prompt 对应一个具体的** AIOps 场景
2. **日常语言 → Agent 解析** — 用户不需要知道 AWS 术语
3. **AIOps 和 FinOps 交叉** — 成本优化、异常检测、自治愈覆盖
4. **按复杂度分级** — 从单步诊断到跨技能编排