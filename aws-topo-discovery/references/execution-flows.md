# Execution Flows

Detailed execution phases for `aws-topo-discovery`.

## Phase 1: Pre-flight Safety Check

**MANDATORY before any CLI execution:**

1. Verify credentials exist:
   ```bash
   test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY" || { echo "ERROR: Credentials not set"; exit 1; }
   ```

2. Check CLI available:
   ```bash
   command -v aws >/dev/null || { echo "ERROR: AWS CLI not found"; exit 1; }
   ```

3. Verify identity (read-only):
   ```bash
   aws sts get-caller-identity --output json
   ```

4. Verify read-only mode:
   - Scan the planned command list
   - Reject any command matching: `(Create|Update|Modify|Delete|Associate|Disassociate|Authorize|Revoke|Stop|Start|Reboot|Run|Terminate|Invoke|Attach|Detach|Release)`
   - If found → HALT and report to user

5. Test API connectivity (read-only):
   ```bash
   aws ec2 describe-regions --region "$AWS_DEFAULT_REGION" --output json >/dev/null 2>&1 || { echo "ERROR: API check failed"; exit 1; }
   ```

### Output Format (Token Efficiency)

All CLI command JSON output MUST be filtered with `--query` or `jq` to the minimum required fields, avoiding full JSON dumps that waste tokens:

```bash
# Before: full JSON output (potentially 100+ lines)
aws ec2 describe-instances --region $AWS_DEFAULT_REGION --output json

# After: only ID + Name + Type + Status
aws ec2 describe-instances --region $AWS_DEFAULT_REGION --output json \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,InstanceName:Tags[?Key==`Name`].Value|[0],InstanceType:InstanceType,State:State.Name}'
```

Per-API field-filtering rules are in the JSON output path mappings in `references/execution-commands.md`.

## Phase 2: Parallel Data Collection

Execute CLI commands in parallel (background) for speed.

> **Note:** `topo-scan.sh` implements multi-VPC scanning, health overlay, and Mermaid diagram generation; see `scripts/topo-scan.sh` for the full implementation. Commands below write full JSON to `/tmp/topo_*.json` for script consumption. Filter with `--query` or `jq` only when piping JSON directly into agent context (see Phase 1).

```bash
# VPC & Subnet (Foundation) — wait for VPCs before querying Subnets
aws ec2 describe-vpcs --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_vpcs.json &
PID_VPC=$!

# Query ELB/NAT/EIP in parallel
aws elbv2 describe-load-balancers --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_elbs.json &
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=*" --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_nats.json &
aws ec2 describe-addresses --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_eips.json &

# Query Subnets after VPCs return
wait $PID_VPC
FIRST_VPC_ID=$(python3 -c "import json;d=json.load(open('/tmp/topo_vpcs.json'));print(d.get('Vpcs',[{}])[0].get('VpcId',''))" 2>/dev/null)
if [ -n "$FIRST_VPC_ID" ]; then
  aws ec2 describe-subnets --filters "Name=vpc-id,Values=$FIRST_VPC_ID" --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_subnets.json &
fi

# EC2 Instances (Optional for detailed mode)
if [ "$REPORT_MODE" = "detailed" ]; then
  aws ec2 describe-instances --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_ec2.json &
  aws ec2 describe-security-groups --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_sgs.json &
  aws eks list-clusters --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_eks.json &
  aws rds describe-db-instances --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_rds.json &
  aws lambda list-functions --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_lambda.json &
fi

# Wait for remaining background jobs
wait
```

## Phase 3: Topology Generation (Template Rendering)

`topo-render.py` automatically:

1. Loads `/tmp/topo_*.json` data
2. Builds Subnet → resource mappings (EC2/ELB/RDS grouped by owning subnet)
3. Loads health overlay (when `--health-json` is provided)
4. Generates output:
   - **ASCII tree**: terminal-friendly, `report.md`
   - **Mermaid diagram**: visual topology, render-ready, `topology.mermaid.md`
5. Writes files to the output directory

> Template file `templates/vpc-topology.md` is kept for reference. Full rendering logic is implemented in `topo-render.py`.

## Phase 4: Report Compilation

**Single File Mode:**
```markdown
# {{user.project_name}} - AWS Network Topology & Resource Inventory

> Generated: {{timestamp}}
> Region: {{env.AWS_DEFAULT_REGION}}
> Mode: {{user.report_mode}}

{{topology_output}}

---

{{inventory_output}}

---

{{statistics_output}}
```

**Multi-File Mode:**
- `topology.md`: VPC tree + Mermaid diagram
- `inventory.md`: Full resource inventory table
- `summary.md`: Summary + architecture analysis + risk alerts

## Phase 5: Post-Execution Verification

1. Verify output file exists and size > 0:
   ```bash
   test -s report.md && echo "Report generated successfully"
   ```

2. Check no credentials leaked:
   ```bash
   grep -E 'AKIA|wJalr|SECRET|secret' report.md && { echo "WARNING: Possible credential leak"; exit 1; }
   ```

3. Verify read-only compliance (meta-check, no commands executed):
   - Confirm no write commands were in the execution log
