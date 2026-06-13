# Topology Health Overlay Integration

Bridges **`aws-aiops-cruise`** findings with **`aws-topo-discovery`** ASCII/Mermaid reports.

## Flow

```
daily-health-check.py  →  cruise-*.json (incidents)
        ↓
cruise-topo-render.py  →  health-overlay-*.json
        ↓
topo-scan.sh --health-json  →  topo-render.py  →  report.md
```

## Health overlay format

`topo-render.py` expects a JSON object keyed by resource identifier:

```json
{
  "i-0abc123": { "level": "CRITICAL", "type": "EC2", "rule_id": "METRIC-EC2-CPU", "z_score": 3.0 },
  "prod-alb": { "level": "WARNING", "type": "ALB", "rule_id": "METRIC-ALB-Latency", "z_score": 2.0 },
  "my-aurora-cluster": { "level": "CRITICAL", "type": "Aurora", "rule_id": "RDS-PROXY-AURORA-02", "z_score": 3.0 }
}
```

`build_health_overlay()` in `cruise-topo-render.py` indexes each incident by:

- Full `resource_id` (ARN, instance id, distribution id)
- ARN suffix (`loadbalancer/app/name/id`)
- Load balancer name segment
- Short id after `/` or `:`

`topo-render.py` `get_health()` matches EC2/RDS/ALB nodes via exact key, suffix, and substring.

## CLI

### One-shot after patrol

```bash
python3 aws-aiops-cruise/runbooks/scripts/daily-health-check.py \
  --resource-group prod-web-rg --region us-east-1 \
  --render-topology --non-interactive
```

Output: `audit-results/topology/report.md` + `health-overlay-<run_id>.json`.

### From existing cruise report

```bash
python3 aws-aiops-cruise/runbooks/scripts/cruise-topo-render.py \
  --cruise-json audit-results/cruise-a1b2c3d4.json \
  --region us-east-1 \
  --output-dir audit-results/topology
```

### Perceive Agent TopoScan

Set `HEALTH_JSON` before invoking `scripts/agents/perceive/infra/toposcan.sh` (or pass via env from orchestrator).

## v1.4+ collectors feeding overlay

| Rule | Resource keys in overlay |
|------|--------------------------|
| CF-S3-01 | CloudFront distribution id |
| S3-PAB-01 | S3 bucket name |
| S3-4XX-01 / S3-5XX-01 | S3 bucket name |
| RDS-PROXY-AURORA-01/02 | Aurora cluster identifier |
| CF-EDGE-01 / METRIC-ALB-* | Distribution id + ALB name |

## Mermaid health styling (v1.5+)

`topo-render.py` applies `classDef` when `--health-json` is set:

- `healthCritical` — red fill (CRITICAL incidents)
- `healthWarning` — amber fill (WARNING)
- Healthy nodes stay default styling (v1.9+ — no blanket green `healthOk`)

Edge subgraph **CloudFront / S3 Edge** lists distributions from `cloudfront list-distributions` plus unhealthy S3 buckets from overlay.

## CF → origin edges (v1.6+)

`topo-scan.sh` runs `cf-origins-collector.py` (read-only `get-distribution-config`) and writes `cloudfront_origins.json`. Mermaid renders:

- `CF distribution -->|origin| ALB` when origin domain matches ELB `DNSName`
- `CF distribution -->|origin| S3 bucket` for S3 static origins
- `CF distribution -->|default|` or `|/api/*|` for DefaultCacheBehavior vs path rules
- `CF distribution --> API Gateway` (`execute-api` domain) or **Lambda Function URL** (`lambda-url` domain)
- Custom origins render as inline nodes with domain label
- **Origin Groups**: primary `-.->|failover 500,502,...|` secondary (dotted Mermaid edge)
- **HTTP API (v2)** vs REST API v1: `apigw_v2` kind from `apigatewayv2 get-apis`

## Delegation

- Static inventory / HCL / baseline diff → `aws-topo-discovery` only
- RCA + self-heal after ≥3 CRITICAL → `aws-aiops-orchestrator`
