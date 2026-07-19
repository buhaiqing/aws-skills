# Core Features

| Feature | Description |
| **Interactive Mode Selection** | User chooses between "Brief" (VPC/Subnet/ELB/EIP summary) or "Detailed" (full resource inventory) |
| **Tree Topology View** | VPC → Subnet → Resource tree structure per template |
| **Multi-Format Output** | ASCII tree + Mermaid diagram + Markdown report |
| **Multi-Document Generation** | Optional single-file or split files (topology / inventory / summary) |
| **Template Engine** | Based on `templates/*.md` files with variable substitution |
| **Health overlay** | `--health-json` from `aws-aiops-cruise` — CRITICAL/WARNING nodes highlighted in Mermaid (v1.9+: no blanket green) |
| **CloudFront origin graph** | `cf-origins-collector.py` — CF→ALB/S3/API GW/Lambda URL edges, Origin Group failover (parallel fetch, detailed/overlay only) |
