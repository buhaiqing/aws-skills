# WAF Skill — Prompt Examples

_Latest update: 2026-05-31_

This document provides concrete user prompts for the `aws-waf-ops` skill.

> **双向链接**: SKILL.md → [prompt-examples.md](prompt-examples.md)
> **双向链接**: prompt-examples.md → [SKILL.md](../SKILL.md)

---

## 场景 1：已有 ALB，添加 WAF 保护

### 用户说
```
我有个正在运行的 ALB 叫 my-web-alb，帮我加上 WAF 防护。
```

### Agent 自动执行

| 步骤 | 操作 | 委派 |
|------|------|------|
| 1. 发现 ALB 是否存在 | `aws elbv2 describe-load-balancers --names my-web-alb` | → `aws-elb-ops` |
| 2. 创建 Web ACL (CommonRuleSet + RateLimit) | `aws wafv2 create-web-acl` | `aws-waf-ops` |
| 3. 关联 ALB | `aws wafv2 associate-web-acl --resource-arn {{lb_arn}}` | `aws-waf-ops` |
| 4. 验证 | `aws wafv2 get-web-acl-for-resource` + CloudWatch metrics | `aws-waf-ops` + `aws-cloudwatch-ops` |
| 5. 建议后续 | 观察 3 天后把 CommonRuleSet 从 Count 切到 Block | `[AI_ASSIST]` |

```bash
# Agent 自动执行的完整命令链
LB_ARN=$(aws elbv2 describe-load-balancers --names my-web-alb --query "LoadBalancers[0].LoadBalancerArn" --output text)

echo "=== 创建 Web ACL ==="
WAF_ID=$(aws wafv2 create-web-acl --name waf-my-web-alb --scope REGIONAL \
  --default-action Allow={} \
  --rules '[
    {"Name":"CommonRuleSet","Priority":0,"Statement":{"ManagedRuleGroupStatement":{"VendorName":"AWS","Name":"AWSManagedRulesCommonRuleSet"}},"OverrideAction":{"Count":{}},"VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"CommonRuleSet"}},
    {"Name":"RateLimit","Priority":1,"Statement":{"RateBasedStatement":{"Limit":2000,"AggregateKeyType":"IP"}},"Action":{"Block":{}},"VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"RateLimit"}}
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=waf-my-web-alb \
  --query 'Summary.Id' --output text)

WAF_ARN=$(aws wafv2 get-web-acl --name waf-my-web-alb --scope REGIONAL --id $WAF_ID --query 'WebACL.ARN' --output text)

echo "=== 关联 ALB ==="
aws wafv2 associate-web-acl --web-acl-arn "$WAF_ARN" --resource-arn "$LB_ARN"

echo "✅ WAF 已关联到 my-web-alb"
echo "   3 天后请检查 BlockedRequests 指标，确认规则无误后切换到 Block 模式"
```

---

## 场景 2：网站被攻击，紧急启用防御

### 用户说
```
网站突然收到大量恶意请求，帮我紧急开启 WAF 防护。
```

### Agent 执行（AIOps 模式）

| 步骤 | 操作 | 决策 |
|------|------|------|
| 1. 检查 ALB 流量异常 | `aws cloudwatch get-metric-data` 检查 RequestCount | → `aws-elb-ops` |
| 2. 检查是否有 WAF 已关联 | `aws wafv2 get-web-acl-for-resource` | |
| 3. 无 WAF → 创建并关联（带紧急规则） | 创建 Web ACL + 严格限速 | `[AUTO_HEAL]` |
| 4. 已有 WAF → 收紧规则 | 降低 RateLimit 至 500 req/s | `[AUTO_HEAL]` |
| 5. 打开采样请求查看攻击特征 | `aws wafv2 get-sampled-requests` | |

```bash
# 紧急限速：降低速率阈值到 500 req/s
aws wafv2 update-web-acl --name {{web_acl_name}} --scope REGIONAL --id {{id}} \
  --rules '[...,{"Name":"EmergencyRateLimit","Priority":100,"Statement":{"RateBasedStatement":{"Limit":500,"AggregateKeyType":"IP"}},"Action":{"Block":{}},"VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"EmergencyRateLimit"}}]'
```

---

## 场景 3：查看 WAF 防护效果

### 用户说
```
上次加了 WAF 之后，帮我看看拦截了多少恶意请求。
```

### Agent 执行

```bash
aws cloudwatch get-metric-statistics --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=WebACL,Value={{web_acl_name}} Name=Rule,Value=All \
  --statistics Sum --period 86400 \
  --start-time "$(date -d '-7 days' -u ...)" --end-time "$(date -u ...)"
```

```
=== WAF 防护报告 (最近 7 天) ===
  Web ACL: waf-my-web-alb
  关联资源: my-web-alb
  总拦截请求: 12,847
  Top 拦截规则:
    - RateLimit (限速): 8,521 次 (66%)
    - AWS-AWSManagedRulesCommonRuleSet: 4,326 次 (34%)
    其中:
      - CrossSiteScripting_XSS: 2,104 次
      - SQLi: 1,843 次
      - LFI: 379 次
```

## Prompt 速查表

| 用户说… | 触发场景 | 决策 | 涉及模块 |
|---------|---------|------|---------|
| "我的 ALB 叫 xxx，帮我加 WAF" | 场景 1: 已有 ALB + WAF | `[AI_ASSIST]` | waf + elb |
| "网站被攻击了" | 场景 2: 紧急限速 | `[AUTO_HEAL]` | waf + elb |
| "WAF 拦截了多少请求" | 场景 3: 防护报告 | `[AI_ASSIST]` | waf + cw |
| "新 ALB 创建时自动加 WAF" | 编排: elb→waf | `[AI_ASSIST]` | elb + waf |