#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../_cruise_env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_cruise_env.sh"
BASELINE="${REPO_ROOT}/aws-topo-discovery/scripts/baseline-manager.py"
if [[ -f "$BASELINE" ]]; then
  python3 "$BASELINE" --diff-latest --output-dir "${RUNTIME_AUDIT_DIR}" 2>/dev/null || \
    echo "[ConfigDrift] no baseline yet — run TopoScan + baseline first"
else
  echo "[ConfigDrift] baseline-manager.py not found"
  exit 1
fi
