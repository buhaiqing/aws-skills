# F1: aws-finops-core 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal**: 创建 `aws-finops-core` Composite L2 Skill，统一成本异常检测 + Idle Resource 发现 + 成本分摊

**Architecture**: L2 composite，编排 aws-ec2-ops / aws-rds-ops / aws-elb-ops / aws-s3-ops / aws-lambda-ops，自身不含 AWS 写操作

**Tech Stack**: Bash (CLI) + Python (数据分析) + Markdown

---

## Task F1.1: 创建目录结构

**Files**: Create `aws-finops-core/` 目录树

- [ ] **Step 1**: 创建目录
  ```bash
  mkdir -p aws-finops-core/references
  mkdir -p aws-finops-core/assets
  ```
- [ ] **Step 2**: 创建 `aws-finops-core/SKILL.md`（~90 lines）：
  - Frontmatter: `name: aws-finops-core`, `type: composite`, `metadata.delegate` 映射 5 个 skill
  - `## Trigger & Scope`（SHOULD/SHOULD NOT）
  - `## Variable Convention`（`{{user.cost_period}}`, `{{user.threshold_pct}}`, `{{user.idle_days}}`）
  - `## Execution Flow Pattern`：Pre-flight → Query Cost Explorer → Idle Detection → Anomaly Analysis → Report
  - `## Quality Gate (GCL)`：recommended, max_iter=3（只读，无 destructive ops）
- [ ] **Step 3**: 校验 frontmatter：`awk '/^---$/{c++; if(c==2)exit} c==1' aws-finops-core/SKILL.md | head -1` 应为 `---`
- [ ] **Step 4**: commit `git commit -m "feat(finops): add aws-finops-core composite skill"`

---

## Task F1.2: references/cost-api-usage.md

**Files**: Create `aws-finops-core/references/cost-api-usage.md`

- [ ] **Step 1**: 编写 Cost Explorer API 汇总，包含：
  - `get-cost-and-usage`（DAILY/MONTHLY，by SERVICE/TAG/RESOURCE）
  - `get-cost-forecast`（成本预测）
  - `get-reservation-coverage`（RI 覆盖率）
  - `get-savings-plans-coverage`（SP 覆盖率）
  - 每个命令带 JSON path 解析示例
- [ ] **Step 2**: 验证所有命令 CLI 格式正确（`aws <svc> <op>` 非 `aws --output json <svc> <op>`）
- [ ] **Step 3**: commit `git commit -m "docs(finops): add cost-api-usage reference"`

---

## Task F1.3: references/idle-detection-rules.md

**Files**: Create `aws-finops-core/references/idle-detection-rules.md`

- [ ] **Step 1**: 编写 5 种资源类型的 Idle 检测规则（见 spec §3.2）：
  - ALB/NLB（RequestCount=0 持续 7 天）
  - EBS Volume（available 状态未挂载超过 30 天）
  - EBS Snapshot（孤立快照）
  - Lambda（Invocations=0 持续 30 天）
  - RDS Instance（DatabaseConnections=0 持续 7 天）
- [ ] **Step 2**: 每个规则包含检测 CLI + CloudWatch 指标查询 + 判定逻辑
- [ ] **Step 3**: commit `git commit -m "docs(finops): add idle-detection-rules reference"`

---

## Task F1.4: references/tag-compliance.md

**Files**: Create `aws-finops-core/references/tag-compliance.md`

- [ ] **Step 1**: 编写 Tag 合规检查逻辑（必填 Tag：Environment, Application, Owner, CostCenter）
- [ ] **Step 2**: 编写 `aws ce get-cost-and-usage --group-by TAG` 查询示例
- [ ] **Step 3**: 编写合规率计算公式 + 告警阈值（< 80% WARNING, < 60% CRITICAL）
- [ ] **Step 4**: commit `git commit -m "docs(finops): add tag-compliance reference"`

---

## Task F1.5: references/anomaly-detection.md + reserved-coverage.md + budget-alerts.md

**Files**: Create `aws-finops-core/references/anomaly-detection.md`, `reserved-coverage.md`, `budget-alerts.md`

- [ ] **Step 1**: `anomaly-detection.md` — 7-day baseline 计算逻辑 + cost > 1.3x / 1.5x 判定
- [ ] **Step 2**: `reserved-coverage.md` — RI/SP 覆盖率查询 + 优化建议
- [ ] **Step 3**: `budget-alerts.md` — Budget API + CloudWatch 告警配置
- [ ] **Step 4**: commit `git commit -m "docs(finops): add anomaly/reserved/budget references"`

---

## Task F1.6: assets/cost-tags.yaml + budget-thresholds.yaml

**Files**: Create `aws-finops-core/assets/cost-tags.yaml`, `budget-thresholds.yaml`

- [ ] **Step 1**: `cost-tags.yaml` — 必填 Tag 定义 + 推荐值（dev/staging/prod）
- [ ] **Step 2**: `budget-thresholds.yaml` — 告警阈值配置（% of budget）
- [ ] **Step 3**: commit `git commit -m "assets(finops): add cost-tags and budget-thresholds config"`

---

## Task F1.7: references/rubric.md + prompt-templates.md + GCL section

**Files**: Create `aws-finops-core/references/rubric.md`, `prompt-templates.md`; Modify `SKILL.md`

- [ ] **Step 1**: `rubric.md` — 5 维度 rubric（Correctness ≥ 0.5, Safety = 1, Idempotency ≥ 0.8, Traceability ≥ 0.8, Spec Compliance ≥ 0.8）
- [ ] **Step 2**: `prompt-templates.md` — thin specialization of shared skeleton
- [ ] **Step 3**: 在 `SKILL.md` 添加 `## Quality Gate (GCL)` section
- [ ] **Step 4**: commit `git commit -m "gcl(finops): add rubric and prompt-templates to aws-finops-core"`

---

## Task F1.8: 最终自检

- [ ] **Step 1**: SKILL.md line count ≤ 100（C6 TE 验证）
- [ ] **Step 2**: 所有 delegate 目录存在（`ls aws-*-ops/SKILL.md | grep -E "ec2|rds|elb|s3|lambda"`）
- [ ] **Step 3**: frontmatter 合规（无 stray `---`）
- [ ] **Step 4**: README.md / README_cn.md 同步（新增 skill 列入 Existing Skills 表格）
