#!/usr/bin/env bash
# Perceive layer dispatcher
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_cruise_env.sh
source "${SCRIPT_DIR}/_cruise_env.sh"
MODE="${1:-all}"

run_agent() {
  local path="$1"
  shift
  echo "[perceive] running $(basename "$path")"
  bash "$path" "$@" || echo "[perceive] WARN $(basename "$path") failed"
}

case "$MODE" in
  health)   run_agent "${SCRIPT_DIR}/infra/healthcruise.sh" "${@:2}" ;;
  topo)     run_agent "${SCRIPT_DIR}/infra/toposcan.sh" "${@:2}" ;;
  drift)    run_agent "${SCRIPT_DIR}/infra/configdrift.sh" "${@:2}" ;;
  cost)     run_agent "${SCRIPT_DIR}/cost/costwatch.sh" "${@:2}" ;;
  security) run_agent "${SCRIPT_DIR}/security/securityscan.sh" "${@:2}" ;;
  audit)    run_agent "${SCRIPT_DIR}/security/audittrail.sh" "${@:2}" ;;
  advisor)  run_agent "${SCRIPT_DIR}/advisor/advisorscan.sh" "${@:2}" ;;
  all)
    run_agent "${SCRIPT_DIR}/infra/healthcruise.sh" "${@:2}"
    run_agent "${SCRIPT_DIR}/infra/toposcan.sh" "${@:2}"
    run_agent "${SCRIPT_DIR}/cost/costwatch.sh" "${@:2}"
    run_agent "${SCRIPT_DIR}/security/securityscan.sh" "${@:2}"
    ;;
  *) echo "Usage: $0 {health|topo|drift|cost|security|audit|advisor|all} [args]"; exit 1 ;;
esac
