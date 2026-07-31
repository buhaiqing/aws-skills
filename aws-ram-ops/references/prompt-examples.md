# RAM Skill — Prompt Examples (多账号资源共享与授权)

_Latest update: 2026-07-31_

> **边界**：RAM **不创建** AWS 账号或 IAM 身份。  
> **链接**：[SKILL.md](../SKILL.md) · [aws-cli-usage.md](aws-cli-usage.md) · [core-concepts.md](core-concepts.md)

## 场景 1：共享生产子网给多应用账号

### Prompt
`网络账号生产 VPC 子网共享给 app-team-dev/staging/prod，创建 RAM 共享。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `sts get-caller-identity` + `ec2 describe-subnets` 取 ARN |
| 2 | `create-resource-share` — `--resource-arns` + `--principals`；组织内 `allow-external-principals` false |
| 3 | `get-resource-share-associations` 验证 `ACTIVE` |

→ [create-and-share-vpc-subnet](aws-cli-usage.md#create-and-share-vpc-subnet) · 组织外需 accept

## 场景 2：接受邀请 / 追加或撤销 principal

### Prompt
`应用账号接受 RAM 邀请；或把 666… 加入 / 333… 移出 shared-prod-subnets。`

### 流程
| 步骤 | 操作 |
|------|------|
| Accept | 消费账号 `get-resource-share-invitations --status PENDING` → accept → `list-resources --resource-owner OTHER-ACCOUNTS` |
| Add | `associate-resource-share --principals 666…` → 验证 `ASSOCIATED` |
| Remove | `list-principals` → `disassociate-resource-share`；整 share 删除需 `confirm=DELETE_RESOURCE_SHARE <arn>` |

→ [accept-invitation-and-verify](aws-cli-usage.md#accept-invitation-and-verify)

## 场景 3：OU 批量授权

### Prompt
`Workloads OU 下所有应用管理账号自动获得共享网络资源。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `enable-sharing-with-aws-organization` |
| 2 | `create-resource-share` — `--principals` 用 OU ARN |

→ [enable-organization-sharing](aws-cli-usage.md#enable-organization-sharing) · 账号创建不在 RAM 范围

## 场景 4：精细化 Permission（只读 vs 读写）

### Prompt
`数据分析账号只读查看子网；DevOps 需创建 ENI；Aurora 只读给 BI。`

### 流程
| 需求 | Permission | Share |
|------|------------|-------|
| 仅查看子网 | `list-permissions --resource-type ec2:Subnet` 选 RO，或 CMP 仅 `DescribeSubnets` | 只读 share |
| 创建 ENI | `AWSRAMDefaultPermissionSubnet` | 读写 share（不同 principal → 不同 share） |
| Aurora RO | `list-permissions --resource-type rds:Cluster` 选 RO | 只读 |

→ [associate-read-only-permission](aws-cli-usage.md#associate-read-only-permission-authorization) · 禁止“只读”标签下挂 Default Subnet Permission

## 场景 5：Aurora / SG / 外部伙伴共享

### Prompt
`Aurora 只读共享给 BI；平台 SG 共享给应用账号；子网共享给组织外合作伙伴。`

### 流程
| 资源 | 要点 |
|------|------|
| Aurora | `[aws-aurora-ops]` 取 ARN → create-share + RO Permission → 消费账号 accept |
| SG | create-share（SG ARN）→ 消费侧 `list-resources --resource-owner OTHER-ACCOUNTS` → `aws-ec2-ops` 引用 |
| 外部 | `--allow-external-principals` + 合作伙伴 accept；合规评审 `[MANUAL]` |

→ [RDS/Aurora sharing](integration.md#5-rds--aurora-sharing) · [cross-account](integration.md#2-cross-account-invitation-flow)

## 场景 6：审计 / 替换 Permission / 消费侧 IAM

### Prompt
`审计账号拿到了哪些共享？把 Aurora 只读升级为可克隆；子网已共享还要什么 IAM 才能起 EC2？`

### 流程
| 目标 | 操作 |
|------|------|
| 审计 | 消费侧 `list-resources --resource-owner OTHER-ACCOUNTS`；所有者侧 `--resource-owner SELF` |
| 替换（单 share） | `associate-resource-share-permission --replace`；扩大权限需审批 |
| 替换（账户级） | `replace-permission-associations` — **禁止** `--resource-share-arn` |
| IAM | RAM 只解决可见性 → `[aws-iam-ops]` EC2 策略 → `[aws-ec2-ops]` |

→ [audit](aws-cli-usage.md#audit-principals-and-resources) · [replace-permission](aws-cli-usage.md#replace-permission-upgrade-downgrade) · [IAM consumer](integration.md#3-iam-integration-consumer-side)

## Quick Reference

| 用户说 | 场景 | 决策 |
|--------|------|------|
| 共享子网 / 接受邀请 / 加减账号 | 1–2 | `[AI_ASSIST]` |
| OU 自动共享 / 合作伙伴跨组织 | 3 / 5 | `[MANUAL]` |
| 只读 vs 读写 Permission / Aurora·SG | 4–5 | `[AI_ASSIST]` |
| 审计 / 替换 Permission / 消费侧 IAM | 6 | 扩大权限 `[MANUAL]` |
| 创建新 AWS 账号 | **非 RAM** | Organizations |
