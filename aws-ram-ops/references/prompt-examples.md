# RAM Skill — Prompt Examples (多账号资源共享与授权)

_Latest update: 2026-07-30_

覆盖应用管理账号通过 RAM 获得共享资源及**精细化授权**的典型场景。

> **边界**：RAM **不创建** AWS 账号或 IAM 身份。  
> **链接**：[SKILL.md](../SKILL.md) · [aws-cli-usage.md](aws-cli-usage.md) · [core-concepts.md](core-concepts.md)

## 场景 1：向多个应用团队账号共享生产子网

### Prompt
`网络账号生产 VPC 子网共享给 app-team-dev/staging/prod 三个应用管理账号，创建 RAM 共享。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `sts get-caller-identity` + `ec2 describe-subnets` 取 ARN |
| 2 | `create-resource-share` — `--resource-arns` + `--principals`；组织内 `allow-external-principals` false |
| 3 | `get-resource-share-associations` 验证 `ACTIVE` |

→ [create-and-share-vpc-subnet](aws-cli-usage.md#create-and-share-vpc-subnet) · `[AI_ASSIST]` 组织外需 accept

## 场景 2：新应用管理账号入驻 — 接受共享邀请

### Prompt
`应用账号 555555555555 收到 RAM 邀请，接受并确认共享子网可用。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | 消费账号 `get-resource-share-invitations --status PENDING` → accept |
| 2 | `list-resources --resource-owner OTHER-ACCOUNTS` 验证 `AVAILABLE` |
| 3 | `aws-ec2-ops` 启动实例验证 |

→ [accept-invitation-and-verify](aws-cli-usage.md#accept-invitation-and-verify)

## 场景 3：组织内批量授权 — OU 共享

### Prompt
`Workloads OU 下所有应用管理账号自动获得共享网络资源。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `enable-sharing-with-aws-organization` |
| 2 | `create-resource-share` — `--principals` 用 OU ARN；`associate-resource-share` 追加资源 |

→ [enable-organization-sharing](aws-cli-usage.md#enable-organization-sharing) · `[MANUAL]` 账号创建不在 RAM 范围

## 场景 4：精细化授权 — 只读 vs 读写 Permission

### Prompt
`数据分析账号只读查看子网；DevOps 账号需创建 ENI。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `list-permissions --resource-type ec2:Subnet` 发现托管 Permission |
| 2 | **只读 share**：list 选 Describe-only，或 `create-permission` **仅** `ec2:DescribeSubnets` |
| 3 | **读写/ENI share**：`AWSRAMDefaultPermissionSubnet`；不同 principal 挂**不同 share** |

| 需求 | Permission | Share |
|------|------------|-------|
| 仅查看 | list 选 RO 或 CMP 仅 `DescribeSubnets` | 只读 |
| 创建 ENI | `AWSRAMDefaultPermissionSubnet` | 读写 |
| Aurora RO | `list-permissions --resource-type rds:Cluster` 选 RO | 只读 |

→ [associate-read-only-permission](aws-cli-usage.md#associate-read-only-permission-authorization) · 禁止"只读"标签下挂 `AWSRAMDefaultPermissionSubnet`

## 场景 5：向已有共享追加应用账号

### Prompt
`新账号 666666666666 加入现有 shared-prod-subnets。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `associate-resource-share --principals 666666666666` |
| 2 | `get-resource-share-associations --association-type PRINCIPAL` 验证 `ASSOCIATED` |

## 场景 6：撤销应用账号访问

### Prompt
`账号 333333333333 下线，从所有 RAM 共享移除。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `list-principals` 定位 share → `disassociate-resource-share` |
| 2 | 验证 `DISASSOCIATED`；废弃整个 share 需 `confirm=DELETE_RESOURCE_SHARE <arn>` |

## 场景 7：Aurora 跨账号只读共享

### Prompt
`Aurora prod-aurora-analytics 只读共享给 BI 账号 777777777777。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `[aws-aurora-ops]` describe → ARN |
| 2 | `create-resource-share`（模式场景 1）+ RO Permission 从 `list-permissions --resource-type rds:Cluster` 选 |
| 3 | 消费账号 accept → `[aws-rds-ops]` 验证 |

→ [RDS/Aurora sharing](integration.md#5-rds--aurora-sharing)

## 场景 8：安全组跨账号共享

### Prompt
`平台标准 SG 共享给各应用账号，在共享子网复用。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `create-resource-share` — SG ARN + principals（模式场景 1） |
| 2 | 消费账号 `list-resources --resource-owner OTHER-ACCOUNTS` → `aws-ec2-ops` 引用共享 SG |

## 场景 9：外部合作伙伴跨组织共享

### Prompt
`专用子网共享给合作伙伴 888888888888（组织外）。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `create-resource-share --allow-external-principals`（模式场景 1） |
| 2 | 合作伙伴 accept；只读 Permission 从 `list-permissions` 选 RO 项 |

→ `[MANUAL]` 合规评审 · [cross-account flow](integration.md#2-cross-account-invitation-flow)

## 场景 10：审计消费账号共享资源

### Prompt
`审计账号 444444444444 获得了哪些共享资源？`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | 消费账号 `list-resources --resource-owner OTHER-ACCOUNTS` |
| 2 | `get-resource-share-associations`；按 `type` + `resourceOwnerId` 汇总 |

→ 所有者侧 `--resource-owner SELF` · [audit](aws-cli-usage.md#audit-principals-and-resources)

## 场景 11：替换 Permission（升级/降级）

### Prompt
`Aurora 共享从只读改成可创建克隆集群。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | **单 share（首选）**：`associate-resource-share-permission --replace` |
| 2 | `[MANUAL]` 权限扩大需审批；执行前 `get-resource-share-associations` |
| 3 | **账户级批量**：`replace-permission-associations` — **禁止** `--resource-share-arn` |

→ [replace-permission](aws-cli-usage.md#replace-permission-upgrade-downgrade)

## 场景 12：共享子网 + 消费账号 IAM

### Prompt
`子网已 RAM 共享，应用账号还要什么 IAM 才能起 EC2？`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `list-resources --resource-owner OTHER-ACCOUNTS` 确认 `AVAILABLE` |
| 2 | `[aws-iam-ops]` 附加 EC2 策略 → `[aws-ec2-ops]` RunInstances |

→ RAM 只解决可见性 · [IAM consumer policies](integration.md#3-iam-integration-consumer-side)

## Quick Reference

| 用户说 | 场景 | 决策 | 模块 |
|--------|------|------|------|
| "共享子网给应用账号" | 1 | `[AI_ASSIST]` | ram + vpc |
| "新账号接受 RAM 邀请" | 2 | `[AI_ASSIST]` | ram |
| "OU 下所有账号自动共享" | 3 | `[MANUAL]` | ram |
| "只读共享 Aurora/子网" | 4 | `[AI_ASSIST]` | ram + rds |
| "加账号到现有共享" | 5 | `[AI_ASSIST]` | ram |
| "下线账号移除访问" | 6 | `[AI_ASSIST]` | ram |
| "Aurora 只读共享" | 7 | `[AI_ASSIST]` | ram + aurora |
| "安全组跨账号共享" | 8 | `[AI_ASSIST]` | ram + ec2 |
| "合作伙伴跨组织共享" | 9 | `[MANUAL]` | ram |
| "审计共享资源" | 10 | `[AI_ASSIST]` | ram |
| "替换 Permission" | 11 | `[MANUAL]` | ram |
| "建 IAM 跑 EC2" | 12 | `[AI_ASSIST]` | ram + iam + ec2 |
| "创建新 AWS 账号" | **非 RAM** | `[MANUAL]` | Organizations |
