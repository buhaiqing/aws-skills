# S1: aws-security-copilot 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement task-by-task.

**Goal**: 创建 `aws-security-copilot` L2 Composite Skill，统一安全态势入口

**Architecture**: L2 composite，编排 GuardDuty + SecurityHub + Config + IAM Analyzer + SecretsManager + KMS + CloudTrail

**Tech Stack**: Bash (CLI) + Python + Markdown

---

## Task S1.1: 创建目录结构

**Files**: Create `aws-security-copilot/` 目录树

- [ ] **Step 1**: 创建目录
  ```bash
  mkdir -p aws-security-copilot/references
  mkdir -p aws-security-copilot/assets
  ```
- [ ] **Step 2**: 创建 `SKILL.md`（~90 lines）：
  - Frontmatter: `name: aws-security-copilot`, `type: composite`, `metadata.delegate` 映射 7 个 skill
  - `## Trigger & Scope`（SHOULD/SHOULD NOT）
  - `## Variable Convention`
  - `## Execution Flow Pattern`：Collect Findings → Merge Posture → Prioritize → Route to Remediation
  - `## Quality Gate (GCL)`：recommended, max_iter=3
- [ ] **Step 3**: commit `git commit -m "feat(secops): add aws-security-copilot composite skill"`

---

## Task S1.2: references/security-api-usage.md

**Files**: Create `aws-security-copilot/references/security-api-usage.md`

- [ ] **Step 1**: 汇总 GuardDuty + SecurityHub + Config + IAM Access Analyzer API：
  - GuardDuty: `list-findings`, `get-findings` (severity filter)
  - SecurityHub: `get-findings` (severity + product filter)
  - Config: `get-compliance-summary-by-config-rule`
  - IAM Access Analyzer: `list-findings`
- [ ] **Step 2**: 每个 API 带 JSON path 示例
- [ ] **Step 3**: commit `git commit -m "docs(secops): add security-api-usage reference"`

---

## Task S1.3: references/findings-matrix.md

**Files**: Create `aws-security-copilot/references/findings-matrix.md`

- [ ] **Step 1**: 编写 ≥ 10 种常见 Finding 的优先级矩阵（见 spec §3.2）：
  - Exposed credentials (CRITICAL)
  - Port 22/3389 open to 0.0.0.0/0 (HIGH)
  - Policy with `*` principal (HIGH)
  - Unencrypted EBS volume (HIGH)
  - GuardDuty CryptoCurrency (CRITICAL)
  - IAM MFA disabled (HIGH)
  - CloudTrail not multi-region (MEDIUM)
  - S3 public access (CRITICAL)
  - RDS publicly accessible (HIGH)
  - Lambda public access (MEDIUM)
- [ ] **Step 2**: 每个 Finding 包含 Source + Severity + Auto-Remediation 路由
- [ ] **Step 3**: commit `git commit -m "docs(secops): add findings-priority-matrix reference"`

---

## Task S1.4: references/incident-schema.md

**Files**: Create `aws-security-copilot/references/incident-schema.md`

- [ ] **Step 1**: 定义安全事件输出 schema（对齐 cruise `incident-schema`）：
  ```json
  {
    "incident": {
      "id": "SEC-{date}-{seq}",
      "type": "security",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "source": "guardduty|securityhub|config|iam-analyzer",
      "finding_type": "...",
      "affected_resources": [...],
      "remediation": {
        "skill": "aws-xxx-ops",
        "action": "...",
        "requires_confirmation": true
      },
      "detected_at": "ISO8601"
    }
  }
  ```
- [ ] **Step 2**: commit `git commit -m "docs(secops): add security incident-schema"`

---

## Task S1.5: references/playbook-routes.md + assets/severity-thresholds.yaml

**Files**: Create `aws-security-copilot/references/playbook-routes.md`, `aws-security-copilot/assets/severity-thresholds.yaml`

- [ ] **Step 1**: `playbook-routes.md` — 每个 Finding type → 对应 ops skill + 操作
- [ ] **Step 2**: `severity-thresholds.yaml` — Finding 严重等级阈值配置
- [ ] **Step 3**: commit `git commit -m "docs(secops): add playbook-routes and severity thresholds"`

---

## Task S1.6: rubric.md + prompt-templates.md + GCL section

**Files**: Create `aws-security-copilot/references/rubric.md`, `prompt-templates.md`; Modify `SKILL.md`

- [ ] **Step 1**: `rubric.md` — 5 维度 rubric（注意：CRITICAL finding 必须 HALT，不能自动修复）
- [ ] **Step 2**: `prompt-templates.md` — thin specialization of shared skeleton
- [ ] **Step 3**: 在 `SKILL.md` 添加 `## Quality Gate (GCL)` section
- [ ] **Step 4**: commit `git commit -m "gcl(secops): add rubric and prompt-templates to aws-security-copilot"`

---

## Task S1.7: README 同步

- [ ] **Step 1**: README.md / README_cn.md 同步检查（新增 skill 列入 Existing Skills 表格）
- [ ] **Step 2**: `aws-aiops-copilot` 是否需要添加 security-copilot 路由（可选，当前不在 scope）
