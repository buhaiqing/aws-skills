#!/usr/bin/env bash
set -euo pipefail
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
START=$(date -u -v-7d +%Y-%m-%d 2>/dev/null || date -u -d '7 days ago' +%Y-%m-%d)
END=$(date -u +%Y-%m-%d)
aws ce get-cost-and-usage \
  --time-period Start="$START",End="$END" \
  --granularity DAILY \
  --metrics BlendedCost \
  --output json > audit-results/costwatch-$(date +%Y%m%d).json 2>/dev/null || \
  echo "[CostWatch] Cost Explorer access denied or unavailable"
