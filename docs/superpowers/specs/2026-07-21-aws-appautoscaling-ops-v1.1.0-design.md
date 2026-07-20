# aws-application-autoscaling-ops 增量扩展 (v1.1.0) — 设计文档

- **日期**: 2026-07-21
- **状态**: 已定稿(用户确认 "all of them" — 全套 ADR defer 落地)
- **对应计划**: `docs/superpowers/plans/2026-07-21-aws-appautoscaling-ops-v1.1.0.md`
- **起源**: [`2026-07-21-aws-appautoscaling-ops-design.md`](2026-07-21-aws-appautoscaling-ops-design.md) §8 ADR defer

## 1. 背景与问题

[aws-application-autoscaling-ops v1.0.0](file:///Users/bohaiqing/opensource/git/aws-skills/aws-application-autoscaling-ops/SKILL.md) commit `00258ff` MVP 范围 = ECS-only。spec §8 + plan `2026-07-21-aws-ecs-ops-aiops-finops.md` §ADR defer 都明确把 Lambda / DynamoDB / Spot Fleet 推到下次 plan。

这次直接做:
1. **3 个 reference 增量扩展**(`lambda.md` / `dynamodb.md` / `spot-fleet.md`),覆盖剩余主流 ServiceNamespace
2. **4 条 cruise inference rules**(`CO-AUTOSCALING-01/02` / `PD-AUTOSCALING-01` / `FD-AUTOSCALING-01`)填补 Application Auto Scaling 的 AIOps 检测层
3. **1 个 AIOps runbook**(`RB-AUTOSCALING-01` — ECS Service right-sizing + Spot 重平衡 决策路径)
4. **version bump** `1.0.0 → 1.1.0`(per project_information_memory "升级时同步更新 SKILL.md + CHANGELOG.md + README")

### 1.1 Disk-verified 现状

| 文件 | 当前 | 本次改动 |
|---|---|---|
| `aws-application-autoscaling-ops/SKILL.md` | `version: "1.0.0"` | bump `1.1.0`,reference files list +3 |
| `aws-application-autoscaling-ops/references/core-concepts.md` | 仅 1-row ECS table | append lambda/dynamodb/spot-fleet 短表 |
| `aws-application-autoscaling-ops/references/` | 无 lambda.md / dynamodb.md / spot-fleet.md | **新建 3 个** |
| `aws-application-autoscaling-ops/CHANGELOG.md` | **不存在** | **新建** (Keep-a-Changelog v1.1.0 entry) |
| `aws-aiops-cruise/references/inference-rules.md` | line 84-89 `ECS-TASK-01`,line 148-150 ECS 块 | append `CO-AUTOSCALING-01/02` + `PD-AUTOSCALING-01` + `FD-AUTOSCALING-01` |
| `aws-aiops-orchestrator/references/runbook-recipes.md` | 27 runbooks (RB-001 — RB-027),无 Application Auto Scaling 专属 RB | append `RB-AUTOSCALING-01` + update §27 Runbook Library Summary 表 |
| `README.md` + `README_cn.md` | 已有 `aws-application-autoscaling-ops v1.0.0` | bump v1.1.0 |
| `aws-finops-core/SKILL.md` | `app-autoscaling-ecs-targets`/`policies` | 不动(MVP 已够) |
| `aws-ecs-ops` 系列 | v1.2.0 已 bump | 不动 |

## 2. 目标与范围

**目标**: 在已 ship 的 `aws-application-autoscaling-ops` 上,补齐 lambda / dynamodb / spot-fleet 三大主流 ServiceNamespace 子文档 + 4 条 AIOps inference rule + 1 个 RB-AUTOSCALING-01 runbook,把 Application Auto Scaling 在仓库内完整化(AIOps 检测层 + 自动化执行 + FinOps delegate 链三件套齐备)。

### 2.1 Scope Boundary(外科手术式)

**新建**:
- `aws-application-autoscaling-ops/references/lambda.md`(~ 60 lines)
- `aws-application-autoscaling-ops/references/dynamodb.md`(~ 70 lines)
- `aws-application-autoscaling-ops/references/spot-fleet.md`(~ 50 lines)
- `aws-application-autoscaling-ops/CHANGELOG.md`(~ 30 lines,Keep-a-Changelog 格式)

**改**:
- `aws-application-autoscaling-ops/SKILL.md`: frontmatter `version: "1.0.0" → "1.1.0"` + `last_updated: "2026-07-21"`(already today)+ References 段新增 3 行
- `aws-application-autoscaling-ops/references/core-concepts.md`: ServiceNamespace × ScalableDimension 表 append 5 短行(Lambda × 1,DynamoDB × 4,Spot Fleet × 1)+ 移除 2 处 stub `<!-- TODO -->` 注释
- `aws-aiops-cruise/references/inference-rules.md`: append 一段 `## Application Auto Scaling` 含 4 条 rule
- `aws-aiops-orchestrator/references/runbook-recipes.md`: append `RB-AUTOSCALING-01` 完整 yaml + update Library Summary 表 +1 行
- `README.md` + `README_cn.md`: aws-application-autoscaling-ops row v1.0.0 → v1.1.0

**不改**:
- `aws-finops-core/SKILL.md`(已有 4 处 ECS + app-autoscaling 引用,无需改)
- `aws-ecs-ops/*`(v1.2.0 已锁,本次增量不触发 ECS 升级)
- 其他 30+ L1 skill

**不引入**:
- EMR / SageMaker / Comprehend 等边缘 namespace(下次 plan 议题)
- New GCL rubric 升级(Application Auto Scaling skill 自身 rubric v1 已够,新文档仅扩展 reference file)
- Inference rule 的 Python 实现(spec 仅追加 markdown,Python 实施是 follow-up)

## 3. 关键决策

### D1: ServiceNamespace 拓展优先级(Lambda > DynamoDB > Spot Fleet)
- 按仓库 advisory **Lambda Provisioned Concurrency 是最常被 use case**(`serverless-lambda` 用例)
- DynamoDB priority 次之(DynamoDB L1 已有 inline `register-scalable-target` 在 `aws-dynamodb-ops/SKILL.md` line 716,补全 cross-skill invoke 路径)
- Spot Fleet 第三(EC2 路线用户少,且有 EC2 ASG fallback path)

### D2: 4 条 Inference Rule 优先级
| Rule ID | Domain | Severity | Trigger metric |
|---|---|---|---|
| `PD-AUTOSCALING-01` | PD | WARNING (≥ 90% over 10m) → CRITICAL | ECS Service `runningCount == MaxCapacity` (无 headroom) |
| `CO-AUTOSCALING-01` | CO | WARNING | ECS Service `MinCapacity == MaxCapacity` (0 headroom for save cost) |
| `CO-AUTOSCALING-02` | CO | INFO | ECS Service target tracking `ScaleInCooldown > 600s` (cost risk — 缩容不足) |
| `FD-AUTOSCALING-01` | FD | WARNING | ECS Service `runningCount < desiredCount` + active scaling policy 不工作 (policy bypass) |

> 不实现 `RB-AUTOSCALING-02`/`RB-AUTOSCALING-03` 等;MVP 只 1 个 RB,覆盖最常触发的 `PD-AUTOSCALING-01` 与 `CO-AUTOSCALING-01`(scale-adjust 决策路径)。

### D3: Runbook `RB-AUTOSCALING-01` 决策层 = `AI_ASSIST`
- Application Auto Scaling 变更决策可能影响 capacity 数十倍,**不允许 AUTO_HEAL**(违反 AGENTS.md "Cost change > $100/month [AI_ASSIST]" 边界)
- `requires_confirm: true` 在所有 modify 操作上
- 用 delegate `aws-application-autoscaling-ops` 而非其它 skill(spec §6 编排图)

### D4: bump 策略 — 一次性 v1.0.0 → v1.1.0
- 4 个 reference 文件扩展 + 4 inference rules + 1 runbook = 跨 scope 升级,**值得 minor bump**
- per project_information_memory:同步 SKILL.md frontmatter + CHANGELOG.md + README 双语
- `aws-application-autoscaling-ops/CHANGELOG.md` 第一次新建(1.1.0 entry + 1.0.0 stub)

### D5: cross-file 现状保留
- 现有 `core-concepts.md` 注释 `<!-- TODO: follow-up plan reference/lambda.md -->` 直接被本计划 reference file 新建消解(stub 注释删除)
- 不改动 `aws-aiops-cruise/scripts/_inference.py`(本次仅追加 markdown 规则,Python 实现 deferred)
- `aws-aiops-orchestrator/references/runbook-recipes.md` Library Summary 表更新 1 行(现有 27 runbooks + RB-AUTOSCALING-01 = 28)

## 4. metadata + 改动矩阵

### A. `aws-application-autoscaling-ops/SKILL.md` frontmatter

```yaml
  version: "1.1.0"   # bumped
  provides:
    - app-autoscaling-register-target
    - app-autoscaling-deregister-target
    - app-autoscaling-put-policy
    - app-autoscaling-delete-policy
    - app-autoscaling-tag-resource
    - app-autoscaling-describe
  # NEW reference files listed in body section "Reference Files"
```

### B. `aws-application-autoscaling-ops/CHANGELOG.md` 新建

```markdown
# Changelog — aws-application-autoscaling-ops

## [1.1.0] - 2026-07-21

### Added (AIOps)
- 4 inference rules in [aws-aiops-cruise/references/inference-rules.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-aiops-cruise/references/inference-rules.md) §Application Auto Scaling:
  - `PD-AUTOSCALING-01`: ECS runningCount == MaxCapacity 无 headroom
  - `CO-AUTOSCALING-01`: MinCapacity == MaxCapacity 0 headroom
  - `CO-AUTOSCALING-02`: TargetTracking ScaleInCooldown > 600s 缩容不足
  - `FD-AUTOSCALING-01`: ECS service 任务 deficit + active policy 不工作
- New runbook `RB-AUTOSCALING-01` in [aws-aiops-orchestrator/references/runbook-recipes.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-aiops-orchestrator/references/runbook-recipes.md) §27 — capacity right-size 决策路径 (AI_ASSIST)

### Added (Lambda/DynamoDB/Spot Fleet)
- references/lambda.md — Lambda Provisioned Concurrency (`lambda:function:ProvisionedConcurrency`)
- references/dynamodb.md — DynamoDB Table / GSI (4 ScalableDimension)
- references/spot-fleet.md — Spot Fleet (`ec2:spot-fleet-request:TargetCapacity`)
- core-concepts.md — ServiceNamespace × ScalableDimension 表 append 6 短行 (Lambda × 1, DynamoDB × 4, Spot Fleet × 1); 移除 stub `<!-- TODO -->` 注释

## [1.0.0] - 2026-07-21

Initial L1 skill, ECS-only MVP.
```

### C. `aws-aiops-cruise/references/inference-rules.md` 追加段(在 §Compute paths 后,§Data layer 前)

```markdown
## Application Auto Scaling

### PD-AUTOSCALING-01: ECS Service at max capacity (no scaling headroom)

| Symptoms | `runningCount == MaxCapacity` 持续 ≥ 10m,target tracking active |
| Inference | Target tracking 已 saturate 上限,业务增长前需主动 raise MaxCapacity |
| Metrics | Namespace `AWS/ECS` — dimension `ClusterName` + `ServiceName`; metric `RunningTaskCount` |
| Fix path | delegate `aws-application-autoscaling-ops` — `register-scalable-target --max-capacity <new>`. Runbook `RB-AUTOSCALING-01` |

### CO-AUTOSCALING-01: ECS Service scaled to ceiling (0 headroom)

| Symptoms | `MinCapacity == MaxCapacity`,target tracking active |
| Inference | 无安全 headroom,无法 scale-down 节省费用 |
| Metrics | Compare `MinCapacity` vs `MaxCapacity` on `describe-scalable-targets` |
| Fix path | delegate `aws-application-autoscaling-ops` — `register-scalable-target --min-capacity <lower>` (keep ≥ desiredCount). Runbook `RB-AUTOSCALING-01` |

### CO-AUTOSCALING-02: TargetTracking ScaleInCooldown > 600s (cost risk)

| Symptoms | `describe-scaling-policies` shows `ScaleInCooldown > 600` for ECS target tracking |
| Inference | 缩容反应慢,非高峰期持续 billing → cost risk |
| Metrics | Application Auto Scaling API (not CloudWatch) |
| Fix path | delegate `aws-application-autoscaling-ops` — `put-scaling-policy` with `ScaleInCooldown=300`. Inform `aws-finops-core` |

### FD-AUTOSCALING-01: ECS service deficit + active scaling policy not firing

| Symptoms | `runningCount < desiredCount` 持续 + active target tracking 不扩容 |
| Inference | Target tracking not responding to metric spike (wrong metric namespace, alarm misconfig) |
| Metrics | `RunningTaskCount`/`DesiredTaskCount` (AWS/ECS) + `ECSServiceAverageCPUUtilization` (Container Insights) |
| Fix path | Verify `PredefinedMetricSpecification` in `describe-scaling-policies`; verify CloudWatch metric has data; delegate `aws-application-autoscaling-ops` to recreate policy
```

### D. `aws-aiops-orchestrator/references/runbook-recipes.md` 追加 §28

```yaml
runbook:
  id: RB-AUTOSCALING-01
  name: "Application Auto Scaling Right-Sizing (ECS target)"
  trigger_rules: [PD-AUTOSCALING-01, CO-AUTOSCALING-01]
  default_decision_tier: AI_ASSIST
  preconditions:
    - Action targets ECS Service only (other ServiceNamespace deferred)
    - Cost change estimated ≤ $1000/month OR operator confirms higher

  steps:
    - id: S1
      skill: aws-application-autoscaling-ops
      action: describe_scalable_targets
      params: { service_namespace: "ecs", resource_id: "{{u.resource_id}}" }

    - id: S2
      skill: aws-application-autoscaling-ops
      action: describe_scaling_policies
      params: { service_namespace: "ecs", resource_id: "{{u.resource_id}}" }

    - id: S3
      skill: aws-ecs-ops
      action: describe_service
      params: { cluster: "{{u.cluster}}", service: "{{u.service}}" }
      # Get desiredCount, runningCount, deployment status

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_capacity_action
      # branches:
      #   raise_max: MaxCapacity bump (PD-AUTOSCALING-01)
      #   lower_min: MinCapacity trim (CO-AUTOSCALING-01)
      #   tune_cooldown: patch scale-in cooldown (CO-AUTOSCALING-02)
      #   no_change: false alarm — log + SUPPRESS

    - id: S5 [raise_max branch]
      skill: aws-application-autoscaling-ops
      action: register_scalable_target_raise_max
      params:
        service_namespace: "ecs"
        resource_id: "{{u.resource_id}}"
        scalable_dimension: "ecs:service:DesiredCount"
        min_capacity: "{{S1.ScalableTargets[0].MinCapacity}}"
        max_capacity: "{{S4.new_max}}"
      requires_confirm: true   # capacity change > $100/mo by AGENTS.md boundary

    - id: S6 [lower_min branch]
      skill: aws-application-autoscaling-ops
      action: register_scalable_target_lower_min
      params:
        min_capacity: "{{S4.new_min}}"
        max_capacity: "{{S1.ScalableTargets[0].MaxCapacity}}"
      requires_confirm: true

    - id: S7 [tune_cooldown branch]
      skill: aws-application-autoscaling-ops
      action: put_scaling_policy
      params:
        policy_name: "{{S2.ScalingPolicies[0].PolicyName}}"
        policy_type: "{{S2.ScalingPolicies[0].PolicyType}}"
        target_tracking_scaling_policy_configuration:
          scale_out_cooldown: "{{S4.scale_out}}"
          scale_in_cooldown: "{{S4.scale_in}}"
      requires_confirm: true

    - id: S8 [always]
      skill: aws-cloudwatch-ops
      action: put_metric_alarm_audit
      params:
        alarm_name: "AppAutoScalingAudit-{{u.resource_id}}"
        metric_name: "RunningTaskCount"
        threshold: "{{S1.ScalableTargets[0].MaxCapacity - 1}}"
        comparison_operator: "GreaterThanThreshold"
      requires_confirm: false

  post_checks:
    - verify: describe_scalable_targets returns updated Min/Max
    - verify: scaling policy active (Alarms[] populated within PT5M)
    - verify: runningCount recovers to desiredCount or headroom restored

  estimated_mttr: PT15M
  rollback_strategy: "register-scalable-target with previous Min/Max — fully reversible."
  owner: platform
  tested_in: [staging]
```

### E. Library Summary 表追加一行(§27)

```markdown
| RB-AUTOSCALING-01 | App Auto Scaling Right-Size | PD-AUTOSCALING-01, CO-AUTOSCALING-01 | AI_ASSIST | PT15M | application-autoscaling, ecs, cloudwatch |
```

### F. README 双语 aws-application-autoscaling-ops 行

```markdown
| aws-application-autoscaling-ops | Application Auto Scaling (cross-service scaler) | ✅ **Complete v1.1.0** — ECS + Lambda Provisioned Concurrency + DynamoDB Table/GSI + Spot Fleet (target tracking / step scaling / scheduled actions on `ECSServiceAverageCPUUtilization`); 4 cruise inference rules + RB-AUTOSCALING-01 |
```

## 5. 端到端数据流(改动后)

```
              ┌───────────────────────────────────────┐
User intent   │         aws-finops-core                │
─────────────▶│ provides: app-autoscaling-ecs-targets │
              │ delegate: app-autoscaling-* → aws-...  │
              └───────────────────────────────────────┘
                              │ invoke
                              ▼
       ┌──────────────────────────────────────┐
       │ aws-application-autoscaling-ops v1.1  │
       │   references/aws-cli-usage.md (ECS+Lambda+DDB+Spot)│
       │   references/lambda.md                  │
       │   references/dynamodb.md                │
       │   references/spot-fleet.md              │
       │   rubric.md / prompt-templates.md (GCL) │
       └──────────────────────────────────────┘
                  │ detect signals (CloudWatch)
                  ▼
       ┌──────────────────────────────────────┐
       │ aws-aiops-cruise                       │
       │   4 new inference rules:               │
       │     PD-AUTOSCALING-01                  │
       │     CO-AUTOSCALING-01 / 02             │
       │     FD-AUTOSCALING-01                  │
       └──────────────────────────────────────┘
                  │ trigger if rule fires
                  ▼
       ┌──────────────────────────────────────┐
       │ aws-aiops-orchestrator                │
       │   matches → RB-AUTOSCALING-01        │
       │   (AI_ASSIST — operator confirm)      │
       └──────────────────────────────────────┘
```

## 6. 验收标准 V1-V13

| # | 项 | 标准 |
|---|---|---|
| V1 | 3 个 reference file 新建存在 + 内容完整 | `ls aws-application-autoscaling-ops/references/{lambda,dynamodb,spot-fleet}.md` 全部存在 |
| V2 | core-concepts.md 移除 2 处 stub `<!-- TODO -->` | grep `<!-- TODO: follow-up plan reference/lambda.md -->` 等 0 命中 |
| V3 | core-concepts.md 扩 ServiceNamespace 表 ≥ 5 行 | awk count Lambda/DynamoDB/Spot 行 ≥ 5 |
| V4 | aws-aiops-cruise/references/inference-rules.md append `## Application Auto Scaling` 段 | grep 命中 |
| V5 | 4 条 rule ID 全部命名 | grep `PD-AUTOSCALING-01\\|CO-AUTOSCALING-01\\|CO-AUTOSCALING-02\\|FD-AUTOSCALING-01` ≥ 4 |
| V6 | aws-aiops-orchestrator/references/runbook-recipes.md 新增 `RB-AUTOSCALING-01` yaml | grep 命中 + yaml 格式 valid |
| V7 | Library Summary 表 +1 行 | grep `RB-AUTOSCALING-01` in summary section |
| V8 | aws-application-autoscaling-ops/SKILL.md frontmatter `version: "1.1.0"` | grep |
| V9 | CHANGELOG.md 存在 + v1.1.0 entry 包含 Added (AIOps + Lambda/DynamoDB/Spot Fleet) | grep `## \\[1.1.0\\]` + 子段 |
| V10 | README + README_cn aws-application-autoscaling-ops 行 v1.1.0 | grep |
| V11 | Frontmatter `---` = 2 per skill file (aws-application-autoscaling-ops/SKILL.md 不动) | awk |
| V12 | Anti-pattern `aws --output json <svc>` 0 命中 (新文件) | grep -rE `^aws --output json ` |
| V13 | TE-5 / TE-6:references 之间不重复 command block | grep `register-scalable-target` 跨 reference 文件 ≥ 1 (canonical CLI) |

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| `aws-aiops-cruise/scripts/_inference.py` 与新增 markdown rule 不同步 | 本次仅追加 spec(spec 标记 "Python 实施 deferred");语义层 rule 已落地,可独立被 `_inference.py` reader 解析 |
| ServiceNamespace × ScalableDimension 错位 | 严格使用 AWS 官方 namespace:string(`ecs`/`lambda`/`dynamodb`/`ec2`),SC 大小写固定 |
| Runbook `requires_confirm: true` 在 modify 上 mandatory | spec §阶段 4 D3 + runbook D5 强化 — 所有变更路径 confirm |
| Cross-skill delegate 路径破坏 | 不动 aws-finops-core delegate;新增 runbook 显式 `skill: aws-application-autoscaling-ops` label |
| Frontmatter 合规 | spec §阶段 4 A 显式 version bump,与 CHANGELOG 同步 |
| V12 anti-pattern 漏 | 新建命令全部 `--output json` 在末尾;与 v1.0.0 同模式 |

## 8. ADR defer(下次 plan 议题)

- Python 实施 `aws-aiops-cruise/scripts/_inference.py` 新增 4 条 rule handler
- `aws-application-autoscaling-ops` 跨 namespace 的 multi-resource runbook (`RB-AUTOSCALING-02`)
- EMR / SageMaker / Comprehend / Keyspace namespace 文档
- Application Auto Scaling Spot Fleet interruption handling (advanced;非 target tracking)
- Scheduled actions per ServiceNamespace 完整覆盖(Lambda cron schedule 等)
