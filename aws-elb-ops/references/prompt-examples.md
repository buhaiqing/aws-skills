# ELB Skill — AIOps Prompt Examples

_Latest update: 2026-05-31_

This document provides concrete user prompts that activate the `aws-elb-ops` skill's AIOps capabilities. Each example shows the user prompt and the full Agent execution flow including cross-module delegation.

> **双向链接**: SKILL.md → [prompt-examples.md](prompt-examples.md)
> **双向链接**: prompt-examples.md → [SKILL.md](../SKILL.md)

---

## 场景 1：ALB 健康检查波动诊断 + 自愈

### Prompt
```
我网站的 ALB 的健康检查最近老是有目标不健康，过一会又自己好了。
帮我看看怎么回事，能自动修复吗？
```

### Agent 执行流程
| 步骤 | 操作 | 决策 |
|------|------|------|
| 1. 发现需求 → 加载 `aws-elb-ops` FD-01 场景 | |
| 2. 采集数据：30 分钟 UnHealthyHostCount 趋势 | `aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name UnHealthyHostCount --statistics Maximum --period 60` | |
| 3. 检测抖动：Min 与 Avg 差异判断 | `aws elbv2 describe-target-health --target-group-arn {{tg_arn}}` | 识别 3 个 target 在 healthy/unhealthy 间切换 |
| 4. 根因诊断 → 委派 `aws-ec2-ops` | `aws ec2 describe-instance-status --instance-ids i-xxx` → StatusCheck 正常 | CPU 短期突增导致健康检查超时 |
| 5. 执行自愈 AH-01 | 注销 → 30s → 重新注册 → 验证 | `[AUTO_HEAL]` |
| 6. 验证结果 | 轮询直到 target == healthy | |
| 7. 反馈记录 | 记录自愈成功，标记 CPU 突增为已知模式 | |

```bash
# 核心自愈命令
aws elbv2 deregister-targets --target-group-arn {{tg_arn}} --targets Id=i-xxx
sleep 30
aws elbv2 register-targets --target-group-arn {{tg_arn}} --targets Id=i-xxx,Port=80
aws elbv2 describe-target-health --target-group-arn {{tg_arn}} --targets Id=i-xxx
```

---

## 场景 2：ALB 502 错误根因分析

### Prompt
```
用户说我们网站突然出现大量的 502 Bad Gateway 错误，
帮我查一下是哪里出了问题。
```

### Agent 执行流程
| 步骤 | 操作 | 跨模块委派 |
|------|------|-----------|
| 1. 发现问题 → `aws-elb-ops` RC-01 流程 | | |
| 2. 检查 ELB 错误率 | `aws cloudwatch get-metric-statistics --metric-name HTTPCode_ELB_5XX` | `aws-elb-ops` |
| 3. 检查 target 健康 | `aws elbv2 describe-target-health --target-group-arn {{tg_arn}}` | `aws-elb-ops` |
| 4. 检查 EC2 状态和 CPU | `aws ec2 describe-instance-status` + `aws cloudwatch get-metric-statistics CPUUtilization` | → `aws-ec2-ops` |
| 5. 检查安全组变更 | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::EC2::SecurityGroup` | → `aws-cloudtrail-ops` |
| 6. 生成 RCA 报告 | 时序对齐 T0: CPU↑ → 502↑ | |
| 7. 推荐操作 | `[AI_ASSIST]` 扩容 EC2 或添加更多 target | |

```bash
# 502 RCA 多步诊断
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name HTTPCode_ELB_5XX --statistics Sum --period 60 --start-time "$(date -d '-1 hour' -u ...)"
aws ec2 describe-instance-status --instance-ids i-xxx
aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::EC2::SecurityGroup --start-time "$(date -d '-2 hours' -u ...)"
```

---

## 场景 3：ALB 延迟突增分析

### Prompt
```
我监控到 API 响应时间变慢了，p99 从 200ms 涨到了 800ms，
是不是后端服务器出了问题？
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. 采集 p50/p90/p99 延迟趋势 | `aws cloudwatch get-metric-data` with 3 个 statistic |
| 2. 检查所有 URL 还是特定 URL 慢 | `aws logs start-query` 分析 ALB Access Logs — 按 request_url 分组 |
| 3. 跨模块：检查 EC2 CPU 趋势 | `aws cloudwatch get-metric-statistics CPUUtilization` → 委派 `aws-ec2-ops` |
| 4. 跨模块：检查 RDS 慢查询（如适用） | → 委派 `aws-rds-ops` |
| 5. 时序对齐分析 | |
| 6. 输出 RCA + 推荐操作 | `[AI_ASSIST]` 扩容/优化/回滚 |

```bash
# 延迟多维度分析
aws cloudwatch get-metric-data --metric-data-queries '[
  {"Id":"p50","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":300,"Stat":"p50"}},
  {"Id":"p90","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":300,"Stat":"p90"}},
  {"Id":"p99","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":300,"Stat":"p99"}}
]'
```

---

## 场景 4：容量预测 + 提前预警

### Prompt
```
马上要到双十一了，帮我看看现在的 ALB 能不能扛住流量增长。
```

### Agent 执行流程
| 步骤 | 操作 | 决策 |
|------|------|------|
| 1. 采集 90 天 RequestCount + ActiveConnectionCount 数据 | `aws cloudwatch get-metric-data ...` | |
| 2. FORECAST 未来 7 天趋势 | `Expression: FORECAST(m1, "linear", 168)` | |
| 3. 对比当前配额上限 | `aws service-quotas get-service-quota` | |
| 4. 检查历史流量峰值模式 | 季节性分解：日常 / 周 / 月模式 | |
| 5. 生成容量报告 | | |
| 6. 推荐操作 | | `[AI_ASSIST]` |

```bash
# 容量预测
aws cloudwatch get-metric-data --metric-data-queries '[
  {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"ActiveConnectionCount","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":3600,"Stat":"Maximum"}},
  {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)","Label":"7-Day Forecast"}
]'
```

```
=== 容量报告 ===
  ALB: my-web-alb
  当前峰值连接数: 15,000 (上限 50,000)
  7 天预测峰值: 22,000 → ✅ 正常
  30 天预测峰值: 35,000 → ⚠️ 超过 80% 阈值
  建议: [AI_ASSIST] 考虑 2 个月内扩容
```

---

## 场景 5：闲置负载均衡器检测 + 成本优化

### Prompt
```
帮我查一下有没有闲置的负载均衡器，我想省点钱。
```

### Agent 执行流程
| 步骤 | 操作 | 决策 |
|------|------|------|
| 1. 列出所有 ALB | `aws elbv2 describe-load-balancers` | |
| 2. 逐个检查 24h 连接数 | `aws cloudwatch get-metric-statistics --metric-name ActiveConnectionCount --period 86400` | |
| 3. 筛选 ActiveConnectionCount = 0 的 LB | | |
| 4. 检查有无下游依赖 | Route53 别名、CloudFront 源站、AutoScaling Group | |
| 5. 生成优化报告 | | |

```bash
# 闲置 LB 检测
aws elbv2 describe-load-balancers --query "LoadBalancers[].LoadBalancerArn" --output text | while read arn; do
  sum=$(aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name ActiveConnectionCount --dimensions Name=LoadBalancer,Value=$arn --statistics Sum --period 86400 --start-time "$(date -d '-24 hours' -u ...)" --query "Datapoints[0].Sum" --output text)
  [ "$sum" = "0.0" ] && echo "IDLE: $arn"
done
```

```
=== 成本优化报告 ===
  🟢 my-web-alb: 活跃中 (15,000 连接/天)
  🔴 staging-alb: 0 连接持续 7 天 → [AI_ASSIST] 建议关闭（省 ~$20/月）
  🟢 internal-nlb: 活跃中 (5,000 流/天)
```

---

## 场景 6：NLB 连接超时排查

### Prompt
```
用户反馈通过 NLB 访问服务经常超时，帮我查一下是网络问题还是后端问题。
```

### Agent 执行流程
| 步骤 | 操作 | 跨模块委派 |
|------|------|-----------|
| 1. 检查 NLB 流数 | `aws cloudwatch get-metric-statistics --namespace AWS/NetworkELB --metric-name ActiveFlowCount` | `aws-elb-ops` |
| 2. 检查 NAT Gateway | `aws cloudwatch get-metric-statistics --namespace AWS/NATGateway --metric-name ActiveConnectionCount PacketsDropCount` | → `aws-vpc-ops` |
| 3. VPC Flow Log 分析 | 查询 REJECT 记录和 packets=0 的连接 | → `aws-vpc-ops` |
| 4. 检查 target 端口可达性 | `nc -zv {{target_ip}} {{port}}` | → `aws-ec2-ops` |
| 5. 生成 RCA | | |

```bash
# NAT Gateway 连接数检查
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway --metric-name PacketsDropCount --statistics Sum --period 300

# VPC Flow Log 分析
aws logs start-query --log-group-name /aws/vpc/flow-logs/{{vpc_name}} --query-string 'fields @timestamp, srcaddr, dstaddr, dstport, action, packets | filter action = "REJECT" | stats count() by dstaddr | sort count desc | limit 10'
```

---

## 场景 7：删除负载均衡器前的变更影响分析

### Prompt
```
把测试环境的 ALB staging-alb 删掉吧。
```

### Agent 执行流程
| 步骤 | 操作 | 决策 |
|------|------|------|
| 1. 安全门禁：需要用户确认 | "删除 LB 会影响以下依赖，是否继续？" | `[MANUAL]` |
| 2. 检查 Route53 别名记录 | `aws route53 list-resource-record-sets` | → `aws-route53-ops` |
| 3. 检查 CloudFront 源站 | `aws cloudfront list-distributions` | → `aws-cloudfront-ops` |
| 4. 检查 AutoScaling Group | `aws autoscaling describe-auto-scaling-groups` | |
| 5. 生成影响报告 + 等待确认 | | |

```
⚠️ 删除 staging-alb 影响分析:
  - Route53 别名: 3 条记录 (DNS 解析会中断)
  - CloudFront 源站: 1 个分布 (CDN 会 503)
  - AutoScaling Group: 无关联
  风险等级: MEDIUM
  确认请回复: DELETE staging-alb
```

---

## 场景 8：ALB 合规基线自动修复

### Prompt
```
帮我检查一下所有 ALB 的合规配置，有问题的自动修复。
```

### Agent 执行流程
| 步骤 | 操作 | 决策 |
|------|------|------|
| 1. 列出所有 ALB | `aws elbv2 describe-load-balancers --query "LoadBalancers[?Type=='application']"` | |
| 2. 逐个检查属性 | `aws elbv2 describe-load-balancer-attributes` | |
| 3. 对照合规基线 | deletion_protection=true, cross_zone=true, access_logs=true, invalid_header_drop=true | |
| 4. 自动修复合规项 | | `[AUTO_HEAL]` |
| 5. 对 access_logs 提建议 | 需要 S3 桶确认 | `[AI_ASSIST]` |
| 6. 生成报告 | | |

```bash
# 合规检查 + 自动修复
deletion_protection=$(aws elbv2 describe-load-balancer-attributes --load-balancer-arn {{arn}} --query "Attributes[?Key=='deletion_protection.enabled'].Value" --output text)
if [ "$deletion_protection" != "true" ]; then
  aws elbv2 modify-load-balancer-attributes --load-balancer-arn {{arn}} --attributes Key=deletion_protection.enabled,Value=true
  echo "[AUTO_HEAL] 已开启 deletion_protection"
fi
```

---

## 场景 9：跨模块 AIOps — 全链路 502 自愈

### Prompt
```
我的网站报 502 了，帮我一条龙查到底，能修的直接修。
```

### Agent 执行流程（完整六层闭环）
| 层 | 步骤 | 操作 | 模块 |
|----|------|------|------|
| 🔵 数据采集 | 1. 获取 502 时间点、target 健康状态、EC2 指标 | `get-metric-data` + `describe-target-health` + `describe-instance-status` | `aws-elb-ops` → `aws-ec2-ops` |
| 🟢 检测分析 | 2. 时序对齐：CPU↑ 时间点与 502↑ 匹配 | Time-Series Correlation | `aws-elb-ops` |
| 🟡 根因诊断 | 3. 定位到 EC2 CPU 97%，无变更事件 | 关联 CloudTrail 确认无 SG/LB 变更 | `aws-cloudtrail-ops` |
| 🟠 决策规划 | 4. CPU 饱和 → resize 方案 | `[AI_ASSIST]` 确认扩容 | |
| 🔴 自动执行 | 5. 停止 → 改类型 → 启动 → 重注册 | `modify-instance-attribute` + `register-targets` | `aws-ec2-ops` → `aws-elb-ops` |
| 🟣 反馈学习 | 6. 记录成功经验 | 知识库更新 | |

```bash
# 全链路诊断命令链
echo "=== Step 1: 502 检测 ==="
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name HTTPCode_ELB_5XX --statistics Sum --period 60

echo "=== Step 2: Target 健康 ==="
aws elbv2 describe-target-health --target-group-arn {{tg_arn}}

echo "=== Step 3: EC2 诊断 ==="
aws ec2 describe-instance-status --instance-ids {{target_id}}
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Value={{target_id}} --statistics Average --period 300

echo "=== Step 4: 变更审计 ==="
aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::ElasticLoadBalancing::LoadBalancer
```

---

## 场景 10：ALB 证书即将过期处理

### Prompt
```
我的 ALB 绑定的 SSL 证书下个月就到期了，帮我处理一下。
```

### Agent 执行流程
| 步骤 | 操作 | 跨模块委派 |
|------|------|-----------|
| 1. 查询证书信息 | `aws acm describe-certificate --certificate-arn {{cert_arn}}` | → `aws-acm-ops` |
| 2. 判断证书类型：DNS 验证 → 自动续期已生效 | `RenewalEligibility == ELIGIBLE` | `aws-acm-ops` |
| 3. 验证续期后证书已绑定到 LB | `aws elbv2 describe-listeners` 确认 listener 引用新 cert | `aws-elb-ops` |
| 4. 通知用户续期状态 | | |

```bash
# 证书检查
aws acm describe-certificate --certificate-arn {{cert_arn}} --query "Certificate.{Domain:DomainName,Status:Status,Expiry:NotAfter,Type:Type,RenewalEligibility:RenewalEligibility}"
```

---

## Prompt 速查表

| 用户说… | 触发 AIOps 场景 | 决策类型 | 涉及模块 |
|---------|--------------|----------|---------|
| "帮我看看 LB 健康检查怎么老失败" | FD-01 目标抖动检测 → AH-01 自愈 | `[AUTO_HEAL]` | elb |
| "网站报 502 怎么回事" | RC-01 502 RCA → 全链路诊断 | `[AI_ASSIST]` | elb → ec2 → vpc → ct |
| "接口突然变慢了" | FD-02 延迟突增 → RC-02 高延迟 RCA | `[AI_ASSIST]` | elb → ec2 → rds |
| "双十一流量扛得住吗" | PA-01 容量预测 → FORECAST | `[AI_ASSIST]` | elb + cw |
| "帮我查查闲置的 LB" | CO-01 闲置 LB 检测 | `[AI_ASSIST]` | elb + cw |
| "把 LB 删掉" | CM-01 变更影响分析 | `[MANUAL]` | elb → r53 → cf |
| "检查 LB 合规配置" | CM-04 合规扫描 → 自动修复 | `[AUTO_HEAL]` | elb |
| "证书快过期了" | PA-03 证书到期预警 | `[AUTO_HEAL]` | acm + elb |
| "一条龙帮我修 502" | 全链路六层闭环 | 混合 | 全 6 模块 |