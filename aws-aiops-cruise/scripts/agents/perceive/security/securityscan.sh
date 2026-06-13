#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../_cruise_env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_cruise_env.sh"
OUTPUT="${RUNTIME_AUDIT_DIR}/perceive/securityscan-$(date +%Y%m%dT%H%M%S).json"
mkdir -p "$(dirname "$OUTPUT")"
# Full patrol includes SG / GuardDuty / native security collectors
python3 "${CRUISE_SCRIPT}" \
  --output-dir "${RUNTIME_AUDIT_DIR}" \
  --non-interactive "$@"
echo '{"agent":"securityscan","status":"completed"}' > "$OUTPUT"
