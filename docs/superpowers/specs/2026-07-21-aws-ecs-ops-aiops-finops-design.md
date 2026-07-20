# aws-ecs-ops AIOps+FinOps 闭环补齐 — 设计文档

- **日期**: 2026-07-21
- **状态**: 已定稿(用户确认范围:P0 + P1 完整闭环)
- **对应计划**: `docs/superpowers/plans/2026-07-21-aws-ecs-ops-aiops-finops.md`

## 1. 背景与问题

`aws-ecs-ops` v1.0.0 是仓库 30+ 服务 skill 中典型"安全 CRUD 手册"形态:
cluster / service / task definition / task lifecycle 操作齐全,GCL rubric 与 safety gate 完备,
但**对 AIOps 检测 / FinOps 优化 / 撮合杠杆 三层全部缺位**。

### 1.1 Disk-verified evidence(2026-07-21 复核)

| 文件 | 当前缺口 |
|---|---|
| [aws-ecs-ops/SKILL.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/SKILL.md) | 无 Container Insights 指标、无 task stoppedReason、无 Capacity Provider 操作、无 Fargate Spot、无 `--tags` on service/task-definition;**无 frontmatter `provides` 字段** |
| [aws-ecs-ops/references/troubleshooting.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/references/troubleshooting.md) | 缺 deployment 失败诊断(circuit breaker / `rolloutState`) |
| [aws-finops-core/SKILL.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-finops-core/SKILL.md) `metadata.delegate` | 仅含 `ec2 / ebs / rds / elb / s3 / lambda`,**ECS 完全缺席** |
| [aws-aiops-cruise/SKILL.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-aiops-cruise/SKILL.md) | `cross_skill_deps` 第 39 行含 `aws-ecs-ops`,但无 ECS-specific inference rule / signal 引用 |
| `aws-application-autoscaling-*` | **整个仓库没有任何 skill 覆盖此服务**(grep 验证,见 §7 风险) |

### 1.2 AIOps 痛点

1. Container Insights 是否启用不可知,AIOps agent 无信号入口
2. Task drift(`runningCount < desiredCount`) 无告警路径
3. Task `stoppedReason` 中 `SpotInterruption` / `EssentialContainerExited` / `CannotPullContainerError` 不进 AIOps 信号链路
4. Deployment circuit breaker `rolloutState=FAILED` 无诊断模板
5. ECS Service Auto Scaling(`aws-application-autoscaling` 命名空间)无任何 skill 覆盖 → AIOps 自动扩缩响应断链

### 1.3 FinOps 痛点

1. `--tags` 仅出现在 `create-cluster`,service / task-definition 创建**无 tag** → Cost Allocation / Chargeback 直接断链
2. Fargate Spot 完全没提,可省 **~70%** 算力费(典型浪费)
3. Compute Optimizer ECS right-sizing 不引用 → 典型 40-70% 资源浪费无建议路径
4. 28-day idle service(`desiredCount=0 && runningCount=0 && deployments=[]`)无 jq 模板
5. VPC NAT Gateway 走 ECR pulls 缺失 Gateway Endpoint 指引,典型高吞吐 service 月费数百美元
6. Savings Plans 覆盖 Fargate 指引缺失 → ~25% 折扣机会未识别

### 1.4 撮合杠杆(cross-cutting)

| 杠杆 | FinOps 价值 | AIOps 价值 |
|---|---|---|
| Capacity Provider(FARGATE ⇄ FARGATE_SPOT) | -70% 算力费 | `SpotInterruption` 是中断预测天然信号源 |
| Service Auto Scaling + Container Insights alarms | 非高峰 -30~60% 账单 | canonical auto-heal recipe(target tracking on `ECSServiceAverageCPUUtilization`) |
| `--tags` on create | Chargeback 入场券 | 资源治理 metadata |
| Compute Optimizer ECS recommendations | right-sizing 直接建议 | 容量推断 / "next month bill" 数据源 |

## 2. 目标与范围

**目标**: 在不打破 `aws-ecs-ops` 现有 CRUD 语义 + Safety gate 的前提下,补齐 AIOps 检测层 + Cost Optimization 操作 + 跨 skill FinOps delegate 链。

### 2.1 Scope Boundary(外科手术式)

**改**:
- [aws-ecs-ops/SKILL.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/SKILL.md) — frontmatter 加 `provides`;新增 Container Insights metric 块;新增 Operation: Update Capacity Providers / Update Service Tags;Create Service / Register Task Definition 加 `--tags` 模板;Safety gate 段补 `deregister-task-definition` confirmation(A8 引用已有 DELETE_SERVICE / DELETE_CLUSTER)
- [aws-ecs-ops/references/aws-cli-usage.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/references/aws-cli-usage.md) — 加 `put-cluster-capacity-providers` / `tag-resource` / `update-service`(--force-new-deployment)
- [aws-ecs-ops/references/troubleshooting.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/references/troubleshooting.md) — 扩 stoppedReason 表 ≥ 8 条 + deployment 失败模式新增
- **新建** [aws-ecs-ops/references/cost-optimization.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/references/cost-optimization.md) — Fargate Spot / Compute Optimizer / Savings Plans / idle queries / Gateway Endpoint / tag governance 6 块
- **新建** [aws-ecs-ops/references/deployment-health.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/references/deployment-health.md) — circuit breaker / `rolloutState` / deployment alarms
- [aws-finops-core/SKILL.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-finops-core/SKILL.md) — `metadata.provides` + `metadata.delegate` 各加 3 条 ECS 项

**不改**:
- `aws-aiops-cruise` / `aws-aiops-orchestrator` / `aws-aiops-copilot`(本次仅 ECS 端;跨 skill 行为不变)
- 现有 GCL rubric 的 5 维度(本次不新增 ECS 专属维度 — defer)
- 现有任何 `aws-*` 安全语义 / Safety Gate 提示语

**不引入**:
- 新建 `aws-application-autoscaling-ops` skill(ADR defer §3 D3)
- ECS-SPOT-01 inference rule(AIOps cruise 演进超出本次 MVP)

## 3. 关键决策(Decisions)

### D1: Spot / Capacity Provider 通过独立 `Operation: Update Capacity Providers` 落地
- 现有 `Operation: Create Cluster` 的 FARGATE-only sample 不动(`LITERAL` 兼容)
- 新 Operation 用 `{{user.opt_in_spot}}` 用户显式确认后才切 Spot
- Resource ARN echo 通过 A8 校验(对 cluster 做 `describe-clusters` 回读)

### D2: `--tags` 模板统一用 `{{user.*}}` 占位
- 必填推荐:`Project` / `Environment` / `ManagedBy` / `CostCenter`
- 默认 `ManagedBy=aiops` 与现有 cluster create 一致

### D3: Application Auto Scaling 决策延后 + ADR defer
- `grep` 验证:仓库内**确实无任何 `aws-application-autoscaling-*` skill**
- 新建路径成本 > 本次 MVP 收益
- 本次仅在 `references/cost-optimization.md` 留 cross-reference "see aws-application-autoscaling-ops (TODO: not yet in repo)"
- 留 ADR 在 plan 文末,后续独立 plan 决策(新建 vs 合并到 aws-autoscaling-ops)

### D4: deployment-health.md 不与 aws-aiops-cruise 重复
- Circuit breaker / `rolloutState` 仅在 `references/deployment-health.md` 表达完整语义
- SKILL.md 只放原则 + link(防 TE-6 violation)

### D5: cost-optimization.md 是 references 而非 SKILL.md 子段
- 保 TE-1:Compute Optimizer / Cost Explorer API 命令 > 硬编码价目表
- 保 TE-6:flows only in SKILL.md;references 是参考资料

## 4. metadata + delegate 改动矩阵

### A. aws-ecs-ops frontmatter 新增字段

```yaml
metadata:
  provides:
    - ecs-cluster-lifecycle
    - ecs-service-lifecycle
    - ecs-task-definition-lifecycle
    - ecs-task-lifecycle
    - ecs-idle-service-discovery   # NEW (FinOps)
    - ecs-fargate-rightsizing      # NEW (FinOps)
    - ecs-fargate-spot-optimization # NEW (FinOps/AIOps 撮合)
```

### B. aws-finops-core frontmatter 改动

`metadata.provides` 加:
```yaml
    - ecs-idle-service-discovery
    - ecs-fargate-rightsizing
    - ecs-fargate-spot-optimization
```

`metadata.delegate` 加:
```yaml
    ecs-idle: aws-ecs-ops
    ecs-rightsizing: aws-ecs-ops
    ecs-fargate-spot: aws-ecs-ops
```

## 5. 端到端数据流(改动后)

```
              ┌───────────────────────────────────────┐
User intent   │         aws-finops-core                │
─────────────▶│  provides.ecs-idle                    │
              │    └─ delegate.ecs-idle → aws-ecs-ops  │
              │            ├─ list idle svc (jq)      │
              │            ├─ ecs-fargate-rightsizing  │
              │            └─ ecs-fargate-spot         │
              └───────────────────────────────────────┘
                              ▲
                              │ provides surface
              ┌─────────────────────────────┐
              │  aws-aiops-cruise           │
              │  cross_skill_deps[ecs-ops]  │
              └─────────────────────────────┘
```

Fargate Spot 撮合:
```
capacity_provider = {FARGATE (weight 20), FARGATE_SPOT (weight 80)}
       ↓
Spot 中断 → task.stoppedReason = "SpotInterruption"
       ↓
(本次不在 MVP 范围)cruise inference ECS-SPOT-01
       ↓
delegate aws-ecs-ops → "switch capacity provider" 或 "提高 FARGATE weight"
```

注: ECS-SPOT-01 inference rule 注册属 `aws-aiops-cruise` 演进,本次仅 ECS 端 SDK/CLI 表达就绪。

## 6. 验收标准

| # | 项 | 标准 |
|---|---|---|
| V1 | `aws-ecs-ops/SKILL.md` frontmatter `provides` ≥ 6 项 | `grep -c "^    - ecs-" frontmatter` ≥ 6 |
| V2 | `aws-ecs-ops/SKILL.md` 新增 Operation: Update Capacity Providers 含完整 4 段 | Pre-flight / Execute CLI+SDK / Validate / Recover 齐 |
| V3 | `aws-ecs-ops/SKILL.md` 顶部"Common Container Insights metric path"JSON paths | `grep -E "CPUReservation\|MemoryReservation"` |
| V4 | `aws-ecs-ops/SKILL.md` Create Service 命令含 `--tags` 模板 | grep 找到 `{{user.*}}` + `Key=Project` |
| V5 | `aws-ecs-ops/references/cost-optimization.md` 覆盖 6 H2 块(Fargate Spot / Compute Optimizer / Savings Plans / Idle queries / Gateway Endpoint / Tag governance) | 6 个 H2 |
| V6 | `aws-ecs-ops/references/deployment-health.md` 覆盖 3 H2 块(circuit breaker / rolloutState / deployment alarms) | 3 个 H2 |
| V7 | `aws-ecs-ops/references/troubleshooting.md` task stoppedReason 表 ≥ 8 条 | line count ≥ 8 in table |
| V8 | `aws-finops-core/SKILL.md` delegate 增 3 条 ECS | grep 3 次 `ecs-` |
| V9 | `aws-finops-core/SKILL.md` provides 增 3 条 ECS | grep 3 次 |
| V10 | All frontmatter `---` 数 = 2 | awk 验证 |
| V11 | TE-1..TE-6 仍 pass | self-review R1 |
| V12 | Charter C1-C6 仍 pass | self-review R1 |
| V13 | Token Efficiency Monitor OPTIMAL / ACCEPT-SUBOPTIMAL | 调起 Monitor 子代理 |

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Capacity Provider 操作破坏现有 Fargate-only 用户语义 | **不改**默认 Operation;新增独立 Operation,显式 `{{user.opt_in_spot}}` 确认 |
| Tag 模板与现有 user inputs 不一致 | `--tags Key=...,Value=...` 用 `{{user.tag_key}}`/`{{user.tag_value}}` 占位,让 user 决定值 |
| Compute Optimizer 调用产生 API cost | 仅 read-only `get-ecs-service-recommendations`,在 reference 标注 "1/day max" |
| `aws-ecs-ops/SKILL.md` 加内容触发 TE 软 cap(70-120 lines) | 操作细节放 references/,SKILL.md 仅 summary + Operation 高层 block |
| FinOps delegate 加 3 条后,aws-ecs-ops 变长 | SKILL.md 仍 ≤ 130 lines(新 file 由 references 承担) |
| 新增 `aws-application-autoscaling-ops` 缺位影响 AIOps auto-heal | ADR defer §3 D3;本次 MVP 不阻塞,以 cost-optimization.md 注释占位 |
| README.md / README_cn.md 是否需更新 | 本次不修改版本号,不在 README skills 列变动;`references/cost-optimization.md` precedent 已存在(EKS),无需 README 同步 |
