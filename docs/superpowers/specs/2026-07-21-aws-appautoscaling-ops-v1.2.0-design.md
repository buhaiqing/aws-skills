# aws-application-autoscaling-ops v1.2.0 Increment — 设计文档

- **日期**: 2026-07-21
- **状态**: 已定稿(用户确认 "其余 name space")
- **对应计划**: `docs/superpowers/plans/2026-07-21-aws-appautoscaling-ops-v1.2.0.md`
- **起源**: [`2026-07-21-aws-appautoscaling-ops-design.md`](2026-07-21-aws-appautoscaling-ops-design.md) §8 ADR defer;`2026-07-21-aws-appautoscaling-ops-v1.1.0-design.md` §8 ADR defer

## 1. 背景与问题

Application Auto Scaling 在仓库内 30+ L1 skill 中目前覆盖 4 个主流 namespace:

- v1.0.0(2026-07-21):ECS `ecs:service:DesiredCount`
- v1.1.0(2026-07-21):Lambda / DynamoDB / Spot Fleet

ADR defer §8 列出还剩 4 个 namespace 未文档化:
- EMR `elasticmapreduce:instancegroup:InstanceCount`
- SageMaker `sagemaker:variant:DesiredInstanceCount`
- Comprehend `comprehend:document-classifier:DesiredInferenceUnits`
- Keyspace(Apache Cassandra-compatible)`cassandra:table:{Read,Write}CapacityUnits`

Completion 路径:
1. **本次 v1.2.0**:把 4 个 namespace reference 文件落地,完成文档侧 ServiceNamespace 全主流覆盖
2. **后续 v1.3.x**:每 namespace 配专属 AIOps inference rule(ServiceNamespace-specific CloudWatch metric namespace 各不同,需独立 rule 设计)+ Python handler 实施
3. **远期 v2.x**:Schedule actions 全 namespace + ElastiCache/Kafka/AppStream 边缘 namespace

## 2. 目标与范围

**目标**: 落地 4 个剩余 namespace reference 文件,把 Application Auto Scaling 文档侧 ServiceNamespace 完成;保持 Repository-wide single-service-skill convention。

### 2.1 Scope Boundary(外科手术式)

**新建 4 个 reference files**:
- `aws-application-autoscaling-ops/references/emr.md`(~ 50 lines)
- `aws-application-autoscaling-ops/references/sagemaker.md`(~ 60 lines)
- `aws-application-autoscaling-ops/references/comprehend.md`(~ 50 lines)
- `aws-application-autoscaling-ops/references/keyspace.md`(~ 50 lines)

**改**:
- `aws-application-autoscaling-ops/SKILL.md`:frontmatter `version: "1.1.0" → "1.2.0"` + Reference Files 段 +4 行
- `aws-application-autoscaling-ops/references/core-concepts.md`:ServiceNamespace × ScalableDimension 表 +5 行(EMR × 1,SageMaker × 1,Comprehend × 1,Keyspace × 2 Read/WriteCapacityUnits)
- `aws-application-autoscaling-ops/CHANGELOG.md`:在 `[1.1.0]` 之前插 `[1.2.0]` 段
- `README.md` + `README_cn.md`:aws-application-autoscaling-ops 行 v1.1.0 → v1.2.0

**不改**:
- `aws-aiops-cruise/references/inference-rules.md`(本次纯文档增量,不触发新 rule)
- `aws-aiops-orchestrator/references/runbook-recipes.md`(RB-AUTOSCALING-01 决策模式可复用)
- `aws-finops-core`(已有 4 处 ECS + app-autoscaling 引用,本次 namespace 文档化不影响 FinOps route)
- 其他 30+ L1 skill

**不引入**:
- 新 inference rule(per namespace 须独立 CloudWatch metric namespace,后续 plan 处理)
- Python handler 实施
- Schedule actions (Lambda cron / 全 namespace) 完整覆盖
- ElastiCache / Kafka / AppStream namespace 文档

## 3. 关键决策

### D1: 每个 namespace 文件结构一致(TE-6 canonical)
- 每个 reference file 含:`ServiceNamespace × ScalableDimension` 1-row 表 + `resource_id` 格式 + 1 个 `register-scalable-target` CLI + 1 个 `put-scaling-policy` CLI + 1 个 boto3 模板 + 注意事项 + quota 提醒(API verification only)
- 避免 lambda.md / dynamodb.md 等已有 file 与新 file 结构漂移

### D2: 不增 inference rules(scope control)
- 4 个 namespace 各有专属 CloudWatch metric namespace(EMR `AWS/ElasticMapReduce` / SageMaker `AWS/SageMaker` / Comprehend `AWS/Comprehend` / Keyspace `AWS/Cassandra`)
- 每个 rule 须独立 metric namespace + PredefinedMetricType 设计;SSR 后续计划拆分
- 文档增量先到,detection / runbook automation 留待 v1.3.x

### D3: Bump 策略 v1.1.0 → v1.2.0
- 4 个 reference 文件 + ServiceNamespace 完全覆盖 — 值得 minor bump
- per project_information_memory 同步 SKILL.md frontmatter + CHANGELOG.md + README 双语
- `last_updated: "2026-07-21"` 不变(同日多次 commit)

### D4: Resource_id 格式严格按 AWS 官方
- EMR: `instancegroup/<cluster-id>/<instance-group-id>`
- SageMaker: `endpoint/<endpoint-name>/variant/<variant-name>`(variants are nested under endpoints)
- Comprehend: `document-classifier/<arn-suffix>` 或 `entity-recognizer/<arn-suffix>`
- Keyspace: `keyspace/<keyspace-name>/table/<table-name>`

完整 resource_id 格式列在各自 reference file 的 `## resource_id 格式` 段,避免执行时调用 API 报错。

## 4. namespace 增量关键 API 一览

| Namespace | ServiceNamespace | ScalableDimension(s) | Key API |
|---|---|---|---|
| EMR | `elasticmapreduce` | `elasticmapreduce:instancegroup:InstanceCount` | `register-scalable-target` + `put-scaling-policy` TargetTracking p50 `InstanceGroupCPUUtilization` |
| SageMaker | `sagemaker` | `sagemaker:variant:DesiredInstanceCount` | endpoint variant 实时推理 instances scaling |
| Comprehend | `comprehend` | `comprehend:document-classifier:DesiredInferenceUnits` | NLP 文档分类 inference units scaling |
| Keyspace | `cassandra` | `cassandra:table:ReadCapacityUnits` + `cassandra:table:WriteCapacityUnits` | Cassandra-compatible table 容量 scaling(与 DynamoDB 类似 read/write 分离) |

### SKILL.md frontmatter
```yaml
  version: "1.2.0"   # bumped from 1.1.0
```

### Reference Files 段追加
```
- [EMR Patterns](references/emr.md) — EMR InstanceGroup scaling
- [SageMaker Patterns](references/sagemaker.md) — endpoint variant
- [Comprehend Patterns](references/comprehend.md) — NLP inference units
- [Keyspace Patterns](references/keyspace.md) — Cassandra-compatible
```

### core-concepts.md ServiceNamespace 表追加 5 行
```
| `elasticmapreduce` | `elasticmapreduce:instancegroup:InstanceCount` | v1.2.0 — full coverage |
| `sagemaker`         | `sagemaker:variant:DesiredInstanceCount` | v1.2.0 — full coverage |
| `comprehend`       | `comprehend:document-classifier:DesiredInferenceUnits` | v1.2.0 — full coverage |
| `cassandra`        | `cassandra:table:ReadCapacityUnits` | v1.2.0 — full coverage |
| `cassandra`        | `cassandra:table:WriteCapacityUnits` | v1.2.0 — full coverage |
```

(实际追加 = EMR × 1 + SageMaker × 1 + Comprehend × 1 + Keyspace × 2 = 5 行)

### CHANGELOG.md `[1.2.0]` 段
```markdown
## [1.2.0] - 2026-07-21

### Added (ServiceNamespace expansion)
- `references/emr.md` — EMR InstanceGroup (`elasticmapreduce:instancegroup:InstanceCount`)
- `references/sagemaker.md` — SageMaker endpoint variant (`sagemaker:variant:DesiredInstanceCount`)
- `references/comprehend.md` — Comprehend NLP inference units (`comprehend:document-classifier:DesiredInferenceUnits`)
- `references/keyspace.md` — Keyspace (Cassandra-compatible, `cassandra:table:{Read,Write}CapacityUnits`)
- `references/core-concepts.md` ServiceNamespace 表 +5 行 (EMR + SageMaker + Comprehend + Keyspace × 2)

### Deferred (next plan)
- Per-namespace inference rules in `aws-aiops-cruise` (各 ServiceNamespace 专属 CloudWatch metric namespace 须独立 rule 设计)
- Python handler 实施 (`aws-aiops-cruise/runbooks/scripts/_inference.py` 新 rule detector)
- Schedule actions (Lambda cron / 全 namespace) 完整覆盖
```

## 5. 端到端数据流(改动后)

```
   ┌─ aws-application-autoscaling-ops v1.2.0 ──────────────┐
   │  references/aws-cli-usage.md (canonical — full ECS+Lambda+DDB+Spot+EMR+SageMaker+Comprehend+Keyspace)  │
   │  references/boto3-sdk-usage.md (canonical SDK)                │
   │  references/core-concepts.md (12-row ServiceNamespace table)  │
   │  references/{lambda,dynamodb,spot-fleet,emr,sagemaker,      │
   │              comprehend,keyspace}.md (per-namespace detail) │
   └────────────────────────────────────────────────────────┘
        │
        ▼ invoke(待 v1.3.x 增 Python handler)
   ┌─ aws-aiops-cruise + aws-aiops-orchestrator ──────┐
   │ (inference rules + runbook 增量 deferred plan)  │
   └────────────────────────────────────────────────┘
```

本次变更仅文档层,exec time 仍走 ECS(EBS `aws-ecs-ops` 链)路径;Lambda / DynamoDB / Spot Fleet / EMR / SageMaker / Comprehend / Keyspace 7 个 namespace 在 v1.3.x 后才能在 exec 层全 hook。

## 6. 验收标准 V1-V10

| # | 项 | 标准 |
|---|---|---|
| V1 | 4 reference files 存在 | `ls references/{emr,sagemaker,comprehend,keyspace}.md` |
| V2 | core-concepts.md 表 12 行 (从 7 → 12) | grep namespace `elasticmapreduce\|sagemaker\|comprehend\|cassandra` 命中 5 |
| V3 | SKILL.md frontmatter `version: "1.2.0"` | grep |
| V4 | Reference Files 段 +4 行 | grep 各新 entry |
| V5 | CHANGELOG.md `[1.2.0] - 2026-07-21` entry 涵盖 4 文件 + core-concepts.md +5 行 | grep |
| V6 | README + README_cn 双语 aws-application-autoscaling-ops 行 v1.2.0 | grep |
| V7 | SKILL.md frontmatter `---` 双闭合 per file | awk |
| V8 | Anti-pattern `aws --output json <svc>` 0 命中 | grep -rE `^aws --output json ` |
| V9 | TE-6 reference 文件间 register_scalable_target 不冗余(canonical 在 aws-cli-usage.md) | grep count |
| V10 | inference-rules.md / runbook-recipes.md / aws-finops-core 不动(本次纯文档增量) | git diff 0 hits |

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| ServiceNamespace 大小写错 | 严格 AWS 官方 namespace:string(`elasticmapreduce`/`sagemaker`/`comprehend`/`cassandra`) |
| Resource_id 格式错 | 验证 `instancegroup/...`、`endpoint/.../variant/...`、`document-classifier/...`、`keyspace/.../table/...` 符合 AWS docs |
| Inference rules 不同步 | markdown 不动 cruise / orchestrator 文件(spec 显式 deferred) |
| TE-6 reference 文件命令冗余 | 每个 reference 文件 1 example + canonical CLI in aws-cli-usage.md |
| Schedule actions 用户期望 | spec 显式 deferred;v1.2.0 是文档覆盖里程碑 |

## 8. ADR defer(next plan candidates)

1. **Per-namespace inference rules**(`aws-aiops-cruise/references/inference-rules.md` § Application Auto Scaling 扩展)+ Python handler 实施 — 各 namespace 的 CloudWatch metric namespace 不同,须独立 rule + 单独 plan
2. **Schedule actions**(`scheduled-action` 命名空间 + 全 namespace 适用)Lambda cron / 业务周期覆盖
3. **ElastiCache replication-group / Kafka broker-storage / AppStream fleet** namespace 扩展(v2.x 议题)
