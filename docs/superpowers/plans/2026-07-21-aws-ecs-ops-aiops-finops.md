# aws-ecs-ops AIOps+FinOps 闭环补齐 — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal**: 在不破坏 `aws-ecs-ops` v1.0.0 CRUD 语义 + Safety gate 的前提下,补齐 AIOps Container Insights 检测信号 + Fargate Spot / Cost Optimizer FinOps 操作 + 跨 skill FinOps delegate 链。

**Spec**: `docs/superpowers/specs/2026-07-21-aws-ecs-ops-aiops-finops-design.md`

**Tech Stack**: Markdown(SKILL.md / references),AWS CLI v2(命令示例),boto3(SDK 示例),YAML(`assets/example-config.yaml` anchor 复用)。

**Out-of-Scope** (ADR defer): 新建 `aws-application-autoscaling-ops` skill;ECS-SPOT-01 inference rule。

---

## 阶段 0:准备(pre-flight)

### Task 0.1: Pre-change CodeGraph sync

**Files**: 无文件改动

- [ ] **Step 1**: `codegraph sync .` — 增量索引,确保 explorer 反映当前仓库状态(spec §7 风险:"Pre-change CodeGraph sync mandatory")
- [ ] **Step 2**: `codegraph explore "aws-ecs-ops"` 确认 base 目录真实存在
- [ ] **Step 3**: `codegraph explore "aws-finops-core"` 确认 base 目录真实存在
- [ ] **Step 4**: 校验无 `aws-application-autoscaling-*` skill(grep 验证 ADR §3 D3):`ls aws-application-autoscaling-ops 2>&1` 应报错

---

## 阶段 1:aws-ecs-ops 改动(Fan-out 写文件,3 个子任务并行)

### Task 1.1: 改 aws-ecs-ops/SKILL.md

**Files**: Modify `aws-ecs-ops/SKILL.md`

- [ ] **Step 1**: 在 frontmatter `metadata` 块内 `last_updated` 字段**之前**插入 `provides` 字段,内容见 spec §4.A
- [ ] **Step 2**: 在 ## Overview 之后、`## Trigger & Scope` 之前新增 `## Common Container Insights metric path` 一节,内容包含 JSON paths:
  ```
  Cluster: aws.ecs.cluster.cpu.utilization, aws.ecs.cluster.memory.utilization
  Service: ECSServiceAverageCPUUtilization, ECSServiceAverageMemoryUtilization
  ```
- [ ] **Step 3**: 在 ## Variable Convention 表格末尾追加 5 行:
  ```
  | `{{user.opt_in_spot}}` | User input | Y/N; required for Capacity Provider Spot toggle |
  | `{{user.tag_project}}` | User input | Cost Allocation: Project tag value |
  | `{{user.tag_environment}}` | User input | Cost Allocation: Environment tag value |
  | `{{user.tag_cost_center}}` | User input | Cost Allocation: CostCenter tag value |
  | `{{output.cluster_capacity_providers}}` | Last API response | `.cluster.capacityProviders` |
  ```
- [ ] **Step 4**: 在 `Operation: Create Service` 的 Execute — CLI 段(`aws ecs create-service` 命令)增加 `--tags Key={{user.tag_project}},Value={{user.tag_project}} Key={{user.tag_environment}},Value={{user.tag_environment}} Key=ManagedBy,Value=aiops`(同一行接续,保持 `--output json` 在末尾)
- [ ] **Step 5**: 在 `Operation: Register Task Definition` Execute — CLI 段(`aws ecs register-task-definition` 命令)的 `--container-definitions` 之后(同一行接续)增加 `--tags Key={{user.tag_project}},Value={{user.tag_project}} Key={{user.tag_environment}},Value={{user.tag_environment}} Key=ManagedBy,Value=aiops`
- [ ] **Step 6**: 在 `Operation: Delete Cluster` 与 `Operation: Deregister Task Definition` 之间**新增** `### Operation: Update Capacity Providers`,完整 4 段(Pre-flight/Execute CLI/Execute SDK/Validate)+ Recover,内容:
  - Pre-flight: require `{{user.opt_in_spot}}=Y` to enable FARGATE_SPOT weight
  - Execute — CLI: `aws ecs put-cluster-capacity-providers --cluster {{user.cluster_name}} --capacity-providers capacityProvider=[{name=FARGATE,weight=20,base=20},{name=FARGATE_SPOT,weight=80,base=0}] --output json`
  - Execute — SDK: `ecs.put_cluster_capacity_providers(...)`
  - Validate: describe-clusters 回读 `.cluster.capacityProviders`
  - 警告:Spot 中断 AIOps 信号见 references/cost-optimization.md
- [ ] **Step 7**: ## Reference Files 表格新增 2 行:
  ```
  - [Cost Optimization](references/cost-optimization.md)
  - [Deployment Health](references/deployment-health.md)
  ```
- [ ] **Step 8**: frontmatter 完整性校验:`awk '/^---$/{c++; if(c==2)exit} c==1' aws-ecs-ops/SKILL.md | head -1` 应输出 `---`(无 stray)
- [ ] **Step 9**: spec §6 V1/V2/V3/V4 grep 验证
- [ ] **Step 10**: commit `git commit -m "docs(ecs-ops): AIOps signals + Fargate Spot + tag governance"`

### Task 1.2: 改 aws-ecs-ops/references/aws-cli-usage.md

**Files**: Modify `aws-ecs-ops/references/aws-cli-usage.md`

- [ ] **Step 1**: 在 `## Commands` 段尾(Stop task 命令之后)新增:
  ```
  # Capacity Providers (Fargate Spot)
  aws ecs put-cluster-capacity-providers --cluster "{{user.cluster_name}}" --capacity-providers capacityProvider=[{name=FARGATE,weight={{user.fargate_weight|default(20)}},base={{user.fargate_base|default(20)}}},{name=FARGATE_SPOT,weight={{user.spot_weight|default(80)}},base={{user.spot_base|default(0)}}}] --output json

  # Tags
  aws ecs tag-resource --resource-arn "{{output.cluster_arn}}" --tags Key={{user.tag_project}},Value={{user.tag_project}} Key={{user.tag_environment}},Value={{user.tag_environment}} Key=ManagedBy,Value=aiops --output json

  # Force new deployment
  aws ecs update-service --cluster "{{user.cluster_name}}" --service "{{user.service_name}}" --force-new-deployment --output json
  ```
- [ ] **Step 2]: spec §6 V/V8 grep 验证(本次不要求新增 ifiled count,作 forward-compat 锚)
- [ ] **Step 3]: 无 commit(纳入 Task 1.1 合并 commit)

### Task 1.3: 改 aws-ecs-ops/references/troubleshooting.md

**Files**: Modify `aws-ecs-ops/references/troubleshooting.md`

- [ ] **Step 1**: Error Table 末尾追加 6 条:
  ```
  | `SpotInterruption` | Fargate Spot was reclaimed; consider ↑ FARGATE weight or migrate to on-demand |
  | `EssentialContainerExited` | App container exit non-zero; check container logs in CloudWatch Logs |
  | `CannotPullContainerError` | Image pull failed; verify ECR perms + NAT/VPC endpoint + image URI |
  | `ResourceInitializationFailed` | ENI/EBS init failed; check VPC + IAM execution role |
  | `Task stopped due to OOM` | Memory limit too low; raise `memory` in task def + verify JVM heap settings |
  | `TimeoutError` | Stop task timeout exceeded; raise `--stop-timeout` on ECS container agent |
  ```
- [ ] **Step 2**: 在 `### Service deployment failing` 子段下追加:
  ```
  ### Deployment circuit breaker tripped
  - `deployments[0].rolloutState == "FAILED"` → see references/deployment-health.md
  - Inspect `service.events[]` for `Service deployment failed: ...` message
  ```
- [ ] **Step 3]: 验 line count ≥ 8 条 in Error Table(spec V7)
- [ ] **Step 4]: 无 commit(纳入 Task 1.4 合并 commit,统一 ECS Ops 一次提交)

### Task 1.4: 新建 aws-ecs-ops/references/cost-optimization.md

**Files**: Create `aws-ecs-ops/references/cost-optimization.md`(~80 lines target)

- [ ] **Step 1**: 文件创建,6 H2 块:
  - `## Fargate Spot` — 解释 capacity provider + weight 配比 + Spot 中断 vs cost 节省算式 + 引用 Operation: Update Capacity Providers
  - `## Compute Optimizer` — `aws compute-optimizer get-ecs-service-recommendations` + "1 call/day max" 标注
  - `## Savings Plans` — `aws ce get-savings-plans-coverage` 模板 + 覆盖 25% 折扣机会说明 + 不在本 skill 范围购买
  - `## Idle Service Discovery` — `aws ecs list-services --query` + jq 找 `desiredCount=0 && runningCount=0` 服务
  - `## VPC Endpoint (NAT Cost)` — 推荐 ECR / CloudWatch Logs / S3 Gateway Endpoint,贴 cli `aws ec2 create-vpc-endpoint` 模板
  - `## Tag Governance` — 必填 Tag 列表 + `--tags` 模板(转链 SKILL.md)
- [ ] **Step 2]: spec §6 V5 grep 验证 6 个 H2 块
- [ ] **Step 3]: commit `git commit -m "docs(ecs-ops): add cost-optimization reference (Fargate Spot / Compute Optimizer / SP / Idle / Gateway Endpoint / tag governance)"`

### Task 1.5: 新建 aws-ecs-ops/references/deployment-health.md

**Files**: Create `aws-ecs-ops/references/deployment-health.md`(~50 lines target)

- [ ] **Step 1**: 文件创建,3 H2 块:
  - `## Deployment Circuit Breaker` — `enable: true/false` in service definition + `rollback: enable/fail` 决策
  - `## rolloutState Diagnostics` — `IN_PROGRESS` / `FAILED` / `COMPLETED` 各对应 inspection 命令(`describe-services` 查询 `deployments[].{rolloutState,taskDefinition,failureReason}`)
  - `## Deployment Alarms` — `aws cloudwatch put-metric-alarm` for `DeploymentRolloutAlarm`
- [ ] **Step 2]: spec §6 V6 grep 验证 3 个 H2 块
- [ ] **Step 3]: commit `git commit -m "docs(ecs-ops): add deployment-health reference (circuit breaker / rolloutState / alarms)"`

---

## 阶段 2:aws-finops-core 改动

### Task 2.1: 改 aws-finops-core/SKILL.md(frontmatter + Execution Flow)

**Files**: Modify `aws-finops-core/SKILL.md`

- [ ] **Step 1]: frontmatter `metadata.provides` 列表追加:
  ```
      - ecs-idle-service-discovery
      - ecs-fargate-rightsizing
      - ecs-fargate-spot-optimization
  ```
- [ ] **Step 2]: frontmatter `metadata.delegate` 列表追加:
  ```
      ecs-idle: aws-ecs-ops
      ecs-rightsizing: aws-ecs-ops
      ecs-fargate-spot: aws-ecs-ops
  ```
- [ ] **Step 3]: ## Execution Flow Pattern 段,`Idle Detection (delegate to base skills)` 子段内追加 3 行:
  ```
      ├─ ECS Service → aws-ecs-ops  (desiredCount=0 & runningCount=0 for 7d)
      ├─ Fargate Right-Sizing      → aws-ecs-ops  (Compute Optimizer ECS recommendations)
      └─ Fargate Spot              → aws-ecs-ops  (capacity provider weight tuning)
  ```
- [ ] **Step 4]: spec §6 V8/V9 grep 验证
- [ ] **Step 5]: frontmatter 合规性 `awk` 校验
- [ ] **Step 6]: commit `git commit -m "docs(finops): add ECS delegate chain (idle / rightsizing / spot)"`

---

## 阶段 3:验证(Gate 顺序:Monitor → R1 → R2)

### Task 3.1: Token Efficiency Monitor 子代理审查

**Files**: 无文件改动(只读审查)

- [ ] **Step 1]: 调起 Agent 子代理(CodeReview 类型),prompt 包含:
  - 改动文件清单:`aws-ecs-ops/SKILL.md`, `aws-ecs-ops/references/{aws-cli-usage,troubleshooting,cost-optimization,deployment-health}.md`, `aws-finops-core/SKILL.md`
  - 三-way disposition 要求(OPTIMAL / REFACTOR-NOW / ACCEPT-SUBOPTIMAL)
  - 长生命周期豁免: README.md / AGENTS.md / SKILL.md 默认 ACCEPT-SUBOPTIMAL
- [ ] **Step 2]: 按 Monitor disposition 执行:REFACTOR-NOW 直接改,ACCEPT-SUBOPTIMAL 记录理由
- [ ] **Step 3]: 记录 disposition + 理由到 progress.md(spec §7 风险"Long-lived asset exemption")

### Task 3.2: Self-review R1(Charter C1-C6 + TE-1..6 + frontmatter)

**Files**: 无文件改动(读 + grep 校验)

对 `aws-ecs-ops/SKILL.md` 与 `aws-finops-core/SKILL.md` 各跑 R1:

- [ ] **Step 1]: R1.1 — 重新 Read `aws-ecs-ops/SKILL.md`(do not trust memory)
- [ ] **Step 2]: R1.2 — Charter C1(frontmatter with name/description/license/compatibility/metadata)+ C2(Trigger & Scope 双段)+ C3(Variable Convention 表只用 `{{env.*}}` / `{{user.*}}` / `{{output.*}}`)+ C4(Pre-flight→Execute→Validate→Recover)+ C5(显式 confirmation 包含 delete-service 之外的本新操作)+ C6(`## Quality Gate (GCL)` 段);失败 → `[CHARTER VIOLATION] C{n}: {reason}` auto-fix
- [ ] **Step 3]: R1.3 — Token Efficiency TE-1..6(TE-1 无 hardcoded 版本/价目表;TE-2 boto3 无 docstring;TE-3 compact error table;TE-4 JSON paths 顶部集中;TE-5 YAML anchor;TE-6 flows only in SKILL.md)
- [ ] **Step 4]: R1.4 — frontmatter single `---` open + close 校验
- [ ] **Step 5]: R1.5 — delegation references 真实存在(`codegraph explore aws-ecs-ops` / `aws-finops-core`)
- [ ] **Step 6]: R1.6 — destructive ops(`delete-service` / `delete-cluster` / `deregister-task-definition` / `put-cluster-capacity-providers` if reducing FARGATE base)各自有 confirmation
- [ ] **Step 7]: R1.7 — JSON paths 与 `references/aws-cli-usage.md` Common JSON Paths 块一致
- [ ] **Step 8]: 对 `aws-finops-core/SKILL.md` 重复 Step 1-7

若 Step 2-7 任一失败:在文件里 auto-fix,重跑直到清洁

### Task 3.3: Self-review R2(Content / CLI / safety / link / dedup / README sync)

- [ ] **Step 1]: R2.1 — 新建命令全部 CLI 验证(对比仓库内其它 skill command format);无 `aws --output json <svc>` 错位
- [ ] **Step 2]: R2.2 — Error codes 表与 AWS 官方文档常见错误对齐(grep `Exception` 关键词)
- [ ] **Step 3]: R2.3 — safety gates(C5 mandate)对所有写操作(Capacity Provider 视作"可能影响 running tasks"加入 confirmation)
- [ ] **Step 4]: R2.4 — link integrity(`grep -rn "\](\.\./"`)无断链
- [ ] **Step 5]: R2.5 — content dedup(`references/cost-optimization.md` 内容不与 `aws-eks-ops/references/cost-optimization.md` 重复 — 复用语义对齐既存模板即可,不要直接复制)
- [ ] **Step 6]: R2.6 — README.md / README_cn.md **不需更新**(本次不动版本号)

### Task 3.4: 最终汇总

- [ ] **Step 1]: 输出 message:
  ```
  [OK] aws-ecs-ops v1.0.0 (no version bump) — N files touched
       M aws-ecs-ops/SKILL.md
       M aws-ecs-ops/references/aws-cli-usage.md
       M aws-ecs-ops/references/troubleshooting.md
       A aws-ecs-ops/references/cost-optimization.md
       A aws-ecs-ops/references/deployment-health.md
       M aws-finops-core/SKILL.md
       - Token Monitor: <disposition + reason>
       - Self-review R1: <C1..C6/TE-1..6 result per skill>
       - Self-review R2: <F1..F6 result>
       - ADR defer: aws-application-autoscaling-ops
       - Spec V1..V13: <PASS/FAIL>
  ```

---

## ADR defer:aws-application-autoscaling-ops

**日期**: 2026-07-21
**触发**: 本次设计 D3 决策。
**问题**: 仓库内无任何 `aws-application-autoscaling` skill,而 ECS Service Auto Scaling 是 AIOps auto-heal + FinOps 弹性计费的同一个杠杆。
**决策**: 本 MVP 不新建/合入 skill,仅在 `aws-ecs-ops/references/cost-optimization.md` 留 cross-reference "see aws-application-autoscaling-ops (TODO: not yet in repo)"。
**下次 plan 议题**:
- 选项 A:新建 `aws-application-autoscaling-ops` (L1 skill,scope 仅 ECS,DynamoDB / Lambda / Spot Fleet 等后续扩张)
- 选项 B:把 EC2 ASG + Application Auto Scaling 合并到一个 skill(`aws-autoscaling-and-appautoscaling-ops`),破坏现有命名
- 选项 C:把 App Auto Scaling 加到 `aws-autoscaling-ops` 现有 skill(scope 扩张),做 compatibility note
**选择依据**: 需用户决策 + charter 兼容性 review。本次不阻塞。
