# API Gateway Troubleshooting

## Error Table

| Error | Resolution |
|-------|-----------|
| `BadRequestException` | Check required parameters; validate JSON body |
| `ConflictException` | Resource/Method/Integration already exists for that path+method |
| `NotFoundException` | Verify resource, method, or REST API ID |
| `LimitExceededException` | Account-level limit per region; request increase or delete unused APIs |
| `TooManyRequestsException` | Throttling — reduce request rate; enable usage plans |
| `InvalidRequestException` | Check endpoint configuration; verify VPC/Lambda ARN |
| `AccessDeniedException` | IAM role or resource policy missing permissions |
| `ServiceUnavailableException` | AWS side issue; retry with backoff |

## Common Issues

### Lambda integration returns 500
- Verify Lambda function exists and IAM execution role includes `lambda:InvokeFunction`
- Check API Gateway resource policy allows the account
- Test Lambda function independently

### Custom domain not resolving
- Verify Route53 alias record points to API Gateway domain name
- Check ACM certificate is in `us-east-1` (required for EDGE-OPTIMIZED endpoints)
- Verify DNS propagation completed

### API Key not working
- Verify API key is enabled and associated with a usage plan
- Check `x-api-key` header is sent in requests
- Verify the stage has API key required enabled