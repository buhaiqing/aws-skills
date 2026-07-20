# aws-application-autoscaling-ops 创建 — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal**: 新建 L1 skill `aws-application-autoscaling-ops`(MVP scope = ECS-only),打通 AIOps auto-heal + FinOps 弹性计费的同一个杠杆点,补齐 aws-finops-core 与 aws-aiops-orchestrator 的 cross-skill delegate 链。

**Spec**: `docs/superpowers/specs/2026-07-21-aws-appautoscaling-ops-design.md`

**Tech Stack**: Markdown(SKILL.md + references),AWS CLI v2 + boto3,YAML(`example-config.yaml` anchor 复用),shared prompt skeleton(`aws-skill-generator/references/prompt-skeletons.md`)。

**Out-of-Scope** (后续 plan 议题): `references/lambda.md` / `references/dynamodb.md`;`aws-aiops-cruise` CO-AUTOSCALING-01 inference rule;AIOps runbook RB-AUTOSCALING-01;`CHANGELOG.md`(本新建无历史)。

---

## 阶段 0:准备

### Task 0.1: Pre-change CodeGraph sync

- [ ] **Step 1**: `codegraph sync .` — 增量索引
- [ ] **Step 2**: `codegraph explore "aws-application-autoscaling-ops"` — 应报错(目录不存在,确认起点 clean)
- [ ] **Step 3**: `codegraph explore "aws-ecs-ops"` + `aws-finops-core` + `aws-cloudwatch-ops` + `aws-cloudtrail-ops` — 全部存在,确认 cross_skill_deps 引用的目录真实
- [ ] **Step 4**: 测试一次 subagent infra(1 call): 若仍 fail model unreachable,准备 fallback 走主 agent 串行

---

## 阶段 1:新建 skill scaffolding

### Task 1.1: 创建 `aws-application-autoscaling-ops/SKILL.md`

**Files**: Create `aws-application-autoscaling-ops/SKILL.md`(target ~200 lines)

- [ ] **Step 1**: 文件创建,frontmatter 严格按 spec §4.A(28 个 metadata 字段)
- [ ] **Step 2**: Markdown body 顺序遵循 `aws-skill-template.md`(已 pre-read):
  ```
  ## Layering Contract (type / provides / delegate)
  ## Overview
  ## Trigger & Scope (SHOULD Use When / SHOULD NOT Use When)
  ## Variable Convention
  ## Config File Placeholders
  ## Execution Flow Pattern (Pre-flight → Execute → Validate → Recover)
  ## Operations Index  (5+ ops listed)
  ## Reference Files
  ## Token Efficiency Guidelines (TE-1..TE-6)
  ## Quality Gate (GCL)
  ## AIOps Delegate Contract
  ```
- [ ] **Step 3**: 写 5 个 operation(Pre-flight + Execute CLI + Execute boto3 + Validate + Recover):
  - `Operation: Register Scalable Target`  (write)
  - `Operation: Deregister Scalable Target` (destructive; `confirm=DEREGISTER_SCALABLE_TARGET <resource_id>`)
  - `Operation: Put Scaling Policy` (write; mutation; TargetTracking on `ECSServiceAverageCPUUtilization`)
  - `Operation: Delete Scaling Policy` (destructive; `confirm=DELETE_SCALING_POLICY <resource_id>`)
  - `Operation: Tag Resource` (write; non-destructive but state-changing)
  - `Operation: Describe Scalable Targets` (read)
  - `Operation: Describe Scaling Policies` (read)
- [ ] **Step 4**: Token Efficiency 段声明 6 条 TE rules + GCL Quality Gate 段说明
- [ ] **Step 5**: 末尾加 CADL line: `> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。`
- [ ] **Step 6]: 验证 frontmatter:`awk '/^---$/{c++; if(c==2)exit} c==1' SKILL.md | head -1` 应为 `---`
- [ ] **Step 7]: spec V1-V6 grep 验证

### Task 1.2: 创建 5 个 reference 文件

**Files**: Create 5 个 references file (~ 250 lines total target)

- [ ] **Step 1**: `references/aws-cli-usage.md`(~ 70 lines):
  - `## Common JSON Paths` 顶部集中(ServiceNamespace / ScalableDimension / ScalableTarget / ScalingPolicy)
  - 命令列表:`register-scalable-target` / `deregister-scalable-target` / `describe-scalable-targets` / `put-scaling-policy` / `delete-scaling-policy` / `describe-scaling-policies` / `tag-resource`
  - 所有命令末尾 `--output json`
  - ECS-specific 示例(`service-namespace ecs`, `resource-id service/<cluster>/<service>`, `scalable-dimension ecs:service:DesiredCount`)
- [ ] **Step 2**: `references/boto3-sdk-usage.md`(~ 60 lines):
  - `import boto3; client = boto3.client('application-autoscaling', region_name=...)`
  - 7 个 SDK 调用 pattern,inline comment,**无 docstring**(TE-2)
- [ ] **Step 3]: `references/core-concepts.md`(~ 50 lines):
  - 短表(≤ 5 rows): ECS ServiceNamespace × ScalableDimension (`ecs:service:DesiredCount`)
  - Stub sections for Lambda / DynamoDB with **明确 markdown comment**: `<!-- TODO: future plan reference/lambda.md -->`
  - Quota:`aws service-quotas get-service-quota --service-code application-autoscaling --quota-code L-...`
  - **不**硬编码版本/端口/状态表 — 全部 API command 主导(TE-1)
- [ ] **Step 4]: `references/troubleshooting.md`(~ 40 lines):
  - Error Table 8 条: `ObjectNotFoundException` / `LimitExceededException` / `ValidationException` / `ConcurrentUpdateException` / `FailedResourceAccessException` / `InternalServiceException` / `ThrottlingException` / `AccessDeniedException`
  - 1 行 per error
  - Polling limits / common issues 各 1 段
- [ ] **Step 5]: spec V11 验证:`wc -l SKILL.md` ≤ 200 lines

### Task 1.3: 创建 `references/rubric.md`(GCL rubric v1)

**Files**: Create `references/rubric.md`(~ 50 lines)

- [ ] **Step 1**: 写 5 维度 rubric(0 / 0.5 / 1 表格): Correctness / Safety / Idempotency / Traceability / Spec Compliance
- [ ] **Step 2]: Safety special cases:
  - `deregister-scalable-target` requires: target existed in last 24h + no active scaling policy + production safety gate
  - `delete-scaling-policy` requires: ensure service will fall back to manual state safely
- [ ] **Step 3]: Operation-specific overrides table:7 ops,列出 Correctness / Safety 详细规则
- [ ] **Step 4]: 末尾:`Reference: AWS rules A1-A10 from gcl-spec.md §8 (cross-skill reference; do not duplicate)`
- [ ] **Step 5]: 验证 spec V7

### Task 1.4: 创建 `references/prompt-templates.md`(shared skeleton specialization)

**Files**: Create `references/prompt-templates.md`(~ 35 lines)

- [ ] **Step 1]: file head: `# GCL Prompt Templates — aws-application-autoscaling-ops`
- [ ] **Step 2]: > Specialization of the shared skeleton: `[references/prompt-skeletons.md](../../aws-skill-generator/references/prompt-skeletons.md)`
- [ ] **Step 3]: Skill metadata table(7 placeholders from spec §4.A)
- [ ] **Step 4]: Hard rules block(8 bullets 引用 gcl-spec.md §8 A-id):
  ```
  - rule A10: sts get-caller-identity MUST be the first command in trace
  - rule A7: --region MUST match {{output.requested_region}}
  - rule A8: resource_id MUST be echoed back from describe-scalable-targets before deletion
  - rule A9: container environment variables / secrets MUST be masked
  - rule A11: deregister-scalable-target MUST verify no active scaling policy first
  - rule A12: put-scaling-policy with TargetTracking MUST validate ECS metric namespace
  - rule A16: tag-resource removing Production tag MUST require confirmation
  - delete-scaling-policy with active ECS service: MUST verify service has fallback capacity
  ```
- [ ] **Step 5]: Confirmation Strings 表:2 条(`deregister-scalable-target` / `delete-scaling-policy`)
- [ ] **Step 6]: Variable Convention deltas(只放 skill-specific,如 `{{user.service_namespace}}` / `{{user.scalable_dimension}}` / `{{user.resource_id_format}}`)
- [ ] **Step 7]: Changelog table 末尾(1.0.0 entry)
- [ ] **Step 8]: spec V8 验证

### Task 1.5: 创建 `assets/example-config.yaml`

**Files**: Create `aws-application-autoscaling-ops/assets/example-config.yaml`(~ 25 lines)

- [ ] **Step 1]: YAML anchors `&ecs-target` / `&ecs-policy-tracking` / `&ecs-policy-step`:
  ```yaml
  ecs_target_common: &ecs_target_common
    service_namespace: ecs
    scalable_dimension: ecs:service:DesiredCount
    resource_id: service/{{user.cluster_name}}/{{user.service_name}}
  
  ecs_target_tracking_50_cpu: &ecs_target_tracking_50_cpu
    <<: *ecs_target_common
    policy_type: TargetTrackingScaling
    target_value: 50
    predefined_metric_spec:
      predefined_metric_type: ECSServiceAverageCPUUtilization
    scale_out_cooldown: 60
    scale_in_cooldown: 300
  ```
- [ ] **Step 2]: 2 个具体 example: target tracking + step scaling
- [ ] **Step 3]: TE-5 验证:grep `&anchor` ≥ 1

### Task 1.6: 自我验证 scaffolding

- [ ] **Step 1]: `ls -la aws-application-autoscaling-ops/` 应有 6+ 文件(SKILL.md + 6 references + 1 assets)
- [ ] **Step 2]: `wc -l SKILL.md references/*.md assets/example-config.yaml` — 文件不全为 0 bytes
- [ **Step 3]: grep `TODO: future plan` references/core-concepts.md ≥ 1(mark stub for future extension)
- [ ] **Step 4]: `aws-application-autoscaling-ops/` 目录权限 / 不在 .gitignore(应 tracked)

---

## 阶段 2:cross-skill 改动

### Task 2.1: 改 `aws-finops-core/SKILL.md`(delegate + provides)

- [ ] **Step 1]: frontmatter `metadata.provides` 列表,在 `ecs-fargate-spot-optimization` 之后追加:
  ```yaml
      - app-autoscaling-ecs-targets
      - app-autoscaling-policies
  ```
- [ ] **Step 2]: frontmatter `metadata.delegate` 列表,在 `ecs-fargate-spot: aws-ecs-ops` 之后追加:
  ```yaml
      app-autoscaling-ecs-targets: aws-application-autoscaling-ops
      app-autoscaling-policies: aws-application-autoscaling-ops
  ```
- [ ] **Step 3]: spec V9 grep 验证:`grep -c "app-autoscaling" aws-finops-core/SKILL.md` ≥ 5(provides 2 + delegate 2 + Execution Flow 已有 1 → 至少 5 处提及)

### Task 2.2: 改 `aws-ecs-ops/references/cost-optimization.md`(ADR defer stub)

- [ ] **Step 1]: line 49 (the `(TODO: not yet in repo)` line) → 替换为有效 cross-ref:
  ```markdown
  - See [aws-application-autoscaling-ops/SKILL.md](../../aws-application-autoscaling-ops/SKILL.md) for
    target tracking / step scaling / scheduled actions on `ecs:service:DesiredCount`
    (compounds the FinOps savings in this file with AIOps auto-heal).
  ```
- [ ] **Step 2]: spec V12 grep 验证:`grep "TODO: not yet in repo" aws-ecs-ops/references/cost-optimization.md` 必须 0 命中

### Task 2.3: 改 `aws-ecs-ops/CHANGELOG.md`(加 1.2.0 entry)

- [ ] **Step 1]: 在 `## [1.1.0] - 2026-07-21` 之前插入:
  ```markdown
  ## [1.2.0] - 2026-07-21
  
  ### Changed
  - `references/cost-optimization.md` ADR defer stub (line 49) replaced with valid
    cross-reference to `aws-application-autoscaling-ops` (new L1 skill shipped same day,
    per ADR defer § spec plan 2026-07-21-aws-ecs-ops-aiops-finops.md).
  ```
- [ ] **Step 2]: 在 frontmatter `version` 字段改为 `"1.2.0"`,`last_updated` 改为 `"2026-07-21"`
- [ ] **Step 3]: grep v1.2.0 一致性

### Task 2.4: 改 README.md Existing Skills 表 +1 行

- [ ] **Step 1]: 在 line 495(`aws-ecs-ops` 行)之后插入新行:
  ```markdown
  | aws-application-autoscaling-ops | Application Auto Scaling (cross-service scaler) | ✅ **Complete v1.0.0 (NEW)** — ECS Service Auto Scaling (target tracking / step scaling / scheduled actions on `ECSServiceAverageCPUUtilization`); FinOps delegate + AIOps self-heal |
  ```
- [ ] **Step 2]: spec V10 grep 验证:grep `aws-application-autoscaling-ops` README.md ≥ 1

### Task 2.5: 改 README_cn.md 同段 +1 行(中文版)

- [ ] **Step 1]: 在 line 495(`aws-ecs-ops` 行)之后插入:
  ```markdown
  | aws-application-autoscaling-ops | Application Auto Scaling（跨服务 scaler） | ✅ **完成 v1.0.0 (新增)** — ECS Service Auto Scaling（target tracking / step scaling / scheduled actions，监测 `ECSServiceAverageCPUUtilization`）；委托给 aws-finops-core 并接入 AIOps 自愈 |
  ```
- [ ] **Step 2]: spec V10 grep 验证

---

## 阶段 3:验证

### Task 3.1: Self-review R1(Charter C1-C6 + TE-1..6 + frontmatter,对新建 skill `aws-application-autoscaling-ops`)

- [ ] **Step 1]: 重新 Read SKILL.md(do not trust memory)
- [ ] **Step 2]: C1: frontmatter 含 name / description / license / compatibility / metadata
- [ ] **Step 3]: C2: Trigger & Scope 双段 SHOULD Use / SHOULD NOT Use
- [ ] **Step 4]: C3: Variable Convention 仅 `{{env.*}}` / `{{user.*}}` / `{{output.*}}`
- [ ] **Step 5]: C4:Pre-flight → Execute → Validate → Recover 每个 operation
- [ ] **Step 6]: C5: destructive ops 有 confirmation(`deregister-scalable-target` / `delete-scaling-policy`)
- [ ] **Step 7]: C6: TE-1..TE-6(TE-1 无硬编码表; TE-2 boto3 无 docstring; TE-3 紧凑 error table; TE-4 JSON paths 集中; TE-5 YAML anchors; TE-6 flows only in SKILL.md)
- [ ] **Step 8]: frontmatter single `---` open + close
- [ ] **Step 9]: cross_skill_deps 目录真实存在(`codegraph explore` 验证)
- [ ] **Step 10]: destructive ops 有 confirmation token(grep `confirm=`)
- [ ] **Step 11]: JSON paths 与 `references/aws-cli-usage.md` Common JSON Paths 块一致

### Task 3.2: Self-review R2(Content / CLI / safety / link / dedup / README sync)

- [ ] **Step 1]: 新建命令全部 CLI 验证(无 `aws --output json <svc>` 错位 anti-pattern)
- [ ] **Step 2]: Error codes 表与 AWS 官方对齐
- [ ] **Step 3]: Safety gates 对所有 destructive ops
- [ ] **Step 4]: link integrity(`grep -rn "\](\.\./"` 无断链)
- [ ] **Step 5]: content dedup(SKILL.md 与 references 不重复)
- [ ] **Step 6]: README/CHANGELOG 与新 skill 一致
- [ ] **Step 7]: `aws-ecs-ops/CHANGELOG.md` 1.2.0 entry 不与 1.1.0 重复

### Task 3.3: Token Efficiency Monitor(尝试 subagent,失败则 self-monitor)

- [ ] **Step 1]: 调起 1 个 subagent(CodeReview 类型),prompt 包含改动清单 + 三选一 disposition 要求
- [ ] **Step 2]: 失败时 fallback to self-monitor,参考上次 plan 的 ACCEPT-SUBOPTIMAL 模板
- [ ] **Step 3]: 记录 disposition 到 message

---

## 阶段 4:合并 commit

### Task 4.1: 1 个 conventional commit 装所有改动(沿用上次合并策略)

- [ ] **Step 1]: `git add` 全部新 + 改文件:
  ```bash
  git add \
    aws-application-autoscaling-ops/ \
    aws-finops-core/SKILL.md \
    aws-ecs-ops/references/cost-optimization.md \
    aws-ecs-ops/CHANGELOG.md \
    aws-ecs-ops/SKILL.md \
    README.md \
    README_cn.md
  ```
  - 注:`aws-ecs-ops/SKILL.md` 上 frontmatter version `1.1.0 → 1.2.0` 这个也得 commit(同 SKILL.md/frontmatter change)。

Wait re-think — `aws-ecs-ops/SKILL.md` version 没改;只在 `CHANGELOG.md` 1.2.0 entry 有提及 `version: 1.1.0 → 1.2.0`。这是我 plan 的不一致点。

3 个选择:
- (A) 同步 bump `aws-ecs-ops/SKILL.md` frontmatter version 1.1.0 → 1.2.0
- (B) 仅 CHANGELOG entry 写 1.2.0 但 frontmatter 仍是 1.1.0(违反 project_information_memory "升级时需同步更新 SKILL.md version 字段")
- (C) 不 bump,改 CHANGELOG entry 名称为 "modified entry under v1.1.0"

按 memory 引用的语义:"项目版本号通过 SKILL.md 文件中的 version 字段定义,升级时需同步更新 CHANGELOG.md" — 必须同步。**采用 A**。

- [ ] **Step 1(revised)]: `aws-ecs-ops/SKILL.md` frontmatter `version: "1.1.0" → "1.2.0"` + `last_updated: "2026-07-21" → "2026-07-21"`(已经是今天)
- [ ] **Step 2]: `git add` 全部文件
- [ ] **Step 3]: `git commit -F <temp_commit_msg_file>` 沿用上次 temp-file 模式(Bash 500 char 限制)

### Task 4.2: 验收 checklist(post-commit)

- [ ] `git log -1 --stat` 显示所有新 + 改文件
- [ ] grep `"1.0.0"` 4 处一致(SKILL.md / aws-application-autoscaling-ops/CHANGELOG 不存在 / README.md / README_cn.md)
- [ ] grep `"1.2.0"` 一致(aws-ecs-ops/SKILL.md frontmatter + CHANGELOG.md)
- [ ] `git status --short` post-commit 清空
- [ ] 代码 frontmatter `---` = 2 per file

---

## Out-of-Scope(本 plan 不动)

- 新增 `references/lambda.md` / `references/dynamodb.md` / `references/spot-fleet.md` / `references/emr.md` / `references/sagemaker.md`
- `aws-aiops-cruise` 新增 CO-AUTOSCALING-01 inference rule
- AIOps runbook RB-AUTOSCALING-01
- `aws-application-autoscaling-ops/CHANGELOG.md`(本 plan 不建,首次 commit 无历史)
- `aws-ecs-ops/SKILL.md` frontmatter `version` 进一步 bump 到 1.3.0(若下次 lambda/dynamo extension 落地可一次 bump)
- `aws-application-autoscaling-ops` 入 path-based detection rules(deferred)
- 不 push(用户后续决定)

## Risks & Mitigations

| 风险 | 缓解 |
|---|---|
| Charter C6 自动失效:硬编码 namespace table > 5 rows | core-concepts.md 仅放 ECS 的 1-3 row table,其它 stub-only with markdown 注释 |
| TE-6:SKILL.md 与 references 重复 | SKILL.md 仅 summary + Operation 高层;CLI/SDK detail 在 references/ |
| cross_skill_deps 引用了不存在 skill | codegraph explore 验证 4 个目录 |
| GCL rubric 评审负担 | rubric.md 用 shared skeleton pattern,降低 boilerplate |
| subagent infra 不可用 | 主 agent 串行 |
| commit message 过长 | `git commit -F <tmpfile>` 模式沿用上次 |
| CHANGELOG.md 1.2.0 与 SKILL.md version 1.2.0 同步错位 | plan §4.1 Step 1 强制要求 SKILL.md frontmatter version 同步 bump |
