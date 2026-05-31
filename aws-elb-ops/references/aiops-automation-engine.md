# AIOps Automation Engine — ELB 全链路自动编排

_Latest update: 2026-05-31_

> 目标：事件 → 数据采集 → 检测分析 → 根因诊断 → 决策 → 执行 → 验证 → 反馈
> 全链路自动化，AI 主导，0 人工介入（边界条件内）

---

## 1. 触发模式（如何启动闭环）

### 模式 A：CloudWatch Alarm 自动触发（推荐）

```
CloudWatch Alarm fires
  → SNS Topic
    → Lambda Function (webhook)
      → AI Agent 被唤醒
        → 加载 aws-elb-ops
          → 执行 AIOps 闭环
```

```bash
# 告警 → SNS → Lambda 触发链（CloudFormation 模板片段）
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  AIOpsTriggerFunction:
    Type: AWS::Lambda::Function
    Properties:
      Handler: index.handler
      Runtime: python3.12
      Code:
        ZipFile: |
          import json, urllib.request
          def handler(event, context):
              alarm = event['Records'][0]['Sns']['Message']
              # 调用 AI Agent API 触发诊断流程
              req = urllib.request.Request(
                  'https://agent-api/trigger/elb-aiops',
                  data=json.dumps({'alarm': alarm}).encode(),
                  headers={'Content-Type': 'application/json'})
              urllib.request.urlopen(req)
  AIOpsAlarmTopic:
    Type: AWS::SNS::Topic
    Properties:
      Subscription:
        - Protocol: lambda
          Endpoint: !GetAtt AIOpsTriggerFunction.Arn
```

### 模式 B：定时巡检（可选）

```
EventBridge Scheduler (每 15 分钟)
  → 调用 AI Agent
    → 执行健康扫描
      → 发现异常 → 自动进入闭环
```

### 模式 C：用户触发（手动）

```
用户输入问题
  → AI Agent 识别关键词
    → 加载 aws-elb-ops
      → 执行 AIOps 闭环
```

---

## 2. 自动闭环流水线（可执行流程）

### 2.1 入口：告警事件解析

```json
{
  "alarm_name": "my-alb-Latency-High",
  "namespace": "AWS/ApplicationELB",
  "metric": "TargetResponseTime",
  "statistic": "p99",
  "threshold": 1000,
  "trigger_time": "2026-05-31T10:23:00Z",
  "lb_arn": "arn:aws:elasticloadbalancing:...",
  "lb_name": "my-alb"
}
```

### 2.2 自动化流程定义

```
╔═══════════════════════════════════════════════════════════════════╗
║                     AIOps 自动闭环流水线                          ║
╚═══════════════════════════════════════════════════════════════════╝
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 1: 数据采集（自动）              │
│ 收集当前异常相关的所有指标和事件       │
├─────────────────────────────────────┤
│ → 固定执行的采集命令                  │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 2: 异常分类（自动）              │
│ 根据指标模式判断异常类型               │
├─────────────────────────────────────┤
│ 类型矩阵 → 命中哪个走哪个             │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 3: 根因诊断（自动 + 跨模块）     │
│ 按预定义的 RCA 链逐层诊断              │
├─────────────────────────────────────┤
│ 链式 → 委派各模块                    │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 4: 决策执行（自动执行）           │
│ 匹配决策表 → 执行修复                 │
├─────────────────────────────────────┤
│ 决策矩阵 → 选择动作                   │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 5: 效果验证（自动）              │
│ 验证修复后指标是否恢复                 │
├─────────────────────────────────────┤
│ 验证命令 → 成功/失败                  │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Step 6: 反馈记录（自动）              │
│ 记录本次闭环结果                      │
├─────────────────────────────────────┤
│ 反馈格式 → 存入知识库                 │
└─────────────────────────────────────┘
```

---

## 3. Step 1：数据采集（固定模板）

无论什么异常，AI Agent 自动执行以下采集命令——不询问用户：

```bash
# 固定数据采集模板 — Agent 自动执行
T0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
T0_30=$(date -d '-30 minutes' -u +%Y-%m-%dT%H:%M:%SZ)
T0_2h=$(date -d '-2 hours' -u +%Y-%m-%dT%H:%M:%SZ)

echo "[AIOPS] Step 1a: LB 状态"
aws elbv2 describe-load-balancers \
  --load-balancer-arns "{{lb_arn}}" \
  --query "LoadBalancers[0].{Name:LoadBalancerName,State:State.Code,Type:Type}"

echo "[AIOPS] Step 1b: 目标健康"
aws elbv2 describe-target-health --target-group-arn "{{tg_arn}}"

echo "[AIOPS] Step 1c: 关键指标"
aws cloudwatch get-metric-data --metric-data-queries '[
  {"Id":"latency","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":60,"Stat":"p99"}},
  {"Id":"errors","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"HTTPCode_Target_5XX","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":60,"Stat":"Sum"}},
  {"Id":"healthy","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"HealthyHostCount","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":60,"Stat":"Minimum"}},
  {"Id":"connections","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"ActiveConnectionCount","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":60,"Stat":"Maximum"}}
]' --start-time "$T0_30" --end-time "$T0"

echo "[AIOPS] Step 1d: 配置变更"
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::ElasticLoadBalancing::LoadBalancer \
  --start-time "$T0_2h" --end-time "$T0" \
  --query 'Events[].{Time:EventTime,Name:EventName}'

echo "[AIOPS] Step 1e: 后端实例状态"
for tid in ${{TARGET_IDS}}; do
  aws ec2 describe-instance-status --instance-ids "$tid" \
    --query 'InstanceStatuses[].{Id:InstanceId,System:SystemStatus.Status,Instance:InstanceStatus.Status}'
done
```

---

## 4. Step 2：异常分类（自动决策树）

AI Agent 根据 Step 1 采集的数据，按以下决策树自动分类：

```
              ┌── HTTPCode_ELB_5XX > 0? ──→ RC-01: 502错误
              │
    异常触发 ──┼── TargetResponseTime > 基线+3σ? ──→ RC-02: 延迟突增
    进入分类    │
              ├── UnHealthyHostCount > 0? ──→ RC-03: 目标不健康
              │
              ├── RejectedConnectionCount > 0? ──→ RC-04: 连接耗尽
              │
              ├── RequestCount 偏离季节性基线? ──→ FD-06: 流量异常
              │
              ├── ActiveConnectionCount 接近上限? ──→ PA-01: 容量预警
              │
              └── 以上都否? ──→ 标记为未知异常 → [AI_ASSIST]
```

```bash
# 自动分类逻辑（伪代码，由 AI Agent 推理执行）
# Agent 按以上决策树顺序执行判断
# 第一个匹配的分类即最终分类

echo "[AIOPS] Step 2: 异常分类"

# 1. 检查 502
elb_5xx=$(echo "$METRICS" | jq '.MetricDataResults[] | select(.Id=="errors") | .Values[0] // 0')
if [ "$(echo "$elb_5xx > 0" | bc -l)" = 1 ]; then
  echo "分类: RC-01 502错误"
  SCENARIO="RC-01"
fi

# 2. 检查延迟
p99=$(echo "$METRICS" | jq '.MetricDataResults[] | select(.Id=="latency") | .Values[0] // 0')
if [ "$(echo "$p99 > 1000" | bc -l)" = 1 ]; then
  echo "分类: RC-02 延迟突增"
  SCENARIO="RC-02"
fi

# 3. 检查健康
unhealthy=$(echo "$TARGET_HEALTH" | jq '[.TargetHealthDescriptions[] | select(.TargetHealth.State=="unhealthy")] | length')
if [ "$unhealthy" -gt 0 ]; then
  echo "分类: RC-03 目标不健康"
  SCENARIO="RC-03"
fi
```

---

## 5. Step 3：根因诊断（自动跨模块链）

根据 Step 2 的分类，自动执行对应的 RCA 链：

### 5.1 RC-01: 502 错误诊断链

```bash
# Agent 自动执行 — 不询问用户

# 委派 aws-ec2-ops: 检查 EC2 CPU
for tid in $TARGET_IDS; do
  CPU=$(aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=InstanceId,Value=$tid \
    --statistics Average --period 300 \
    --start-time "$T0_30" --end-time "$T0")
  echo "EC2 $tid: $CPU %"
done

# 委派 aws-cloudtrail-ops: 检查 SG 变更
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress \
  --start-time "$T0_2h" --end-time "$T0"

# 综合判定
# CPU > 90% → "根因: 容量饱和"
# StatusCheck failed → "根因: 系统/操作系统故障"
# SG 变更 → "根因: 安全组配置变更"
# 全正常 → "根因: 应用层问题"
```

### 5.2 RC-03: 目标不健康诊断链

```bash
# Agent 自动执行

# 判断：全部不健康还是部分不健康？
ALL=$(echo "$TARGET_HEALTH" | jq '[.TargetHealthDescriptions[].TargetHealth.State] | unique')

if echo "$ALL" | grep -q '"unhealthy"' && ! echo "$ALL" | grep -q '"healthy"'; then
  echo "全部不健康 → 应用层或SG问题"
  # → 检查健康检查路径
  aws elbv2 describe-target-groups --target-group-arns {{tg_arn}}
  # → 检查 SG 规则
  aws ec2 describe-security-groups --group-ids {{sg_ids}}
  echo "决策: [AI_ASSIST] 应用层/SG 问题需要人工确认"
else
  echo "部分不健康 → 逐个诊断并自愈"
  for tid in $UNHEALTHY_IDS; do
    echo "执行 AH-01 目标重注册"
    # 自动注销→等待→注册→验证
  done
  echo "决策: [AUTO_HEAL]"
fi
```

---

## 6. Step 4：决策执行（自动动作）

### 6.1 全局决策引擎

```
             异常分类结果
                  │
                  ▼
        ┌─────────────────────┐
        │ 匹配决策表          │
        └─────────┬───────────┘
                  │
        ┌─────────┴───────────┐
        │                     │
  命中 [AUTO_HEAL]      命中 [AI_ASSIST]
        │                     │
        ▼                     ▼
  自动执行命令          输出推荐方案
  跳过用户确认          等待用户确认
        │                     │
        ▼                     ▼
  执行验证命令          用户确认后执行
```

### 6.2 自动修复执行表（无人工介入）

| 条件 | 自动执行命令 | 验证方法 |
|------|------------|---------|
| AH-01: 单 target 不健康 | `deregister-targets → sleep 30 → register-targets` | Poll `describe-target-health` 直到 healthy |
| AH-03: cross_zone 未开启 | `modify-load-balancer-attributes cross_zone.enabled=true` | 检查返回值为 true |
| CM-04: deletion_protection 未开启 | `modify-load-balancer-attributes deletion_protection.enabled=true` | 检查返回值为 true |
| CM-04: invalid_header_drop 未开启 | `modify-load-balancer-attributes drop_invalid_header_fields.enabled=true` | 检查返回值为 true |
| AH-EC2-01: StatusCheckFailed_Instance | `reboot-instances` | Poll 直到 StatusCheck = ok |

```bash
# Agent 执行 [AUTO_HEAL] 的标准模式：
# 1. 不询问用户
# 2. 直接执行命令
# 3. 执行验证
# 4. 成功后通知（被动展示）
```

---

## 7. Step 5：效果验证（自动）

无论执行了什么动作，固定执行以下验证：

```bash
# 统一验证模板 — Agent 自动执行
echo "[AIOPS] Step 5a: 验证修复效果"
echo "验证目标: $SCENARIO 相关指标"

# 再次采集 5 分钟后的指标
sleep 30
aws cloudwatch get-metric-data --metric-data-queries '[
  {"Id":"'$METRIC'","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"'$METRIC'","Dimensions":[{"Name":"LoadBalancer","Value":"'$LB_ARN'"}]},"Period":60,"Stat":"'$STAT'"}}
]' --start-time "$(date -d '-2 minutes' -u ...)" --end-time "$(date -u ...)"

# 判定
# 指标恢复到阈值以下 → [SUCCESS] 闭环完成
# 指标未恢复 → [RETRY] 执行回退或降级策略
```

---

## 8. Step 6：反馈记录（自动）

每次闭环的最终步骤——自动记录结果：

```json
// 反馈记录格式 — Agent 自动写入
{
  "timestamp": "2026-05-31T10:23:00Z",
  "scenario": "RC-01",
  "trigger": "HTTPCode_ELB_5XX > 0",
  "data_collection_ms": 3420,
  "classification": "502错误",
  "rca_result": {
    "root_cause": "EC2 CPU 97% → 健康检查超时",
    "confidence": 0.85
  },
  "decision": "[AUTO_HEAL]",
  "action": "AH-EC2-02 resize t3.medium→t3.large",
  "action_success": true,
  "verification_ms": 45000,
  "mttr_ms": 120000,
  "knowledge_update": "新增模式: CPU高→502→扩容"
}
```

---

## 9. 完整自动化示例（AI Agent 执行日志）

```
=== AIOps 自动闭环 === 2026-05-31 10:23:00 UTC ===

[TRIGGER] CloudWatch Alarm: my-alb-HealthyHosts-Low → ALARM

[STEP 1] 自动数据采集...
  ✓ LB 状态: active
  ✓ Target 健康: 2/5 unhealthy [i-xxx, i-yyy]
  ✓ 指标趋势: HealthyHostCount 5→3→2 (30min)
  ✓ CloudTrail: 无变更事件
  ✓ EC2 状态: i-xxx CPU 95%, StatusCheck=ok

[STEP 2] 异常分类...
  → 匹配 RC-03: 目标不健康
  → 子类型: 部分不健康 (2/5)

[STEP 3] 根因诊断...
  → CPU 95% — 容量饱和
  → 决策: [AUTO_HEAL] AH-01 目标重注册

[STEP 4] 自动执行...
  ✓ Deregister i-xxx
  ✓ Wait 30s
  ✓ Re-register i-xxx
  ✓ Verify: healthy after 45s
  ✓ Deregister i-yyy
  ✓ Wait 30s
  ✓ Re-register i-yyy
  ✓ Verify: healthy after 50s

[STEP 5] 效果验证...
  ✓ HealthyHostCount: 5/5 (已恢复)
  ✓ TargetResponseTime: 180ms (正常)

[STEP 6] 反馈记录...
  ✓ 已写入知识库
  ✓ MTTR: 4分30秒

=== 闭环完成 === 自愈成功 ===
```

---

## 10. 边界条件处理

| 条件 | 引擎行为 |
|------|---------|
| [AUTO_HEAL] 执行失败 1 次 | 重试一次 |
| [AUTO_HEAL] 执行失败 2 次 | 降级为 `[MANUAL]` → 创建 ticket |
| 首次出现的异常模式 | 自动降级为 `[AI_ASSIST]` → 标记为新模式 |
| 涉及数据删除 | 始终 `[MANUAL]` |
| 成本变更 > $100/月 | 降级为 `[AI_ASSIST]` → 需确认 |
| 跨账号操作 | 始终 `[MANUAL]` |

```bash
# 降级触发 — Agent 自动执行
ATTEMPT=1
while [ $ATTEMPT -le 2 ]; do
  # 执行修复
  if verify_success; then
    echo "[AUTO_HEAL] 成功"
    break
  fi
  ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -gt 2 ]; then
  echo "[AUTO_HEAL] 两次失败 → 降级为 [MANUAL]"
  echo "创建运维事件: 自愈失败，需人工介入"
fi
```