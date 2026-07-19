# FinOps + SecurityOps + AIOps 推理规则落地 — 设计文档

- **日期**: 2026-07-19
- **状态**: 待评审
- **范围**: 在 `aws-aiops-cruise` 中新增 6 条推理规则（FinOps ×1, SecurityOps ×2, AIOps ×3），覆盖 SQS、ACM、EC2 Idle、GuardDuty、Security Hub、KMS

## 1. 背景与已核实现状

**已核实事实**：

| 维度 | 现状 | 证据 |
|------|------|------|
| 推理规则总数 | 44 条（`_inference.py` 中 `rule = "` 去重） | `grep 'rule = "' _inference.py \| sort -u` |
| 有 skill 但无 cruise 规则 | SQS、ACM、GuardDuty、SecurityHub、KMS、EC2 (idle) | 各 skill 目录存在，cruise 路由表无对应条目 |
| 有 skill 但无 alarm | KMS 密钥轮换、ACM 证书到期 | `cruise-inference-alarms.yaml` 无这两个 |
| SQS collector | 存在 `collectors/data.py` → `signals["SQS"]` | `audit_sqs_queues()` 函数存在 |
| GuardDuty collector | 无 | `collectors/` 中无 guardduty 模块 |
| GuardDuty skill | 存在 `aws-guardduty-ops/` | 目录 listing |
| SecurityHub skill | 存在 `aws-securityhub-ops/` | 目录 listing |
| KMS skill | 存在 `aws-kms-ops/` | 目录 listing |
| EC2 已有规则 | EC2-MEM-01/EC2-IO-01/EC2-IO-02/EC2-NET-01/EC2-NET-02 | `_inference.py` 中已有 |
| ACM skill | 存在 `aws-acm-ops/` | 目录 listing |

**核心缺口**：大量 skill 存在但未接入 inference engine，处于"有人写 skill，没人写规则"的状态。

## 2. 新增规则清单

### 2.1 FinOps

| Rule ID | 触发条件 | 委托目标 | 依赖信号 |
|---------|----------|----------|----------|
| `EC2-IDLE-01` | EC2 `CPUUtilization < 5%` 持续 7d 且 `StatusCheckFailed == 0` | `aws-ec2-ops` | `signals["EC2"]["<id>"]["CPUUtilization"]`（已有 compute collector） |

**逻辑**：
- WARN: CPU < 5% 持续 7d（非 launch/warmup 期，忽略新实例前 24h）
- CRITICAL: CPU < 5% 持续 14d
- Guard: `StatusCheckFailed == 0`（排除 health check 失败但实际 running 的实例）
- Guard: `InstanceLifecycle != "spot"`（Spot 实例不适用）
- Action: delegate `aws-ec2-ops` with `health-check`

### 2.2 SecurityOps

| Rule ID | 触发条件 | 委托目标 | 依赖信号 |
|---------|----------|----------|----------|
| `ACM-CERT-01` | ACM 证书 `NotAfter` 距今 < 30d（WARN）/ < 7d（CRIT） | `aws-acm-ops` | `signals["ACM"]`（需新建 `audit_acm_certs` collector） |
| `KMS-ROTATE-01` | KMS key `KeyRotationEnabled == false` 且创建 > 365d | `aws-kms-ops` | `signals["KMS"]`（需新建 `audit_kms_keys` collector） |

**ACM-CERT-01 逻辑**：
- Guard: 跳过 `DomainName` 包含 `.internal` 的证书（内部 CA 管理）
- WARN: `NotAfter - now < 30d`
- CRIT: `NotAfter - now < 7d`
- Action: delegate `aws-acm-ops` with `health-check`

**KMS-ROTATE-01 逻辑**：
- Guard: 仅检查对称密钥（`KeySpec` 不以 `HMAC` 开头）
- Guard: 跳过 AWS 托管密钥（`KeyManager == AWS`）
- CRIT: `KeyRotationEnabled == false && CreatedTimestamp < now - 365d`
- Action: delegate `aws-kms-ops` with `health-check`

### 2.3 AIOps

| Rule ID | 触发条件 | 委托目标 | 依赖信号 |
|---------|----------|----------|----------|
| `SQS-DLQ-01` | SQS DLQ `ApproximateNumberOfMessagesVisible > 0` 持续 > 1h | `aws-sqs-ops` | `signals["SQS"]`（已有 `audit_sqs_queues`） |
| `GUARDDUTY-HIGH-01` | GuardDuty finding `Severity` >= 7（高危）且未处理 | `aws-guardduty-ops` | `signals["GuardDuty"]`（需新建 collector） |
| `SECHUB-FAILED-01` | Security Hub `ComplianceStatus == FAILED` 且未修复 > 7d | `aws-securityhub-ops` | `signals["SecurityHub"]`（需新建 collector） |

**SQS-DLQ-01 逻辑**：
- WARN: DLQ messages > 0 且 age > 1h（首次发现）
- CRITICAL: DLQ messages > 10 且 age > 1h
- Guard: 仅检查名称以 `DLQ` 或 `DeadLetter` 结尾的队列
- Action: delegate `aws-sqs-ops` with `self-heal`

**GUARDDUTY-HIGH-01 逻辑**：
- Guard: 仅处理 `Severity >= 7` 的未处理 findings
- Guard: 跳过 `Type` 包含 `Backdoor:EC2/S3`（这类需要立即人工介入）
- CRIT: severity >= 7 且 `ServiceName` in (`EC2`, `S3`, `RDS`, `IAM`)
- Action: delegate `aws-guardduty-ops` with `rca`
- Action: 如果 `Type` in (`Backdoor:EC2`, `Backdoor:S3`) → 升级人工，不 delegate

**SECHUB-FAILED-01 逻辑**：
- Guard: 仅检查 `ComplianceStatus == FAILED`
- WARN: `FirstObservedAt < now - 7d` 且 `WorkflowStatus != RESOLVED`
- CRITICAL: `FirstObservedAt < now - 30d` 且 `WorkflowStatus != RESOLVED`
- Action: delegate `aws-securityhub-ops` with `compliance-scan`

## 3. Collector 新增需求

| Collector | 文件 | 信号 key | 实现说明 |
|-----------|------|----------|----------|
| `audit_acm_certs` | `collectors/acm.py` | `signals["ACM"]` | `list_certificates()` + `describe_certificate()`（AWS API） |
| `audit_kms_keys` | `collectors/kms.py` | `signals["KMS"]` | `list_keys()` + `get_key_rotation_status()` |
| `audit_guardduty_findings` | `collectors/guardduty.py` | `signals["GuardDuty"]` | `list_findings()` with `FilterCriterion` |
| `audit_securityhub_findings` | `collectors/securityhub.py` | `signals["SecurityHub"]` | `get_findings()` with `Filters` |

**注**：`audit_sqs_queues` 已存在，检查 DLQ 逻辑需确认是否支持 `ApproximateAgeOfOldestMessage`。

## 4. 跨文件改动映射

| 文件 | 改动类型 |
|------|----------|
| `runbooks/scripts/collectors/acm.py` | 新增 |
| `runbooks/scripts/collectors/kms.py` | 新增 |
| `runbooks/scripts/collectors/guardduty.py` | 新增 |
| `runbooks/scripts/collectors/securityhub.py` | 新增 |
| `runbooks/scripts/collectors/registry.py` | 修改：追加 4 个新 collector import + 注册 |
| `runbooks/scripts/_inference.py` | 修改：追加 6 条规则函数调用 |
| `references/inference-rules-addendum.md` | 修改：追加 6 条规则文档 |
| `assets/alarms/cruise-inference-alarms.yaml` | 修改：追加 ACM-CERT-01、KMS-ROTATE-01 的 alarm 定义 |
| `aws-aiops-cruise/SKILL.md` | 修改：追加路由条目（ACM、KMS、GuardDuty、SecurityHub） |
| `aws-aiops-orchestrator/SKILL.md` | 修改：确认 delegate 路由条目存在 |
| `tests/test_inference_phase23.py` | 修改：追加 6 条规则的合成测试 |

## 5. 不在本次 scope

- 新建 `aws-cost-ops` FinOps 技能（后续独立 plan）
- CIS benchmark conformance 规则（S1）
- self-heal 自动执行逻辑（仅 detect + recommend + delegate）
- GuardDuty/SecurityHub 的 CloudWatch alarm（后续独立 plan）

## 6. 验证标准

| 验收项 | 标准 |
|--------|------|
| 规则可执行 | `_inference.py` 中 6 条新规则语法正确，函数签名匹配 `apply_chain_inference` |
| Collector 可运行 | 4 个新 collector 有 `list_audits()` 入口，`registry.py` 正确 import |
| 路由表完整 | `aws-aiops-cruise/SKILL.md` 路由表新增 ACM/KMS/GuardDuty/SecurityHub 条目 |
| 测试通过 | 新增 6 条规则各有 ≥ 2 个合成测试（hit / miss），ruff clean |
| Alarm 定义 | `cruise-inference-alarms.yaml` 新增 ACM-CERT-01 / KMS-ROTATE-01 |
| 无破坏性 | 所有新 collector 仅读 API（`list_*` / `describe_*` / `get_*`），无 `delete` / `put` / `modify` 调用 |
