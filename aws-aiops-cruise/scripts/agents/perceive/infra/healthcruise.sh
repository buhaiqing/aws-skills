#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../_cruise_env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_cruise_env.sh"
OUTPUT="${RUNTIME_AUDIT_DIR}/perceive/healthcruise-$(date +%Y%m%dT%H%M%S).json"
mkdir -p "$(dirname "$OUTPUT")"
python3 "${CRUISE_SCRIPT}" \
  --output-dir "${RUNTIME_AUDIT_DIR}" \
  --non-interactive "$@"
echo '{"agent":"healthcruise","status":"completed"}' > "$OUTPUT"
