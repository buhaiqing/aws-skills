# DynamoDB Core Concepts

AWS DynamoDB architecture, components, and operational concepts.

## Service Overview

**AWS DynamoDB** - Fully managed NoSQL database service that provides fast and predictable performance with seamless scalability.

**Key Benefits:**
- Single-digit millisecond latency at any scale
- Automatic scaling (on-demand and auto-scaling modes)
- Built-in high availability and durability (3 copies across 3 AZs)
- Serverless, no capacity planning required (on-demand mode)
- ACID transactions support
- Streams for event-driven architectures
- Global tables for multi-region replication
- TTL (Time to Live) for automatic data expiration

## Key Components

### Tables
- **Primary container** for data
- No fixed schema (except keys)
- Unlimited items per table
- Each table must have a primary key

### Items
- Individual data records in a table
- Maximum size: 400 KB (including attribute names and values)
- Items are uniquely identified by primary key
- Can have varying attributes (schemaless)

### Attributes
- Data elements within an item
- Supported types:
  - **Scalar**: String (S), Number (N), Binary (B), Boolean (BOOL), Null (NULL)
  - **Document**: List (L), Map (M)
  - **Set**: String Set (SS), Number Set (NS), Binary Set (BS)

### Primary Key

#### Partition Key Only
- Single attribute as primary key
- All items with same partition key stored together
- Maximum 10 GB per partition
- **Use case**: Single attribute unique identification

```
┌─────────────────┐
│ Partition Key   │
│ (user_id)       │
├─────────────────┤
│ user123         │
│ user456         │
│ user789         │
└─────────────────┘
```

#### Composite Primary Key
- Partition key + Sort key
- Partition key groups items
- Sort key determines ordering within partition
- **Use case**: Time-series data, hierarchical relationships

```
┌─────────────────┬─────────────────┐
│ Partition Key   │ Sort Key        │
│ (device_id)     │ (timestamp)     │
├─────────────────┼─────────────────┤
│ device123       │ 2024-01-01T00:00│
│ device123       │ 2024-01-01T01:00│
│ device456       │ 2024-01-01T00:00│
└─────────────────┴─────────────────┘
```

## Index Types

### Global Secondary Index (GSI)
- **Independent** from base table
- Can have different partition key than base table
- Can have different sort key
- Separate capacity (for provisioned mode)
- Async replication from base table

**Key Characteristics:**
- Unlimited per table (but recommended max: 20)
- Projection options: ALL, KEYS_ONLY, INCLUDE
- Eventual consistency (async replication)
- Supports sparse indexes (only items with projected attributes)

**Use Cases:**
- Alternative query patterns
- Different access patterns than primary key
- Reducing load on base table

### Local Secondary Index (LSI)
- **Same partition key** as base table
- **Different sort key**
- Shares capacity with base table
- Must be defined at table creation

**Key Characteristics:**
- Max 5 per table
- Strong consistency option available
- Shares RCU/WCU with base table

**Use Cases:**
- Alternative sorting within partition
- Query patterns with same partition key

## Capacity Modes

### On-Demand
**Characteristics:**
- Pay per request
- No capacity planning
- Auto-scales to workload
- Default: 4,000 RCU, 4,000 WCU per partition
- **Best for:** Unpredictable workloads, new applications, dev/test

**Cost Model:**
- Read: $0.25 per million read request units
- Write: $1.25 per million write request units

### Provisioned
**Characteristics:**
- Specify RCU and WCU upfront
- Auto-scaling supported
- Reserved capacity options
- **Best for:** Predictable workloads, large scale, cost optimization

**Capacity Units:**
- **1 RCU** = 1 strongly consistent read/sec OR 2 eventually consistent reads/sec, up to 4KB
- **1 WCU** = 1 write/sec, up to 1KB
- **Transactional reads/writes** = 2x cost

**Burst Capacity:**
- Accumulated unused capacity (5 minutes)
- Temporary usage above provisioned capacity

**Cost Model:**
- $0.00013 per RCU-hour
- $0.00065 per WCU-hour
- Reserved capacity: 1-year/3-year commitment

## Consistency Models

### Eventual Consistency
- Default behavior
- Lower latency
- Lower cost
- May read stale data (within 1 second typically)

### Strong Consistency
- Returns most recent data
- Higher latency
- Higher cost (2x read capacity)
- Use `ConsistentRead=True`

## Time to Live (TTL)

**Purpose:** Automatically delete expired items without consuming write capacity.

**Characteristics:**
- Attribute stores expiration timestamp (epoch seconds)
- Deletion happens within 48 hours of expiration
- No WCU consumed for TTL deletion
- Can be enabled/disabled without downtime

**Example:**
```
{
  "user_id": "user123",
  "session_data": {...},
  "ttl": 1705000000  // Expires at this Unix timestamp
}
```

## DynamoDB Streams

**Purpose:** Capture item-level changes for event-driven architectures.

**Stream View Types:**
- **KEYS_ONLY**: Only key attributes
- **NEW_IMAGE**: Entire item after modification
- **OLD_IMAGE**: Entire item before modification
- **NEW_AND_OLD_IMAGES**: Both before and after

**Common Use Cases:**
- Real-time data replication
- Trigger Lambda functions
- Audit logging
- Data pipeline processing

**Retention:**
- 24 hours max
- Ordered by time
- No duplicates within shard

## DynamoDB Accelerator (DAX)

**Purpose:** In-memory caching for microsecond latency.

**Characteristics:**
- Fully managed caching layer
- Compatible with DynamoDB API
- Multi-AZ deployment
- Cache hit: microseconds
- Cache miss: falls back to DynamoDB

**Cache Operations:**
- Item cache (GetItem, BatchGetItem)
- Query cache
- Scan cache (not recommended)

**Use Cases:**
- Read-heavy workloads
- Repeated reads
- Session stores
- Real-time dashboards

## Transactions

**ACID Support:**
- Atomic transactions across multiple items/tables
- All-or-nothing execution
- Up to 100 actions per transaction
- Up to 4 MB total payload

**Operations:**
- `TransactGetItems`: Read multiple items atomically
- `TransactWriteItems`: Write multiple items atomically
- Includes: Put, Update, Delete, ConditionCheck

**Limitations:**
- Cannot use with GSI projections
- No transactions in Streams
- 2x capacity cost

## Global Tables

**Purpose:** Multi-region, multi-active replication.

**Characteristics:**
- Automatic conflict resolution (last-write-wins)
- Sub-second replication latency
- Supports on-demand and provisioned modes
- No application changes required

**Requirements:**
- Streams enabled
- Conflict detection streams
- Identical table names in all regions

## Partitions

### Partition Distribution
- Items distributed by partition key hash
- Even distribution critical for performance
- Hot partitions cause throttling

### Partition Limits
- 10 GB storage per partition
- 3,000 RCU per partition
- 1,000 WCU per partition

### Avoid Hot Partitions
- Use high-cardinality partition keys
- Avoid sequential IDs (use UUID)
- Distribute writes across keys
- Consider write sharding

## Quotas (Service Limits)

| Quota | Default Limit | Notes |
|-------|---------------|-------|
| Tables per region | 2,500 | Can increase |
| GSI per table | 20 | Can increase to 30 |
| LSI per table | 5 | Fixed |
| Partition key size | 2,048 bytes | - |
| Sort key size | 1,024 bytes | - |
| Item size | 400 KB | Includes attribute names |
| Attributes per item | No limit | Within 400KB |
| Nested attribute depth | 32 levels | - |
| BatchGetItem | 100 items | 16 MB max |
| BatchWriteItem | 25 items | 16 MB max |
| Query/Scan page size | 1 MB | Use pagination |
| Filter expression size | 4 KB | - |
| Projection expression | 4 KB | - |
| Transaction items | 100 | 4 MB max |
| TTL precision | 48 hours | Approximate deletion |

## Common Access Patterns

### Single Item Operations
- **GetItem**: Retrieve single item by full primary key
- **PutItem**: Create or replace item
- **UpdateItem**: Partial update with expressions
- **DeleteItem**: Remove single item

### Multi-Item Operations
- **Query**: Retrieve items with same partition key
- **Scan**: Read entire table (avoid in production)
- **BatchGetItem**: Retrieve up to 100 items
- **BatchWriteItem**: Write up to 25 items

### Conditional Operations
- **ConditionExpression**: Conditional writes
- **FilterExpression**: Client-side filtering
- **ProjectionExpression**: Select specific attributes

## Best Practices

### Table Design
- Use single-table design when possible
- Keep related data in same item
- Use composite keys for hierarchical data
- Project minimal attributes to GSIs

### Performance
- Use eventually consistent reads when possible
- Implement exponential backoff for throttling
- Use parallel scans for large datasets
- Cache frequently accessed data

### Cost Optimization
- Use on-demand for unpredictable workloads
- Use provisioned with auto-scaling for steady workloads
- Enable TTL to delete obsolete data
- Compress large attributes

### Security
- Enable encryption at rest
- Use fine-grained IAM policies
- Enable CloudTrail for API auditing
- Use VPC endpoints for private access

### Monitoring
- Watch `ThrottledRequests` metric
- Monitor `ConsumedReadCapacityUnits` vs provisioned
- Alert on hot partition indicators
- Use Contributor Insights for top keys

## Common Anti-Patterns

| Anti-Pattern | Better Approach |
|--------------|-----------------|
| Scanning entire table | Use Query with specific partition key |
| Sequential IDs (timestamps) | Use UUID or hash prefix |
| Storing large files | Use S3, store reference in DynamoDB |
| Hot partition keys | Use high-cardinality, well-distributed keys |
| Too many GSIs | Single-table design, carefully chosen indexes |
| Large items near 400KB | Split into multiple items or use S3 |
| Strong consistency for all reads | Use eventual consistency when possible |