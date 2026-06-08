# OpenSearch Service Core Concepts

Amazon OpenSearch Service architecture, components, and operational concepts.

## Service Overview
**Amazon OpenSearch Service** — Managed search and analytics engine (successor to Amazon Elasticsearch Service). Supports OpenSearch and legacy Elasticsearch engines. Key benefits: automated provisioning, managed snapshots, VPC isolation, encryption, fine-grained access control.

## Supported Engines
```bash
aws opensearch list-versions --query "Versions"
```
| Engine | Version Example | Notes |
|--------|----------------|-------|
| OpenSearch | 2.11, 2.9, 1.3 | Recommended; latest features |
| Elasticsearch | 7.10 | Legacy; no new features |

## Domain Components

**DomainName**: 3-28 lowercase alphanumeric + hyphens, must start with letter.

**Instance Types**: Search-optimized prefixes
- `r6g.*.search` — Graviton2, memory-optimized (recommended)
- `r6i.*.search` — Intel, memory-optimized
- `m6g.*.search` — Graviton2, general purpose
- `c6g.*.search` — Graviton2, compute-optimized
- `ultrawarm1.*.search` — Ultrawarm tier (warm data)
- `t3.*.search` — Burstable (dev/test only)

**Storage**: EBS gp3 (default), gp2, io1/io2. UltraWarm / Cold tiers for cost optimization.

**Cluster Config**:
- `InstanceCount` — data nodes (min 1, recommended 3 for prod)
- `DedicatedMasterEnabled` — separate master nodes for prod (recommended ≥3)
- `ZoneAwarenessEnabled` — spread across AZs (recommended for prod)

## High Availability
- **Multi-AZ**: ZoneAwareness with 2-3 AZs; replicas distributed
- **Dedicated master nodes**: Isolate cluster management from data workload
- **Snapshot repository**: S3-based automated + manual snapshots

## Security
- **VPC**: Deploy inside VPC with private subnets; optional VPC endpoints
- **Encryption at rest**: AES-256 via AWS KMS (cannot disable after creation)
- **Node-to-node encryption**: TLS between nodes
- **Fine-grained access control**: Internal user DB or IAM integration
- **Access policies**: Resource-based JSON policies (IP, IAM role, VPC endpoint)
- **Domain endpoint options**: Enforce HTTPS, custom endpoint, TLS policy

## Snapshots
- **Automated**: Daily, retained 14 days (default), stored in S3 service repo
- **Manual**: User-initiated, retained until deleted, cross-region copy supported
- **Snapshot repository**: Must register S3 bucket as repo first

## Data Ingestion (OpenSearch Ingestion)
- Managed ingestion pipelines based on Data Prepper
- Supports OTel, S3, Kinesis, Kafka sources
- VPC support for private data sources

## Key Metrics (CloudWatch AWS/OpenSearch)
`ClusterStatus.green|yellow|red`, `Nodes`, `SearchableDocuments`, `CPUUtilization`, `JVMMemoryPressure`, `FreeStorageSpace`, `IndexingRate`, `SearchRate`, `ShardCount`, `ActiveShards`

## Quotas
| Resource | Default Limit | Check Command |
|----------|--------------|---------------|
| Domains | 100/region | `aws service-quotas get-service-quota --service-code opensearch --quota-code L-...` |
| Instance types | Varies by region | `aws opensearch list-instance-type-details` |
| EBS volume | 3-1536 TB per domain | |
| Snapshots | 200 manual / domain | |

**Quota Increase**: Via AWS Service Quotas console.

## Domain States
`Active` | `Processing` | `Upgrading` | `Modifying` | `Deleting` | `Isolated`

## Best Practices
**Production**: Multi-AZ + dedicated master + encryption + VPC + fine-grained access control + HTTPS enforced + automated snapshots + CloudWatch alarms.
**Dev/Test**: Single AZ + smaller instance + shorter snapshot retention.

## Pricing (FinOps Reference)
- **Instance**: Per-hour by type. Graviton2 lower cost. Dedicated master adds cost.
- **Storage**: Per GB/month. gp3: base + provisioned IOPS. UltraWarm cheaper than hot.
- **Data Transfer**: Standard AWS rates. Cross-AZ replication within domain free.
- **Ingestion pipeline**: Per-hour pipeline capacity.

**Security**: No public access (prod) + fine-grained access control + Secrets Manager for passwords.
