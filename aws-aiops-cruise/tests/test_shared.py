#!/usr/bin/env python3
"""Unit tests for _shared.py core functions."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "runbooks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _shared import (  # noqa: E402
    INFERENCE_RULE_VERSION,
    W,
    C,
    get_metric_stats,
    get_wow_change,
    level_for_value,
    make_incident,
    parallel_metric_scan,
)


# ---------------------------------------------------------------------------
# make_incident
# ---------------------------------------------------------------------------
class TestMakeIncident:
    """Tests for make_incident()."""

    def _make(self, **overrides):
        defaults = dict(
            run_id="run-1",
            customer="test",
            region="us-east-1",
            resource_type="EC2",
            resource_id="i-abc",
            rule_id="EC2-CPU-01",
            title="High CPU",
            level="WARNING",
            metric="CPUUtilization",
            current_value=80.0,
        )
        defaults.update(overrides)
        return make_incident(**defaults)

    def test_schema_version(self):
        inc = self._make()
        assert inc["schema_version"] == "1.1.0"

    def test_rule_version_uses_constant(self):
        inc = self._make()
        assert inc["rule_version"] == INFERENCE_RULE_VERSION

    def test_required_fields_present(self):
        inc = self._make()
        for field in (
            "incident_id",
            "customer",
            "timestamp",
            "run_id",
            "level",
            "resource_type",
            "resource_id",
            "region",
            "rule_id",
            "rule_version",
            "title",
            "dedup_key",
            "metric",
            "current_value",
        ):
            assert field in inc, f"Missing required field: {field}"

    def test_dedup_key_format(self):
        inc = self._make(customer="acme", resource_type="EC2", resource_id="i-abc", rule_id="EC2-CPU-01")
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        assert inc["dedup_key"] == f"acme:EC2:i-abc:EC2-CPU-01:{today}"

    def test_incident_id_is_uuid(self):
        inc = self._make()
        # UUID4 format: 8-4-4-4-12
        parts = inc["incident_id"].split("-")
        assert len(parts) == 5
        assert len(inc["incident_id"]) == 36

    def test_wow_percent_included_when_provided(self):
        inc = self._make(wow_percent=55.0)
        assert inc["wow_percent"] == 55.0

    def test_wow_percent_omitted_when_none(self):
        inc = self._make()
        assert "wow_percent" not in inc

    def test_thresholds_stored(self):
        inc = self._make(threshold_warning=70.0, threshold_critical=85.0)
        assert inc["threshold_warning"] == 70.0
        assert inc["threshold_critical"] == 85.0

    def test_recommendation_stored(self):
        inc = self._make(recommendation="Resize instance")
        assert inc["recommendation"] == "Resize instance"


# ---------------------------------------------------------------------------
# level_for_value
# ---------------------------------------------------------------------------
class TestLevelForValue:
    """Tests for level_for_value()."""

    thresholds = {W: 70, C: 85}

    def test_none_returns_none(self):
        assert level_for_value(None, self.thresholds) is None

    def test_below_warning_returns_none(self):
        assert level_for_value(50, self.thresholds) is None

    def test_at_warning_returns_warning(self):
        assert level_for_value(70, self.thresholds) == "WARNING"

    def test_between_warning_and_critical(self):
        assert level_for_value(77, self.thresholds) == "WARNING"

    def test_at_critical_returns_critical(self):
        assert level_for_value(85, self.thresholds) == "CRITICAL"

    def test_above_critical_returns_critical(self):
        assert level_for_value(99, self.thresholds) == "CRITICAL"

    def test_invert_below_critical_returns_critical(self):
        assert level_for_value(10, self.thresholds, invert=True) == "CRITICAL"

    def test_invert_between_warning_and_critical(self):
        # invert: value < c → CRITICAL, value < w → WARNING
        # 77 < 85 → CRITICAL (lower is worse when inverted)
        assert level_for_value(77, self.thresholds, invert=True) == "CRITICAL"

    def test_invert_above_warning_returns_none(self):
        assert level_for_value(90, self.thresholds, invert=True) is None

    def test_no_thresholds_returns_none(self):
        assert level_for_value(50, {}) is None

    def test_only_warning_threshold(self):
        assert level_for_value(75, {W: 70}) == "WARNING"
        assert level_for_value(99, {W: 70}) == "WARNING"

    def test_only_critical_threshold(self):
        assert level_for_value(80, {C: 85}) is None
        assert level_for_value(90, {C: 85}) == "CRITICAL"


# ---------------------------------------------------------------------------
# get_metric_stats
# ---------------------------------------------------------------------------
class TestGetMetricStats:
    """Tests for get_metric_stats() with mocked run_aws."""

    @patch("_shared.run_aws")
    def test_no_datapoints_returns_none(self, mock_run):
        mock_run.return_value = {"Datapoints": []}
        result = get_metric_stats("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        assert result == {"avg": None, "max": None, "sum": None}

    @patch("_shared.run_aws")
    def test_none_response_returns_none(self, mock_run):
        mock_run.return_value = None
        result = get_metric_stats("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        assert result == {"avg": None, "max": None, "sum": None}

    @patch("_shared.run_aws")
    def test_average_computed_correctly(self, mock_run):
        mock_run.return_value = {
            "Datapoints": [
                {"Average": 10.0, "Timestamp": "2026-07-01T00:00:00Z"},
                {"Average": 30.0, "Timestamp": "2026-07-01T01:00:00Z"},
            ]
        }
        result = get_metric_stats("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        assert result["avg"] == 20.0

    @patch("_shared.run_aws")
    def test_max_computed_correctly(self, mock_run):
        mock_run.return_value = {
            "Datapoints": [
                {"Maximum": 10.0, "Timestamp": "2026-07-01T00:00:00Z"},
                {"Maximum": 30.0, "Timestamp": "2026-07-01T01:00:00Z"},
            ]
        }
        result = get_metric_stats("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        assert result["max"] == 30.0

    @patch("_shared.run_aws")
    def test_sum_computed_correctly(self, mock_run):
        mock_run.return_value = {
            "Datapoints": [
                {"Sum": 10.0, "Timestamp": "2026-07-01T00:00:00Z"},
                {"Sum": 30.0, "Timestamp": "2026-07-01T01:00:00Z"},
            ]
        }
        result = get_metric_stats("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        assert result["sum"] == 40.0


# ---------------------------------------------------------------------------
# get_wow_change
# ---------------------------------------------------------------------------
class TestGetWowChange:
    """Tests for get_wow_change() with mocked run_aws."""

    @patch("_shared.run_aws")
    def test_no_current_data_returns_none(self, mock_run):
        # First call: current metric (no data), second call: old metric
        mock_run.side_effect = [
            {"Datapoints": []},  # current
            {"Datapoints": []},  # old
        ]
        result = get_wow_change("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        assert result is None

    @patch("_shared.run_aws")
    def test_no_old_data_returns_none(self, mock_run):
        mock_run.side_effect = [
            {"Datapoints": [{"Average": 50.0, "Timestamp": "2026-07-04T00:00:00Z"}]},  # current
            {"Datapoints": []},  # old
        ]
        result = get_wow_change("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        assert result is None

    @patch("_shared.run_aws")
    def test_old_avg_zero_returns_none(self, mock_run):
        mock_run.side_effect = [
            {"Datapoints": [{"Average": 50.0, "Timestamp": "2026-07-04T00:00:00Z"}]},  # current
            {"Datapoints": [{"Average": 0.0, "Timestamp": "2026-06-27T00:00:00Z"}]},  # old (0)
        ]
        result = get_wow_change("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        assert result is None

    @patch("_shared.run_aws")
    def test_wow_calculation(self, mock_run):
        mock_run.side_effect = [
            {"Datapoints": [{"Average": 50.0, "Timestamp": "2026-07-04T00:00:00Z"}]},  # current
            {"Datapoints": [{"Average": 25.0, "Timestamp": "2026-06-27T00:00:00Z"}]},  # old
        ]
        result = get_wow_change("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        # (50 - 25) / 25 * 100 = 100.0
        assert result == 100.0

    @patch("_shared.run_aws")
    def test_wow_negative_change(self, mock_run):
        mock_run.side_effect = [
            {"Datapoints": [{"Average": 20.0, "Timestamp": "2026-07-04T00:00:00Z"}]},  # current
            {"Datapoints": [{"Average": 40.0, "Timestamp": "2026-06-27T00:00:00Z"}]},  # old
        ]
        result = get_wow_change("us-east-1", "AWS/EC2", "CPUUtilization", "InstanceId", "i-abc")
        # (20 - 40) / 40 * 100 = -50.0
        assert result == -50.0


# ---------------------------------------------------------------------------
# parallel_metric_scan
# ---------------------------------------------------------------------------
class TestParallelMetricScan:
    """Tests for parallel_metric_scan() with mocked run_aws and get_metric_data_batch."""

    @patch("_shared.get_metric_data_batch")
    @patch("_shared.run_aws")
    def test_basic_scan(self, mock_run, mock_batch):
        # Mock inventory: return EC2 instances
        mock_run.return_value = {"Reservations": [{"Instances": [{"InstanceId": "i-abc123"}]}]}
        # Mock metric data: CPU at 50% (below WARNING threshold)
        mock_batch.return_value = {
            ("CPUUtilization", "i-abc123"): {"avg": 50.0, "max": 60.0, "sum": None},
        }

        incidents, signals, risk = parallel_metric_scan("us-east-1", set(), "run-1", "test")
        # 50 < 70 (WARNING threshold) → no incident
        ec2_incidents = [i for i in incidents if i.get("resource_id") == "i-abc123"]
        assert len(ec2_incidents) == 0

    @patch("_shared.get_metric_data_batch")
    @patch("_shared.run_aws")
    def test_wow_bump_triggers_warning(self, mock_run, mock_batch):
        mock_run.return_value = {"Reservations": [{"Instances": [{"InstanceId": "i-abc123"}]}]}
        # CPU at 50%, Memory at 40%, StatusCheck at 0 — all below thresholds
        # but WoW > 50% triggers WARNING for each
        mock_batch.return_value = {
            ("CPUUtilization", "i-abc123"): {"avg": 50.0, "max": 60.0, "sum": None},
            ("MemoryUtilization", "i-abc123"): {"avg": 40.0, "max": 45.0, "sum": None},
            ("StatusCheckFailed", "i-abc123"): {"avg": 0.0, "max": 0.0, "sum": None},
        }

        with patch("_shared.get_wow_change", return_value=60.0):
            incidents, _, _ = parallel_metric_scan("us-east-1", set(), "run-1", "test")

        ec2_incidents = [i for i in incidents if i.get("resource_id") == "i-abc123"]
        # WoW bump triggers WARNING for each metric (CPU, Memory, StatusCheck)
        assert len(ec2_incidents) == 3
        for inc in ec2_incidents:
            assert inc["level"] == "WARNING"
            assert inc["wow_percent"] == 60.0

    @patch("_shared.get_metric_data_batch")
    @patch("_shared.run_aws")
    def test_critical_threshold(self, mock_run, mock_batch):
        mock_run.return_value = {"Reservations": [{"Instances": [{"InstanceId": "i-abc123"}]}]}
        # CPU at 90% → CRITICAL (>= 85)
        mock_batch.return_value = {
            ("CPUUtilization", "i-abc123"): {"avg": 90.0, "max": 95.0, "sum": None},
        }

        incidents, _, _ = parallel_metric_scan("us-east-1", set(), "run-1", "test")
        ec2_incidents = [i for i in incidents if i.get("resource_id") == "i-abc123"]
        assert len(ec2_incidents) == 1
        assert ec2_incidents[0]["level"] == "CRITICAL"

    @patch("_shared.run_aws")
    def test_empty_inventory_returns_empty(self, mock_run):
        mock_run.return_value = {"Reservations": []}

        incidents, signals, risk = parallel_metric_scan("us-east-1", set(), "run-1", "test")
        assert incidents == []


# ---------------------------------------------------------------------------
# collect_aws_native_insights
# ---------------------------------------------------------------------------
class TestCollectAwsNativeInsights:
    """Tests for collect_aws_native_insights() with mocked collectors."""

    @patch("collectors.registry.audit_xray_service_graph", return_value=[])
    @patch("collectors.registry.audit_rds_proxy", return_value=[])
    @patch("collectors.registry.audit_rds_performance_insights", return_value=[])
    @patch("collectors.registry.audit_autoscaling_headroom", return_value=[])
    @patch("collectors.registry.audit_compute_optimizer", return_value=[])
    @patch("collectors.registry.audit_eks_nodes", return_value=[])
    @patch("collectors.registry.audit_ecs_drift", return_value=[])
    @patch("collectors.registry.audit_waf_blocked", return_value=[])
    @patch("collectors.registry.audit_route53_health_checks", return_value=[])
    @patch("collectors.registry.audit_config_compliance", return_value=[])
    @patch("collectors.registry.audit_guardduty", return_value=[])
    @patch("collectors.registry.audit_security_hub", return_value=[])
    @patch("collectors.registry.audit_devops_guru", return_value=[])
    @patch("collectors.registry.audit_cloudfront_s3_origins", return_value=[])
    @patch("collectors.registry.audit_cloudfront", return_value=[])
    @patch("collectors.registry.audit_acm_expiry", return_value=[])
    @patch("collectors.registry.audit_cloudwatch_alarms", return_value=[])
    def test_all_collectors_run(self, *mocks):
        from collectors.registry import collect_aws_native_insights

        incidents, meta = collect_aws_native_insights(
            "us-east-1", set(), "run-1", "test",
            enable_pi=True, enable_guru=True, enable_cloudfront=True,
            enable_xray=False, enable_rds_proxy=True,
        )
        assert isinstance(incidents, list)
        assert isinstance(meta, dict)
        assert "collectors" in meta
        # All 16 collectors (11 base + pi + guru + cloudfront + cloudfront_s3 + rds_proxy) should be recorded
        assert len(meta["collectors"]) >= 11

    @patch("collectors.registry.audit_acm_expiry", side_effect=Exception("API error"))
    @patch("collectors.registry.audit_cloudwatch_alarms", return_value=[])
    def test_collector_failure_recorded(self, _mock_alarms, _mock_acm):
        from collectors.registry import collect_aws_native_insights

        incidents, meta = collect_aws_native_insights(
            "us-east-1", set(), "run-1", "test",
            enable_pi=False, enable_guru=False, enable_cloudfront=False,
            enable_xray=False, enable_rds_proxy=False,
        )
        # Should not raise, and error should be recorded
        errors = [c for c in meta["collectors"] if "error" in c]
        assert len(errors) >= 1
        assert "API error" in errors[0]["error"]

    @patch("collectors.registry.audit_guardduty", return_value=[{"rule_id": "GD-01"}])
    @patch("collectors.registry.audit_security_hub", return_value=[])
    @patch("collectors.registry.audit_config_compliance", return_value=[])
    @patch("collectors.registry.audit_route53_health_checks", return_value=[])
    @patch("collectors.registry.audit_cloudwatch_alarms", return_value=[])
    @patch("collectors.registry.audit_acm_expiry", return_value=[])
    def test_incidents_aggregated(self, *mocks):
        from collectors.registry import collect_aws_native_insights

        incidents, meta = collect_aws_native_insights(
            "us-east-1", set(), "run-1", "test",
            enable_pi=False, enable_guru=False, enable_cloudfront=False,
            enable_xray=False, enable_rds_proxy=False,
        )
        # guardduty mock returns 1 incident
        assert len(incidents) == 1
        assert incidents[0]["rule_id"] == "GD-01"
