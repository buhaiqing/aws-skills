# Level 3 关联覆盖盲区补全 — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 8 个未接入 cruise/orchestrator 的 `aws-<svc>-ops` 技能补全委托路由 + inference rules，分 3 期迭代，每期 GCL 评审。

**Architecture:** 沿用 `_inference.py` 现有内联模式（单一 `apply_chain_inference` 函数内按 `resource_type` 分组循环），新增 8 段规则逻辑；路由表在 cruise/orchestrator SKILL.md 元数据层补充；规则语义在新建 `inference-rules-addendum.md` 定义。

**Tech Stack:** Python 3.10+（现有 `_inference.py` / `_shared.py` 同模式）、pytest、Markdown。

**关键事实（已核实磁盘代码）：**
- `apply_chain_inference(signals, *, run_id, customer, region, existing_rule_ids) -> tuple[list[dict], list[str]]`
- `Signals = dict[resource_type -> resource_id -> metric -> value]`
- `make_incident(*, run_id, customer, region, resource_type, resource_id, rule_id, title, level, metric, current_value, threshold_warning, threshold_critical, recommendation, wow_percent)` 见 `_shared.py:659`
- 现有 14 条规则**无单测**（测试目录无 `_inference` 测试）
- 导入为 `from _shared import make_incident`（同目录相对导入）

---

## 期 1：dynamodb + elasticache + opensearch

### Task 1.1: cruise Cross-Skill References 表 +3 行

**Files:** Modify `aws-aiops-cruise/SKILL.md` (Cross-Skill References 表, ~line 95-104)

- [ ] **Step 1**: 在 Cross-Skill References 表追加 3 行（对齐现有格式）：
```
| DynamoDB diagnosis | `aws-dynamodb-ops` | Throttling, GSI hot shard, TTL |
| ElastiCache diagnosis | `aws-elasticache-ops` | Memory pressure, failover, evictions |
| OpenSearch diagnosis | `aws-opensearch-ops` | Heap pressure, shard imbalance, 5xx |
```
- [ ] **Step 2**: 用 CodeGraph 校验引用存在：`codegraph explore "aws-dynamodb-ops"` 确认目录存在
- [ ] **Step 3**: 验证 frontmatter 仍合法：`awk '/^---$/{c++; if(c==2)exit} c==1' aws-aiops-cruise/SKILL.md | head -1` 应为 `---`
- [ ] **Step 4**: commit `git commit -m "docs(cruise): add dynamodb/elasticache/opensearch to cross-skill references"`

### Task 1.2: orchestrator cross_skill_deps 表 +3 行

**Files:** Modify `aws-aiops-orchestrator/SKILL.md` (cross_skill_deps, ~line 38-53)

- [ ] **Step 1**: 在 cross_skill_deps 追加 3 行：
```
    - aws-dynamodb-ops      # NoSQL throttling + GSI diagnosis
    - aws-elasticache-ops   # In-memory store diagnosis
    - aws-opensearch-ops    # Search/analytics cluster diagnosis
```
- [ ] **Step 2**: `codegraph explore` 校验三目录存在
- [ ] **Step 3**: commit `git commit -m "docs(orchestrator): add dynamodb/elasticache/opensearch deps"`

### Task 1.3: 新建 inference-rules-addendum.md（Markdown 规则语义）

**Files:** Create `aws-aiops-cruise/references/inference-rules-addendum.md`

- [ ] **Step 1**: 写入 6 条规则语义（ID/触发/判定/关联动作），例如：
```
## Phase-1 Rules

### DYNAMO-THROTTLE-01
- Trigger: CloudWatch DynamoDB `ThrottledRequests` > 0 (or `ReadThrottleEvents`/`WriteThrottleEvents`)
- Logic: throttled > 0 → WARNING; sustained > 100/min → CRITICAL
- Action: recommend capacity mode review; delegate aws-dynamodb-ops

### DYNAMO-GSI-01
- Trigger: GSI `ProvisionedThroughput` throttled or `GSIWriteThrottleEvents` > 0
- Logic: gsi throttle > 0 → WARNING
- Action: delegate aws-dynamodb-ops

### EC-MEM-01
- Trigger: ElastiCache `DatabaseMemoryUsagePercentage` >= 80
- Logic: >=80 WARNING; >=95 CRITICAL
- Action: delegate aws-elasticache-ops

### EC-FAILOVER-01
- Trigger: `FailoverInProgress` event or primary/Replica `CPUUtilization` spike + replica lag
- Logic: failover event present → CRITICAL
- Action: delegate aws-elasticache-ops

### OS-HEAP-01
- Trigger: OpenSearch `JVMMemoryPressure` >= 80
- Logic: >=80 WARNING; >=95 CRITICAL
- Action: delegate aws-opensearch-ops

### OS-SHARD-01
- Trigger: `ClusterIndexWritesBlocked` = true OR unassigned shards > 0
- Logic: writes blocked → CRITICAL; unassigned>0 → WARNING
- Action: delegate aws-opensearch-ops
```
- [ ] **Step 2**: commit `git commit -m "docs: add phase-1 inference rule semantics (dynamodb/elasticache/opensearch)"`

### Task 1.4: _inference.py 实现 6 段规则（TDD）

**Files:** Modify `aws-aiops-cruise/runbooks/scripts/_inference.py`
**Test:** Create `aws-aiops-cruise/tests/test_inference_phase1.py`

- [ ] **Step 1**: 写失败测试 `test_inference_phase1.py`：
```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__ + "/..") + "/runbooks/scripts")
from _inference import apply_chain_inference

def _sig():
    return {
        "DynamoDB": {"tbl-1": {"ThrottledRequests": 5, "GSIWriteThrottleEvents": 0}},
        "ElastiCache": {"cache-1": {"DatabaseMemoryUsagePercentage": 90}},
        "OpenSearch": {"os-1": {"JVMMemoryPressure": 85, "ClusterIndexWritesBlocked": 1}},
    }

def test_phase1_rules_fire():
    inc, lines = apply_chain_inference(
        _sig(), run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set())
    ids = {i["rule_id"] for i in inc}
    assert "DYNAMO-THROTTLE-01" in ids
    assert "EC-MEM-01" in ids
    assert "OS-HEAP-01" in ids
    assert "OS-SHARD-01" in ids

def test_phase1_suppressed_by_existing():
    inc, _ = apply_chain_inference(
        _sig(), run_id="r1", customer="c", region="us-east-1",
        existing_rule_ids={"DYNAMO-THROTTLE-01","EC-MEM-01","OS-HEAP-01","OS-SHARD-01"})
    assert inc == []
```
- [ ] **Step 2**: 运行 `cd aws-aiops-cruise && python3 -m pytest tests/test_inference_phase1.py -v` 确认 FAIL（规则未实现）
- [ ] **Step 3**: 在 `apply_chain_inference` 内（现有规则段之后、`return` 之前）添加 6 段规则逻辑，沿用现有模式：
```python
    # --- Phase 1: DynamoDB / ElastiCache / OpenSearch ---
    for rid, m in signals.get("DynamoDB", {}).items():
        thr = m.get("ThrottledRequests") or m.get("GSIWriteThrottleEvents")
        if thr is not None and thr > 0:
            rule = "DYNAMO-THROTTLE-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: DynamoDB `{rid}` throttled ({thr}) → capacity/GSi review")
                incidents.append(make_incident(
                    run_id=run_id, customer=customer, region=region,
                    resource_type="DynamoDB", resource_id=rid, rule_id=rule,
                    title="DynamoDB throttling", level="WARNING",
                    metric="ThrottledRequests", current_value=float(thr),
                    recommendation="Review capacity mode; delegate aws-dynamodb-ops"))
        if (m.get("GSIWriteThrottleEvents") or 0) > 0:
            rule = "DYNAMO-GSI-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: DynamoDB `{rid}` GSI throttle → delegate aws-dynamodb-ops")
                incidents.append(make_incident(
                    run_id=run_id, customer=customer, region=region,
                    resource_type="DynamoDB", resource_id=rid, rule_id=rule,
                    title="DynamoDB GSI throttle", level="WARNING",
                    metric="GSIWriteThrottleEvents",
                    current_value=float(m["GSIWriteThrottleEvents"]),
                    recommendation="Delegate aws-dynamodb-ops"))
    for rid, m in signals.get("ElastiCache", {}).items():
        mem = m.get("DatabaseMemoryUsagePercentage")
        if mem is not None and mem >= 80:
            rule = "EC-MEM-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: ElastiCache `{rid}` memory {mem:.0f}% → eviction risk")
                incidents.append(make_incident(
                    run_id=run_id, customer=customer, region=region,
                    resource_type="ElastiCache", resource_id=rid, rule_id=rule,
                    title="ElastiCache memory pressure", level="CRITICAL" if mem >= 95 else "WARNING",
                    metric="DatabaseMemoryUsagePercentage", current_value=float(mem),
                    threshold_warning=80, threshold_critical=95,
                    recommendation="Delegate aws-elasticache-ops"))
        if (m.get("FailoverInProgress") or 0) > 0:
            rule = "EC-FAILOVER-01"
            if rule not in existing_rule_ids:
                incidents.append(make_incident(
                    run_id=run_id, customer=customer, region=region,
                    resource_type="ElastiCache", resource_id=rid, rule_id=rule,
                    title="ElastiCache failover in progress", level="CRITICAL",
                    metric="FailoverInProgress", current_value=1.0,
                    recommendation="Delegate aws-elasticache-ops"))
    for rid, m in signals.get("OpenSearch", {}).items():
        heap = m.get("JVMMemoryPressure")
        if heap is not None and heap >= 80:
            rule = "OS-HEAP-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: OpenSearch `{rid}` JVM pressure {heap:.0f}%")
                incidents.append(make_incident(
                    run_id=run_id, customer=customer, region=region,
                    resource_type="OpenSearch", resource_id=rid, rule_id=rule,
                    title="OpenSearch JVM pressure", level="CRITICAL" if heap >= 95 else "WARNING",
                    metric="JVMMemoryPressure", current_value=float(heap),
                    threshold_warning=80, threshold_critical=95,
                    recommendation="Delegate aws-opensearch-ops"))
        if (m.get("ClusterIndexWritesBlocked") or 0) > 0 or (m.get("UnassignedShards") or 0) > 0:
            rule = "OS-SHARD-01"
            if rule not in existing_rule_ids:
                incidents.append(make_incident(
                    run_id=run_id, customer=customer, region=region,
                    resource_type="OpenSearch", resource_id=rid, rule_id=rule,
                    title="OpenSearch shard issue", level="CRITICAL",
                    metric="ClusterIndexWritesBlocked", current_value=1.0,
                    recommendation="Delegate aws-opensearch-ops"))
```
- [ ] **Step 4**: 运行 `cd aws-aiops-cruise && python3 -m pytest tests/test_inference_phase1.py -v` 确认 PASS
- [ ] **Step 5**: 运行现有测试 `cd aws-aiops-cruise && python3 -m pytest tests/ -v` 确认零 failure（不回归）
- [ ] **Step 6**: 验证无自动写操作：`grep -nE "modify-|delete-|terminate-|create-" aws-aiops-cruise/runbooks/scripts/_inference.py` 在新增段应无匹配
- [ ] **Step 7**: commit `git commit -m "feat(inference): add phase-1 rules dynamodb/elasticache/opensearch"`

### Task 1.5: 期 1 GCL 评审（reflect-until-clean）

- [ ] **Step 1**: 对期 1 全部改动运行 GCL 多子 Agent 评审（Generator + ≥2 Critic），直到零问题
- [ ] **Step 2**: 修复评审发现的全部问题，复评直到 PASS
- [ ] **Step 3**: 更新 `docs/level3-progress.md` 期 1 段（范围/改动文件/GCL 轮次/测试）

---

## 期 2：eks + cloudfront（同构，替换专属参数）

规则 ID/指标：
- EKS-NODE-01: `NodeNotReady` count > 0 → WARNING; EKS `ResourceType=Node`, metric `NotReady`
- EKS-OOM-01: `pod_eviction` or OOM events > 0 → CRITICAL
- CF-ORIGIN-02: CloudFront `OriginLatency` > 1000ms → WARNING; `OriginSuccessRate` < 0.99 → CRITICAL
- CF-CACHE-01: `CacheHitRate` < 0.8 → WARNING

按 Task 1.1–1.5 同结构执行，resource_type 用 `EKS` / `CloudFront`。

## 期 3：athena + ram + secretsmanager（同构）

规则 ID/指标：
- ATHENA-COST-01: Athena `EstimatedBytesScanned` 异常 or 查询时长 > 600s → WARNING; delegate aws-athena-ops
- RAM-SHARE-01: RAM `ShareStatus` != ACTIVE or 关联账号拒绝 → WARNING; delegate aws-ram-ops
- SEC-ROTATE-01: SecretsManager `LastRotated` age > 90d → WARNING; delegate aws-secretsmanager-ops

按 Task 1.1–1.5 同结构执行，resource_type 用 `Athena` / `RAM` / `SecretsManager`。
