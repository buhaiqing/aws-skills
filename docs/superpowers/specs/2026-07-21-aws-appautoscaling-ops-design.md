# aws-application-autoscaling-ops 创建 — 设计文档

- **日期**: 2026-07-21
- **状态**: 已定稿(用户确认方案 A, memory 9f30ba81-1297-411d-951c-38cdd51ed78b)
- **对应计划**: `docs/superpowers/plans/2026-07-21-aws-appautoscaling-ops.md`
- **起源**: 上次 plan `2026-07-21-aws-ecs-ops-aiops-finops.md` §ADR defer

## 1. 背景与问题

上次 aws-ecs-ops AIOps+FinOps 闭环补齐 commit(`23db04a`)时,把 `aws-application-autoscaling` 缺位作为 ADR defer 留档,确定本次 plan 议题采用方案 A: **新建独立 L1 skill `aws-application-autoscaling-ops`,MVP scope = ECS-only**。

### 1.1 Disk-verified 现状(2026-07-21 复核)

| 项 | 实测 |
|---|---|
| 仓库内是否有 `aws-application-autoscaling-*` 目录 | **无**;grep 0 命中 |
| 其他 skill 引用 `aws application-autoscaling` CLI | 1 处:`[aws-dynamodb-ops/SKILL.md line 716](file:///Users/bohaiqing/opensource/git/aws-skills/aws-dynamodb-ops/SKILL.md#L716)` inline `register-scalable-target` 调用,**不是 cross-skill delegate** |
| `aws-autoscaling-ops` 引用密度 | **0**;isolation skill,改名/扩 scope 都不影响 cross_skill_deps |
| AWS CLI namespace | `aws application-autoscaling` (与 EC2 ASG 的 `aws autoscaling` 是**两个不同 namespace**) |
| 服务覆盖 | `ServiceNamespace` ∈ {ecs, dynamodb, lambda, spot-fleet, emr, appstream, sagemaker, comprehend, kafka, keyspace, elasticache, ...},ScalableDimension 也多 |

### 1.2 痛点(AIOps)

1. ECS Service Container Insights alarms (`ECSServiceAverageCPUUtilization` / `MemoryUtilization`)目前**没有自动 scaling 闭环** — 只能人工 scale
2. `aws-aiops-cruise` 53 detection rules 中无 CO-AUTOSCALING-01 / CO-AUTOSCALING-02 类型规则
3. ECS `runningCount < desiredCount` 不能自动 recover — 只能 alert

### 1.3 痛点(FinOps)

1. ECS services 长期 over-provisioned 不触发 scale-down → 非高峰期烧 ~30-60% 浪费费
2. Fargate Spot 中断时无 auto-replacement 路径(`aws-ecs-ops` SKILL.md 引用 `aws-application-autoscaling-ops` 但无 skill 实现)
3. 没有 spot-vs-on-demand capacity rebalance 自动化 — capacity provider strategy 改动后需手动调整 scaling 上下限

### 1.4 撮合杠杆 — 闭环

| 杠杆 | AIOps 价值 | FinOps 价值 |
|---|---|---|
| **Target tracking on `ECSServiceAverageCPUUtilization`** | canonical auto-heal recipe;Service deficit 自动补 capacity | 自动 scale-down 砍掉非高峰 30-60% 账单 |
| **Step scaling with CloudWatch alarms** | 突发 burst alarm → 立即 scaling | burst 时间可控,成本可预测 |
| **Scheduled actions** | 业务周期高峰预警 | 按时段错峰,优化 SP 折扣命中率 |
| **Tag + Capacity tracking** | 治理 metadata(AIOps 资源归属) | Cost Allocation by team / project |

## 2. 目标与范围

**目标**: 新建 L1 skill `aws-application-autoscaling-ops`,MVP scope = ECS-only,把 AIOps auto-heal + FinOps 弹性计费合在同一个杠杆点上,补齐 cross-skill delegate 链。

### 2.1 Scope Boundary(外科手术式)

**新建**:
- `aws-application-autoscaling-ops/SKILL.md`(L1, `metadata.type: base`)
- `aws-application-autoscaling-ops/references/aws-cli-usage.md`
- `aws-application-autoscaling-ops/references/boto3-sdk-usage.md`
- `aws-application-autoscaling-ops/references/core-concepts.md`
- `aws-application-autoscaling-ops/references/troubleshooting.md`
- `aws-application-autoscaling-ops/references/rubric.md`(GCL required)
- `aws-application-autoscaling-ops/references/prompt-templates.md`(shared skeleton specialization)
- `aws-application-autoscaling-ops/assets/example-config.yaml`

**改**:
- [aws-finops-core/SKILL.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-finops-core/SKILL.md): `metadata.provides` +2(`app-autoscaling-ecs-targets` / `app-autoscaling-policies`),`metadata.delegate` +2(`app-autoscaling-ecs-targets: aws-application-autoscaling-ops` / `app-autoscaling-policies: aws-application-autoscaling-ops`)
- [aws-ecs-ops/references/cost-optimization.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/references/cost-optimization.md): line 49 ADR defer stub `(TODO: not yet in repo)` → 改为有效 link 到 `aws-application-autoscaling-ops`
- [aws-ecs-ops/CHANGELOG.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/CHANGELOG.md): 新增 entry `## [1.2.0] / 2026-07-21 / ### Changed: references/cost-optimization.md ADR defer stub 替换为有效 cross-ref`
- [README.md](file:///Users/bohaiqing/opensource/git/aws-skills/README.md): Existing Skills 表 +1 行
- [README_cn.md](file:///Users/bohaiqing/opensource/git/aws-skills/README_cn.md): Existing Skills 表 +1 行

**不改**:
- [aws-ecs-ops/SKILL.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/SKILL.md) frontmatter(version 锁 1.1.0)
- [aws-ecs-ops/references/cost-optimization.md](file:///Users/bohaiqing/opensource/git/aws-skills/aws-ecs-ops/references/cost-optimization.md) 内容体不改,只改末尾 ADR defer 一行
- [aws-autoscaling-ops](file:///Users/bohaiqing/opensource/git/aws-skills/aws-autoscaling-ops/SKILL.md)(EC2 ASG 专用,与本 skill 完全独立)
- `aws-dynamodb-ops/SKILL.md` line 716 inline `register-scalable-target` 调用是 DynamoDB L1 skill 的 DynamoDB-specific 用法 — **不替代**(不引入 circular dependency)

**不引入**:
- `references/lambda.md` / `references/dynamodb.md`(后续 plan 增量)
- `aws-aiops-cruise` inference rules 改动(deferred 到另一个 plan)
- Application Auto Scaling Spot Fleet target tracking(deferred)

## 3. 关键决策

### D1: MVP scope = ECS-only
- core-concepts.md 只列 ECS 的 ServiceNamespace + ScalableDimension 表格
- references/ 暂只含 aws-cli-usage / boto3 / core-concepts / troubleshooting / rubric / prompt-templates
- 后续 incremental 加 `references/lambda.md` / `references/dynamodb.md` 不需改 SKILL.md 主体

### D2: SKILL.md frontmatter `version: "1.0.0"` (L1 default)
- 与新 skill 起点对齐(L1 service skill 一般 v1.0.0 起,见 `aws-ecs-ops` v1.0.0 → v1.1.0 已 bump)
- 不建 `CHANGELOG.md`(NEW skill 无历史,首次 commit 一行 `Changelog` H2 不必要;后续 bump 时再加)
- README 状态: `✅ Complete v1.0.0 (NEW) — ECS Service Auto Scaling (cross-service scaler namespace)`

### D3: GCL 配置 — `required` / `max_iter=2`
- 5 个 write 操作需 GCL 评估(C1-C6 + TE)
- 关键 destructive events:
  - `deregister-scalable-target` (removes scaling config → 服务失去 auto-scale,等价 deletion-impact)
  - `delete-scaling-policy` (removes policy,scale config falls back to manual)
- 都需要 explicit confirm token,遵循 `gcl-spec.md` §8 rules A7 / A8 / A9 / A10
- prompt-templates.md 用 shared skeleton specialization(`aws-skill-generator/references/prompt-skeletons.md`)

### D4: Charter C7 (Layering Contract)
- `metadata.type: base`
- 提供 `provides`:`app-autoscaling-register-target` / `app-autoscaling-deregister-target` / `app-autoscaling-put-policy` / `app-autoscaling-delete-policy` / `app-autoscaling-tag-resource` / `app-autoscaling-describe`
- 不提供 `delegate:`(base skill 默认 omit;`aws-finops-core` 加 delegate 反向指过来)

### D5: 命名一致性
- 仓库 30+ L1 skill 用 `aws-<service>-ops` 命名 convention
- 服务真实 namespace 是 `aws application-autoscaling`,故 skill 名 `aws-application-autoscaling-ops`
- 与 EC2 ASG `aws-autoscaling-ops` 通过名字区分(`application-autoscaling` 是更长的 prefix,显式区分)

### D6: Cross-skill Integration via Delegate Adapter Patch
- `metadata.orchestrator_aware: true` + `metadata.orchestrator_compat: ">=0.1.0"`
- `metadata.delegate.accepts: ['capacity-forecast', 'self-heal']`
- `metadata.delegate.produces_facts: ['state']`
- `metadata.delegate.idempotency_ttl: "PT24H"`
- `metadata.delegate.destructive_ops_require_confirm: true`

## 4. metadata 改动矩阵

### A. `aws-application-autoscaling-ops/SKILL.md` frontmatter

```yaml
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-21"
  runtime: Harness AI Agent
  type: base
  provides:
    - app-autoscaling-register-target
    - app-autoscaling-deregister-target
    - app-autoscaling-put-policy
    - app-autoscaling-delete-policy
    - app-autoscaling-tag-resource
    - app-autoscaling-describe
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-ecs-ops           # Service / Cluster lookup
    - aws-cloudwatch-ops    # alarm source for target tracking
    - aws-cloudtrail-ops    # 变更审计
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['capacity-forecast', 'self-heal']
    produces_facts: ['state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
```

### B. `aws-finops-core/SKILL.md` 改动

`metadata.provides` 追加:
```yaml
    - app-autoscaling-ecs-targets
    - app-autoscaling-policies
```

`metadata.delegate` 追加:
```yaml
    app-autoscaling-ecs-targets: aws-application-autoscaling-ops
    app-autoscaling-policies: aws-application-autoscaling-ops
```

### C. `aws-ecs-ops/CHANGELOG.md` 加 1 个新 entry

```markdown
## [1.2.0] - 2026-07-21

### Changed
- `references/cost-optimization.md` ADR defer stub (line 49) replaced with valid
  cross-reference to `aws-application-autoscaling-ops` (new L1 skill shipped same day).
```

### D. `README.md` + `README_cn.md` Existing Skills 表 +1 行

```markdown
| aws-application-autoscaling-ops | Application Auto Scaling (cross-service scaler) | ✅ Complete v1.0.0 (NEW) — ECS Service Auto Scaling (Target tracking on `ECSServiceAverageCPUUtilization`, step scaling, scheduled actions); delegate → aws-finops-core / aws-aiops-orchestrator |
```

(中文版对应翻译)

## 5. 端到端数据流(改动后)

```
┌──────────────────────────────────────┐
User intent: "auto-scale ECS on CPU"   │
└──────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
aws-finops-core (composite L2)         │
  ├─ provides.app-autoscaling-policies │
  └─ delegate.app-autoscaling-policies │
       └─ aws-application-autoscaling-ops  ◀─── 本次新建
              │                         
              ├─ Operation: Register Scalable Target
              │    (service=ecs, dimension=ecs:service:DesiredCount,
              │     min=1, max=10)
              ├─ Operation: Put Scaling Policy
              │    (TargetTracking on ECSServiceAverageCPUUtilization 50%)
              └─ cross_skill_deps: aws-ecs-ops + aws-cloudwatch-ops
                                              │
                                              ▼
                                     aws-ecs-ops / aws-cloudwatch-ops
                                     (verify service exists, alarm created)

┌──────────────────────────────────────┐
User intent: "predict ECS cost / 30d"  │
└──────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
aws-aiops-orchestrator (composite L2)   │
  └─ Layer 1: data collection           │
       ├─ aws-ecs-ops (Container Insights)│
       └─ aws-application-autoscaling-ops  ◀─── (future: cost per target)
```

## 6. 验收标准

| # | 项 | 标准 |
|---|---|---|
| V1 | Frontmatter 闭合:`awk '/^---$/{c++; if(c==2){exit}} c==1'` 返回 frontmatter 全块 | 2 个 `---` per file |
| V2 | SKILL.md Charter C1-C6 全 pass | C6 TE-1..TE-6 全部 pass |
| V3 | Operations 列 ≥ 5 条 | `grep -c "^### Operation:"` ≥ 5 |
| V4 | Destructive ops 有 confirmation token | `grep "DEREGISTER_SCALABLE_TARGET" SKILL.md` 命中 |
| V5 | `metadata.type: base` 显式声明 | grep `^  type: base$` |
| V6 | `metadata.provides` 列出 ≥ 4 条 operation | grep `- app-autoscaling-` ≥ 4 |
| V7 | rubric.md 完整 5 维度 + AWS rules A1-A10 引用 | `gcl-spec.md §8` 引用 1+ |
| V8 | prompt-templates.md 用 shared skeleton specialization | `prompt-skeletons.md` 引用 1 |
| V9 | aws-finops-core delegate + provides 都增 2 条 | grep 3 处 `app-autoscaling` |
| V10 | README / README_cn Existing Skills 表 +1 行 | grep `aws-application-autoscaling-ops` |
| V11 | TE 软 cap:SKILL.md ≤ 200 lines | `wc -l` ≤ 200 |
| V12 | `aws ecs references/cost-optimization.md` ADR defer 替换为有效 ref | grep 无 `TODO: not yet in repo` |

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Charter C6 自动失效:任何 hardcoded table > 5 rows | core-concepts.md 仅放 ECS ServiceNamespace + ScalableDimension 短表;reference 全部走 API 命令 |
| TE-6:SKILL.md 与 references 重复内容 | SKILL.md 仅 ~ 200 lines 含 operation summary;CLI/SDK 详细命令在 references/ |
| cross_skill_deps 引用了不存在的 skill | codegraph explore 验证 aws-ecs-ops/aws-cloudwatch-ops/aws-cloudtrail-ops 目录真实存在 |
| GCL required 触发评审压力 | rubric.md + prompt-templates.md 用 shared skeleton pattern,降低 boilerplate |
| subagent infra 不可用 | 主 agent 自己串行,沿用上次 plan fallback 模式 |
| 现有 L1 skill 引用方式不一致 | `aws-dynamodb-ops` 是 inline CLI 引用,不是 cross_skill delegate — 我们的新建 skill 不动它 |
| README 版本表已很密集 | 加入一行 `✅ Complete v1.0.0 (NEW) ...` 即够,不破坏表格对齐 |

## 8. ADR defer(本 plan 不做,留给后续 plan)

- `references/lambda.md` (Lambda Provisioned Concurrency `lambda:function:ProvisionedConcurrency`)
- `references/dynamodb.md` (DynamoDB Table ReadCapacityUnits / WriteCapacityUnits / GSI)
- `references/spot-fleet.md` (Spot Fleet Request target tracking)
- `references/emr.md` / `references/sagemaker.md` (其他 namespace,低优先级)
- `aws-aiops-cruise` 新增 CO-AUTOSCALING-01 detection rule (定时查 scalable-targets over-provisioned)
- AIOps runbook RB-AUTOSCALING-01 (auto-heal deregister stale targets)
- `aws-application-autoscaling-ops/CHANGELOG.md` (v1.1.0)
