# S2: 安全基线自动化检查设计文档

- **日期**: 2026-07-19
- **状态**: 定稿
- **对应计划**: `2026-07-19-secops-security-baseline.md`
- **目标**: 扩展 `aws-config-ops`，建立 CIS/AWS Foundational Security 标准规则集 + 自动修复能力

## 1. 背景

当前 `aws-config-ops` 只有基础的 Config Recorder 管理 + 单规则操作。
S2 扩展为完整的 **安全基线检查框架**，覆盖：
- CIS AWS Foundations Benchmark（CIS 1.x / 2.x）
- AWS Foundational Security Best Practices (FSBP)
- 自动修复（Config Conformance Pack + SSM Automation）

## 2. 目标与范围

**修改范围**:
```
aws-config-ops/
  SKILL.md                           # 扩展 + GCL section
  references/
    aws-cli-usage.md                 # 补充 conformance pack + SSM automation
    security-baseline-rules.md        # 新建：CIS/FSBP 规则集
    auto-remediation.md              # 新建：SSM Automation 修复手册
    cis-checklist.md                 # 新建：CIS 对照检查表
```

**不修改**: 其他 `aws-*-ops` skill。

## 3. 安全基线规则集

### 3.1 CIS AWS Foundations Benchmark（核心规则）

| CIS Rule ID | AWS Config Rule | 描述 | Severity |
|------------|-----------------|------|----------|
| CIS 1.1 | `aws configservice describe-config-rules` → EC2:CreatedVPC | 确保 VPC 默认安全组阻止入站流量 | HIGH |
| CIS 1.2 | `aws ec2 describe-vpcs` → default security group | 确保默认 SG 无入站规则 | HIGH |
| CIS 1.3 | `aws ec2 describe-regions` | 确保所有新区域启用 Config | MEDIUM |
| CIS 2.1 | `aws iam get-account-summary` → MFA enabled | 确保 root 账户启用 MFA | CRITICAL |
| CIS 2.2 | `aws iam get-credential-report` | 确保 MFA for all users with console access | HIGH |
| CIS 2.3 | `aws iam list-access-keys` | 确保 Access Key rotation < 90 days | MEDIUM |
| CIS 3.1 | `aws cloudtrail describe-trails` | 确保 CloudTrail 开启并 Multi-Region | HIGH |
| CIS 3.2 | `aws cloudtrail get-event-selectors` | 确保 CloudTrail 日志写入 S3 并加密 | HIGH |
| CIS 4.1 | `aws logs describe metric-filters` → Unauthorized API call | 确保 CloudWatch Logs 审计 | MEDIUM |

### 3.2 AWS FSBP（Foundational Security Best Practices）

| FSBP Rule | 描述 | Severity |
|-----------|------|----------|
| `AUTOSCALING_ELB_HEALTH_CHECK_REQUIRED` | ASG 配置 ELB 健康检查 | HIGH |
| `API_GW_CERT_AND_PUBLIC_ACCESS_BLOCKED` | API Gateway 公开访问阻止 | HIGH |
| `DYNAMODB_TABLE_ENCRYPTED_KMS` | DynamoDB 表加密 | HIGH |
| `ECR_PRIVATE_SUBNET_ONLY` | ECR 仅私有子网 | MEDIUM |
| `ELBv2_ACM_CERTIFICATE_REQUIRED` | ALB 配置 ACM 证书 | HIGH |
| `RDS_STORAGE_ENCRYPTED` | RDS 存储加密 | HIGH |
| `REDSHIFT_CLUSTER_ENCRYPTION` | Redshift 集群加密 | HIGH |
| `S3_BUCKET_LEVEL_PUBLIC_ACCESS_PROHIBITED` | S3 桶级公开访问阻止 | CRITICAL |

## 4. 自动修复（SSM Automation）

Config Conformance Pack 可以触发 SSM Automation Document 自动修复：

```bash
# 启用 Config Conformance Pack（CIS 包含 40+ 规则）
aws configservice put-conformance-pack \
  --conformance-pack-name cis-baseline \
  --template-body 'file://conformance-pack-template.yaml'

# 触发 SSM Automation 修复（例如：限制 S3 公开访问）
aws ssm start-automation-execution \
  --document-name AWS-DisableS3BucketPublicReadWrite \
  --parameters '{"S3BucketName":["{{bucket_name}}"]}'

# 查看修复状态
aws configservice get-conformance-pack-compliance-summary \
  --conformance-pack-name cis-baseline
```

**修复策略矩阵**:

| Config Rule | SSM Document | 是否需人工确认 | 可逆性 |
|------------|-------------|--------------|--------|
| `S3_BUCKET_LEVEL_PUBLIC_ACCESS_PROHIBITED` | `AWS-DisableS3BucketPublicReadWrite` | 是 | 可逆 |
| `IAM_PASSWORD_POLICY` | `AWSConfigRemediation-SetIAMPasswordPolicy` | 否 | 可逆 |
| `CLOUDWATCH_ALARM_ACTION_CHECK` | `AWSConfigRemediation-EnableCloudWatchAlarmActions` | 是 | 可逆 |

## 5. 执行模式

**两种模式**:
1. **Audit-only（默认）**: 只读扫描，生成不符合规则列表，不修复
2. **Auto-remediate（用户确认后）**: 对非 critical 规则自动触发 SSM Automation

## 6. 验收标准

1. CIS 规则集覆盖 ≥ 10 条核心规则
2. FSBP 规则集覆盖 ≥ 8 条高危规则
3. SSM Automation 修复手册覆盖 ≥ 5 个常见场景
4. Audit-only 模式不触发任何写入操作
5. SKILL.md ≤ 120 lines（C6 通过）
6. GCL rubric 评分标准明确（Safety = 0 的场景必须 HALT）
