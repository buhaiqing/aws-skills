#!/usr/bin/env bash
# Shared paths for aws-aiops-cruise Perceive agents
set -euo pipefail

_perceive_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export AIOPS_DIR="$(cd "${_perceive_dir}/../../.." && pwd)"
export REPO_ROOT="$(cd "${AIOPS_DIR}/.." && pwd)"
# shellcheck source=../../lib/runtime_root.sh
source "${AIOPS_DIR}/scripts/lib/runtime_root.sh"
aiops_runtime_init "aws-aiops-cruise"
export CRUISE_SCRIPT="${AIOPS_DIR}/runbooks/scripts/daily-health-check.py"
export TOPO_RENDER="${AIOPS_DIR}/runbooks/scripts/cruise-topo-render.py"
export TOPO_SCAN="${REPO_ROOT}/aws-topo-discovery/scripts/topo-scan.sh"

cruise_latest_overlay() {
  local audit_dir="${1:-${RUNTIME_AUDIT_DIR}}"
  python3 "${TOPO_RENDER}" --overlay-from-latest "${audit_dir}" 2>/dev/null || true
}
