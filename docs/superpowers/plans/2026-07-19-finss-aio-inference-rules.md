# FinOps + SecurityOps + AIOps 推理规则落地 — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Spec**: `docs/superpowers/specs/2026-07-19-finss-aio-inference-rules-design.md`

**Goal**: 在 `aws-aiops-cruise` 中新增 6 条推理规则 + 4 个新 collector，覆盖 FinOps (EC2-IDLE-01)、SecurityOps (ACM-CERT-01, KMS-ROTATE-01)、AIOps (SQS-DLQ-01, GUARDDUTY-HIGH-01, SECHUB-FAILED-01)。

**Architecture**: Python（4 个新 collector + 1 个 registry 修改 + `_inference.py` 规则追加），纯 detect + recommend + delegate，无破坏性操作。

**验证标准**（每步完成后必须验证）：
- `ruff check` zero error
- 新增测试全部 passed
- 无 `delete`/`put`/`modify` 等破坏性 API 调用（grep 确认）

---

## Phase 1: Collector 实现（4 个新 collector）

### 1.1 `collectors/acm.py` — ACM 证书到期检测

- [ ] **Step 1**: 创建 `runbooks/scripts/collectors/acm.py`
  - 函数 `audit_acm_certs(customer, region)` → `signals["ACM"]`
  - 使用 `aws acm list-certificates` + `aws acm describe-certificate`
  - 信号结构：`{cert_arn: {"DomainName": str, "NotAfter": float (unix ts), "InUseBy": list}}`
  - **验证**: `ruff check aws-aiops-cruise/runbooks/scripts/collectors/acm.py` zero error

- [ ] **Step 2**: 在 `registry.py` 中注册 `audit_acm_certs`
  - import + 追加到 collectors 列表
  - **验证**: `python3 -c "from collectors.registry import _collectors; print([c.__name__ for c in _collectors])"` 包含 `audit_acm_certs`

### 1.2 `collectors/kms.py` — KMS 密钥轮换检测

- [ ] **Step 3**: 创建 `runbooks/scripts/collectors/kms.py`
  - 函数 `audit_kms_keys(customer, region)` → `signals["KMS"]`
  - 使用 `aws kms list-keys` + `aws kms get-key-rotation-status`
  - 信号结构：`{key_arn: {"KeyRotationEnabled": bool, "KeyManager": str, "CreatedTimestamp": float (unix ts), "KeySpec": str}}`
  - **验证**: `ruff check aws-aiops-cruise/runbooks/scripts/collectors/kms.py` zero error

- [ ] **Step 4**: 在 `registry.py` 中注册 `audit_kms_keys`

### 1.3 `collectors/guardduty.py` — GuardDuty 高危 Findings

- [ ] **Step 5**: 创建 `runbooks/scripts/collectors/guardduty.py`
  - 函数 `audit_guardduty_findings(customer, region)` → `signals["GuardDuty"]`
  - 使用 `aws guardduty list-findings` + `aws guardduty get-findings`
  - 信号结构：`{finding_arn: {"Severity": float, "Type": str, "ServiceName": str, "ResourceType": str, "CreatedAt": float (unix ts), "UpdatedAt": float}}`
  - 仅返回 `Severity >= 7` 的 findings
  - **验证**: `ruff check aws-aiops-cruise/runbooks/scripts/collectors/guardduty.py` zero error

- [ ] **Step 6**: 在 `registry.py` 中注册 `audit_guardduty_findings`

### 1.4 `collectors/securityhub.py` — Security Hub 合规失败

- [ ] **Step 7**: 创建 `runbooks/scripts/collectors/securityhub.py`
  - 函数 `audit_securityhub_findings(customer, region)` → `signals["SecurityHub"]`
  - 使用 `aws securityhub get-findings` with `ComplianceStatus=FAILED`
  - 信号结构：`{finding_arn: {"ComplianceStatus": str, "WorkflowStatus": str, "FirstObservedAt": float, "Title": str, "ProductName": str}}`
  - **验证**: `ruff check aws-aiops-cruise/runbooks/scripts/collectors/securityhub.py` zero error

- [ ] **Step 8**: 在 `registry.py` 中注册 `audit_securityhub_findings`

---

## Phase 2: 推理规则追加（6 条新规则）

- [ ] **Step 9**: 读取 `runbooks/scripts/_inference.py` 末尾 50 行，确认 `apply_chain_inference` 函数结构（参数、返回值、make_incident 调用方式）
- [ ] **Step 10**: 在 `_inference.py` 中追加以下规则（在 `apply_chain_inference` 函数内，`existing_rule_ids` 检查之后）：
  - `EC2-IDLE-01`（FinOps）
  - `ACM-CERT-01`（SecurityOps）
  - `KMS-ROTATE-01`（SecurityOps）
  - `SQS-DLQ-01`（AIOps）
  - `GUARDDUTY-HIGH-01`（AIOps）
  - `SECHUB-FAILED-01`（AIOps）
- [ ] **Step 11**: 确认每个规则的 delegate 目标与 spec §2 一致
- [ ] **Step 12**: `ruff check aws-aiops-cruise/runbooks/scripts/_inference.py` zero error

---

## Phase 3: 文档更新

- [ ] **Step 13**: 更新 `references/inference-rules-addendum.md`，追加 6 条规则文档（格式参照现有规则）
- [ ] **Step 14**: 更新 `aws-aiops-cruise/SKILL.md` 路由表，追加 ACM、KMS、GuardDuty、SecurityHub 条目（delegate 目标）
- [ ] **Step 15**: 更新 `assets/alarms/cruise-inference-alarms.yaml`，追加 ACM-CERT-01 和 KMS-ROTATE-01 的 alarm 定义

---

## Phase 4: 测试追加

- [ ] **Step 16**: 在 `tests/test_inference_phase23.py` 追加 6 条规则的合成测试
  - 每个规则至少 2 个测试：hit（触发）/ miss（不触发）
  - 测试结构参照现有测试：`test_rule_<id>_hit`、`test_rule_<id>_miss`
- [ ] **Step 17**: 运行 `pytest tests/test_inference_phase23.py -v` 确认全部 passed
- [ ] **Step 18**: 运行 `ruff check aws-aiops-cruise/runbooks/scripts/` 确认 zero error

---

## Phase 5: 安全门禁

- [ ] **Step 19**: `grep -n "delete\|put\|modify\|remove\|deregister" aws-aiops-cruise/runbooks/scripts/collectors/acm.py aws-aiops-cruise/runbooks/scripts/collectors/kms.py aws-aiops-cruise/runbooks/scripts/collectors/guardduty.py aws-aiops-cruise/runbooks/scripts/collectors/securityhub.py` — 确认无破坏性 API
- [ ] **Step 20**: `git diff --stat` 确认仅涉及预期文件（无触碰其他 skill 或无关文件）

---

## Phase 6: 提交

- [ ] **Step 21**: commit：`git add` 所有改动文件 + `git commit -m "feat(aiops-cruise): add 6 inference rules + 4 collectors (FinOps/SecurityOps/AIOps)"`
- [ ] **Step 22**: push：`git push`

---

## 后续路线图（不在本次 scope）

| ID | 描述 | 依赖 |
|----|------|------|
| COST-IDLE-01 | 统一 FinOps 技能（aws-cost-ops）+ Idle EC2/NAT/LB 成本规则 | 新建 skill |
| CIS-BENCHMARK-01 | CIS benchmark conformance rules | 需 aws-config-ops 强化 |
| GUARDDUTY-ALARM-01 | GuardDuty findings → CloudWatch alarm | 独立 plan |
| SQS-DLQ-AUTO-HEAL | SQS DLQ → 触发 Lambda 重新入队 | self-heal 能力 |
