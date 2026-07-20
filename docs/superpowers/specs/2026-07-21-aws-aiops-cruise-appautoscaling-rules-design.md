# aws-aiops-cruise v1.x AIOps 后端完整化 — 设计文档

- **日期**: 2026-07-21
- **状态**: 已定稿(用户确认 "3 分,逐个 plan 跑" + Cluster 1 = AIOps 后端)
- **对应计划**: `docs/superpowers/plans/2026-07-21-aws-aiops-cruise-appautoscaling-rules.md`
- **起源**: 
  - [v1.1.0 plan §8 ADR defer](file:///Users/bohaiqing/opensource/git/aws-skills/docs/superpowers/plans/2026-07-21-aws-appautoscaling-ops-v1.1.0.md) "Per-namespace inference rules"
  - [v1.2.0 plan §8 ADR defer](file:///Users/bohaiqing/opensource/git/aws-skills/docs/superpowers/plans/2026-07-21-aws-appautoscaling-ops-v1.2.0.md) "Per-namespace inference rules" + "Python handler 实施"

## 1. 背景与问题

[aws-application-autoscaling-ops v1.2.0](file:///Users/bohaiqing/opensource/git/aws-skills/aws-application-autoscaling-ops/SKILL.md) 已 ship 8 ServiceNamespace × 12 ScalableDimension 的文档层覆盖(v1.0.0 ECS → v1.1.0 +Lambda/DDB/Spot → v1.2.0 +EMR/SageMaker/Comprehend/Keyspace)。

但 AIOps Detection 层仍只有 4 条 ECS-focused rule(v1.1.0 ship):
- `PD-AUTOSCALING-01`: ECS runningCount == MaxCapacity
- `CO-AUTOSCALING-01`: ECS MinCapacity == MaxCapacity
- `CO-AUTOSCALING-02`: ECS ScaleInCooldown > 600s
- `FD-AUTOSCALING-01`: ECS deficit + active policy not firing

7 个非-ECS ServiceNamespace(Lambda / DynamoDB / Spot Fleet / EMR / SageMaker / Comprehend / Keyspace)的 Application Auto Scaling 在仓库内**没有任何 inference rule**,导致:
1. detective signal 缺失 —— 即使 Application Auto Scaling config 错配或容量超阈值,cruise patrol 不会告警
2. runbook routing 失效 —— `aws-aiops-cruise/references/inference-rules.md` 的 chain inference 不会触发,RB-AUTOSCALING-01 不会被 orchestrate

ADR defer 明确 "各 ServiceNamespace 专属 CloudWatch metric namespace 不同,SSR 后续 plan 拆分" + "Python handler 实施"。

## 2. 目标与范围

**目标**:为 8 个 ServiceNamespace 各配 3-4 条 AIOps inference rule(共 ~28-32 rule),覆盖 Fault Detection(FD)/ Predictive(PD)/ Cost Optimization(CO)三个 domain;同时实施 Python handler 让 `aws-aiops-cruise/runbooks/scripts/_inference.py` runtime 能触发这些 rule。

### 2.1 Scope Boundary

**改**:
- `aws-aiops-cruise/references/inference-rules.md`:append `## Application Auto Scaling — 8 Namespaces` H2 段,内含 8 个 H3 sub-section × 3-4 rule
- `aws-aiops-cruise/runbooks/scripts/_inference.py`:新增 ~8 `detect_app_autoscaling_*` 函数,注册到 `apply_chain_inference` 主函数
- `aws-aiops-cruise/scripts/_sync_prompt_skeletons.py`(若有,verify 中):Hard rules 增 ~8-10 条

**不改**:
- `aws-application-autoscaling-ops/*`(已 ship v1.2.0,不动)
- `aws-aiops-orchestrator/references/runbook-recipes.md`(RB-AUTOSCALING-01 决策 mode 通用,不增新 runbook)
- 其他 30+ L1 skill

**bump 策略**:
- `aws-aiops-cruise`:保持当前 version 不动(cruise skill v1.x stable,本次仅 inference rules + handler 增量)— 不写 CHANGELOG(下次 CR 周期 bump 时一并)
- `aws-application-autoscaling-ops`:不动 v1.2.0
- `aws-aiops-orchestrator`:不动

### 2.2 ServiceNamespace → CloudWatch metric 映射(per AWS docs)

| Namespace | Primary CloudWatch metric namespace | 主要 metric(s) | PredefinedMetricType (for Target tracking via app-autoscaling) |
|---|---|---|---|
| `ecs` | `AWS/ECS` | `RunningTaskCount` / `DesiredTaskCount` | `ECSServiceAverageCPUUtilization` / `ECSServiceAverageMemoryUtilization` |
| `lambda` | `AWS/Lambda` | `ProvisionedConcurrencyUtilization` / `ConcurrentExecutions` | `LambdaProvisionedConcurrencyUtilization` |
| `dynamodb` | `AWS/DynamoDB` | `ProvisionedReadCapacityUtilization` / `ProvisionedWriteCapacityUtilization` | `DynamoDBReadCapacityUtilization` / `DynamoDBWriteCapacityUtilization` |
| `ec2:spot-fleet-request` | `AWS/EC2SpotFleetRequest` | `TargetCapacity` / `ActualCapacity` / `CPUUtilization` (custom) | (custom Spec) |
| `elasticmapreduce` | `AWS/ElasticMapReduce` | `IsIdle` / `JobFlowCPUUtilization` / `AppsCompleted` / `AppsPending` | `EMRClusterCoreCPUUtilization` |
| `sagemaker` | `AWS/SageMaker` | `Invocations` / `InvocationsPerInstance` / `GPUUtilization` / `CPUUtilization` | `SageMakerVariantInvocationsPerInstance` |
| `comprehend` | `AWS/Comprehend` | `InferenceRequestCount` (custom) | (custom Spec) |
| `cassandra` | `AWS/Cassandra` | `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits` (custom) | (custom Spec) |

(实际 AWS 官方 metric namespace 与 statistic 以 docs 为准;本次 design 列结构,具体值在 plan §阶段 1 step)

### 2.3 Rule 设计原则

- 4 个 rule domain:`FD-*` (Fault) / `PD-*` (Predictive) / `CO-*` (Cost) / `SD-*` (Security,本次**不**增 Security Detection rule 因 Application Auto Scaling 不是 security 边界)
- 每个 namespace 优先 3 条 rule:**1 FD + 1 PD + 1 CO**(minimum viable coverage)
- 命名:`<DOMAIN>-AUTO-<NS>-<NUMBER>`,如 `FD-AUTO-LAMBDA-01`
- 每个 rule 主体 4-6 行 (Symptoms / Inference / Metrics / Fix path) — 严格对照 v1.1.0 的 4 条 ECS rule 格式
- Severity:WARNING / CRITICAL(per AGENTS.md §11.5 边界)
- Fix path 必须明确 delegate 到 `aws-application-autoscaling-ops` 的具体 operation(`register-scalable-target` / `put-scaling-policy` / `deregister-scalable-target` 等)

### 2.4 Python handler 实施

- 既有 `aws-aiops-cruise/runbooks/scripts/_inference.py` 已有 `apply_chain_inference(signals, *, run_id, customer, region, existing_rule_ids)` 主函数 + 多 `detect_*` 单 namespace 函数
- 实施模式:
  ```python
  def detect_app_autoscaling_lambda(signals, *, region):
      """lambda:function namespace signals → incidents."""
      ...

  def detect_app_autoscaling_dynamodb(...):
      ...
  # 8 functions total
  ```
- 在 `apply_chain_inference` 主函数内 concatenate 8 detect 调用
- 每个 detect 调用 `make_incident(*, ..., rule_id="FD-AUTO-LAMBDA-01", ...)` 来自 `_shared.py`
- rule_id 字符串与 markdown rule 的 `### <rule_id>:` header 一致(便于 grep + audit)
- 严格 type hints + inline comments(TE-2 no docstring)

### 2.5 8 ServiceNamespace × 28 rule 计划

| Namespace | FD | PD | CO |
|---|---|---|---|
| `ecs` | (existing 4 rules) | (existing) | (existing) |
| `lambda` | 1 (throttle / errors) | 1 (concurrent limit near ceiling) | 1 (over-provisioned PC) |
| `dynamodb` | 1 (throttle count > 0) | 1 (consumed capacity > 80%) | 1 (over-provisioned RCU/WCU) |
| `ec2:spot-fleet-request` | 1 (interruption spike) | 1 (capacity < target) | 1 (target reduced vs history) |
| `elasticmapreduce` | 1 (idle cluster) | 1 (core CPU saturated) | 1 (over-scaled instance group) |
| `sagemaker` | 1 (invocation errors) | 1 (invocations > 80% target) | 1 (over-provisioned instance) |
| `comprehend` | 1 (inference throttled) | 1 (utilization > 80%) | 1 (over-provisioned inference units) |
| `cassandra` | 1 (consumption errors) | 1 (capacity > 80%) | 1 (over-provisioned RC/WC) |

总计 = 7 × 3 = **21 新 rule**(excluding existing 4 ECS rules)。

## 3. 关键决策

### D1: Rule ID 命名空间 —— family 化(单一 `AUTO-*` family)
- 选项 A:**family 化**(`FD-AUTO-LAMBDA-01`, `FD-AUTO-SAGEMAKER-01` ...)— 单一 `AUTO-*` family 便于 grep
- 选项 B:**namespace 化**(`FD-AUTOSCALING-LAMBDA-01`, `FD-AUTOSCALING-SAGEMAKER-01`)— 显式 namespace 标识
- 选 A(family 化)— 与现有 v1.1.0 的 `PD-AUTOSCALING-01` 不冲突(那个 NAMESPACE-prefix 是 `AUTOSCALING` 而新的是 `AUTO-*`)

### D2: Python handler 注册模式
- 既有 `apply_chain_inference` 内单 namespace 函数 + 内联逻辑
- 沿用同一模式:每 namespace 一个 detect function,在 `apply_chain_inference` 末尾 concatenate
- 不引入新的 abstraction / class(避免架构 breaking change)

### D3: 不 bump cruise 版本
- 本次仅 inference rules markdown + Python handler,无 frontmatter schema 改动
- version 不 bump;CHANGELOG 不写(下次 cruise skill CR / 周期 bump 时一并)
- 与 v1.1.0 plan §3 D3 一致(inference rule 增不触发 version bump)

### D4: Spec 严谨性(参考 v1.1.0 的 4 条 ECS rule 质量 bar)
- Metric Data Point 来源明确(CloudWatch metric name + namespace + statistic + period)
- Fix path 必须明确 delegate(avoid "execute directly" 反模式)
- minimum viable resource_id format 列在 fix path(便于 agent runtime parsing)

### D5: Priority order
1. Lambda(最常用)
2. DynamoDB(已被 dynamodb-ops inline 路径可借鉴)
3. Spot Fleet / EMR(EC2 边缘)
4. SageMaker / Comprehend(ML 边缘)
5. Keyspace(新引入 niche)

### D6: CHANGELOG 策略
- 不写 cruise skill CHANGELOG(本计划不 bump)
- 不写 application-autoscaling-ops CHANGELOG(它跨版本 已在 v1.2.0 收尾)
- commit message 详细列出 21 rule ID + 8 detect function names

## 4. metadata 改动矩阵

### 4.1 `aws-aiops-cruise/references/inference-rules.md`

Insert 段(在 `## Data layer` 之前,既有 `## Application Auto Scaling` H2 之后):

```markdown
## Application Auto Scaling — 8 Namespaces

> Per ServiceNamespace coverage. Initial 4 ECS-focused rules shipped in v1.1.0; remaining 7 namespaces covered in v1.3.0.
> 共 21 新 rule(FD / PD / CO 各 1 per namespace).

### Lambda

#### FD-AUTO-LAMBDA-01: Lambda Provisioned Concurrency throttled
| Symptoms | `ConcurrentExecutions == ReservedConcurrency` 持续 ≥ 5m |
| Inference | PC ceilings hit;Lambda 业务 throttle(FailuresInvocations 飙) |
| Metrics | Namespace `AWS/Lambda` — `ConcurrentExecutions` + `Failures`(per function dimension) |
| Fix path | delegate `aws-application-autoscaling-ops` — `put-scaling-policy` TargetTracking 提升 max;verify Reserved vs Provisioned 区别 |

#### PD-AUTO-LAMBDA-01: Lambda concurrent close to Provisioned ceiling
| Symptoms | `ProvisionedConcurrencyUtilization > 80%` 持续 ≥ 10m |
| Inference | PC ceiling 即将 hit;业务增长前需主动 raise MaxCapacity |
| Metrics | `AWS/Lambda` — `ProvisionedConcurrencyUtilization`(per function) |
| Fix path | delegate `aws-application-autoscaling-ops` — `register-scalable-target --max-capacity <new>` |

#### CO-AUTO-LAMBDA-01: Lambda Provisioned Concurrency over-provisioned
| Symptoms | `ProvisionedConcurrencyUtilization < 20%` 持续 ≥ 24h |
| Inference | 预热资源过冗余;非高峰期持续 billing |
| Metrics | `AWS/Lambda` — `ProvisionedConcurrencyUtilization` |
| Fix path | delegate `aws-application-autoscaling-ops` — `register-scalable-target --min-capacity <lower>` (keep ≥ recent p99 usage) |

### DynamoDB (Table + Index)

[same 3-rule pattern as Lambda]
- FD-AUTO-DYNAMODB-01: throttle > 0
- PD-AUTO-DYNAMODB-01: ConsumedReadCapacityUtilization > 80%
- CO-AUTO-DYNAMODB-01: ConsumedReadCapacityUtilization < 20% sustained 24h

### Spot Fleet (ec2:spot-fleet-request)

- FD-AUTO-SPOT-01: Spot interruption spike (5+ / hour)
- PD-AUTO-SPOT-01: ActualCapacity < TargetCapacity sustained 15m
- CO-AUTO-SPOT-01: TargetCapacity reduce vs rolling average

### EMR (elasticmapreduce)

- FD-AUTO-EMR-01: EMR cluster IsIdle 持续 ≥ 30m
- PD-AUTO-EMR-01: JobFlowCPUUtilization > 85% 持续 15m
- CO-AUTO-EMR-01: EMR instance count exceeding WMA by 30%+

### SageMaker (sagemaker:variant)

- FD-AUTO-SAGEMAKER-01: Invocation 5XX > 1% 持续 10m
- PD-AUTO-SAGEMAKER-01: InvocationsPerInstance > 80% target 持续 15m
- CO-AUTO-SAGEMAKER-01: Variant instance count exceeding p95 by 30%+

### Comprehend (comprehend:document-classifier)

- FD-AUTO-COMPREHEND-01: ThrottledInferenceException count > 0
- PD-AUTO-COMPREHEND-01: InferenceRequestCount > 80% Provisioned 持续 15m
- CO-AUTO-COMPREHEND-01: InferenceUnits usage < 20% sustained 24h

### Keyspace (cassandra:table)

- FD-AUTO-CASSANDRA-01: ProvisionedThroughputExceededException > 0
- PD-AUTO-CASSANDRA-01: ConsumedReadCapacityUnits > 80% Provisioned 持续 15m
- CO-AUTO-CASSANDRA-01: ConsumedReadCapacityUnits < 20% sustained 24h
```

### 4.2 `aws-aiops-cruise/runbooks/scripts/_inference.py`

新增 8 detect function(各 ~30-40 lines):

```python
def detect_app_autoscaling_lambda(signals, *, region, existing_rule_ids):
    """lambda:function:* signals → incidents."""
    rules_emitted: list[Incident] = []
    for resource_id, m in signals.get("Lambda", {}).items():
        cc = m.get("ConcurrentExecutions")
        util = m.get("ProvisionedConcurrencyUtilization")
        if cc is not None and util is not None:
            # rule 触发条件按 markdown spec
            if rule_id not in existing_rule_ids:
                rules_emitted.append(make_incident(...))
    return rules_emitted

# 同模式 for dynamodb / spot-fleet / emr / sagemaker / comprehend / cassandra
```

+ `apply_chain_inference` 主函数末尾调用 7 个新 detect(ECS 4 rule 已在 v1.1.0 shipping)

## 5. 端到端数据流(改动后)

```
CloudWatch metrics (per namespace)
  ↓
aws-aiops-cruise patrol (collect 6h + WoW)
  ↓
_signals.get("Lambda", {}).items() ...
_signals.get("DynamoDB", {}).items() ...
_signals.get("EC2SpotFleetRequest", {}).items() ...
_signals.get("ElasticMapReduce", {}).items() ...
_signals.get("SageMaker", {}).items() ...
_signals.get("Comprehend", {}).items() ...
_signals.get("Cassandra", {}).items() ...
  ↓
detect_app_autoscaling_<ns> (新增,8 函数 × 3 rule = 24 emit)
  ↓
make_incident(*, run_id, customer, region, ..., rule_id="FD-AUTO-LAMBDA-01", ...)
  ↓
rulematching → RB-AUTOSCALING-01 (existing, AI_ASSIST, capacity right-size)
```

## 6. 验收标准 V1-V10

| # | 项 | 标准 |
|---|---|---|
| V1 | inference-rules.md append 8 sub-section × 3 rule = 21 new rule | grep `AUTO-` rule ID 命中 ≥ 21 |
| V2 | _inference.py register 7 new detect function(2 namespace 因 ECS 已有 inline) | grep `def detect_app_autoscaling_` ≥ 7 |
| V3 | Python 语法 / lint pass | `python3 -c "import _inference"` 无 error |
| V4 | Rule ID naming `<DOMAIN>-AUTO-<NS>-<NUMBER>` 严格 | 所有 AUTO-* rule ID 前缀一致 |
| V5 | Metric namespace + PredefinedMetricType 严格 AWS 官方 | grep Audit rule metric 段 |
| V6 | Fix path delegate 到 aws-application-autoscaling-ops | grep `aws-application-autoscaling-ops` in inference-rules.md |
| V7 | Anti-pattern 0 | grep anti-pattern |
| V8 | link integrity | grep check `[..](../..)` paths valid |
| V9 | TE-1..6 pass(本次不增 error 表 in inference-rules.md) | self-review |
| V10 | 不动 application-autoscaling-ops/* + orchestrator/* + 其他 | git diff stat 0 for those |

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Rule ID 与 v1.1.0 4 rule 冲突 | 用 `AUTO-*` prefix(v1.1.0 用 `*-AUTOSCALING-01/02`),grep 验证 |
| CloudWatch metric 错误 | 严格 AWS docs(API Namespace/Metric Name/Dimension);spec §2.2 已列结构 |
| Python handler 阻塞 runnable | 主 agent 先 try `python3 -c "import _inference"` 验证 import |
| _inference.py 重构引入 regression | 沿用现有 inline 模式,不引入 class abstraction |
| detect function 命名漂移 | 严格 `detect_app_autoscaling_<ns>` 命名 + grep 验证 |

## 8. ADR defer(后续 plan 议题)

- Plan B (v1.3.1): `aws-application-autoscaling-ops/references/scheduled-actions.md` 新建 + Runbook RB-AUTOSCALING-01 扩 S9-S12 steps 处理 scheduled-action
- Plan C (v1.4.0): `aws-application-autoscaling-ops/references/elasticache.md` + `kafka.md` + `appstream.md` 新建(剩余 3 namespace docs)
- Plan D (远期): Per-resource event-driven invocation(替换 passive polling),Cross-AWS-account orchestration,Learning from runbook outcomes
