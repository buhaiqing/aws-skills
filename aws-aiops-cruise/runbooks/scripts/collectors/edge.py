"""Edge layer collectors (Route53, WAF, CloudFront, S3 origins)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from _shared import make_incident, resource_in_scope, run_aws

from collectors._time import json_time

def _list_all_health_checks() -> list[dict]:
    """Paginate through all Route53 health checks (list-health-checks default max=100)."""
    all_checks: list[dict] = []
    marker = None
    while True:
        cmd = ["aws", "route53", "list-health-checks"]
        if marker:
            cmd.extend(["--marker", marker])
        data = run_aws(cmd, "us-east-1")
        if not data:
            break
        all_checks.extend(data.get("HealthChecks", []))
        if data.get("IsTruncated") and data.get("Marker"):
            marker = data["Marker"]
        else:
            break
    return all_checks


def audit_route53_health_checks(run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    checks = _list_all_health_checks()
    if not checks:
        return incidents
    for hc in checks:
        hid = hc.get("Id", "")
        status = run_aws(
            ["aws", "route53", "get-health-check-status", "--health-check-id", hid],
            "us-east-1",
        )
        if not status:
            continue
        st = status.get("HealthCheckObservations", [])
        failed = [o for o in st if o.get("StatusReport", {}).get("Status", "").startswith("Failure")]
        if len(failed) > len(st) / 2 and st:
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region="global",
                    resource_type="Route53",
                    resource_id=hid,
                    rule_id="R53-HC-01",
                    title=f"Route53 health check failing: {hc.get('HealthCheckConfig', {}).get('FullyQualifiedDomainName', hid)}",
                    level="CRITICAL",
                    metric="HealthCheckFailure",
                    current_value=float(len(failed)),
                    recommendation="Check target endpoint; delegate aws-route53-ops for failover records",
                )
            )
    return incidents

def audit_waf_blocked(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    wafs = run_aws(["aws", "wafv2", "list-web-acls", "--scope", "REGIONAL"], region)
    if not wafs:
        return incidents
    for acl in wafs.get("WebACLs", []):
        arn = acl.get("ARN", "")
        name = acl.get("Name", "")
        dim = f"{name}-regional"
        end = datetime.now(UTC)
        start = end - timedelta(hours=1)
        data = run_aws(
            [
                "aws",
                "cloudwatch",
                "get-metric-statistics",
                "--namespace",
                "AWS/WAFV2",
                "--metric-name",
                "BlockedRequests",
                "--dimensions",
                f"Name=WebACL,Value={name}",
                f"Name=Region,Value={region}",
                "Name=Rule,Value=ALL",
                "--start-time",
                json_time(start),
                "--end-time",
                json_time(end),
                "--period",
                "300",
                "--statistics",
                "Sum",
            ],
            region,
        )
        if not data or not data.get("Datapoints"):
            continue
        total = sum(p.get("Sum", 0) for p in data["Datapoints"])
        if total > 1000:
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="WAF",
                    resource_id=name,
                    rule_id="WAF-BLOCK-01",
                    title=f"WAF blocked {int(total)} requests in last 1h — possible attack or false positive",
                    level="WARNING" if total < 10000 else "CRITICAL",
                    metric="BlockedRequests",
                    current_value=total,
                    recommendation="aws-waf-ops: review rule matches vs ALB 403/502; tune rate-based rules",
                )
            )
    return incidents

def audit_cloudfront(scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    """CloudFront edge metrics (global distribution). API via us-east-1."""
    incidents: list[dict] = []
    cf_region = "us-east-1"
    data = run_aws(["aws", "cloudfront", "list-distributions"], cf_region)
    if not data:
        return incidents
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    for dist in data.get("DistributionList", {}).get("Items", []):
        did = dist.get("Id", "")
        domain = dist.get("DomainName", did)
        if scope_ids and not resource_in_scope(did, scope_ids) and not resource_in_scope(domain, scope_ids):
            aliases = dist.get("Aliases", {}).get("Items", [])
            if not any(resource_in_scope(a, scope_ids) for a in aliases):
                continue
        for metric, thr_w, thr_c in (
            ("5xxErrorRate", 1.0, 5.0),
            ("TotalErrorRate", 2.0, 10.0),
            ("OriginLatency", 1000, 3000),
        ):
            stats = run_aws(
                [
                    "aws",
                    "cloudwatch",
                    "get-metric-statistics",
                    "--namespace",
                    "AWS/CloudFront",
                    "--metric-name",
                    metric,
                    "--dimensions",
                    f"Name=DistributionId,Value={did} Name=Region,Value=Global",
                    "--start-time",
                    json_time(start),
                    "--end-time",
                    json_time(end),
                    "--period",
                    "300",
                    "--statistics",
                    "Average",
                ],
                cf_region,
            )
            if not stats or not stats.get("Datapoints"):
                continue
            val = max(p.get("Average", 0) for p in stats["Datapoints"])
            level = None
            if val >= thr_c:
                level = "CRITICAL"
            elif val >= thr_w:
                level = "WARNING"
            if level:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region="global",
                        resource_type="CloudFront",
                        resource_id=did,
                        rule_id="CF-EDGE-01" if "Error" in metric else "CF-ORIGIN-01",
                        title=f"CloudFront {domain} {metric}={val:.2f}",
                        level=level,
                        metric=metric,
                        current_value=round(val, 3),
                        threshold_warning=thr_w,
                        threshold_critical=thr_c,
                        recommendation="Check origin (ALB/S3) health; cache behavior; WAF at edge",
                    )
                )
    return incidents

def audit_cloudfront_s3_origins(scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    """CloudFront distributions with S3 static origins — OAC/OAI, PAB, S3 4xx/5xx metrics."""
    incidents: list[dict] = []
    cf_region = "us-east-1"
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    seen_buckets: set[str] = set()
    listed = run_aws(["aws", "cloudfront", "list-distributions"], cf_region)
    if not listed:
        return incidents

    def bucket_region(bucket: str) -> str:
        loc = run_aws(["aws", "s3api", "get-bucket-location", "--bucket", bucket], cf_region)
        if not loc:
            return cf_region
        r = loc.get("LocationConstraint") or cf_region
        return "eu-west-1" if r == "EU" else r

    def s3_error_metrics(bucket: str, did: str, domain: str) -> None:
        if bucket in seen_buckets:
            return
        seen_buckets.add(bucket)
        breg = bucket_region(bucket)
        for metric, thr_w, thr_c, rule in (
            ("4xxErrors", 50, 200, "S3-4XX-01"),
            ("5xxErrors", 10, 50, "S3-5XX-01"),
        ):
            stats = run_aws(
                [
                    "aws",
                    "cloudwatch",
                    "get-metric-statistics",
                    "--namespace",
                    "AWS/S3",
                    "--metric-name",
                    metric,
                    "--dimensions",
                    f"Name=BucketName,Value={bucket} Name=StorageType,Value=AllStorageTypes",
                    "--start-time",
                    json_time(start),
                    "--end-time",
                    json_time(end),
                    "--period",
                    "300",
                    "--statistics",
                    "Sum",
                ],
                breg,
            )
            if not stats or not stats.get("Datapoints"):
                continue
            val = sum(p.get("Sum", 0) for p in stats["Datapoints"])
            if val < thr_w:
                continue
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=breg,
                    resource_type="S3",
                    resource_id=bucket,
                    rule_id=rule,
                    title=f"S3 `{bucket}` (CF {domain}) {metric}={val:.0f} (1h)",
                    level="CRITICAL" if val >= thr_c else "WARNING",
                    metric=metric,
                    current_value=val,
                    threshold_warning=thr_w,
                    threshold_critical=thr_c,
                    recommendation="Check OAC/bucket policy; object ACL; origin path; CloudFront cache key",
                )
            )

    for summary in listed.get("DistributionList", {}).get("Items", []):
        did = summary.get("Id", "")
        domain = summary.get("DomainName", did)
        if scope_ids and not resource_in_scope(did, scope_ids) and not resource_in_scope(domain, scope_ids):
            aliases = summary.get("Aliases", {}).get("Items", [])
            if not any(resource_in_scope(a, scope_ids) for a in aliases):
                continue
        cfg = run_aws(["aws", "cloudfront", "get-distribution-config", "--id", did], cf_region)
        if not cfg:
            continue
        dist = cfg.get("DistributionConfig", {})
        for origin in dist.get("Origins", {}).get("Items", []):
            odomain = origin.get("DomainName", "")
            if ".s3." not in odomain and not odomain.endswith("amazonaws.com"):
                continue
            bucket = odomain.split(".s3.")[0] if ".s3." in odomain else odomain
            oai = origin.get("S3OriginConfig", {}).get("OriginAccessIdentity", "")
            has_oac = bool(origin.get("OriginAccessControlId"))
            has_oai = bool(oai and oai != "")
            if not has_oac and not has_oai:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region="global",
                        resource_type="CloudFront",
                        resource_id=did,
                        rule_id="CF-S3-01",
                        title=f"CloudFront {domain} → S3 `{bucket}` without OAC/OAI",
                        level="CRITICAL",
                        metric="OriginAccess",
                        current_value=0.0,
                        recommendation="Attach OAC to origin; block public S3 access; use bucket policy for CloudFront only",
                    )
                )
            pab = run_aws(
                ["aws", "s3api", "get-public-access-block", "--bucket", bucket],
                cf_region,
            )
            if pab:
                conf = pab.get("PublicAccessBlockConfiguration", {})
                if not all(
                    conf.get(k)
                    for k in (
                        "BlockPublicAcls",
                        "IgnorePublicAcls",
                        "BlockPublicPolicy",
                        "RestrictPublicBuckets",
                    )
                ):
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region="global",
                            resource_type="S3",
                            resource_id=bucket,
                            rule_id="S3-PAB-01",
                            title=f"S3 bucket `{bucket}` (CloudFront origin) public access block incomplete",
                            level="WARNING",
                            metric="PublicAccessBlock",
                            current_value=0.0,
                            recommendation="Enable full public access block; serve via CloudFront OAC only",
                        )
                    )
            s3_error_metrics(bucket, did, domain)
    return incidents

