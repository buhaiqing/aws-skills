# S2: 安全基线自动化检查执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement task-by-task.

**Goal**: 扩展 `aws-config-ops`，建立 CIS/FSBP 标准规则集 + SSM Automation 自动修复

**Architecture**: 在 `aws-config-ops/references/` 新增 3 个文件；修改 SKILL.md 添加 GCL section

**Tech Stack**: Bash (CLI) + YAML + Markdown

---

## Task S2.1: aws-config-ops/references/security-baseline-rules.md

**Files**: Create `aws-config-ops/references/security-baseline-rules.md`

- [ ] **Step 1**: 编写 CIS AWS Foundations Benchmark 规则集（≥ 10 条核心规则）：
  - CIS 1.1/1.2: VPC default SG 规则
  - CIS 1.3: Config 跨区域开启
  - CIS 2.1/2.2/2.3: IAM MFA + Access Key rotation
  - CIS 3.1/3.2: CloudTrail 配置
  - CIS 4.1: CloudWatch Logs 审计
- [ ] **Step 2**: 编写 AWS FSBP 规则集（≥ 8 条高危规则）：DynamoDB/RDS/ELB/S3/EC2/Redshift 加密 + SG 规则
- [ ] **Step 3**: 每个规则包含：Rule ID + AWS Config Rule Name + 描述 + Severity + 检测 CLI
- [ ] **Step 4**: commit `git commit -m "docs(config): add security-baseline-rules (CIS+FSBP)"`

---

## Task S2.2: aws-config-ops/references/auto-remediation.md

**Files**: Create `aws-config-ops/references/auto-remediation.md`

- [ ] **Step 1**: 编写 SSM Automation 修复手册（≥ 5 个场景）：
  - S3 公开访问阻止 → `AWS-DisableS3BucketPublicReadWrite`
  - IAM Password Policy 设置 → `AWSConfigRemediation-SetIAMPasswordPolicy`
  - CloudWatch Alarm Action 启用 → `AWSConfigRemediation-EnableCloudWatchAlarmActions`
  - EBS 加密启用 → `AWSConfigRemediation-EnableEBSEncryptionByDefault`
  - Public snapshot 阻止 → `AWSConfigRemediation-ModifyEBSSnapshotPermission`
- [ ] **Step 2**: 每个修复包含：SSM Document Name + 参数 + 是否需人工确认 + 可逆性
- [ ] **Step 3**: commit `git commit -m "docs(config): add SSM auto-remediation playbook"`

---

## Task S2.3: aws-config-ops/references/cis-checklist.md

**Files**: Create `aws-config-ops/references/cis-checklist.md`

- [ ] **Step 1**: 编写 CIS 对照检查表（Markdown checklist 格式）
- [ ] **Step 2**: 每条包含：Checkbox + CIS ID + 描述 + AWS Console 手动验证路径 + Config Rule 自动检查 CLI
- [ ] **Step 3**: commit `git commit -m "docs(config): add CIS benchmark checklist"`

---

## Task S2.4: aws-config-ops/SKILL.md — 扩展 GCL section

**Files**: Modify `aws-config-ops/SKILL.md`

- [ ] **Step 1**: 添加 `## Quality Gate (GCL)` section（recommended, max_iter=3）
- [ ] **Step 2**: 添加 rubric.md + prompt-templates.md 引用（先确认文件存在）
- [ ] **Step 3**: 校验 SKILL.md line count ≤ 120（C6 TE 验证）
- [ ] **Step 4**: commit `git commit -m "gcl(config): add GCL section to aws-config-ops"`

---

## Task S2.5: aws-config-ops/references/rubric.md + prompt-templates.md

**Files**: Create `aws-config-ops/references/rubric.md`, `prompt-templates.md`

- [ ] **Step 1**: `rubric.md` — 5 维度 rubric，Safety 特别说明：
  - **CRITICAL 规则修复（CryptoCurrency / Public exposure）必须 HALT + 人工确认**
  - Safety = 0 立即 ABORT
- [ ] **Step 2**: `prompt-templates.md` — thin specialization of shared skeleton
- [ ] **Step 3**: commit `git commit -m "gcl(config): add rubric and prompt-templates to aws-config-ops"`

---

## Task S2.6: Conformance Pack YAML 模板

**Files**: Create `aws-config-ops/assets/cis-conformance-pack.yaml`

- [ ] **Step 1**: 编写 Config Conformance Pack YAML 模板（CIS 规则子集，可直接 apply）
- [ ] **Step 2**: commit `git commit -m "assets(config): add CIS conformance pack template"`
