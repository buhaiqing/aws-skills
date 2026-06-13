#!/usr/bin/env python3
"""Unit tests for cruise health overlay key expansion."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "runbooks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("cruise_topo_render", SCRIPTS / "cruise-topo-render.py")
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
build_health_overlay = _mod.build_health_overlay


class TestHealthOverlay(unittest.TestCase):
    def test_alb_arn_suffix_keys(self) -> None:
        incidents = [
            {
                "resource_id": "arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/prod-alb/abc",
                "level": "CRITICAL",
                "resource_type": "ALB",
                "rule_id": "METRIC-ALB-5XX-01",
                "title": "5xx spike",
            }
        ]
        overlay = build_health_overlay(incidents)
        self.assertIn(
            "arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/prod-alb/abc",
            overlay,
        )
        self.assertIn("loadbalancer/app/prod-alb/abc", overlay)
        self.assertEqual(overlay["loadbalancer/app/prod-alb/abc"]["level"], "CRITICAL")

    def test_severity_merge_keeps_critical(self) -> None:
        incidents = [
            {
                "resource_id": "i-abc123",
                "level": "WARNING",
                "resource_type": "EC2",
                "rule_id": "EC2-CPU-01",
                "title": "CPU",
            },
            {
                "resource_id": "i-abc123",
                "level": "CRITICAL",
                "resource_type": "EC2",
                "rule_id": "EC2-STATUS-01",
                "title": "Status check",
            },
        ]
        overlay = build_health_overlay(incidents)
        self.assertEqual(overlay["i-abc123"]["level"], "CRITICAL")


if __name__ == "__main__":
    unittest.main()
