# S1: aws-security-copilot 设计文档

- **日期**: 2026-07-19
- **状态**: 定稿
- **对应计划**: `2026-07-19-secops-security-copilot.md`
- **目标**: 创建统一 SecOps Composite Skill，整合 GuardDuty + SecurityHub + Config + IAM Access Analyzer

## 1. 背景

当前仓库：
- GuardDuty 有独立 `aws-guardduty-ops`
- SecurityHub 有独立 `aws-securityhub-ops`
- Config 有独立 `aws-config-ops`
- IAM Access Analyzer 有 `aws-iam-ops`
- **缺少统一安全态势入口**

痛点：运维需在多个 skill 之间切换才能获取完整安全视图。

## 2. 目标与范围

**目标**: 创建 `aws-security-copilot`（L2 Composite Skill），统一安全态势入口。

**目录布局**:
```
aws-security-copilot/
  SKILL.md                          # L2 composite, ~80-100 lines
  references/
    security-api-usage.md           # GuardDuty/SecurityHub/Config/IAM Analyzer API 汇总
    findings-matrix.md              # Finding 优先级矩阵
    incident-schema.md              # 安全事件输出 schema（对齐 cruise incident-schema）
    playbook-routes.md              # 各类 Finding → 对应 ops skill 修复
  assets/
    severity-thresholds.yaml        # Finding 严重等级阈值
```

**metadata.type**: `composite`

**delegate 映射**:
| Security Operation | Delegate Skill |
|-------------------|----------------|
| GuardDuty findings 调查 | `aws-guardduty-ops` |
| Security Hub findings | `aws-securityhub-ops` |
| Config 规则合规扫描 | `aws-config-ops` |
| IAM 策略分析 | `aws-iam-ops` |
| Secrets 泄露检测 | `aws-secretsmanager-ops` |
| KMS 密钥策略 | `aws-kms-ops` |
| CloudTrail 审计 | `aws-cloudtrail-ops` |

## 3. 核心能力

### 3.1 安全态势统一视图（Security Posture Summary）

```bash
# GuardDuty HIGH/CRITICAL findings count
aws guardduty list-findings \
  --detector-id {{guardduty_detector_id}} \
  --finding-criteria '{"SeverityNames":{"Eq":["HIGH","CRITICAL"]}}'

# Security Hub active findings by severity
aws securityhub get-findings \
  --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}'

# Config 规则合规率
aws configservice get-compliance-summary-by-config-rule \
  --config-rules {{config_rule_names}}
```

**统一输出 schema**:
```json
{
  "security_posture": {
    "guardduty": { "critical": N, "high": N, "last_updated": "ISO8601" },
    "securityhub": { "critical": N, "high": N, "informational": N },
    "config_compliance": { "compliant": N, "non_compliant": N, "compliance_rate": "P%" },
    "overall_score": "A/B/C/D/F"
  }
}
```

### 3.2 Finding 优先级矩阵

| Finding Type | Source | Severity | Auto-Remediation |
|-------------|--------|----------|-----------------|
| Exposed credentials | GuardDuty | CRITICAL | Delegate IAM ops: rotate key |
| Port 22/3389 open to 0.0.0.0/0 | Config | HIGH | Delegate EC2/VPC ops: restrict SG |
| Policy with `*` principal | IAM Access Analyzer | HIGH | Delegate IAM ops: restrict policy |
| Secrets older than 90 days | Secrets Manager | MEDIUM | Delegate secretsmanager ops: rotate |
| Unencrypted EBS volume | Config | HIGH | Delegate EC2 ops: enable encryption |
| GuardDuty CryptoCurrency | GuardDuty | CRITICAL | **HALT + 立即告警** |

### 3.3 Playbook 路由

每类 Finding 映射到修复 Skill + 对应操作：
- **Exposure**: IAM key rotation → `aws-iam-ops rotate-access-key`
- **Network**: Open SG → `aws-ec2-ops restrict-sg` / `aws-vpc-ops`
- **Data**: Unencrypted → `aws-ec2-ops enable-encryption` / `aws-rds-ops enable-storage-encryption`
- **Secrets**: Old secrets → `aws-secretsmanager-ops rotate-secret`
- **CryptoCurrency Attack**: Immediate alert + isolate → `aws-ec2-ops terminate` (需人工确认)

## 4. 与 aws-aiops-copilot 的关系

`aws-security-copilot` 是 `aws-aiops-copilot` 的安全专项入口：
```
aws-aiops-copilot
  ├── aws-aiops-cruise    (健康检查)
  ├── aws-aiops-orchestrator (跨服务 RCA)
  └── aws-security-copilot  (新增：安全态势)
```

## 5. GCL 考量

- 所有操作为 **只读查询**（Security Posture Summary）
- 修复操作（remediation）由对应 base skill 的 GCL 处理
- 安全告警触发阈值需用户确认后执行

## 6. 验收标准

1. SKILL.md ≤ 100 lines，C6 通过
2. delegate 映射 7 个目标目录全部存在
3. Finding 优先级矩阵覆盖 ≥ 10 种常见 Finding 类型
4. Playbook 路由覆盖关键安全场景
5. 输出 schema 与 `incident-schema` 对齐
