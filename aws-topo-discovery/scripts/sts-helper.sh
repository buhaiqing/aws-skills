#!/bin/bash
# ============================================================
# STS AssumeRole helper for aws-topo-discovery.
# Sources temporary credentials from AWS STS and exports them
# as AWS_ACCESS_KEY_ID / SECRET / SESSION_TOKEN.
#
# Usage:
#   source sts-helper.sh --role-arn arn:aws:iam::123456789012:role/TopologyReader
#   source sts-helper.sh --role-arn "$ROLE_ARN" --session-name "topo" --duration 3600
#
# Exit codes:
#   0  - Success
#   10 - AssumeRole failed
#   11 - Missing credentials
#   12 - Invalid role ARN format
# ============================================================
set -euo pipefail

SESSION_NAME="topo-discovery"
DURATION_SECONDS=3600

while [[ $# -gt 0 ]]; do
    case "$1" in
        --role-arn) ROLE_ARN="$2"; shift 2 ;;
        --session-name) SESSION_NAME="$2"; shift 2 ;;
        --duration) DURATION_SECONDS="$2"; shift 2 ;;
        *) echo "[ERROR] Unknown option: $1" >&2; exit 12 ;;
    esac
done

if [[ -z "${ROLE_ARN:-}" ]]; then
    exit 0
fi

# Validate ARN format
if ! echo "$ROLE_ARN" | grep -qE '^arn:aws:iam::[0-9]{12}:role/.+$'; then
    echo "[ERROR] Invalid role ARN format: $ROLE_ARN" >&2
    echo "[ERROR] Expected: arn:aws:iam::<account_id>:role/<role_name>" >&2
    exit 12
fi

# Check credentials
if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]]; then
    echo "[ERROR] AWS_ACCESS_KEY_ID not set" >&2
    echo "[ERROR] STS AssumeRole requires primary credentials first." >&2
    exit 11
fi

echo "[DIAG] Assuming role: $ROLE_ARN" >&2
STS_OUTPUT=$(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "$SESSION_NAME" \
    --duration-seconds "$DURATION_SECONDS" \
    --output json \
    2>&1) || {
    echo "[ERROR] TYPE=ASSUME_ROLE_FAILED FIX=Check role ARN, permissions, and network" >&2
    echo "[ERROR] aws sts output: $STS_OUTPUT" >&2
    exit 10
}

# Extract and export credentials
export AWS_ACCESS_KEY_ID=$(echo "$STS_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['AccessKeyId'])")
export AWS_SECRET_ACCESS_KEY=$(echo "$STS_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['SecretAccessKey'])")
export AWS_SESSION_TOKEN=$(echo "$STS_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['SessionToken'])")

if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" ]]; then
    echo "[ERROR] TYPE=EMPTY_CREDENTIALS FIX=Check STS AssumeRole response" >&2
    exit 10
fi

echo "[RESULT] Credentials assumed, session: $SESSION_NAME, expires: $(echo "$STS_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['Expiration'])")" >&2
