# A2: 拓扑因果图谱执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement task-by-task.

**Goal**: 扩展 `aws-topo-discovery`，构建 X-Ray Trace + CloudWatch Service Lens 拓扑，生成因果链用于 RCA

**Architecture**: 修改 `aws-topo-discovery/SKILL.md` + 新建 `scripts/causal-graph.sh` + `scripts/causal_inference.py` + `references/xray-api-usage.md` + `references/causal-rules.md`

**Tech Stack**: Bash (CLI) + Python (因果推理) + Markdown + JSON

---

## Task A2.1: aws-topo-discovery/SKILL.md — 扩展 Causal Graph section

**Files**: Modify `aws-topo-discovery/SKILL.md`

- [ ] **Step 1**: 添加 `## Causal Graph Operations` section：
  - `get-causal-graph` 操作：从 X-Ray trace 构建服务调用拓扑
  - `find-root-cause` 操作：基于错误率溯源
  - 输入：`{{user.time_window}}`（默认最近 24h）, `{{user.target_service}}`
  - 输出：JSON（含 `services`, `edges`, `anomalies`, `root_cause_candidates`）
- [ ] **Step 2**: 添加 `## Quality Gate (GCL)` section（recommended, max_iter=3，只读）
- [ ] **Step 3**: 校验 SKILL.md line count ≤ 120（C6 TE 验证）
- [ ] **Step 4**: commit `git commit -m "feat(topo): add causal graph operations to aws-topo-discovery"`

---

## Task A2.2: scripts/causal-graph.sh

**Files**: Create `aws-topo-discovery/scripts/causal-graph.sh`

- [ ] **Step 1**: 编写 X-Ray Service Graph 收集脚本：
  - `get-service-graph` → 获取服务拓扑
  - `batch-get-traces-summaries` → 获取 trace 摘要
  - `get-error-summaries` → 获取错误分布
- [ ] **Step 2**: 输出 JSON 格式的 Service Graph
- [ ] **Step 3**: 处理无 X-Ray 数据的 fallback（优雅降级）：
  ```bash
  if ! aws xray get-service-graph ...; then
    echo "X-Ray not enabled, falling back to CloudWatch metrics"
    # 调用 CloudWatch 的替代逻辑
  fi
  ```
- [ ] **Step 4**: commit `git commit -m "feat(topo): add causal-graph.sh X-Ray collector"`

---

## Task A2.3: scripts/causal_inference.py

**Files**: Create `aws-topo-discovery/scripts/causal_inference.py`

- [ ] **Step 1**: 实现 `CausalGraph` 类（见 spec §3.2）：
  - `add_trace(segments)` — 从 X-Ray trace 添加数据
  - `build_edges()` — 构建 CausalEdge 列表
  - `find_root_cause(target_service, error_rate_threshold)` — BFS 溯源
- [ ] **Step 2**: 实现 `calculate_error_rates()` — 计算每个服务的错误率
- [ ] **Step 3**: 实现 `detect_anomalies()` — 基于 baseline 的异常检测
- [ ] **Step 4**: 编写单元测试 `test_causal_inference.py`（覆盖：正常调用链/有错误的上游/无数据降级）
- [ ] **Step 5**: 运行 pytest：`pytest aws-topo-discovery/scripts/test_causal_inference.py -v`
- [ ] **Step 6**: commit `git commit -m "feat(topo): add causal inference engine"`

---

## Task A2.4: references/xray-api-usage.md + service-lens-usage.md

**Files**: Create `aws-topo-discovery/references/xray-api-usage.md`, `aws-topo-discovery/references/service-lens-usage.md`

- [ ] **Step 1**: `xray-api-usage.md`：
  - `get-service-graph`（service map + edges）
  - `batch-get-traces-summaries`（trace details）
  - `get-error-summaries`（error distribution）
  - 每个带 JSON path 示例
- [ ] **Step 2**: `service-lens-usage.md`：
  - CloudWatch ServiceLens（应用层面的服务依赖图）
  - `get-insight-rules`（CloudWatch Contributor Insights）
- [ ] **Step 3**: commit `git commit -m "docs(topo): add X-Ray and Service Lens API references"`

---

## Task A2.5: references/causal-rules.md

**Files**: Create `aws-topo-discovery/references/causal-rules.md`

- [ ] **Step 1**: 编写 5 条因果推断规则（见 spec §3.3）：
  - CAUSAL-01: ALB 5xx 溯源
  - CAUSAL-02: RDS 连接超时溯源
  - CAUSAL-03: Lambda 超时溯源
  - CAUSAL-04: ECS 任务重启溯源
  - CAUSAL-05: NAT Gateway 丢包溯源
- [ ] **Step 2**: 每条包含：Rule ID + 场景 + 因果逻辑（pseudo-code）+ X-Ray trace 字段映射
- [ ] **Step 3**: commit `git commit -m "docs(topo): add causal inference rules"`

---

## Task A2.6: assets/causal-graph-template.json

**Files**: Create `aws-topo-discovery/assets/causal-graph-template.json`

- [ ] **Step 1**: 编写输出模板（与 spec §4 JSON schema 对齐）
- [ ] **Step 2**: 包含 services/edges/anomalies/root_cause_candidates 四个部分
- [ ] **Step 3**: commit `git commit -m "assets(topo): add causal graph output template"`

---

## Task A2.7: 集成到 aws-aiops-orchestrator

**Files**: Modify `aws-aiops-orchestrator/SKILL.md` 或 `references/runbook-recipes.md`

- [ ] **Step 1**: 在 RCA 流程描述中添加：步骤 2 → 调用 `aws-topo-discovery get-causal-graph` → 步骤 3 → `find-root-cause`
- [ ] **Step 2**: commit `git commit -m "docs(orchestrator): integrate causal graph into RCA flow"`
