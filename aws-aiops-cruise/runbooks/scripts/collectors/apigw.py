"""API Gateway layer collectors (REST + HTTP APIs)."""

from __future__ import annotations

from typing import Any

from _shared import make_incident, resource_in_scope, run_aws, log


def audit_apigw_health(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    """Check REST APIs and HTTP APIs (v2) for undeployed and misconfigured APIs."""
    incidents: list[dict] = []

    # REST APIs
    rest_apis = run_aws(["aws", "apigateway", "get-rest-apis"], region)
    if rest_apis:
        for api in rest_apis.get("items", []):
            api_id = api.get("id", "")
            if scope_ids and not resource_in_scope(api_id, scope_ids):
                continue

            # APIGW-DEPLOY-01: no stages → never deployed
            stages = run_aws(["aws", "apigateway", "get-stages", "--rest-api-id", api_id], region)
            if not stages or not stages.get("item"):
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="APIGateway",
                        resource_id=f"rest:{api_id}",
                        rule_id="APIGW-DEPLOY-01",
                        title=f"REST API '{api.get('name', api_id)}' has no stages (never deployed)",
                        level="WARNING",
                        metric="StageCount",
                        current_value=0.0,
                        threshold_warning=1,
                        recommendation=f"Deploy via: aws apigateway create-deployment --rest-api-id {api_id} --stage-name <stage>",
                    )
                )

    # HTTP APIs (API Gateway v2)
    http_apis = run_aws(["aws", "apigatewayv2", "get-apis"], region)
    if http_apis:
        for api in http_apis.get("Items", []):
            api_id = api.get("ApiId", "")
            if scope_ids and not resource_in_scope(api_id, scope_ids):
                continue

            # APIGW-V2-01: HTTP API with no stages
            stages = run_aws(["aws", "apigatewayv2", "get-stages", "--api-id", api_id], region)
            if not stages or not stages.get("Items"):
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="APIGatewayV2",
                        resource_id=f"http:{api_id}",
                        rule_id="APIGW-V2-01",
                        title=f"HTTP API '{api.get('Name', api_id)}' has no stages",
                        level="WARNING",
                        metric="StageCount",
                        current_value=0.0,
                        threshold_warning=1,
                        recommendation=f"Deploy via: aws apigatewayv2 create-deployment --api-id {api_id} --stage-name <stage>",
                    )
                )

    return incidents
