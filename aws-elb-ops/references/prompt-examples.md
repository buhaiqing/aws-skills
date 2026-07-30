# ELB Skill — Prompt Examples (ALB/NLB/CLB + AIOps)

_Latest update: 2026-07-30_

典型 Prompt 与 Agent 流程。破坏性操作须带 `confirm=` token → [prompt-templates.md](prompt-templates.md)。

> **链接**：[SKILL.md](../SKILL.md) · [aws-cli-usage.md](aws-cli-usage.md) · [troubleshooting.md](troubleshooting.md)

## 场景 1：ALB 健康检查波动 + 自愈

### Prompt
`ALB 目标老是不健康，过一会又好了，帮我查并自动修复。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `cloudwatch` UnHealthyHostCount 30min + `describe-target-health` |
| 2 | → `aws-ec2-ops` `describe-instance-status` 排除 StatusCheck |
| 3 | AH-01：`deregister-targets`（须 confirm）→ 30s → `register-targets` → 轮询 healthy |

→ [AH-01](aws-cli-usage.md#ah-01-target-re-registration-auto_heal) · `[AUTO_HEAL]`

## 场景 2：502 错误根因 / 全链路自愈

### Prompt
`网站大量 502，查根因；能修的直接修。`

### 流程
| 步骤 | 操作 | 委派 |
|------|------|------|
| 1 | `HTTPCode_ELB_5XX` + `describe-target-health` | elb |
| 2 | `describe-instance-status` + CPU | → ec2 |
| 3 | `cloudtrail lookup-events` SG 变更 | → cloudtrail |
| 4 | 时序对齐 RCA → resize/重注册 | ec2 → elb |

→ [RC-01](aws-cli-usage.md#rc-01-502-error-diagnostic-chain) · `[AI_ASSIST]` / 混合

## 场景 3：延迟突增 / 容量预测

### Prompt
`API p99 从 200ms 涨到 800ms` 或 `大促前 ALB 能否扛住流量？`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `get-metric-data` p50/p90/p99 或 90 天 RequestCount |
| 2 | `FORECAST(m1,"linear",168)` + `service-quotas get-service-quota` |
| 3 | → ec2/rds 后端检查 · 容量报告 + `[AI_ASSIST]` |

→ [FORECAST](aws-cli-usage.md#forecast-capacity-planning)

## 场景 4：闲置 LB 成本优化

### Prompt
`有没有闲置负载均衡器可以省钱？`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `describe-load-balancers` + 24h ActiveConnectionCount = 0 |
| 2 | 查 Route53/CloudFront/ASG 依赖 → 成本报告 + `[AI_ASSIST]` |

## 场景 5：删除 LB 前影响分析

### Prompt
`把测试环境 ALB staging-alb 删掉。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `describe-load-balancers` → ARN；`describe-listeners` 须为空 |
| 2 | → route53 别名 · → cloudfront 源站 · 影响报告 |
| 3 | 等待 `confirm=DELETE_LB <lb-arn>` → `delete-load-balancer` |

```
确认: confirm=DELETE_LB arn:aws:elasticloadbalancing:region:acct:loadbalancer/app/staging-alb/id
```

→ `[MANUAL]` · 无 confirm → SAFETY_FAIL

## 场景 6：目标注销（A12 排水阈值）

### Prompt
`从 target group 注销一半 healthy 目标做维护。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `describe-target-health` 统计 healthy；计算注销比例 |
| 2 | ≥50% → `confirm=DEREGISTER_DRAIN <tg-arn> count=<n>/<total>` |
| 3 | 100% → `confirm=DEREGISTER_ALL <tg-arn>` → `deregister-targets` |

→ [Confirmation Strings](prompt-templates.md#confirmation-strings-mandatory-for-every-destructive-op) · `[MANUAL]`

## Prompt 速查表

| 用户说… | 场景 | 决策 | 模块 |
|---------|------|------|------|
| "LB 健康检查老失败" | FD-01 → AH-01 | `[AUTO_HEAL]` | elb |
| "网站报 502" | RC-01 | `[AI_ASSIST]` | elb → ec2 → ct |
| "接口变慢" / "流量扛得住吗" | FD-02 / PA-01 | `[AI_ASSIST]` | elb + cw |
| "查闲置 LB" | CO-01 | `[AI_ASSIST]` | elb + cw |
| "把 LB 删掉" | CM-01 | `[MANUAL]` + `confirm=DELETE_LB` | elb → r53 |
| "注销 target" | A12 | `[MANUAL]` + `confirm=DEREGISTER_*` | elb |
