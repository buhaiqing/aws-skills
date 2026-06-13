#!/bin/bash
set -euo pipefail

# ---- Argument parsing ----
REPORT_MODE="brief"
REGION_ID="${AWS_DEFAULT_REGION:-us-east-1}"
OUTPUT_DIR="${TOPO_OUTPUT_DIR:-.}"
ASSUME_ROLE=""

TOPO_TMP_EXTERNAL=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --assume-role) ASSUME_ROLE="$2"; shift 2 ;;
        --mode|-m) REPORT_MODE="$2"; shift 2 ;;
        --region|-r) REGION_ID="$2"; shift 2 ;;
        --output-dir|-o) OUTPUT_DIR="$2"; shift 2 ;;
        --format|-f) FORMAT="$2"; shift 2 ;;
        --health-json) HEALTH_JSON="$2"; shift 2 ;;
        --tmp-dir) TMP_DATA_DIR="$2"; TOPO_TMP_EXTERNAL=1; shift 2 ;;
        brief|detailed) REPORT_MODE="$1"; shift ;;
        *) echo "[ERROR] Unknown option: $1"; exit 1 ;;
    esac
done

# Defaults
FORMAT="${FORMAT:-both}"

# ---- Concurrent safety: unique temp dir per run ----
TMP_DATA_DIR="${TMP_DATA_DIR:-/tmp/topo_scan_$$_$(date +%s)}"
mkdir -p "$TMP_DATA_DIR"
export TOPO_TMP_DIR="$TMP_DATA_DIR"

# ---- STS AssumeRole (optional) ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -n "$ASSUME_ROLE" ]]; then
    echo "[DIAG] Using cross-account role: $ASSUME_ROLE"
    source "$SCRIPT_DIR/sts-helper.sh" --role-arn "$ASSUME_ROLE"
fi

SCAN_TIMESTAMP=$(date +%FT%T%z)

echo "[DIAG] Starting AWS network topology scan... Mode: $REPORT_MODE | Region: $REGION_ID | Tmp: $TMP_DATA_DIR"

# Safety Gate: Read-Only Verification
FORBIDDEN="create-|delete-|modify-|update-|associate-|disassociate-|authorize-|revoke-|stop-|start-|reboot-|run-|invoke-|attach-|detach-|release-|put-"
_VERIFIED=""

verify_cmd() {
    local cmd="$1"
    # Extract the aws subcommand (e.g. "describe-vpcs" from "aws ec2 describe-vpcs")
    local api_op
    api_op=$(echo "$cmd" | grep -oE '(describe|list|get)-[a-z-]+' | head -1)
    if [[ -z "$api_op" ]]; then
        echo "WARN: Cannot extract API operation from: $cmd"
        return 0
    fi
    # dedup
    case " $_VERIFIED " in
        *" $api_op "*) return 0 ;;
    esac
    if echo "$cmd" | grep -qE "($FORBIDDEN)"; then
        echo "FORBIDDEN: Write operation detected - $cmd | HALT"
        exit 1
    fi
    _VERIFIED="$_VERIFIED $api_op"
    echo "   OK $api_op"
}

# ---- Phase 1: Parallel data collection ----
verify_cmd "aws ec2 describe-vpcs"
aws ec2 describe-vpcs --region "$REGION_ID" --output json > "$TMP_DATA_DIR/vpcs.json" &
PID_VPC=$!
verify_cmd "aws elbv2 describe-load-balancers"
aws elbv2 describe-load-balancers --region "$REGION_ID" --output json > "$TMP_DATA_DIR/elbs.json" 2>/dev/null &
verify_cmd "aws ec2 describe-nat-gateways"
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=*" --region "$REGION_ID" --output json > "$TMP_DATA_DIR/nats.json" 2>/dev/null &
verify_cmd "aws ec2 describe-addresses"
aws ec2 describe-addresses --region "$REGION_ID" --output json > "$TMP_DATA_DIR/eips.json" &
verify_cmd "aws ec2 describe-security-groups"
aws ec2 describe-security-groups --region "$REGION_ID" --output json > "$TMP_DATA_DIR/sgs.json" &
verify_cmd "aws cloudfront list-distributions"
aws cloudfront list-distributions --output json > "$TMP_DATA_DIR/cloudfront.json" 2>/dev/null &
verify_cmd "aws apigateway get-rest-apis"
aws apigateway get-rest-apis --region "$REGION_ID" --output json > "$TMP_DATA_DIR/apigateway.json" 2>/dev/null &
verify_cmd "aws apigatewayv2 get-apis"
aws apigatewayv2 get-apis --region "$REGION_ID" --output json > "$TMP_DATA_DIR/apigatewayv2.json" 2>/dev/null &
verify_cmd "aws lambda list-functions"
aws lambda list-functions --region "$REGION_ID" --output json > "$TMP_DATA_DIR/lambda.json" 2>/dev/null &

echo -e "\nWaiting for core network resources..."
wait $PID_VPC

# Parse all VPCs for multi-VPC support
VPC_IDS=$(python3 -c "import json;d=json.load(open('$TMP_DATA_DIR/vpcs.json'));vpcs=d.get('Vpcs',[]);print(' '.join(v['VpcId'] for v in vpcs))" 2>/dev/null || echo "")
FIRST_VPC_ID=$(echo "$VPC_IDS" | awk '{print $1}')

if [ -n "$FIRST_VPC_ID" ]; then
  # Collect Subnets for the first VPC
  verify_cmd "aws ec2 describe-subnets"
  aws ec2 describe-subnets --filters "Name=vpc-id,Values=$FIRST_VPC_ID" --region "$REGION_ID" --output json > "$TMP_DATA_DIR/subnets.json"

  # Save multi-VPC context for renderer
  echo "$VPC_IDS" > "$TMP_DATA_DIR/multi_vpc_ids.txt"

  if [ "$REPORT_MODE" = "detailed" ]; then
      echo -e "\nPhase 2: Detailed Resources..."
      verify_cmd "aws ec2 describe-instances"
      aws ec2 describe-instances --region "$REGION_ID" --output json > "$TMP_DATA_DIR/ec2.json" &
      verify_cmd "aws rds describe-db-instances"
      aws rds describe-db-instances --region "$REGION_ID" --output json > "$TMP_DATA_DIR/rds.json" 2>/dev/null &
      verify_cmd "aws eks list-clusters"
      aws eks list-clusters --region "$REGION_ID" --output json > "$TMP_DATA_DIR/eks.json" 2>/dev/null &
      echo -e "\nWaiting for detailed resources..."
  fi
else
  echo "[]" > "$TMP_DATA_DIR/subnets.json"
  echo "" > "$TMP_DATA_DIR/multi_vpc_ids.txt"
fi

# Wait for all remaining background jobs
wait

# CloudFront origin detail for CF→ALB/S3 Mermaid edges (detailed mode or health overlay only)
if [[ -f "$TMP_DATA_DIR/cloudfront.json" ]] && [[ -s "$TMP_DATA_DIR/cloudfront.json" ]]; then
  if [[ "$REPORT_MODE" == "detailed" ]] || { [[ -n "${HEALTH_JSON:-}" ]] && [[ -f "${HEALTH_JSON}" ]]; }; then
    verify_cmd "aws cloudfront get-distribution-config"
    python3 "$SCRIPT_DIR/cf-origins-collector.py" \
      "$TMP_DATA_DIR/cloudfront.json" "$TMP_DATA_DIR/cloudfront_origins.json" "$REGION_ID" \
      --workers "${CF_ORIGINS_WORKERS:-5}" || true
  else
    echo '{"distributions":[]}' > "$TMP_DATA_DIR/cloudfront_origins.json"
    echo "[topo-scan] Skipping CF origin config fetch (brief mode; use detailed or --health-json)"
  fi
fi

# ---- Phase 2: Report Generation ----
echo -e "\nPhase 3: Generating Report..."
cd "$SCRIPT_DIR"
FORMAT_ARGS="--format $FORMAT"
HEALTH_ARGS=""
[ -n "${HEALTH_JSON:-}" ] && [ -f "$HEALTH_JSON" ] && HEALTH_ARGS="--health-json $HEALTH_JSON"

TOPO_TMP_DIR="$TMP_DATA_DIR" python3 ./topo-render.py \
  "$OUTPUT_DIR" "$REPORT_MODE" "$SCAN_TIMESTAMP" "$REGION_ID" \
  $FORMAT_ARGS $HEALTH_ARGS

# Cleanup: only if we created the tmp dir
if [ -z "${TOPO_TMP_EXTERNAL:-}" ]; then
    rm -rf "$TMP_DATA_DIR" 2>/dev/null || true
fi
