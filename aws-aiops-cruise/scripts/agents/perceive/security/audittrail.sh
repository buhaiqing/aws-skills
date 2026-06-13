#!/usr/bin/env bash
set -euo pipefail
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
aws cloudtrail lookup-events --region "$REGION" --max-results 50 --output json \
  > "audit-results/audittrail-$(date +%Y%m%dT%H%M%S).json"
echo "[AuditTrail] CloudTrail events captured (read-only)"
