# CloudFront Core Concepts

AWS CloudFront architecture, components, and operational concepts.

## Service Overview

**AWS CloudFront** - Global Content Delivery Network (CDN) for fast, secure content delivery.

**Key Benefits:**
- Global edge locations
- Low latency
- HTTPS support
- Integration with AWS services
- DDoS protection

## Components

### Distributions
- **Web Distribution**: Websites, APIs, streaming
- **RTMP Distribution**: Adobe Flash media (legacy)

### Origins
- **S3 Origin**: Static content
- **Custom Origin**: EC2, ELB, on-premise
- **Multi-Origin**: Geographic routing

### Cache Behaviors
- **Path Pattern**: Match URL paths
- **Origin**: Target origin for matched paths
- **TTL**: Cache duration
- **Protocol Policy**: HTTP/HTTPS settings
- **Allowed Methods**: GET/POST/PUT/DELETE

### Edge Locations
- **Global Network**: 300+ edge locations
- **Regional Edge Caches**: 13 regional caches
- **Lambda@Edge**: Run code at edge

## Cache Control

### TTL Settings
- **Default TTL**: 24 hours
- **Min TTL**: 0 seconds
- **Max TTL**: 1 year
- **Origin Cache-Control**: Override CloudFront defaults

### Cache Keys
- **Query Strings**: Forward/query string cache
- **Cookies**: Forward/drop cookies
- **Headers**: Forward specific headers
- **Path**: Cache by path pattern

### Invalidation
- **Paths**: Wildcard support (*, **)
- **Cost**: First 1000 paths/month free
- **Alternative**: Versioned URLs

## Security

### HTTPS
- **SSL/TLS**: Custom certificates (ACM)
- **Viewer Protocol**: Redirect/reject HTTP
- **Origin Protocol**: HTTPS to origin

### Access Control
- **Signed URLs**: Time-limited access
- **Signed Cookies**: Browser-based control
- **OAI/OAC**: Origin access identity
- **WAF Integration**: Web application firewall

### Origin Access
- **S3**: OAI for private buckets
- **Custom**: Origin authentication

## Pricing

- **Data Transfer**: $0.085-$0.15/GB (varies by region)
- **Requests**: $0.01-$0.007/10,000
- **Invalidations**: Free first 1000 paths/month
- **Lambda@Edge**: Standard Lambda rates

## Best Practices

### Performance
- Enable compression
- Use HTTP/2
- Configure cache headers
- Use versioned assets
- Enable regional edge caches

### Security
- Use HTTPS only
- Enable WAF
- Use OAC for S3 origins
- Enable signed URLs/cookies for restricted content

### Cost
- Use PriceClass to restrict edge locations
- Configure appropriate TTLs
- Use origin compression
- Monitor with CloudWatch