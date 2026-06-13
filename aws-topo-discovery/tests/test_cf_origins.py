#!/usr/bin/env python3
"""Unit tests for cf-origins-collector (no AWS calls)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import importlib.util

_spec = importlib.util.spec_from_file_location("cf_origins_collector", SCRIPTS / "cf-origins-collector.py")
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
origin_kind = _mod.origin_kind
parse_distribution_config = _mod.parse_distribution_config


class TestOriginKind(unittest.TestCase):
    def test_apigw_v2(self) -> None:
        ids = {"abc123xyz"}
        self.assertEqual(origin_kind("abc123xyz.execute-api.us-east-1.amazonaws.com", ids), "apigw_v2")

    def test_apigw_rest(self) -> None:
        self.assertEqual(origin_kind("abc123.execute-api.us-east-1.amazonaws.com", set()), "apigw")

    def test_lambda_url(self) -> None:
        self.assertEqual(origin_kind("abc.lambda-url.us-east-1.on.aws", set()), "lambda_url")

    def test_s3_and_alb(self) -> None:
        self.assertEqual(origin_kind("mybucket.s3.us-east-1.amazonaws.com", set()), "s3")
        self.assertEqual(origin_kind("my-alb-123.us-east-1.elb.amazonaws.com", set()), "alb")


class TestParseDistributionConfig(unittest.TestCase):
    def test_origin_group_failover(self) -> None:
        item = {"Id": "E123", "DomainName": "d111.cloudfront.net"}
        cfg = {
            "DistributionConfig": {
                "DefaultCacheBehavior": {"TargetOriginId": "primary-s3"},
                "CacheBehaviors": {"Items": []},
                "OriginGroups": {
                    "Items": [
                        {
                            "Id": "og1",
                            "Members": {"Items": [{"OriginId": "primary-s3"}, {"OriginId": "fail-alb"}]},
                            "FailoverCriteria": {"StatusCodes": {"Items": [500, 502]}},
                        }
                    ]
                },
                "Origins": {
                    "Items": [
                        {"Id": "primary-s3", "DomainName": "b.s3.amazonaws.com"},
                        {"Id": "fail-alb", "DomainName": "alb.us-east-1.elb.amazonaws.com"},
                    ]
                },
            }
        }
        parsed = parse_distribution_config(item, cfg, set())
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(len(parsed["originGroups"]), 1)
        self.assertEqual(parsed["originGroups"][0]["failoverStatusCodes"], [500, 502])
        roles = {o["id"]: o.get("originGroup", {}).get("role") for o in parsed["origins"]}
        self.assertEqual(roles["primary-s3"], "primary")
        self.assertEqual(roles["fail-alb"], "failover")


if __name__ == "__main__":
    unittest.main()
