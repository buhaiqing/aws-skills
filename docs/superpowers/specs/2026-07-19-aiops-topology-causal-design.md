# A2: 拓扑因果图谱设计文档

- **日期**: 2026-07-19
- **状态**: 定稿
- **对应计划**: `2026-07-19-aiops-topology-causal.md`
- **目标**: 扩展 `aws-topo-discovery`，构建 X-Ray Trace + CloudWatch Service Lens 拓扑，生成因果链用于 RCA

## 1. 背景

当前 `aws-topo-discovery` 只生成静态拓扑（资源关联），无**因果关系**。
A2 新增：
- X-Ray 追踪数据 → 构建调用链拓扑
- CloudWatch ServiceLens → 服务间依赖关系
- 因果图谱生成 → 支持根因定位（RCA）

## 2. 目标与范围

**修改范围**:
```
aws-topo-discovery/
  SKILL.md                           # 扩展 + Causal Graph section
  scripts/
    causal-graph.sh                  # 新建：X-Ray trace 收集
    causal-inference.py              # 新建：因果图谱推理引擎
  references/
    xray-api-usage.md                # 新建：X-Ray API 参考
    service-lens-usage.md            # 新建：Service Lens API 参考
    causal-rules.md                  # 新建：因果推断规则库
  assets/
    causal-graph-template.json       # 拓扑图模板
```

**X-Ray 依赖**: 需要 X-Ray SDK 已注入应用（纯 AWS 托管服务可省略）

## 3. 核心能力

### 3.1 X-Ray Trace 拓扑

```bash
# 获取服务映射（Service Graph）
aws xray get-service-graph \
  --start-time 1719000000 \
  --end-time 1719086400 \
  --time-range-type ABSOLUTE \
  --output json

# 获取最近 N 条 trace summary
aws xray batch-get-traces-summaries \
  --trace-summaries '[{"Id": "trace-id-1"}, {"Id": "trace-id-2"}]' \
  --output json

# 获取错误分布
aws xray get-error-summaries \
  --group-name "default" \
  --start-time 1719000000 \
  --end-time 1719086400
```

**X-Ray Service Graph 输出结构**:
```json
{
  "Services": [
    {
      "Name": "api-gateway",
      "Type": "AWS::API Gateway",
      "Root": true,
      "ReferenceId": 0
    },
    {
      "Name": "ec2-instance",
      "Type": "AWS::EC2",
      "ReferenceId": 1,
      "Segments": [...]
    }
  ],
  "Edges": [
    {"StartId": 0, "EndId": 1, "ResponseTimeHistogram": [...]}
  ]
}
```

### 3.2 因果图谱推理引擎

基于 X-Ray trace 构建因果图 + 时序异常检测：

```python
from typing import NamedTuple
from collections import defaultdict

class CausalEdge(NamedTuple):
    source: str      # 上游服务
    target: str      # 下游服务
    latency_p50_ms: float
    latency_p99_ms: float
    error_rate: float
    trace_count: int

class CausalGraph:
    def __init__(self):
        self.edges: list[CausalEdge] = []
        self.service_latencies: dict[str, list[float]] = defaultdict(list)

    def add_trace(self, segments: list[dict]) -> None:
        """从 X-Ray trace 添加数据"""
        for seg in segments:
            service_name = seg.get('service', {}).get('name', 'unknown')
            annotations = seg.get('annotations', {})
            latency_ms = seg.get('end_time', 0) - seg.get('start_time', 0)
            self.service_latencies[service_name].append(latency_ms)

            # 建立因果边（基于 HTTP 主键关系）
            for ref in seg.get('subsegments', []):
                self.edges.append(CausalEdge(
                    source=service_name,
                    target=ref.get('name', 'unknown'),
                    latency_p50_ms=0,  # 待计算
                    latency_p99_ms=0,
                    error_rate=0,
                    trace_count=1
                ))

    def find_root_cause(self, target_service: str, error_rate_threshold: float = 0.05) -> list[str]:
        """
        基于错误率溯源。
        返回可能根因的服务列表（按嫌疑度排序）。
        """
        # 构建反向调用图
        callers: dict[str, list[str]] = defaultdict(list)
        for edge in self.edges:
            callers[edge.target].append(edge.source)

        # BFS 溯源：从错误服务向上游找高错误率节点
        suspects = []
        visited = set()
        queue = [target_service]

        while queue:
            svc = queue.pop(0)
            if svc in visited:
                continue
            visited.add(svc)

            # 计算该服务的错误率
            if svc in self.service_latencies:
                error_rate = sum(1 for v in self.service_latencies[svc] if v < 0)  # TODO: real error marker
                if error_rate > error_rate_threshold:
                    suspects.append((svc, error_rate))

            queue.extend(callers.get(svc, []))

        return [s[0] for s in sorted(suspects, key=lambda x: x[1], reverse=True)]
```

### 3.3 因果规则库

| Rule ID | 场景 | 因果逻辑 |
|---------|------|---------|
| CAUSAL-01 | ALB 5xx 激增 | 查找 X-Ray 中 error=true 的 trace → 定位到具体 downstream service |
| CAUSAL-02 | RDS 连接超时 | 查找高 latency 的 DB call → 判断是连接池耗尽还是查询慢 |
| CAUSAL-03 | Lambda 超时 | 查找 downstream service 响应时间 > Lambda timeout |
| CAUSAL-04 | ECS 任务重启 | 查找 HEALTH_CHECK_FAIL 相关的 trace → 判断是应用 crash 还是 LB 问题 |
| CAUSAL-05 | NAT Gateway 丢包 | 查找跨越 NAT 的 trace → 判断是带宽限制还是目标服务问题 |

### 3.4 与 aws-aiops-orchestrator 的集成

`aws-aiops-orchestrator` 的 cross-service RCA 阶段调用因果图谱：

```
aws-aiops-orchestrator RCA 流程:
  1. symptom detection → 哪个服务报错
  2. causal graph query → 调用 aws-topo-discovery causal-graph
  3. root cause inference → 返回 top-3 嫌疑服务
  4. targeted diagnosis → delegate 到对应 skill 深查
```

## 4. 可视化输出

```json
{
  "causal_graph": {
    "generated_at": "2026-07-19T00:00:00Z",
    "time_window": {"start": "2026-07-18T00:00:00Z", "end": "2026-07-19T00:00:00Z"},
    "traces_analyzed": 15420,
    "services": ["api-gw", "ec2-app", "rds-primary", "elasticache"],
    "edges": [
      {"from": "api-gw", "to": "ec2-app", "latency_p99_ms": 230, "error_rate": 0.02},
      {"from": "ec2-app", "to": "rds-primary", "latency_p99_ms": 45, "error_rate": 0.00},
      {"from": "ec2-app", "to": "elasticache", "latency_p99_ms": 8, "error_rate": 0.00}
    ],
    "anomalies": [
      {
        "service": "ec2-app",
        "metric": "latency_p99",
        "value_ms": 230,
        "baseline_ms": 120,
        "deviation_pct": 92,
        "alert_level": "WARNING"
      }
    ]
  },
  "root_cause_candidates": [
    {"service": "ec2-app", "confidence": 0.78, "reason": "high latency deviation on downstream calls"},
    {"service": "rds-primary", "confidence": 0.21, "reason": "minor latency spike"}
  ]
}
```

## 5. 验收标准

1. X-Ray trace 数据收集 + Service Graph 生成
2. 因果图谱支持 ≥ 10 个服务节点
3. `find_root_cause()` 算法返回按嫌疑度排序的 Top-3 服务
4. 因果规则库覆盖 ≥ 5 种常见故障场景
5. 输出格式与 incident-schema 对齐
6. SKILL.md ≤ 120 lines（C6 通过）
7. X-Ray SDK 依赖有 fallback（无 SDK 时优雅降级为 CloudWatch metrics）
