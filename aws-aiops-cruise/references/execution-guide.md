# Execution Guide — AWS CLI Map

> JSON paths declared once here. All commands: `aws <svc> <op> --output json`.

## Pre-flight (mandatory first command)

```bash
aws sts get-caller-identity --output json
# .Account, .Arn, .UserId
```

## Scope resolution

### Resource Group (preferred)

```bash
aws resource-groups list-groups --output json
# .Groups[].Name, .Groups[].GroupArn

aws resource-groups list-group-resources --group "$GROUP" --output json
# .Resources[].Identifier, .Resources[].ResourceType
```

### Tag filter

```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=production \
  --output json
# .ResourceTagMappingList[].ResourceARN
```

## Inventory (parallel-safe)

| Layer | Command | JSON path |
|-------|---------|-----------|
| VPC | `aws ec2 describe-vpcs` | `.Vpcs[]` |
| Subnet | `aws ec2 describe-subnets` | `.Subnets[]` |
| EC2 | `aws ec2 describe-instances` | `.Reservations[].Instances[]` |
| ALB/NLB | `aws elbv2 describe-load-balancers` | `.LoadBalancers[]` |
| Target health | `aws elbv2 describe-target-health --target-group-arn $ARN` | `.TargetHealthDescriptions[]` |
| RDS | `aws rds describe-db-instances` | `.DBInstances[]` |
| Aurora | `aws rds describe-db-clusters` | `.DBClusters[]` |
| ElastiCache | `aws elasticache describe-cache-clusters` | `.CacheClusters[]` |
| NAT | `aws ec2 describe-nat-gateways` | `.NatGateways[]` |
| EIP | `aws ec2 describe-addresses` | `.Addresses[]` |
| SG | `aws ec2 describe-security-groups` | `.SecurityGroups[]` |
| Lambda | `aws lambda list-functions` | `.Functions[]` |
| DynamoDB | `aws dynamodb list-tables` | `.TableNames[]` |

## CloudWatch metrics

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --start-time 2026-06-13T04:00:00Z \
  --end-time 2026-06-13T10:00:00Z \
  --period 300 \
  --statistics Average Maximum \
  --output json
# .Datapoints[].Average, .Datapoints[].Maximum
```

ALB dimension value: suffix of ARN after `loadbalancer/` (e.g. `app/name/id`).

CloudFront: namespace `AWS/CloudFront`, dimensions `DistributionId` + `Region=Global`.

RDS Proxy `ClientConnections`: compare **percentage** of pool limit  
(`max_connections` × `MaxConnectionsPercent` from target + proxy target group) — rule `RDS-PROXY-01` at 80%/95%.

## AWS-native collectors (`collectors/` + `_aws_native.py` facade)

| Module | Collectors | Rule IDs (sample) |
|--------|------------|-------------------|
| `governance.py` | CloudWatch alarms, DevOps Guru, Security Hub, Config, Compute Optimizer | CW-ALARM-01, DG-INSIGHT-01, SH-CRIT-01, CFG-NC-01, CO-EC2-01 |
| `edge.py` | Route53 HC, WAF, CloudFront edge, CF S3 origins | R53-HC-01, WAF-BLOCK-01, CF-EDGE-01, CF-S3-01, S3-4XX-01 |
| `compute.py` | ECS, EKS, ASG, X-Ray | ECS-TASK-01, EKS-NG-01, ASG-CAP-01, XRAY-FAULT-01 |
| `data.py` | RDS PI, RDS Proxy → Aurora | RDS-PI-01, RDS-PROXY-01/02, RDS-PROXY-AURORA-* |
| `registry.py` | `collect_aws_native_insights()` orchestrator | — |

Legacy imports: `from _aws_native import collect_aws_native_insights` still works.

Flags: `--no-cloudfront`, `--no-rds-proxy`, `--no-pi`, `--no-guru`, `--enable-xray`.

## Topology + health overlay

```bash
# After patrol — incidents → overlay → topo scan
python3 aws-aiops-cruise/runbooks/scripts/daily-health-check.py \
  --resource-group prod-web-rg --region us-east-1 --render-topology --non-interactive

# Or from existing cruise JSON
python3 aws-aiops-cruise/runbooks/scripts/cruise-topo-render.py \
  --cruise-json audit-results/cruise-a1b2c3d4.json --region us-east-1
```

Topo scan (with overlay):

```bash
HEALTH_JSON=audit-results/health-overlay-abc.json \
  bash aws-topo-discovery/scripts/topo-scan.sh --mode detailed --region us-east-1 \
  --output-dir audit-results/topology
```

Origin linking (inside topo-scan when **detailed** or `--health-json`):  
`cf-origins-collector.py` (parallel `get-distribution-config`, default 5 workers)  
+ `apigateway get-rest-apis` + `apigatewayv2 get-apis` + `lambda list-functions`.  
Brief mode without overlay skips per-distribution config fetch.

## Optional deep modes

| Mode | Command | Delegate |
|------|---------|----------|
| SSM | `aws ssm send-command` | `aws-ssm-ops` |
| RDS PI (instance) | `aws pi get-resource-metrics` | `aws-rds-ops` |
| Aurora cluster | `aws rds describe-db-clusters` + CW | `aws-aurora-ops` |
| CloudTrail | `aws cloudtrail lookup-events` | `aws-cloudtrail-ops` |
| GuardDuty | `aws guardduty list-findings` | `aws-guardduty-ops` |
| Cost | `aws ce get-cost-and-usage` | Cost Explorer read-only |

## Baseline (topo-discovery)

```bash
python3 aws-topo-discovery/scripts/baseline-manager.py --apply-retention --retention-days 90
```

## Credential convention

Use `{{env.AWS_ACCESS_KEY_ID}}`, `{{env.AWS_SECRET_ACCESS_KEY}}`, `{{env.AWS_PROFILE}}`, `{{env.AWS_DEFAULT_REGION}}` — never ask user to paste secrets.

## Dual-path note

Scripts use AWS CLI first (`run_aws` in `_shared.py`). On CLI failure after retries, **`run_aws_boto3`** parses the same argv and invokes the matching boto3 client method. Collectors should call `run_aws` only — fallback is automatic per repo baseline (`CLAUDE.md`).
