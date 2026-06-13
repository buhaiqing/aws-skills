# RAM Skill — Prompt Examples (多账号资源共享与授权)

_Latest update: 2026-06-13_

覆盖**应用管理账号**（多账号 Landing Zone 中的团队/环境账号）通过 RAM 获得网络、数据库等共享资源，以及**精细化授权**（Permission 关联）的典型场景。

> **边界说明**：RAM **不创建** AWS 账号或 IAM 用户/角色。创建 Organizations 成员账号、IAM 身份 → 先完成账号/IAM 建设，再用本技能做资源共享与授权。  
> **链接**：[SKILL.md](../SKILL.md) · [aws-cli-usage.md](aws-cli-usage.md) · [core-concepts.md](core-concepts.md)

---

## 场景 1：向多个应用团队账号共享生产子网

### Prompt
```
网络账号里有一套生产 VPC 子网，需要共享给 app-team-dev、app-team-staging、app-team-prod 三个应用管理账号（账号 ID 已知），帮我创建 RAM 共享。
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `aws sts get-caller-identity` 确认当前为网络/共享服务账号 |
| 2 | `aws ec2 describe-subnets` 获取子网 ARN（或用户提供） |
| 3 | `aws ram create-resource-share` — `--resource-arns` 子网列表，`--principals` 三个账号 ID |
| 4 | 组织内共享：`allow-external-principals` 保持 false；跨组织则 true |
| 5 | `get-resource-shares` + `get-resource-share-associations` 验证 `ACTIVE` |

```bash
aws ram create-resource-share \
  --name "shared-prod-subnets" \
  --resource-arns "arn:aws:ec2:{{user.region}}:111111111111:subnet/subnet-aaa" \
                  "arn:aws:ec2:{{user.region}}:111111111111:subnet/subnet-bbb" \
  --principals "222222222222" "333333333333" "444444444444" \
  --region "{{user.region}}" \
  --output json
```

### 输出示例
```
【完成】ResourceShare shared-prod-subnets ACTIVE
【Principal】222222222222, 333333333333, 444444444444 — association ASSOCIATED
【决策】[AI_ASSIST] 各应用账号需各自 accept invitation（组织外）或自动可见（组织内已启用共享）
```

---

## 场景 2：新应用管理账号入驻 — 接受共享邀请

### Prompt
```
我们刚新建了应用管理账号 555555555555，网络团队发来 RAM 邀请，帮我接受并确认能用到共享子网。
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | 在**消费账号**（555555555555）执行 `get-resource-share-invitations --status PENDING` |
| 2 | `accept-resource-share-invitation --resource-share-invitation-arn <arn>` |
| 3 | `list-pending-invitation-resources` 查看待接入资源 |
| 4 | `list-resources` 验证子网/安全组已 `AVAILABLE` |
| 5 | 跨技能：在消费账号用 `aws-ec2-ops` 启动实例验证子网可见 |

```bash
aws ram get-resource-share-invitations --status PENDING --region "{{user.region}}" --output json
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "{{user.invitation_arn}}" \
  --region "{{user.region}}" --output json
aws ram list-resources --region "{{user.region}}" --output json
```

---

## 场景 3：组织内批量授权 — 启用 Organizations 共享并向 OU 授权

### Prompt
```
公司用 AWS Organizations，希望 Workloads OU 下所有应用管理账号自动能用到共享网络资源，怎么开？
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | 管理账号或委派管理员执行 `enable-sharing-with-aws-organization` |
| 2 | 创建或更新 resource share，`--principals` 使用 OU ARN：`arn:aws:organizations::mgmt:ou/o-xxx/ou-yyy` |
| 3 | `associate-resource-share` 追加子网/安全组 ARN |
| 4 | OU 下新建应用账号**无需逐账号邀请**，自动继承共享（组织策略允许时） |

```bash
aws ram enable-sharing-with-aws-organization --region "{{user.region}}" --output json

aws ram create-resource-share \
  --name "org-workloads-network" \
  --principals "arn:aws:organizations::111111111111:ou/o-abc123/ou-def456" \
  --resource-arns "arn:aws:ec2:{{user.region}}:111111111111:subnet/subnet-shared" \
  --region "{{user.region}}" --output json
```

> **注意**：Organizations 账号创建本身不在 `aws-ram-ops` 范围；OU 结构变更后检查 `list-principals` 是否覆盖新成员账号。

---

## 场景 4：精细化授权 — 只读 vs 读写 Permission

### Prompt
```
共享子网给数据分析应用账号，但只能只读查看，不能改子网属性；另一个 DevOps 账号需要能创建 ENI。
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `list-permissions --resource-type ec2:Subnet` 查看托管 Permission |
| 2 | 只读 share：`associate-resource-share-permission` → `AmazonVPCSubnetReadOnlyAccess` |
| 3 | 读写 share：`AmazonEC2SubnetShare` 或自定义 `create-permission` |
| 4 | 不同 principal 可挂在**不同 resource share** 上，各挂不同 permission |

```bash
# 只读授权
aws ram associate-resource-share-permission \
  --resource-share-arn "{{user.share_arn}}" \
  --permission-arn "arn:aws:ram::aws:permission/AmazonVPCSubnetReadOnlyAccess" \
  --region "{{user.region}}" --output json

# 自定义策略模板（示例）
aws ram create-permission \
  --name "app-subnet-readonly-custom" \
  --resource-type "ec2:Subnet" \
  --policy-template '{"effect":"Allow","actions":["ec2:DescribeSubnets","ec2:CreateNetworkInterface"],"conditions":{}}' \
  --region "{{user.region}}" --output json
```

### 决策
| 需求 | Permission 示例 | 决策 |
|------|-----------------|------|
| 仅查看子网 | `AmazonVPCSubnetReadOnlyAccess` | `[AI_ASSIST]` |
| 创建 ENI 部署应用 | `AmazonEC2SubnetShare` | `[AI_ASSIST]` |
| 合作伙伴只读 Aurora | `AmazonRDSDBClusterReadOnlyAccess` | `[AI_ASSIST]` + `aws-rds-ops` 验证 |

---

## 场景 5：向已有共享追加新应用管理账号

### Prompt
```
又上线了一个应用管理账号 666666666666，把它加到现有的 shared-prod-subnets 共享里。
```

```bash
aws ram associate-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --principals "666666666666" \
  --region "{{user.region}}" --output json

aws ram get-resource-share-associations \
  --association-type PRINCIPAL \
  --resource-share-arns "{{user.share_arn}}" \
  --region "{{user.region}}" --output json
```

---

## 场景 6：撤销应用账号访问（离职/下线应用）

### Prompt
```
应用账号 333333333333 已下线，从所有 RAM 共享里移除它的访问权限。
```

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `list-principals` 或 `get-resource-share-associations` 定位该账号关联的 share |
| 2 | 对每个 share 执行 `disassociate-resource-share --principals 333333333333` |
| 3 | 验证 association 状态为 `DISASSOCIATED` |
| 4 | **不删除** share 本身（除非共享已无其他消费者） |

```bash
aws ram disassociate-resource-share \
  --resource-share-arn "{{user.share_arn}}" \
  --principals "333333333333" \
  --region "{{user.region}}" --output json
```

> **安全门**：`delete-resource-share` 仅当整个共享废弃时使用，需 `confirm=DELETE_RESOURCE_SHARE <arn>`。

---

## 场景 7：Aurora 集群跨账号只读共享（BI / 分析应用账号）

### Prompt
```
把 Aurora 集群 prod-aurora-analytics 只读共享给 BI 应用管理账号 777777777777。
```

### 跨技能链
```
1. [aws-aurora-ops] describe-db-clusters → 集群 ARN
2. [aws-ram-ops] create-resource-share + associate-resource-share-permission (ReadOnly)
3. [消费账号 aws-ram-ops] accept-resource-share-invitation
4. [aws-rds-ops / aws-aurora-ops] 消费账号 describe-db-clusters 验证可见
```

```bash
aws ram create-resource-share \
  --name "aurora-analytics-readonly" \
  --resource-arns "arn:aws:rds:{{user.region}}:111111111111:cluster:prod-aurora-analytics" \
  --principals "777777777777" \
  --region "{{user.region}}" --output json

aws ram associate-resource-share-permission \
  --resource-share-arn "{{output.resourceShareArn}}" \
  --permission-arn "arn:aws:ram::aws:permission/AmazonRDSDBClusterReadOnlyAccess" \
  --region "{{user.region}}" --output json
```

---

## 场景 8：安全组跨账号共享（应用账号复用统一网络策略）

### Prompt
```
平台团队维护了一套标准安全组，要让各应用管理账号在共享子网里复用这些 SG 规则。
```

```bash
aws ram create-resource-share \
  --name "platform-standard-sgs" \
  --resource-arns "arn:aws:ec2:{{user.region}}:111111111111:security-group/sg-platform-web" \
                  "arn:aws:ec2:{{user.region}}:111111111111:security-group/sg-platform-db" \
  --principals "arn:aws:organizations::111111111111:ou/o-abc/ou-workloads" \
  --region "{{user.region}}" --output json
```

消费账号用 `aws-ec2-ops` 创建实例时 `--security-group-ids` 引用共享 SG ID。

---

## 场景 9：外部合作伙伴账号共享（跨组织）

### Prompt
```
需要把专用子网共享给合作伙伴 AWS 账号 888888888888（不在我们 Organization 里）。
```

| 检查项 | 要求 |
|--------|------|
| `allow-external-principals` | 必须为 `true` |
| 邀请流程 | 合作伙伴账号必须 `accept-resource-share-invitation` |
| 合规 | `[MANUAL]` 安全评审 + 最小权限 Permission |

```bash
aws ram create-resource-share \
  --name "partner-dedicated-subnet" \
  --resource-arns "arn:aws:ec2:{{user.region}}:111111111111:subnet/subnet-partner" \
  --principals "888888888888" \
  --allow-external-principals \
  --region "{{user.region}}" --output json
```

---

## 场景 10：审计 — 应用管理账号获得了哪些共享资源

### Prompt
```
审计一下：应用管理账号 444444444444 当前能用到哪些别人共享过来的资源？
```

```bash
# 在消费账号 444444444444 执行
aws ram list-resources --region "{{user.region}}" --output json
aws ram get-resource-share-associations \
  --association-type PRINCIPAL \
  --region "{{user.region}}" --output json
aws ram get-resource-share-invitations --region "{{user.region}}" --output json
```

输出：按 `type`（`ec2:Subnet`、`ec2:SecurityGroup`、`rds:Cluster` 等）汇总 + `resourceOwnerId`（资源所有者账号）。

---

## 场景 11：替换共享 Permission（权限升级/降级）

### Prompt
```
数据分析账号的 Aurora 共享要从只读改成可创建克隆集群，怎么换 Permission？
```

```bash
aws ram replace-permission-associations \
  --resource-share-arn "{{user.share_arn}}" \
  --from-permission-arn "arn:aws:ram::aws:permission/AmazonRDSDBClusterReadOnlyAccess" \
  --to-permission-arn "arn:aws:ram::aws:permission/AmazonRDSDBClusterShare" \
  --region "{{user.region}}" --output json
```

> **决策**：`[MANUAL]` 权限扩大需变更审批；执行前 `get-resource-share-associations` 确认影响范围。

---

## 场景 12：跨技能 — 共享子网 + 消费账号 IAM 角色

### Prompt
```
子网已经通过 RAM 共享给应用账号了，应用账号里还要建什么 IAM 才能在里面起 EC2？
```

RAM 只解决**资源可见性**；消费账号内启动实例还需 IAM：

```
1. [aws-ram-ops] 确认 list-resources 子网 AVAILABLE
2. [aws-iam-ops] 消费账号创建/附加 ec2:RunInstances、ec2:CreateNetworkInterface 等策略
3. [aws-ec2-ops] RunInstances --subnet-id <共享子网 ID> --security-group-ids <共享 SG>
```

---

## Quick Reference

| 用户说 | 场景 | 决策 | 模块 |
|--------|------|------|------|
| "共享子网给应用账号" | 多账号网络共享 | `[AI_ASSIST]` | ram + vpc |
| "新账号接受 RAM 邀请" | 入驻 onboarding | `[AI_ASSIST]` | ram |
| "OU 下所有应用账号自动共享" | Organizations 批量授权 | `[MANUAL]` 需管理账号 | ram |
| "只读共享 Aurora/子网" | Permission 精细化授权 | `[AI_ASSIST]` | ram + aurora/rds |
| "加一个应用账号到现有共享" | associate principal | `[AI_ASSIST]` | ram |
| "下线应用账号移除访问" | disassociate principal | `[AI_ASSIST]` | ram |
| "合作伙伴跨组织共享" | external principals | `[MANUAL]` 合规评审 | ram |
| "审计应用账号有哪些共享资源" | list-resources / associations | `[AI_ASSIST]` | ram |
| "创建新的 AWS 应用管理账号" | **非 RAM 范围** | `[MANUAL]` | Organizations / 账号工厂 |
| "应用账号里建 IAM 角色跑 EC2" | RAM + IAM 组合 | `[AI_ASSIST]` | ram + iam + ec2 |
