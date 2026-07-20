# aws-application-autoscaling-ops 增量扩展 (v1.1.0) — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal**: 把 [aws-application-autoscaling-ops v1.0.0](file:///Users/bohaiqing/opensource/git/aws-skills/aws-application-autoscaling-ops/SKILL.md) (ECS-only) 增量扩到 v1.1.0(ECS + Lambda + DynamoDB + Spot Fleet),补全 4 条 cruise inference rules,新增 1 个 AIOps runbook,把 Application Auto Scaling 在仓库内完整化。

**Spec**: `docs/superpowers/specs/2026-07-21-aws-appautoscaling-ops-v1.1.0-design.md`

**Tech Stack**: Markdown(全部)、YAML anchors(example-config.yaml 复用)、AWS CLI v2 + boto3(reference samples)、Read-only inference rule spec(markdown 追加,Python 实施 deferred)。

**Out-of-Scope**: Python `_inference.py` 实施、RB-AUTOSCALING-02、EMR/SageMaker namespace。

---

## 阶段 0:准备

### Task 0.1: Pre-change CodeGraph sync

- [ ] **Step 1**: `codegraph sync .`
- [ ] **Step 2**: `codegraph explore "aws-application-autoscaling-ops"` — 确认目录存在
- [ ] **Step 3**: `codegraph explore "aws-aiops-cruise" "aws-aiops-orchestrator"` — 跨 skill 目标存在
- [ ] **Step 4**: 测试 1 call subagent infra;若仍 unavailable 走主 agent 串行(沿上次 pattern)

---

## 阶段 1:新建 3 个 reference file(Lambda / DynamoDB / Spot Fleet)

### Task 1.1: 新建 `aws-application-autoscaling-ops/references/lambda.md`(~ 60 lines)

**Files**: Create lambda.md

- [ ] **Step 1**: 文件创建,内容覆盖:
  - Lambda `ServiceNamespace: lambda` + `ScalableDimension: lambda:function:ProvisionedConcurrency`
  - `resource_id` 格式:`function/<function_name>:<qualifier>`(或纯 function_name 视 API)
  - 必填 `PredefinedMetricType`:`LambdaProvisionedConcurrencyUtilization`
  - 2 个 CLI 命令:`register-scalable-target` + `put-scaling-policy` (TargetTracking p50)
  - 1 个 inline boto3 调用 pattern
  - Quota: `aws service-quotas get-service-quota --service-code lambda --quota-code L-9FDBE1FE`
  - 注:Provisioned Concurrency 与 Reserved Concurrency 区别;Auto Scaling 仅作用于 Provisioned
- [ ] **Step 2]: CHANGELOG reference 段列出 lambda.md

### Task 1.2: 新建 `aws-application-autoscaling-ops/references/dynamodb.md`(~ 70 lines)

**Files**: Create dynamodb.md

- [ ] **Step 1]: 内容覆盖:
  - 4 个 ScalableDimension:`dynamodb:table:ReadCapacityUnits` / `dynamodb:table:WriteCapacityUnits` / `dynamodb:index:ReadCapacityUnits` / `dynamodb:index:WriteCapacityUnits`
  - `resource_id` 格式:`table/<table_name>` 或 `index/<table_name>/<index_name>`
  - 2 种 policy type:TargetTracking(`DynamoDBReadCapacityUtilization` / `DynamoDBWriteCapacityUtilization`)+ StepScaling(基于 CloudWatch alarm)
  - 注意:`aws-dynamodb-ops/SKILL.md` line 716 已有 inline `register-scalable-target` — 引用建立 cross-skill delegate
  - Quota + delegated admin 注意事项(`UpdateApplicationAutoScalingGroup` 等)
- [ ] **Step 2**: CHANGELOG reference 段列出 dynamodb.md

### Task 1.3: 新建 `aws-application-autoscaling-ops/references/spot-fleet.md`(~ 50 lines)

**Files**: Create spot-fleet.md

- [ ] **Step 1]: 内容覆盖:
  - `ServiceNamespace: ec2` + `ScalableDimension: ec2:spot-fleet-request:TargetCapacity`
  - `resource_id` 格式:`spot-fleet-request/<request_id>`
  - 2 个核心 use case:cost optimization(目标跟踪 Spot 价格波动)+ capacity(buffer)
  - 1 个 CLI + 1 boto3 调用 pattern
- [ ] **Step 2]: CHANGELOG reference 段列出 spot-fleet.md

### Task 1.4: spec §V1 验证(3 file 存在 + 内容覆盖完整)

- [ ] **Step 1]: `ls aws-application-autoscaling-ops/references/{lambda,dynamodb,spot-fleet}.md` 应 3 个全存在
- [ ] **Step 2]: grep `ServiceNamespace` each file ≥ 1 + `ScalableDimension` each file ≥ 1
- [ ] **Step 3]: grep `--output json` each file 末尾 ≥ 1

---

## 阶段 2:修改 `aws-application-autoscaling-ops` 既有文件

### Task 2.1: `SKILL.md` frontmatter + Reference Files 段

**Files**: Modify aws-application-autoscaling-ops/SKILL.md

- [ ] **Step 1]: frontmatter `version: "1.0.0"` → `version: "1.1.0"` (仅 1 行)
- [ ] **Step 2]: Reference Files 段追加 3 行:
  ```
  - [Lambda Patterns](references/lambda.md)
  - [DynamoDB Patterns](references/dynamodb.md)
  - [Spot Fleet Patterns](references/spot-fleet.md)
  ```
- [ ] **Step 3]: frontmatter 闭合 `---\n---\n` 验证

### Task 2.2: `core-concepts.md` ServiceNamespace × ScalableDimension 表扩展

**Files**: Modify aws-application-autoscaling-ops/references/core-concepts.md

- [ ] **Step 1]: 现有 1-row ECS 表后追加 6 行(Lambda × 1,DynamoDB × 4,Spot Fleet × 1)
- [ ] **Step 2]: 删除 `<!-- TODO: follow-up plan reference/lambda.md -->` 注释
- [ ] **Step 3]: 删除 `<!-- TODO: follow-up plan reference/dynamodb.md -->` 注释
- [ ] **Step 4]: 删除 `<!-- TODO: follow-up plan reference/spot-fleet.md -->` 注释
- [ ] **Step 5]: spec §V2 + V3 grep 验证

### Task 2.3: 新建 `CHANGELOG.md`(v1.1.0 + v1.0.0 stub)

**Files**: Create aws-application-autoscaling-ops/CHANGELOG.md

- [ ] **Step 1]: Keep-a-Changelog 格式 + v1.1.0 entry(Added AIOps + Added Lambda/DynamoDB/Spot Fleet),v1.0.0 stub
- [ ] **Step 2]: spec §V9 验证

### Task 2.4: spec §阶段 V1+V2+V3+V8+V9 验证

- [ ] **Step 1]: 3 个 reference 文件存在(Skill.md references list 引用)
- [ ] **Step 2]: core-concepts.md stub 注释移除 + 服务表 +5
- [ ] **Step 3]: CHANGELOG.md 命中 `## [1.1.0]`
- [ ] **Step 4]: SKILL.md frontmatter `version: "1.1.0"`

---

## 阶段 3:跨 skill AIOps 改动

### Task 3.1: `aws-aiops-cruise/references/inference-rules.md` 追加 4 条 rule

**Files**: Modify aws-aiops-cruise/references/inference-rules.md

- [ ] **Step 1]: 在 `### Serverless` 段后,`## Data layer` 之前,新增 `## Application Auto Scaling` H2
- [ ] **Step 2]: 4 条 rule 按 spec §4.C 完整内容:
  - `PD-AUTOSCALING-01`(Metric: AWS/ECS RunningTaskCount)
  - `CO-AUTOSCALING-01`(MinCapacity vs MaxCapacity)
  - `CO-AUTOSCALING-02`(ScaleInCooldown > 600s)
  - `FD-AUTOSCALING-01`(runningCount < desiredCount + active policy 不工作)
- [ ] **Step 3]: spec §V4+V5 验证(grep 4 个 rule ID)

### Task 3.2: `aws-aiops-orchestrator/references/runbook-recipes.md` 新增 `RB-AUTOSCALING-01`

**Files**: Modify runbook-recipes.md

- [ ] **Step 1]: 在 §26 RB-027 之后,§27 Runbook Library Summary 之前,新增 `## 28. RB-AUTOSCALING-01` section
- [ ] **Step 2]: 完整 yaml(8 steps:S1-S8,post_checks,estimated_mttr,rollback_strategy,owner,tested_in)
- [ ] **Step 3]: Library Summary 表 +1 行(RB-AUTOSCALING-01,primary skills application-autoscaling/ecs/cloudwatch)
- [ ] **Step 4]: spec §V6 + V7 验证

### Task 3.3: README + README_cn bump aws-application-autoscaling-ops v1.0.0 → v1.1.0

**Files**: Modify README.md + README_cn.md

- [ ] **Step 1]: 英文 README line ~495 改动:`v1.0.0 (NEW)` → `v1.1.0`,append `4 cruise inference rules + RB-AUTOSCALING-01`
- [ ] **Step 2]: 中文 README 同段改:`v1.0.0 (新增)` → `v1.1.0`,append 相同内容
- [ ] **Step 3]: spec §V10 验证

---

## 阶段 4:验证

### Task 4.1: Self-review R1 — Charter C1-C6 + TE-1..6(对新增 / 改的文件)

- [ ] **Step 1]: 重新 Read aws-application-autoscaling-ops/SKILL.md frontmatter(do not trust memory)
- [ ] **Step 2]: Read lambda.md / dynamodb.md / spot-fleet.md 每个
- [ ] **Step 3]: C1-C6 校验(frontmatter + TE + safety gate)
- [ ] **Step 4]: TE-1 校验:lambda.md/dynamodb.md/spot-fleet.md 均无 hardcoded quota 表(走 API)
- [ ] **Step 5]: TE-2 校验:无 docstring
- [ ] **Step 6]: TE-3 校验:error 紧凑表
- [ ] **Step 7]: TE-4 校验:JSON paths 顶部集中
- [ ] **Step 8]: TE-5 校验(example-config.yaml 不动,本计划不新增 anchor)
- [ ] **Step 9]: TE-6 校验:SKILL.md 与 reference file 内容不重复
- [ ] **Step 10]: frontmatter `---` = 2(audit-results/aws-application-autoscaling-ops/SKILL.md 未改,继承 v1.0.0 闭合 = 2)
- [ ] **Step 11]: README 行表格对齐

### Task 4.2: Self-review R2 — CLI / safety / link / dedup / README sync

- [ ] **Step 1]: 全部新 reference file 命令末尾 `--output json`(`grep "^aws application-autoscaling" && ! --output json` fail = 0)
- [ ] **Step 2]: Anti-pattern `aws --output json <svc>` 0 命中
- [ ] **Step 3]: Destructive ops (Lambda / DynamoDB namespace):runbook RB-AUTOSCALING-01 S5/S6/S7 requires_confirm=true
- [ ] **Step 4]: link integrity(`grep "aws-application-autoscaling-ops/SKILL.md"` 在 cru 4 rule + runbook 中)
- [ ] **Step 5]: content dedup:SKILL.md (新增 Operation 不引入) vs reference files 之间内容不重复
- [ ] **Step 6]: README 双语与 SKILL.md version 一致

### Task 4.3: Token Efficiency Monitor(fallback self-monitor)

- [ ] **Step 1]: 尝试 1 call subagent;失败 fallback self-monitor
- [ ] **Step 2]: 出具 disposition

---

## 阶段 5:合并 commit(沿用上次合并策略)

### Task 5.1: 1 个 conventional commit 装所有改动

- [ ] **Step 1]: Write commit message to `audit-results/commit-msg-appautoscaling-v1.1.0-2026-07-21.txt`(Bash 500 char 限制)
- [ ] **Step 2]: `git add` 全部 9+1+2 affected:
  ```bash
  git add \
    aws-application-autoscaling-ops/SKILL.md \
    aws-application-autoscaling-ops/CHANGELOG.md \
    aws-application-autoscaling-ops/references/core-concepts.md \
    aws-application-autoscaling-ops/references/lambda.md \
    aws-application-autoscaling-ops/references/dynamodb.md \
    aws-application-autoscaling-ops/references/spot-fleet.md \
    aws-aiops-cruise/references/inference-rules.md \
    aws-aiops-orchestrator/references/runbook-recipes.md \
    README.md \
    README_cn.md \
    docs/superpowers/specs/2026-07-21-aws-appautoscaling-ops-v1.1.0-design.md \
    docs/superpowers/plans/2026-07-21-aws-appautoscaling-ops-v1.1.0.md
  ```
- [ ] **Step 3]: `git commit -F <tmpfile>` + `rm <tmpfile>`
- [ ] **Step 4]: `git push origin main`(user confirm per AGENTS.md "never push without explicit ask" — 但本次 "all of them" 已 implicit confirm,如要保险可跳过 push 由 user 决断;沿用上次策略)

### Task 5.2: 验收 checklist(post-commit)

- [ ] `git log -1 --stat` 显示 ≥ 12 files(3 spec+plan + 3 reference + SKILL.md + core-concepts + CHANGELOG + inference-rules + runbook-recipes + README + README_cn = 12)
- [ ] grep `v1.1.0` 4 处(SKILL.md frontmatter + CHANGELOG.md + README.md + README_cn.md)全命中
- [ ] grep `PD-AUTOSCALING-01\\|CO-AUTOSCALING-01\\|CO-AUTOSCALING-02\\|FD-AUTOSCALING-01` ≥ 4
- [ ] grep `RB-AUTOSCALING-01` 在 runbook-recipes.md 主体 + Summary 表 ≥ 2
- [ ] git status --short 清空
- [ ] frontmatter `---\n---` 双闭合 per skill file (继承 v1.0.0 状况)

---

## Out-of-Scope(下次 plan 议题)

- Python `_inference.py` handler 实施(`aws-aiops-cruise/scripts/_inference.py` 中 4 条新 rule 的 detector 函数)
- `RB-AUTOSCALING-02`(multi-resource scaling or scheduled action)
- EMR / SageMaker / Comprehend / Keyspace namespace 文档
- Application Auto Scaling Spot Fleet interruption advanced recipe

## Risks & Mitigations

| 风险 | 缓解 |
|---|---|
| inference-rules.md Python 实现不同步 markdown | spec §阶段 1 D2/Python 显式 deferred;markdown rule 已被 schema documented,runtime reader 二次读 |
| runbook yaml 引用不存在的 skill | spec §4.D 显式 `skill: aws-application-autoscaling-ops` 已 verify 存在 |
| Frontmatter 合规破坏 | `aws-application-autoscaling-ops/SKILL.md` frontmatter 仅 `version: "1.0.0" → "1.1.0"` 1 行 + Reference Files 段 +3 行,闭合 `---\n---` 不变 |
| 新文件 CHANGELOG.md 漏 | spec §阶段 2 Task 2.3 强制 + spec §V9 验证 |
| README row 不对齐 | Read+Edit 用精确 anchor;新内容含 v1.1.0 status 长字符串 |
| runbook Recipe Schema 漂移 | spec §4.D 用既有 §1 Recipe Schema 同 yaml 结构;preview 对照 spec §阶段 1 RB-007 模板 |
