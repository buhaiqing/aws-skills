# Causal Graph Operations

Builds X-Ray trace + CloudWatch ServiceLens topology for cross-service RCA.

## get-causal-graph

Collects X-Ray Service Graph and trace summaries to build causal call-chain topology.

**Input**: `{{user.time_window}}` (default: last 24h), `{{env.AWS_DEFAULT_REGION}}`

**Output**: JSON `{services, edges, anomalies}` — see `assets/causal-graph-template.json`

```bash
# Execute via causal-graph.sh (X-Ray → fallback to CloudWatch metrics if X-Ray disabled)
bash scripts/causal-graph.sh --time-window 86400 --region "$AWS_DEFAULT_REGION"

# Process traces via causal_inference.py
python3 scripts/causal_inference.py \
  --traces /tmp/xray_traces.json \
  --mode build-graph \
  --output /tmp/causal_graph.json
```

**Fallback**: If X-Ray is not enabled, `causal-graph.sh` falls back to CloudWatch Contributor Insights to infer service dependencies from latency/error metrics.

## find-root-cause

Given a target service and error-rate threshold, traces upstream call-chain to rank candidate root causes.

**Input**: `{{user.target_service}}`, `{{user.error_rate_threshold}}` (default: 0.05)

**Output**: JSON `[{service, confidence, reason}, ...]` — top-3 suspects ranked by confidence

```bash
python3 scripts/causal_inference.py \
  --graph /tmp/causal_graph.json \
  --mode find-root-cause \
  --target "{{user.target_service}}" \
  --threshold 0.05 \
  --output /tmp/root_cause.json
```

**Rule coverage**: ALB 5xx · RDS connection timeout · Lambda timeout · ECS task restart · NAT Gateway packet drop — see `references/causal-rules.md`.

## Integration with aws-aiops-orchestrator

`aws-aiops-orchestrator` Layer-3 RCA invokes:
1. `get-causal-graph` → build topology from X-Ray traces
2. `find-root-cause` → rank top-3 candidate services
3. Delegates to product-level skill for targeted diagnosis
