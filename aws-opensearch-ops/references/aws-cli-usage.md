# AWS CLI Usage — OpenSearch Service

AWS CLI commands for OpenSearch Service operations. All commands use `--output json`.
Service name: `opensearch` (NOT `es` — legacy Elasticsearch service).

## Common JSON Paths (Reusable)
```
# Domain: .DomainStatus.{DomainId,DomainName,ARN,Endpoint,EngineVersion,ClusterConfig,AccessPolicies,AdvancedSecurityOptions,VPCOptions,DomainEndpointOptions}
# List:   .DomainNames[].{DomainName,EngineType}
# Snap:   .SnapshotList[].{SnapshotName,Status,ClusterName,SnapshotSource}
# VPC EP: .VpcEndpoints[].{VpcEndpointId,VpcEndpointOwner,DomainArn,Status,VpcOptions}
# Ingest: .IngestionPipelineSummaries[].{PipelineName,PipelineArn,Status}
# Tags:   .TagList[].{Key,Value}
```

## Domain Operations

### Create Domain
```bash
aws opensearch create-domain \
  --domain-name {{user.DomainName}} \
  --engine-version {{user.EngineVersion}} \
  --cluster-config 'InstanceType={{user.InstanceType}},InstanceCount={{user.InstanceCount}},DedicatedMasterEnabled={{user.DedicatedMasterEnabled}},DedicatedMasterType={{user.DedicatedMasterType}},DedicatedMasterCount={{user.DedicatedMasterCount}},ZoneAwarenessEnabled={{user.ZoneAwarenessEnabled}},ZoneAwarenessConfig={AvailabilityZoneCount={{user.AZCount}}}' \
  --ebs-options 'EBSEnabled=true,VolumeType=gp3,VolumeSize={{user.VolumeSize}},Iops={{user.Iops}}' \
  --vpc-options 'SubnetIds=[{{user.SubnetIds}}],SecurityGroupIds=[{{user.SecurityGroupIds}}]' \
  --access-policies '{{user.AccessPolicies}}' \
  --encryption-at-rest-options 'Enabled=true,KmsKeyId={{user.KmsKeyId}}' \
  --node-to-node-encryption-options 'Enabled=true' \
  --domain-endpoint-options 'EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-2019-07' \
  --advanced-security-options 'Enabled=true,InternalUserDatabaseEnabled=true,MasterUserOptions={MasterUserName={{user.MasterUserName}},MasterUserPassword={{user.MasterUserPassword}}}' \
  --output json
```

### Describe / List / Delete
```bash
# Describe single domain
aws opensearch describe-domain --domain-name {{user.DomainName}} --output json

# List all domains
aws opensearch list-domain-names --output json

# List domain details (batch)
aws opensearch describe-domains --domain-names '{{user.DomainName}}' --output json

# Delete domain (safety gate required)
aws opensearch delete-domain --domain-name {{user.DomainName}} --output json

# Update domain config
aws opensearch update-domain-config \
  --domain-name {{user.DomainName}} \
  --cluster-config 'InstanceType={{user.NewInstanceType}}' \
  --ebs-options 'VolumeSize={{user.NewVolumeSize}}' \
  --output json
```

### Upgrade Domain
```bash
# Check upgrade eligibility
aws opensearch get-compatible-versions --domain-name {{user.DomainName}} --output json

# Perform upgrade (safety gate required)
aws opensearch upgrade-domain \
  --domain-name {{user.DomainName}} \
  --target-version {{user.TargetVersion}} \
  --perform-check-only false \
  --output json
```

## Snapshot Operations

### Create / List / Delete
```bash
# Create snapshot (manual)
aws opensearch create-snapshot \
  --domain-name {{user.DomainName}} \
  --snapshot-name {{user.SnapshotName}} \
  --repository-name {{user.RepositoryName}} \
  --output json

# List snapshots
aws opensearch describe-snapshots \
  --domain-name {{user.DomainName}} \
  --repository-name {{user.RepositoryName}} \
  --output json

# Delete snapshot (safety gate required)
aws opensearch delete-snapshot \
  --domain-name {{user.DomainName}} \
  --snapshot-name {{user.SnapshotName}} \
  --repository-name {{user.RepositoryName}} \
  --output json
```

## VPC Endpoint Operations

### Create / Describe / Delete
```bash
# Create VPC endpoint
aws opensearch create-vpc-endpoint \
  --domain-arn {{user.DomainArn}} \
  --vpc-options 'SubnetIds=[{{user.SubnetIds}}],SecurityGroupIds=[{{user.SecurityGroupIds}}]' \
  --output json

# Describe VPC endpoints
aws opensearch describe-vpc-endpoints --vpc-endpoint-ids '{{user.VpcEndpointId}}' --output json

# Delete VPC endpoint (safety gate required)
aws opensearch delete-vpc-endpoint --vpc-endpoint-id {{user.VpcEndpointId}} --output json
```

## Data Ingestion (OpenSearch Ingestion)

### Create / Describe / List / Delete
```bash
# Create ingestion pipeline
aws opensearch create-ingestion \
  --pipeline-name {{user.PipelineName}} \
  --pipeline-configuration-body '{{user.PipelineConfig}}' \
  --vpc-options 'SubnetIds=[{{user.SubnetIds}}],SecurityGroupIds=[{{user.SecurityGroupIds}}]' \
  --buffer-options 'PersistentBufferEnabled={{user.PersistentBuffer}}' \
  --output json

# Describe pipeline
aws opensearch describe-ingestion --pipeline-name {{user.PipelineName}} --output json

# List pipelines
aws opensearch list-ingestions --output json

# Delete pipeline (safety gate required)
aws opensearch delete-ingestion --pipeline-name {{user.PipelineName}} --output json
```

## Tag Operations

```bash
# Add tags
aws opensearch add-tags \
  --arn {{user.DomainArn}} \
  --tag-list 'Key={{user.TagKey}},Value={{user.TagValue}}' \
  --output json

# Remove tags
aws opensearch remove-tags \
  --arn {{user.DomainArn}} \
  --tag-keys '{{user.TagKey}}' \
  --output json

# List tags
aws opensearch list-tags --arn {{user.DomainArn}} --output json
```

## Access Policy & Security

```bash
# Update access policies
aws opensearch update-domain-config \
  --domain-name {{user.DomainName}} \
  --access-policies '{{user.AccessPolicies}}' \
  --output json

# Update fine-grained access control
aws opensearch update-domain-config \
  --domain-name {{user.DomainName}} \
  --advanced-security-options 'Enabled=true,InternalUserDatabaseEnabled=true,MasterUserOptions={MasterUserName={{user.MasterUserName}},MasterUserPassword={{user.MasterUserPassword}}}' \
  --output json

# Update domain endpoint options
aws opensearch update-domain-config \
  --domain-name {{user.DomainName}} \
  --domain-endpoint-options 'EnforceHTTPS=true,CustomEndpointEnabled=true,CustomEndpoint={{user.CustomEndpoint}},CustomEndpointCertificateArn={{user.CertificateArn}}' \
  --output json
```

## Waiters

```bash
# Poll domain until active (CLI wait not available; use loop)
while true; do
  STATUS=$(aws opensearch describe-domain --domain-name {{user.DomainName}} --query 'DomainStatus.Processing' --output text)
  [[ "$STATUS" == "False" ]] && break
  sleep 30
done
```

## Common Option Flags
```
--engine-version OpenSearch_2.11 | OpenSearch_1.3 | Elasticsearch_7.10
--cluster-config InstanceType=r6g.large.search,InstanceCount=3
--ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=100,Iops=3000
--encryption-at-rest-options Enabled=true,KmsKeyId={{key}}
--node-to-node-encryption-options Enabled=true
--domain-endpoint-options EnforceHTTPS=true
--advanced-security-options Enabled=true,InternalUserDatabaseEnabled=true
```
