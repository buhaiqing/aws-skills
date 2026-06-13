#!/usr/bin/env bash
# EventBridge / CloudWatch Alarm → emergency troubleshoot
# Usage: alarm-trigger.sh --alarm-name MyALB5xx --resource-group prod-rg --region us-east-1
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALARM=""
RG=""
TAG_KEY=""
TAG_VAL=""
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
SYMPTOM="alarm"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --alarm-name) ALARM="$2"; shift 2 ;;
    --resource-group) RG="$2"; shift 2 ;;
    --tag-key) TAG_KEY="$2"; shift 2 ;;
    --tag-value) TAG_VAL="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --symptom) SYMPTOM="$2"; shift 2 ;;
    *) shift ;;
  esac
done

if [[ -n "$ALARM" ]]; then
  aws cloudwatch describe-alarm-history --alarm-name "$ALARM" --history-item-type StateUpdate \
    --max-records 3 --region "$REGION" --output json > /tmp/alarm-"$ALARM".json 2>/dev/null || true
fi

CMD=(python3 "${SCRIPT_DIR}/emergency-troubleshoot.py" --region "$REGION" --symptom "$SYMPTOM" --non-interactive)
[[ -n "$RG" ]] && CMD+=(--resource-group "$RG")
[[ -n "$TAG_KEY" ]] && CMD+=(--tag-key "$TAG_KEY" --tag-value "$TAG_VAL")
exec "${CMD[@]}"
