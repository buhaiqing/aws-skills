#!/usr/bin/env python3
"""Tests for causal_inference.py — covers 5 fault scenarios + normal path."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from causal_inference import CausalEdge, CausalGraph  # noqa: E402


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def graph():
    return CausalGraph()


@pytest.fixture
def xray_trace_normal():
    """Normal call chain: API GW → EC2 App → RDS + ElastiCache"""
    return [
        {
            "service": {"name": "api-gw", "error": False},
            "start_time": 0.0,
            "end_time": 0.15,
            "has_error": False,
            "subsegments": [
                {
                    "name": "ec2-app",
                    "start_time": 0.01,
                    "end_time": 0.12,
                    "error": False,
                    "subsegments": [
                        {"name": "rds-primary", "start_time": 0.02, "end_time": 0.05, "error": False},
                        {"name": "elasticache", "start_time": 0.03, "end_time": 0.035, "error": False},
                    ],
                }
            ],
        },
        {
            "service": {"name": "api-gw", "error": False},
            "start_time": 0.0,
            "end_time": 0.18,
            "has_error": False,
            "subsegments": [
                {
                    "name": "ec2-app",
                    "start_time": 0.01,
                    "end_time": 0.15,
                    "error": False,
                    "subsegments": [
                        {"name": "rds-primary", "start_time": 0.02, "end_time": 0.06, "error": False},
                        {"name": "elasticache", "start_time": 0.03, "end_time": 0.04, "error": False},
                    ],
                }
            ],
        },
    ]


@pytest.fixture
def xray_trace_errors():
    """ALB-01 scenario: EC2 app returns 5xx upstream of RDS timeout"""
    return [
        {
            "service": {"name": "api-gw", "error": True},
            "start_time": 0.0,
            "end_time": 0.5,
            "has_error": True,
            "subsegments": [
                {
                    "name": "ec2-app",
                    "start_time": 0.01,
                    "end_time": 0.48,
                    "error": True,
                    "subsegments": [
                        {
                            "name": "rds-primary",
                            "start_time": 0.02,
                            "end_time": 0.46,  # Very slow → timeout
                            "error": True,
                        }
                    ],
                }
            ],
        },
        {
            "service": {"name": "ec2-app", "error": True},
            "start_time": 0.0,
            "end_time": 0.6,
            "has_error": True,
            "subsegments": [
                {
                    "name": "rds-primary",
                    "start_time": 0.02,
                    "end_time": 0.58,
                    "error": True,
                }
            ],
        },
    ]


@pytest.fixture
def xray_trace_lambda_timeout():
    """CAUSAL-03: Lambda timeout due to downstream slow response"""
    return [
        {
            "service": {"name": "lambda-handler", "error": False},
            "start_time": 0.0,
            "end_time": 0.95,  # Near 1s timeout
            "has_error": False,
            "subsegments": [
                {
                    "name": "dynamodb-table",
                    "start_time": 0.01,
                    "end_time": 0.90,  # Very slow DynamoDB
                    "error": False,
                }
            ],
        }
    ]


@pytest.fixture
def xray_trace_ecs_restart():
    """CAUSAL-04: ECS task restarted due to health check failure"""
    return [
        {
            "service": {"name": "ecs-task", "error": True},
            "start_time": 0.0,
            "end_time": 0.3,
            "has_error": True,
            "subsegments": [
                {
                    "name": "nlb",
                    "start_time": 0.01,
                    "end_time": 0.28,
                    "error": True,  # Health check fail → restart
                    "subsegments": [],
                }
            ],
        }
    ]


@pytest.fixture
def xray_trace_nat_drop():
    """CAUSAL-05: NAT Gateway packet drop"""
    return [
        {
            "service": {"name": "private-subnet-app", "error": True},
            "start_time": 0.0,
            "end_time": 1.0,
            "has_error": True,
            "subsegments": [
                {
                    "name": "nat-gateway",
                    "start_time": 0.01,
                    "end_time": 1.0,
                    "error": True,
                    "subsegments": [
                        {
                            "name": "internet-egress",
                            "start_time": 0.02,
                            "end_time": 1.0,
                            "error": True,
                        }
                    ],
                }
            ],
        }
    ]


@pytest.fixture
def service_graph_xray():
    """X-Ray get-service-graph output"""
    return {
        "Services": [
            {"Name": "api-gateway", "Type": "AWS::API Gateway", "ReferenceId": 0},
            {"Name": "ec2-app", "Type": "AWS::EC2", "ReferenceId": 1},
            {"Name": "rds-primary", "Type": "AWS::RDS", "ReferenceId": 2},
            {"Name": "elasticache", "Type": "AWS::ElastiCache", "ReferenceId": 3},
        ],
        "Edges": [
            {"StartId": 0, "EndId": 1, "ResponseTimeHistogram": [{"Value": 0.12}]},
            {"StartId": 1, "EndId": 2, "ResponseTimeHistogram": [{"Value": 0.045}]},
            {"StartId": 1, "EndId": 3, "ResponseTimeHistogram": [{"Value": 0.008}]},
        ],
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCausalGraphAddTrace:
    def test_normal_call_chain_builds_edges(self, graph, xray_trace_normal):
        graph.add_trace(xray_trace_normal)
        assert len(graph.edges) >= 2  # api-gw→ec2-app + ec2-app→rds + ec2-app→elasticache
        services = graph._service_names
        assert "api-gw" in services
        assert "ec2-app" in services
        assert "rds-primary" in services
        assert "elasticache" in services

    def test_error_traces_set_error_rate(self, graph, xray_trace_errors):
        graph.add_trace(xray_trace_errors)
        err_rates = graph.calculate_error_rates()
        assert err_rates.get("rds-primary", 0) > 0.0

    def test_find_root_cause_alb5xx(self, graph, xray_trace_errors):
        graph.add_trace(xray_trace_errors)
        suspects = graph.find_root_cause("api-gw", error_rate_threshold=0.01)
        assert len(suspects) >= 1
        assert any(s["error_rate"] > 0 for s in suspects)

    def test_find_root_cause_lambda_timeout(self, graph, xray_trace_lambda_timeout):
        graph.add_trace(xray_trace_lambda_timeout)
        suspects = graph.find_root_cause(
            "lambda-handler",
            error_rate_threshold=0.01,
            latency_threshold_ms=100.0,
        )
        # dynamodb-table is the downstream culprit (high latency > threshold)
        assert len(suspects) >= 1
        svc_names = [s["service"] for s in suspects]
        assert "dynamodb-table" in svc_names

    def test_find_root_cause_ecs_restart(self, graph, xray_trace_ecs_restart):
        graph.add_trace(xray_trace_ecs_restart)
        suspects = graph.find_root_cause("ecs-task", error_rate_threshold=0.01)
        assert len(suspects) >= 1
        # nlb is the caller with high error rate (health check failure → ECS restart)
        assert any("nlb" in s["service"] or s["error_rate"] > 0 for s in suspects)

    def test_find_root_cause_nat_drop(self, graph, xray_trace_nat_drop):
        graph.add_trace(xray_trace_nat_drop)
        suspects = graph.find_root_cause("private-subnet-app", error_rate_threshold=0.01)
        assert len(suspects) >= 1

    def test_detect_anomalies_deviation(self, graph, xray_trace_errors, xray_trace_normal):
        graph.add_trace(xray_trace_normal)
        graph.add_trace(xray_trace_errors)
        anomalies = graph.detect_anomalies(
            baseline_p99={"rds-primary": 30.0},
            deviation_threshold_pct=50.0,
        )
        assert len(anomalies) >= 1
        assert any(a["service"] == "rds-primary" for a in anomalies)


class TestCausalGraphServiceGraph:
    def test_build_from_service_graph(self, graph, service_graph_xray):
        graph.build_from_service_graph(service_graph_xray)
        assert "api-gateway" in graph._service_names
        assert "rds-primary" in graph._service_names
        assert len(graph.edges) == 3

    def test_to_dict_serialization(self, graph, service_graph_xray):
        graph.build_from_service_graph(service_graph_xray)
        d = graph.to_dict()
        assert "services" in d
        assert "edges" in d
        assert len(d["services"]) == 4
        assert len(d["edges"]) == 3


class TestCausalGraphEdgeMerging:
    def test_duplicate_edges_merged(self, graph):
        seg1 = [
            {
                "service": {"name": "a"},
                "start_time": 0.0,
                "end_time": 0.1,
                "has_error": False,
                "subsegments": [{"name": "b", "start_time": 0.01, "end_time": 0.08, "error": False}],
            }
        ]
        seg2 = [
            {
                "service": {"name": "a"},
                "start_time": 0.0,
                "end_time": 0.2,
                "has_error": False,
                "subsegments": [{"name": "b", "start_time": 0.01, "end_time": 0.15, "error": False}],
            }
        ]
        graph.add_trace(seg1)
        graph.add_trace(seg2)
        # Edge a→b should be merged, not duplicated
        ab_edges = [e for e in graph.edges if e.source == "a" and e.target == "b"]
        assert len(ab_edges) == 1
        assert ab_edges[0].trace_count == 2


class TestCausalGraphFallback:
    def test_empty_trace_does_not_crash(self, graph):
        graph.add_trace([])
        assert graph.edges == []
        assert len(graph._service_names) == 0

    def test_unknown_service_skipped(self, graph):
        graph.add_trace([{"service": {}, "start_time": 0, "end_time": 0}])
        assert len(graph._service_names) == 0

    def test_find_root_cause_unknown_target(self, graph):
        suspects = graph.find_root_cause("nonexistent", error_rate_threshold=0.01)
        assert suspects == []


class TestCLI:
    def test_build_graph_cli(self):
        trace_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump({"Traces": [{"service": {"name": "svc"}, "start_time": 0, "end_time": 0.1, "has_error": False, "subsegments": []}]}, trace_file)
        trace_file.close()
        out_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        out_file.close()

        result = subprocess.run(
            [sys.executable, "aws-topo-discovery/scripts/causal_inference.py",
             "build-graph", "--traces", trace_file.name, "--output", out_file.name],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        with open(out_file.name) as f:
            data = json.load(f)
        assert data["_mode"] == "build-graph"
        assert "services" in data
        Path(trace_file.name).unlink()
        Path(out_file.name).unlink()

    def test_find_root_cause_cli(self, service_graph_xray):
        graph = CausalGraph()
        graph.build_from_service_graph(service_graph_xray)
        graph_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(graph.to_dict(), graph_file)
        graph_file.close()
        out_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        out_file.close()

        result = subprocess.run(
            [sys.executable, "aws-topo-discovery/scripts/causal_inference.py",
             "find-root-cause", "--graph", graph_file.name,
             "--target", "rds-primary", "--threshold", "0.05",
             "--output", out_file.name],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        with open(out_file.name) as f:
            data = json.load(f)
        assert "root_cause_candidates" in data
        Path(graph_file.name).unlink()
        Path(out_file.name).unlink()

    def test_compat_mode_build(self):
        """Backward-compat single-flag mode: --mode build-graph"""
        trace_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump({"Traces": [{"service": {"name": "x"}, "start_time": 0, "end_time": 0.1, "has_error": False, "subsegments": []}]}, trace_file)
        trace_file.close()
        out_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        out_file.close()

        result = subprocess.run(
            [sys.executable, "aws-topo-discovery/scripts/causal_inference.py",
             "--mode", "build-graph", "--traces", trace_file.name, "--output", out_file.name],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        Path(trace_file.name).unlink()
        Path(out_file.name).unlink()
