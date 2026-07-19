# Causal Inference Rules Library

因果规则库：基于 X-Ray trace 字段映射，从错误/Latency 模式推断根因。
每条规则包含：Rule ID + 场景 + 因果逻辑 (pseudo-code) + X-Ray trace 字段映射。

---

## CAUSAL-01: ALB 5xx 激增溯源

**场景**: ALB 目标组返回 5xx 错误激增

**因果逻辑**:
```
INPUT: X-Ray traces with HasError=true, segment.service.name=alb-target
1. Find traces where segment.has_error=true on downstream subsegments
2. Group by subsegment.name (the failing downstream service)
3. Rank by error_count desc
4. Top-1 suspect is the root cause (if downstream error rate > threshold)
5. Verify: check if upstream ALB error rate correlates with downstream latency spike
```

**X-Ray 字段映射**:
- Error flag: `.Segments[].has_error` or `.Segments[].service.error`
- Downstream: `.Segments[].subsegments[].name`
- Latency: `.Segments[].end_time - .Segments[].start_time`

**阈值**: error_rate > 5% in 5-minute window → alert

---

## CAUSAL-02: RDS 连接超时溯源

**场景**: RDS 连接超时或连接池耗尽

**因果逻辑**:
```
INPUT: X-Ray traces targeting RDS subsegments
1. Identify traces with rds subsegment latency > baseline_p99
2. Determine cause type:
   a. Connection timeout: subsegment.error=true, short duration
   b. Query slow: subsegment latency > connection_timeout_threshold
   c. Connection pool: high concurrent calls, latency spike correlation
3. If connection timeout: check if RDS instance is in available state via describe-db-instances
4. If query slow: correlate with slow_query_log CloudWatch metric
```

**X-Ray 字段映射**:
- RDS subsegment: `.Segments[].subsegments[].name` containing `rds` or `database`
- Connection error: `.Segments[].subsegments[].error=true`
- Latency: `.Segments[].subsegments[].end_time - .Segments[].subsegments[].start_time`

**阈值**: latency_p99 > 200ms (connection pool) or error=true (connection timeout)

---

## CAUSAL-03: Lambda 超时溯源

**场景**: Lambda 函数超时（默认 1s）

**因果逻辑**:
```
INPUT: X-Ray traces where lambda-handler segment duration > timeout_threshold
1. Find lambda subsegments with high latency (downstream service is culprit)
2. Sort subsegments by latency_p99 desc
3. Top-1 with latency > Lambda timeout is root cause
4. Check: is the slow downstream service in a different availability zone?
```

**X-Ray 字段映射**:
- Lambda root: `.Segments[].service.name` containing `lambda`
- Duration: `.Segments[].end_time - .Segments[].start_time`
- Downstream: `.Segments[].subsegments[].name`

**阈值**: downstream latency > Lambda configured timeout (typically 1s)

---

## CAUSAL-04: ECS 任务重启溯源

**场景**: ECS 服务任务频繁重启 (HEALTH_CHECK_FAIL)

**因果逻辑**:
```
INPUT: X-Ray traces from ECS task segments
1. Identify ECS task segments with consecutive health check failures
2. Check if health check failure correlates with:
   a. Application crash: segment has_error=true, short duration
   b. LB misconfiguration: segment ok but health check target unreachable
   c. Resource exhaustion: segment latency spike before failure
3. Trace upstream: is the ECS task's parent ALB/NLB reporting healthy targets?
```

**X-Ray 字段映射**:
- ECS task: `.Segments[].service.name` containing `ecs` or `fargate`
- Health check: `.Segments[].subsegments[].name` containing `health` or `elb`
- Error: `.Segments[].has_error` or `.Segments[].subsegments[].has_error`

**阈值**: 2+ consecutive health check failures in 5-minute window

---

## CAUSAL-05: NAT Gateway 丢包溯源

**场景**: 私有子网实例通过 NAT Gateway 访问互联网超时

**因果逻辑**:
```
INPUT: X-Ray traces with NAT Gateway in call chain
1. Identify traces where nat-gateway subsegment has_error=true
2. Determine cause type:
   a. Bandwidth limit: ConnectionsPerSecond limit exceeded
   b. Transit Gateway: cross-AZ latency spike
   c. Internet egress: destination unreachable
3. Correlate with NAT Gateway CloudWatch metrics:
   - PacketsDropCause: PortAllocationExceeded → connection pool exhaustion
   - PacketsDropCause: Errors → instance-level issue
```

**X-Ray 字段映射**:
- NAT GW: `.Segments[].subsegments[].name` containing `nat`
- Error flag: `.Segments[].subsegments[].has_error=true`
- Latency: `.Segments[].subsegments[].end_time - .Segments[].subsegments[].start_time`

**阈值**: NAT GW error rate > 1% OR latency spike > 2x baseline
