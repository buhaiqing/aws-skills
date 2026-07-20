# aws-aiops-cruise AIOps 后端完整化 (Cluster 1 of 3) — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal**: 把 8 ServiceNamespace 各配 3 条 AIOps inference rule(共 21 新 rule);在 `aws-aiops-cruise/runbooks/scripts/_inference.py` 实施 7 个 detect function(ECS 4 rule 已有 inline)。

**Spec**: `docs/superpowers/specs/2026-07-21-aws-aiops-cruise-appautoscaling-rules-design.md`

**Tech Stack**: Markdown(inference rules),Python 3.10+(_inference.py),AWS CloudWatch metric namespace docs。

**Out-of-Scope**: scheduled-actions.md / elasticache.md / kafka.md / appstream.md(plan B,C);runbook 增量(Spec §阶段 2 D3);frontmatter bump。

---

## 阶段 0 — Pre-change CodeGraph sync

- [ ] **Step 1**: `codegraph sync .` — 增量索引
- [ ] **Step 2**: `codegraph explore "aws-aiops-cruise"` — 确认目录 + `_inference.py` 路径

## 阶段 1 — `inference-rules.md` append 8 sub-section × 3 rule

### Task 1.1 — Lambda sub-section(~ 50 lines)

- [ ] **Step 1**: SearchReplace anchor `## Application Auto Scaling`(既有 §)块尾 → 在此 H2 后 append `## Application Auto Scaling — 8 Namespaces` + Lambda H3 + 3 rule body
  - **insight**:既有 § Application Auto Scaling 仅一段描述 + 4 条 ECS rule。本计划在既有 H2 段内 append sub-H3 namespace sections,**不动既有 ECS 4 rule**
- [ ] **Step 2**: 验证 grep `FD-AUTO-LAMBDA-01` / `PD-AUTO-LAMBDA-01` / `CO-AUTO-LAMBDA-01` 各 1 命中

### Task 1.2 — DynamoDB sub-section
- [ ] **Step 1]: append `### DynamoDB (Table + Index)` H3 + 3 rule(FD/PD/CO)

### Task 1.3 — Spot Fleet sub-section
- [ ] **Step 1]: append `### Spot Fleet (ec2:spot-fleet-request)` + 3 rule

### Task 1.4 — EMR sub-section
- [ ] **Step 1]: append `### EMR (elasticmapreduce)` + 3 rule

### Task 1.5 — SageMaker sub-section
- [ ] **Step 1]: append `### SageMaker (sagemaker:variant)` + 3 rule

### Task 1.6 — Comprehend sub-section
- [ ] **Step 1]: append `### Comprehend (comprehend:document-classifier)` + 3 rule

### Task 1.7 — Keyspace sub-section
- [ ] **Step 1]: append `### Keyspace (cassandra:table)` + 3 rule

### Task 1.8 — spec §V1-V6 验证

- [ ] **Step 1]: grep `AUTO-` 总 rule ID 命中 = 21(4 existing ECS + 21 新)
- [ ] **Step 2]: grep `aws-application-autoscaling-ops` delegate check ≥ 21 + (ECS 4)
- [ ] **Step 3]: grep `<DOMAIN>-AUTO-<NS>-<NUMBER>` 命名格式严格

## 阶段 2 — `_inference.py` 实施 7 detect function

### Task 2.1 — Read 现有 file 模板

- [ ] **Step 1]: Read `aws-aiops-cruise/runbooks/scripts/_inference.py` 全文(理解 inline pattern)
- [ ] **Step 2]: Identify `apply_chain_inference` 主函数位置 + 既有 ECS rule implement pattern

### Task 2.2 — `detect_app_autoscaling_lambda` (~ 30 lines)

- [ ] **Step 1]: 检测 Signals["Lambda"] 资源;condition: `ProvisionedConcurrencyUtilization > 80` 或 `ConcurrentExecutions == ReservedConcurrency`
- [ ] **Step 2]: emit 3 个 incident(rule_id: `FD-AUTO-LAMBDA-01` / `PD-AUTO-LAMBDA-01` / `CO-AUTO-LAMBDA-01`)
- [ ] **Step 3]: 调用 `make_incident(*, ..., rule_id=...)` from `_shared.py`
- [ ] **Step 4]: 严格 no docstring(TE-2),inline comment only

### Task 2.3 — `detect_app_autoscaling_dynamodb` (~ 35 lines)
- [ ] **Step 1]: 检测 Signals["DynamoDB"] 资源
- [ ] **Step 2]: 3 rule(throttle count / ProvisionedReadCapacityUtilization)emit

### Task 2.4 — `detect_app_autoscaling_spot_fleet` (~ 30 lines)
- [ ] **Step 1]: 检测 Signals["EC2SpotFleetRequest"];custom Spec 处理 Spot interruption rate

### Task 2.5 — `detect_app_autoscaling_emr` (~ 30 lines)
- [ ] **Step 1]: 检测 Signals["ElasticMapReduce"];isIdle / JobFlowCPUUtilization / apps pending

### Task 2.6 — `detect_app_autoscaling_sagemaker` (~ 35 lines)
- [ ] **Step 1]: 检测 Signals["SageMaker"];invocation 5XX / InvocationsPerInstance

### Task 2.7 — `detect_app_autoscaling_comprehend` (~ 30 lines)
- [ ] **Step 1]: 检测 Signals["Comprehend"];ThrottledInferenceException / InferenceRequestCount

### Task 2.8 — `detect_app_autoscaling_cassandra` (~ 30 lines)
- [ ] **Step 1]: 检测 Signals["Cassandra"];ProvisionedThroughputExceededException / ConsumedReadCapacityUnits

### Task 2.9 — Main function integrate

- [ ] **Step 1]: SearchReplace anchor `apply_chain_inference` 主函数末尾 → append 7 个 `detect_app_autoscaling_<ns>(signals, *, region=region, ...)` 调用
- [ ] **Step 2]: incidents.extend call for each detect function

### Task 2.10 — Python 验证

- [ ] **Step 1]: `cd aws-aiops-cruise && python3 -c "import sys; sys.path.insert(0, 'runbooks/scripts'); import _inference"` — 无 error
- [ ] **Step 2]: `python3 -m py_compile runbooks/scripts/_inference.py` — 无 syntax error

## 阶段 3 — Self-review R1+R2 + Monitor fallback

### Task 3.1 — R1(Charter + TE)

- [ ] **Step 1]: Read `inference-rules.md` 4 namespace sections(从 Lambda 到 Keyspace)
- [ ] **Step 2]: 每条 rule ID 命名严格 `<DOMAIN>-AUTO-<NS>-<NUMBER>`
- [ ] **Step 3]: 每条 rule 4 字段(Symptoms / Inference / Metrics / Fix path)齐
- [ ] **Step 4]: Fix path 必须 `aws-application-autoscaling-ops` delegate
- [ ] **Step 5]: Metric namespace 严格 AWS 官方(`AWS/Lambda` 等)
- [ ] **Step 6]: Python handler type hints + no docstring

### Task 3.2 — R2(CLI / safety / link / dedup / README sync)

- [ ] **Step 1]: audit markdown 不 anti-pattern
- [ ] **Step 2]: Python file consistency(无 unused import / 无 dead code)
- [ ] **Step 3]: 不动 `aws-application-autoscaling-ops/* + orchestrator/* + 其他 skill`

### Task 3.3 — Token Efficiency Monitor

- [ ] **Step 1]: 尝试 1 call subagent;失败 fallback self-monitor
- [ ] **Step 2]: ACCEPT-SUBOPTIMAL disposition

## 阶段 4 — 合并 commit + push

### Task 4.1 — Commit msg file

- [ ] **Step 1]: Write to `audit-results/commit-msg-cruise-appautoscaling-2026-07-21.txt`

### Task 4.2 — git add + commit + push

- [ ] **Step 1]: `git add aws-aiops-cruise/references/inference-rules.md aws-aiops-cruise/runbooks/scripts/_inference.py docs/superpowers/specs/2026-07-21-aws-aiops-cruise-appautoscaling-rules-design.md docs/superpowers/plans/2026-07-21-aws-aiops-cruise-appautoscaling-rules.md`
- [ ] **Step 2]: `git commit -F <file>` + `rm <file>`
- [ ] **Step 3]: `git push origin main`(user 已 confirm push)

### Task 4.3 — Acceptance

- [ ] `git log -1 --stat` 显示 5 files
- [ ] `grep "AUTO-"` 在 inference-rules.md ≥ 21
- [ ] `grep "def detect_app_autoscaling_"` ≥ 7
- [ ] `python3 -c "import _inference"` 无 error
- [ ] `git status --short` 清空
- [ ] `git log origin/main` 含 v1.3.0 commit

## Out-of-Scope(后续 plan 议题)

- Plan B (v1.3.1): scheduled-actions.md + RB-AUTOSCALING-01 扩 S9-S12
- Plan C (v1.4.0): elasticache.md + kafka.md + appstream.md (3 namespace docs)
- Plan D (远期): event-driven invocation, cross-account orchestration, learning from runbook outcomes

## Risk mitigation

| 风险 | 缓解 |
|---|---|
| Rule ID 与 v1.1.0 4 rule 冲突 | 用 `AUTO-*` prefix,v1.1.0 用 `*-AUTOSCALING-01/02`,grep 隔离 |
| CloudWatch metric 错误 | spec §2.2 列结构,write rule 时严格 cross-ref docs |
| Python handler 阻塞 import | 主 agent 先 `python3 -c "import _inference"` 验证 |
| 既有 ECS rule regression | detect function 走独立 branch,不影响 ECS 既有 inline |
| Markdown append 错位 | SearchReplace anchor 严格 `## Application Auto Scaling` 块尾 |

## 安全与回滚

- 不动 `aws-application-autoscaling-ops` / 其他 skill
- commit on local main,`git reset --soft HEAD~1` 即回滚
- user 已 confirm push,本次 push
