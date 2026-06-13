#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../_cruise_env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_cruise_env.sh"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
OUTPUT="${TOPO_OUTPUT_DIR:-${RUNTIME_AUDIT_DIR}}/toposcan-$(date +%Y%m%d).md"
mkdir -p "$(dirname "$OUTPUT")"

if [[ -z "${HEALTH_JSON:-}" ]]; then
  HEALTH_JSON="$(cruise_latest_overlay "${RUNTIME_AUDIT_DIR}")"
fi

if [[ ! -x "$TOPO_SCAN" ]]; then
  echo "[TopoScan] aws-topo-discovery not found at $TOPO_SCAN"
  exit 1
fi

TOPO_ARGS=(--mode detailed --region "$REGION" --output-dir "$(dirname "$OUTPUT")")
if [[ -n "${HEALTH_JSON:-}" && -f "${HEALTH_JSON}" ]]; then
  TOPO_ARGS+=(--health-json "$HEALTH_JSON")
  echo "[TopoScan] Using health overlay: $HEALTH_JSON"
fi
bash "$TOPO_SCAN" "${TOPO_ARGS[@]}"
