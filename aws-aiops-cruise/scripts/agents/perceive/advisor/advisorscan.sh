#!/usr/bin/env bash
set -euo pipefail
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
OUT="audit-results/advisorscan-$(date +%Y%m%d).json"
mkdir -p audit-results
aws support describe-trusted-advisor-checks --language en --region us-east-1 --output json > "$OUT" 2>/dev/null || \
  echo '{"note":"Trusted Advisor requires Business/Enterprise support plan"}' > "$OUT"
aws compute-optimizer get-enrollment-status --region "$REGION" --output json >> "$OUT" 2>/dev/null || true
echo "[AdvisorScan] wrote $OUT"
