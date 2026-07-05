# API Gateway Core Concepts

## API Types

| Type | Protocol | Use Case |
|------|----------|----------|
| **REST API** | HTTP/HTTPS | Full-featured RESTful APIs; request transformation, API keys, usage plans |
| **HTTP API** | HTTP/HTTPS | Lower-latency, simpler; Lambda/HTTP integrations, JWT/Cognito auth |
| **WebSocket** | WebSocket | Real-time bidirectional communication (chat, streaming) |

## Key Concepts

- **Resource**: A path in your API (e.g., `/users`, `/orders/{id}`). Nested under parent resources.
- **Method**: HTTP verb (GET, POST, PUT, DELETE, PATCH, OPTIONS, ANY) attached to a resource.
- **Integration**: Backend service (Lambda, HTTP, Mock, AWS Service, VPC Link) that handles requests.
- **Deployment**: A snapshot of the API configuration that can be promoted to stages.
- **Stage**: Named snapshot (prod, staging, dev) with its own endpoint URL, throttling, logging.
- **API Key**: Access key for usage plans and rate limiting.

## Integration Types

| Type | Description |
|------|-------------|
| **MOCK** | Returns static response; no backend call |
| **AWS** | Direct AWS service integration |
| **AWS_PROXY** | Lambda proxy; full request passed to Lambda |
| **HTTP** | Any HTTP endpoint |
| **HTTP_PROXY** | Pass-through HTTP proxy |
| **VPC_LINK** | Private integration via NLB |

## Endpoint Types

| Type | Description |
|------|-------------|
| **EDGE-OPTIMIZED** | CloudFront distribution; global clients |
| **REGIONAL** | Single-region; for custom CloudFront/CDN |
| **PRIVATE** | VPC-only via interface VPC endpoints |

## Limits

| Resource | Default |
|----------|---------|
| REST APIs per region | 60 |
| Resources per API | 300 |
| Deployment stages per API | 10 |
| API key length | 40 chars |