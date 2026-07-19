# A1: 预测性容量预警执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement task-by-task.

**Goal**: 扩展 `aws-cloudwatch-ops`，集成预测算法，实现基于 14-day 趋势的主动容量预警

**Architecture**: 修改 `aws-cloudwatch-ops/SKILL.md` + 新建 `references/capacity-forecast-rules.md` + `scripts/capacity_forecast.py`

**Tech Stack**: Bash (CLI) + Python (预测算法) + Markdown

---

## Task A1.1: aws-cloudwatch-ops/SKILL.md — 扩展 Predictive Operations section

**Files**: Modify `aws-cloudwatch-ops/SKILL.md`

- [ ] **Step 1**: 在 `## Execution Flow Pattern` 后添加 `## Predictive Operations` 新 section：
  - `get-capacity-forecast` 操作定义
  - 输入参数：`{{user.resource_id}}`, `{{user.metric_name}}`, `{{user.forecast_days}}`（默认 7）
  - 输出格式：JSON（含 `forecast_7d_avg`, `alert_level`, `recommendation`）
- [ ] **Step 2**: 添加 `## Cross-Skill References`（aws-aiops-cruise 调用方式）
- [ ] **Step 3**: 校验 SKILL.md line count ≤ 120（C6 TE 验证）
- [ ] **Step 4**: commit `git commit -m "feat(cloudwatch): add predictive capacity operations"`

---

## Task A1.2: references/capacity-forecast-rules.md

**Files**: Create `aws-cloudwatch-ops/references/capacity-forecast-rules.md`

- [ ] **Step 1**: 编写 6 条预测规则（见 spec §3.3）：
  - CAP-FC-01: EC2 CPUUtilization
  - CAP-FC-02: ECS CPUUtilization
  - CAP-FC-03: RDS DatabaseConnections
  - CAP-FC-04: ElastiCache DatabaseMemoryUsagePercentage
  - CAP-FC-05: ALB ActiveConnectionCount
  - CAP-FC-06: Lambda ProvisionedConcurrencyUtilization
- [ ] **Step 2**: 每条规则包含：Rule ID + 服务 + 指标 + Warning/Critical 阈值 + 行动建议
- [ ] **Step 3**: commit `git commit -m "docs(cloudwatch): add capacity forecast rules"`

---

## Task A1.3: references/capacity-alert-thresholds.md

**Files**: Create `aws-cloudwatch-ops/references/capacity-alert-thresholds.md`

- [ ] **Step 1**: 编写阈值配置（可调参数，非硬编码）：
  - 默认 Warning: 80%
  - 默认 Critical: 90%
  - 数据点要求: ≥ 14 天历史
  - 预测周期: 7 天（可配置）
- [ ] **Step 2**: commit `git commit -m "docs(cloudwatch): add capacity alert thresholds"`

---

## Task A1.4: Python 预测算法实现

**Files**: Create `aws-cloudwatch-ops/scripts/capacity_forecast.py`

- [ ] **Step 1**: 实现 `predict_capacity()` 函数（线性回归趋势预测）：
  - 输入：CloudWatch `get_metric_statistics` 返回的 datapoints 列表
  - 输出：包含 `predictable`, `current_avg`, `forecast_7d_avg`, `forecast_7d_max`, `trend`, `will_exceed_warning`, `will_exceed_critical` 的 dict
- [ ] **Step 2**: 实现 `batch_forecast()` 函数（批量预测多个资源）
- [ ] **Step 3**: 边界处理：
  - 数据点 < 2 → `predictable: False`
  - slope = 0 → `trend: "stable"`
  - 预测值 clamp 到 [0, 100]
- [ ] **Step 4**: 编写单元测试 `test_capacity_forecast.py`（至少覆盖：正常数据/数据不足/完全稳定/持续上升）
- [ ] **Step 5**: 运行 pytest：`pytest aws-cloudwatch-ops/scripts/test_capacity_forecast.py -v`
- [ ] **Step 6**: commit `git commit -m "feat(cloudwatch): add capacity forecast algorithm"`

---

## Task A1.5: references/aws-cli-usage.md — 补充 forecast CLI

**Files**: Modify `aws-cloudwatch-ops/references/aws-cli-usage.md`

- [ ] **Step 1**: 追加 `get-metric-statistics` 的批量查询示例（用于预测数据收集）
- [ ] **Step 2**: 注意：AWS 无原生 forecast API，用 `get_metric_statistics` 收集历史 + Python 计算趋势
- [ ] **Step 3**: commit `git commit -m "docs(cloudwatch): update CLI usage for forecast operations"`

---

## Task A1.6: 集成到 aws-aiops-cruise

**Files**: Modify `aws-aiops-cruise/SKILL.md`（Cross-Skill References 表）

- [ ] **Step 1**: 在 Cross-Skill References 表追加一行：
  ```
  | Capacity forecast | `aws-cloudwatch-ops` | 14-day trend prediction, proactive resize |
  ```
- [ ] **Step 2**: commit `git commit -m "docs(cruise): add cloudwatch forecast to cross-skill refs"`
