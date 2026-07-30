# EC2 Skill — AIOps Prompt Examples

_Latest update: 2026-07-30_

EC2-LB 集成诊断、容量预测与 SSM 应用健康检查的典型 Prompt。

> **链接**：[troubleshooting.md](troubleshooting.md) · [aws-cli-usage.md](aws-cli-usage.md)

## 场景 1：LB 后端 EC2 不健康

### Prompt
`ALB 持续将实例 i-xxx 标记为 unhealthy，请检查并修复。`

### 流程
| 步骤 | 操作 | 决策 |
|------|------|------|
| 1 | `describe-instance-status` — 实例与状态检查 | |
| 2 | CloudWatch CPUUtilization + StatusCheckFailed（30 min） | |
| 3 | CloudTrail `lookup-events` 查近期变更 | |
| 4 | 症状 → 根因对照决策矩阵 | 见链接 |
| 5 | 轮询 StatusCheck 直至 ok | |

→ [EC2-LB 诊断流](troubleshooting.md#aiops-ec2-lb-cross-module-diagnostic-flow) · [自愈决策矩阵](troubleshooting.md#auto-healing-decision-matrix-for-lb-targets) · InstanceCheck 失败 → `[AUTO_HEAL]` reboot

## 场景 2：CPU 容量预测（FORECAST）

### Prompt
`EC2 CPU 持续上升，会很快到 100% 吗？`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `get-metric-data` — FORECAST 表达式预测 CPUUtilization |
| 2 | 对比 7d/14d 预测与阈值（如 80%） | |
| 3 | 建议 resize 或 scale-out | `[AI_ASSIST]` |

**注意**：MetricStat **必须**含 `Dimensions Name=InstanceId` — 缺 InstanceId 维度 FORECAST 无效。

→ [Predictive capacity FORECAST](troubleshooting.md#predictive-capacity-check-forecast)

## 场景 3：LB 健康检查失败 — SSM 诊断

### Prompt
`LB 健康检查失败，对目标实例跑 SSM 诊断找出原因。`

### 流程
| 步骤 | 操作 |
|------|------|
| 1 | `ssm send-command` — AWS-RunShellScript（端口、systemd、磁盘、内存） |
| 2 | 解析输出 — 端口未监听 / 磁盘满 / OOM |
| 3 | 重启服务或升级处理 | `[AI_ASSIST]` |

→ [SSM 诊断命令](troubleshooting.md#ssm-diagnostic-commands-for-application-health)

## Quick Reference

| 用户说 | 场景 | 决策 | 模块 |
|--------|------|------|------|
| "Instance keeps going unhealthy in LB" | 1 | `[AUTO_HEAL]` | ec2 + elb |
| "CPU is rising, will it hit 100%" | 2 | `[AI_ASSIST]` | ec2 + cw |
| "Health check fails, run SSM check" | 3 | `[AI_ASSIST]` | ec2 + ssm |
