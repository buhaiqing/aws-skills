# aws-application-autoscaling-ops v1.2.0 Increment — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal**: 完成 Application Auto Scaling 文档侧 ServiceNamespace 全主流覆盖(v1.0.0 → v1.1.0 → v1.2.0 → 4 个剩余 namespace reference 文件:EMR / SageMaker / Comprehend / Keyspace)。

**Spec**: `docs/superpowers/specs/2026-07-21-aws-appautoscaling-ops-v1.2.0-design.md`

**Tech Stack**: Markdown(reference files),AWS CLI v2 + boto3(samples),YAML anchors(无新文件)。

**Out-of-Scope**: 新 inference rules、Python handler、Schedule actions、ElastiCache/Kafka/AppStream。

---

## 阶段 0 — Pre-change CodeGraph sync

- [ ] **Step 1**: `codegraph sync .` — 增量索引
- [ ] **Step 2**: `codegraph explore "aws-application-autoscaling-ops"` — 确认目录存在

## 阶段 1 — 4 reference files 新建(emr / sagemaker / comprehend / keyspace)

### Task 1.1 — `references/emr.md`(~ 50 lines)

- [ ] **Step 1**: 文件创建
  - H2 `## ServiceNamespace × ScalableDimension` (1 row: `elasticmapreduce` + `elasticmapreduce:instancegroup:InstanceCount`)
  - H2 `## resource_id 格式`:`instancegroup/<cluster-id>/<instance-group-id>`
  - H2 `## 常用 CLI`:`register-scalable-target` + `put-scaling-policy` TargetTracking p50 `InstanceGroupCPUUtilization`
  - H2 `## boto3 模板`(inline comment,no docstring)
  - H2 `## 注意事项`:EMR core instance vs task instance group 区别;Instance Fleet 不需要 Application Auto Scaling
  - Quota 段:API 验证(无硬编码)
- [ ] **Step 2]: CHANGELOG reference 段列 emr.md

### Task 1.2 — `references/sagemaker.md`(~ 60 lines)

- [ ] **Step 1**: 文件创建
  - 1 row table(`sagemaker` + `sagemaker:variant:DesiredInstanceCount`),mention deprecated `sagemaker:endpoint-variant` (legacy)
  - `resource_id`: `endpoint/<endpoint-name>/variant/<variant-name>`(嵌套)
  - 1 CLI + 1 boto3
  - `PredefinedMetricType: SageMakerVariantInvocationsPerInstance`(canonical metric)
  - 注意事项:real-time endpoint vs async inference,multi-variant 一个 endpoint
  - Quota:API 验证
- [ ] **Step 2]: CHANGELOG reference 段列 sagemaker.md

### Task 1.3 — `references/comprehend.md`(~ 50 lines)

- [ ] **Step 1**: 文件创建
  - 1 row table(`comprehend` + `comprehend:document-classifier:DesiredInferenceUnits`), mention 另一个 dim `comprehend:entity-recognizer:DesiredInferenceUnits`(stub,不展开)
  - `resource_id`: `document-classifier/<arn-suffix>` 或 `entity-recognizer/<arn-suffix>`(ARN 末尾部分)
  - 1 CLI + 1 boto3
  - `PredefinedMetricType`:无预定义;`CustomizedMetricSpecification` 路径(模型自动不适用)
  - 注意事项:custom model 仅 inference 时有效;training 阶段不伸缩
  - Quota:API 验证
- [ ] **Step 2]: CHANGELOG reference 段列 comprehend.md

### Task 1.4 — `references/keyspace.md`(~ 50 lines)

- [ ] **Step 1**: 文件创建
  - 2 rows table(`cassandra` + 2 ScalableDimensions),与 DynamoDB read/write 类似
  - `resource_id`: `keyspace/<keyspace-name>/table/<table-name>`
  - 1 CLI(target tracking on ReadCapacityUnits) + 1 CLI(put scaling policy)
  - 1 boto3 模板
  - `PredefinedMetricType`:无预定义;用 `CustomizedMetricSpecification` + CloudWatch 指标 `AWS/Cassandra` namespace
  - 注意事项:Cassandra-compatible (Apache Cassandra 协议);与 DynamoDB 容量模型类似但底层是 Keyspace 节点
  - Quota:API 验证
- [ ] **Step 2]: CHANGELOG reference 段列 keyspace.md

### Task 1.5 — V1 + V9 验证
- [ ] **Step 1**: `ls references/{emr,sagemaker,comprehend,keyspace}.md` 全部 4 个存在
- [ ] **Step 2]: 每个 reference 文件 grep `ServiceNamespace` ≥ 1 + `ScalableDimension` ≥ 1 + `--output json` ≥ 1(末尾)
- [ ] **Step 3**: TE-6 dedup:跨 4 个 reference 文件 register_scalable_target 应 ≤ 1 + canonical in aws-cli-usage.md ≥ 6 commands

## 阶段 2 — aws-application-autoscaling-ops 既有文件改

### Task 2.1 — `SKILL.md` frontmatter v1.1.0 → v1.2.0 + Reference Files +4 行

- [ ] **Step 1**: SearchReplace `version: "1.1.0"` → `version: "1.2.0"` (单行)
- [ ] **Step 2**: SearchReplace Reference Files 段 anchor `- [CHANGELOG](CHANGELOG.md) — v1.1.0+ history` → prepend 4 行:
  ```
  - [Lambda Patterns](references/lambda.md) — Lambda Provisioned Concurrency
  - [DynamoDB Patterns](references/dynamodb.md) — DynamoDB Table / GSI capacity
  - [Spot Fleet Patterns](references/spot-fleet.md) — ec2:spot-fleet-request:TargetCapacity
  ```
- [ ] **Step 3]: 验证 frontmatter `---` 双闭合不变(仅 version 1 行改)

### Task 2.2 — `core-concepts.md` ServiceNamespace 表 append 5 行

- [ ] **Step 1**: SearchReplace anchor `| \`ec2\`            | \`ec2:spot-fleet-request:TargetCapacity\` | v1.1.0 — full coverage |`
  - replacement:append 5 行 (`elasticmapreduce` / `sagemaker` / `comprehend` / `cassandra` × 2)
- [ ] **Step 2]: 验证表行数从 7 → 12(greq 5 新 ns)

### Task 2.3 — `CHANGELOG.md` 新增 `[1.2.0]` entry

- [ ] **Step 1**: SearchReplace anchor `^## \[1.1.0\] - 2026-07-21` (前置 insert) → prepend `[1.2.0]` entry 完整段(Added ServiceNamespace expansion + Deferred next plan)
- [ ] **Step 2]: 验证新 entry 在 1.1.0 entry 之前

## 阶段 3 — README 双语 bump

- [ ] **Step 1]: SearchReplace README.md anchor `- aws-application-autoscaling-ops \| Application Auto Scaling (cross-service scaler) | ✅ **Complete v1.1.0**` → v1.2.0(完整 + 内容描述 +4 namespace reference)
- [ ] **Step 2]: SearchReplace README_cn.md 同样 anchor(中文版)
- [ ] **Step 3]: V6 grep 验证

## 阶段 4 — Self-review R1+R2 + Monitor fallback

### Task 4.1 — R1(Charter + TE)

- [ ] **Step 1]: 重新 Read SKILL.md frontmatter(do not trust memory)
- [ ] **Step 2]: C1-C6 校验
- [ ] **Step 3]: TE-1:4 个新 ref 文件 quota 全部用 API 验证(no hardcoded)
- [ ] **Step 4]: TE-2:无 docstring
- [ ] **Step 5]: TE-3:error 紧凑表 (本次不增 error 表)
- [ ] **Step 6]: TE-4:JSON paths 顶部集中(每个 ref 文件都用 AWS API 命令,JSON path 默认 `--query` 模板)
- [ ] **Step 7]: TE-5:不增 anchor 文件(本次 yaml 不动)
- [ ] **Step 8]: TE-6:reference 文件间 register_scalable_target example ≤ 1 per file
- [ ] **Step 9]: V7 frontmatter `---` 双闭合(本计划 SKILL.md 仅 version 1 行改)
- [ ] **Step 10]: V10 git diff 行 scope 仅上述文件

### Task 4.2 — R2(CLI / safety / link / dedup / README sync)

- [ ] **Step 1]: Anti-pattern check 0 命中
- [ ] **Step 2]: link integrity:ServiceNamespace 严格 namespace:string
- [ ] **Step 3]: content dedup:4 个 ref 文件 example 与 aws-cli-usage.md canonical 不重复超出预期
- [ ] **Step 4]: README 双语表完整

### Task 4.3 — Token Efficiency Monitor fallback

- [ ] **Step 1]: 尝试 1 call subagent;失败 fallback self-monitor
- [ ] **Step 2]: 出具 ACCEPT-SUBOPTIMAL disposition

## 阶段 5 — 合并 commit + push

### Task 5.1 — 1 个 conventional commit

- [ ] **Step 1]: Write commit msg to `audit-results/commit-msg-appautoscaling-v1.2.0-2026-07-21.txt`
- [ ] **Step 2]: `git add` 全部 8 个 affected files(per plan §3):
  ```bash
  git add \
    aws-application-autoscaling-ops/SKILL.md \
    aws-application-autoscaling-ops/CHANGELOG.md \
    aws-application-autoscaling-ops/references/core-concepts.md \
    aws-application-autoscaling-ops/references/emr.md \
    aws-application-autoscaling-ops/references/sagemaker.md \
    aws-application-autoscaling-ops/references/comprehend.md \
    aws-application-autoscaling-ops/references/keyspace.md \
    README.md \
    README_cn.md \
    docs/superpowers/specs/2026-07-21-aws-appautoscaling-ops-v1.2.0-design.md \
    docs/superpowers/plans/2026-07-21-aws-appautoscaling-ops-v1.2.0.md
  ```
- [ ] **Step 3]: `git commit -F <tmpfile>` + `rm <tmpfile>`
- [ ] **Step 4]: `git status --short` 应清空
- [ ] **Step 5]: `git push origin main`(user 已 confirm 推 push)

### Task 5.2 — 验收 checklist

- [ ] `git log -1 --stat` 显示 ≥ 10 files
- [ ] `grep "1.2.0"` 在 4 文件(SKILL.md frontmatter / CHANGELOG.md / README.md / README_cn.md)全命中
- [ ] `ls aws-application-autoscaling-ops/references/{emr,sagemaker,comprehend,keyspace}.md` 4 全在
- [ ] `git status --short` 清空
- [ ] frontmatter `---` 双闭合 per skill file (SKILL.md 不动)
- [ ] Anti-pattern 0 命中

## Out-of-Scope(下次 plan 议题)

- Per-namespace inference rules in `aws-aiops-cruise`(各 namespace 专属 CloudWatch metric namespace 须独立 design)
- Python handler 实施 (`aws-aiops-cruise/runbooks/scripts/_inference.py`)
- Schedule actions 全 namespace 覆盖
- ElastiCache / Kafka / AppStream namespace 文档(v2.x)

## Risk mitigation

| 风险 | 缓解 |
|---|---|
| ServiceNamespace 大小写错 | 严格 AWS 官方 namespace:string |
| Resource_id 格式错 | 验证符合 AWS docs(`instancegroup/`、`endpoint/.../variant/`、`document-classifier/`、`keyspace/.../table/`) |
| 4 ref 文件内容漂移 | 每个文件结构 1-row table + resource_id + 2 CLI + 1 boto3 + caveats + quota |
| Frontmatter 合规 | 仅 version 1 行 + References +4 行 |
| TE-6 冗余 | 每个 ref 文件 1 example + canonical aws-cli-usage.md |
| Inference rules 用户期望 | spec §8 显式 deferred spec §6 V10 验证 git diff |

## 安全与回滚

- 不动 IAM / credentials;全 markdown
- 不 push 上 remote unless user explicit(本计划 user 已 confirm push,可 push)
- commit on local `main`;`git reset --soft HEAD~1` 即回滚
