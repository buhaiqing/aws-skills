#!/usr/bin/env bash
# aws-topo-discovery/scripts/causal-graph.sh
# Collects X-Ray Service Graph + trace summaries for causal topology.
# Falls back to CloudWatch Contributor Insights if X-Ray is not enabled.

set -euo pipefail

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
TIME_WINDOW="${TIME_WINDOW:-86400}"  # seconds, default 24h
END_TIME="${END_TIME:-$(date +%s)}"
START_TIME=$((END_TIME - TIME_WINDOW))
OUTPUT="${OUTPUT:-/tmp/causal_graph.json}"
XRAY_ENABLED=true

# ── CLI args ──────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $0 [--time-window SECONDS] [--region REGION] [--output PATH]
  --time-window  Seconds to look back (default: 86400 = 24h)
  --region       AWS region (default: \$AWS_DEFAULT_REGION or us-east-1)
  --output       Output JSON path (default: /tmp/causal_graph.json)
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --time-window) TIME_WINDOW="$2"; shift 2 ;;
    --region)      REGION="$2";       shift 2 ;;
    --output)      OUTPUT="$2";       shift 2 ;;
    --help|-h)     usage ;;
    *)             echo "Unknown option: $1"; usage ;;
  esac
done

START_TIME=$(( $(date +%s) - TIME_WINDOW ))
END_TIME=$(date +%s)

echo "[causal-graph] region=$REGION window=${TIME_WINDOW}s start=$(date -r $START_TIME) end=$(date -r $END_TIME)" >&2

# ── Temp files ─────────────────────────────────────────────────────────────────
SG_FILE=$(mktemp /tmp/xray_service_graph.XXXX.json)
TRACE_FILE=$(mktemp /tmp/xray_traces.XXXX.json)
ERROR_FILE=$(mktemp /tmp/xray_errors.XXXX.json)
CW_FILE=$(mktemp /tmp/cw_insights.XXXX.json)
MERGED_FILE=$(mktemp /tmp/causal_merged.XXXX.json)

cleanup() { rm -f "$SG_FILE" "$TRACE_FILE" "$ERROR_FILE" "$CW_FILE" "$MERGED_FILE"; }
trap cleanup EXIT

# ── X-Ray collectors ────────────────────────────────────────────────────────────
collect_xray() {
  echo "[causal-graph] Collecting X-Ray service graph..." >&2

  # Service Graph: services + call-chain edges
  if ! aws xray get-service-graph \
    --start-time "$START_TIME" \
    --end-time "$END_TIME" \
    --time-range-type ABSOLUTE \
    --region "$REGION" \
    --output json > "$SG_FILE" 2>/dev/null; then
    echo "[causal-graph] WARN: get-service-graph failed, X-Ray may not be enabled" >&2
    XRAY_ENABLED=false
    return 1
  fi

  # Trace summaries (last 100 segments)
  echo "[causal-graph] Collecting X-Ray trace summaries..." >&2
  aws xray batch-get-traces-summaries \
    --start-time "$START_TIME" \
    --end-time "$END_TIME" \
    --region "$REGION" \
    --output json > "$TRACE_FILE" 2>/dev/null || true

  # Error summaries
  echo "[causal-graph] Collecting X-Ray error summaries..." >&2
  aws xray get-error-summaries \
    --start-time "$START_TIME" \
    --end-time "$END_TIME" \
    --region "$REGION" \
    --output json > "$ERROR_FILE" 2>/dev/null || true

  XRAY_ENABLED=true
  echo "[causal-graph] X-Ray data collected successfully" >&2
  return 0
}

# ── CloudWatch fallback ─────────────────────────────────────────────────────────
collect_cw_fallback() {
  echo "[causal-graph] Falling back to CloudWatch Contributor Insights..." >&2

  localinsights_rule="arn:aws:cloudwatch:${REGION}:${ACCOUNT_ID}:insight-rules/aws-codedo-notational-request-insight-1"

  # Attempt Contributor Insights for latency/error signals per service
  if aws insights get-insight-rule-results \
    --rule-name "causal-graph-service-latency" \
    --start-time "$(date -r $START_TIME -u +%Y-%m-%dT%H:%M:%SZ)" \
    --end-time "$(date -r $END_TIME -u +%Y-%m-%dT%H:%M:%SZ)" \
    --region "$REGION" \
    --output json > "$CW_FILE" 2>/dev/null; then
    echo "[causal-graph] CloudWatch Contributor Insights data collected" >&2
    return 0
  fi

  # Last-resort: scan LB target groups + RDS connections via describe APIs
  echo "[causal-graph] Last-resort: scanning LB/RDS/ECS endpoints via Describe APIs..." >&2

  localelbs; elbs=$(aws elbv2 describe-target-groups --region "$REGION" --output json 2>/dev/null | \
    jq '{targetGroups: [.TargetGroups[] | {name: .TargetGroupName, vpc: .VpcId}]}' 2>/dev/null || echo '{"targetGroups":[]}')

  local rds_instances; rds_instances=$(aws rds describe-db-instances \
    --region "$REGION" \
    --output json \
    --query 'DBInstances[*].DBInstanceIdentifier' 2>/dev/null | jq '.' || echo '[]')

  echo "{\"targetGroups\": $elbs, \"rdsInstances\": $rds_instances}" > "$CW_FILE"
  return 0
}

# ── Main ──────────────────────────────────────────────────────────────────────
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "000000000000")

if ! collect_xray; then
  collect_cw_fallback
fi

# ── Merge into causal graph JSON ───────────────────────────────────────────────
echo "[causal-graph] Building causal graph JSON..." >&2

# Build service list from Service Graph
SERVICES=$(jq -r '[.Services[]? | {name: .Name, type: .Type, referenceId: .ReferenceId}]' "$SG_FILE" 2>/dev/null || echo '[]')

# Build edges from Service Graph
EDGES=$(jq -r '[.Edges[]? | {fromRefId: .StartId, toRefId: .EndId, responseTimeHistogram: .ResponseTimeHistogram}]' "$SG_FILE" 2>/dev/null || echo '[]')

# Trace count
TRACE_COUNT=$(jq 'length' "$TRACE_FILE" 2>/dev/null || echo 0)

# Error summary
ERRORS=$(jq '.' "$ERROR_FILE" 2>/dev/null || echo '{}')

# CloudWatch fallback data
CW_DATA=$(jq '.' "$CW_FILE" 2>/dev/null || echo '{}')

jq -n \
  --argjson services "$SERVICES" \
  --argjson edges "$EDGES" \
  --argjson cw "$CW_DATA" \
  --argjson errors "$ERRORS" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg region "$REGION" \
  --arg account "$ACCOUNT_ID" \
  --argjson xrayEnabled "$XRAY_ENABLED" \
  --arg start "$(date -r $START_TIME -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg end "$(date -r $END_TIME -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson traceCount "$TRACE_COUNT" \
  '{
    causal_graph: {
      generated_at: $ts,
      time_window: {start: $start, end: $end},
      region: $region,
      account: $account,
      traces_analyzed: $traceCount,
      xray_enabled: $xrayEnabled,
      services: $services,
      edges: $edges,
      error_summaries: $errors
    },
    cloudwatch_fallback: $cw
  }' > "$MERGED_FILE"

cp "$MERGED_FILE" "$OUTPUT"
echo "[causal-graph] Output written to $OUTPUT" >&2
cat "$OUTPUT"
