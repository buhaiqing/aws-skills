#!/usr/bin/env python3
# aws-topo-discovery/scripts/causal_inference.py
# Causal graph inference engine for X-Ray trace + CloudWatch data.
# Supports: build-graph, find-root-cause, detect-anomalies modes.

import argparse
import json
import sys
from collections import defaultdict
from typing import Any, NamedTuple


class CausalEdge(NamedTuple):
    source: str
    target: str
    latency_p50_ms: float
    latency_p99_ms: float
    error_rate: float
    trace_count: int


class CausalGraph:
    def __init__(self):
        self.edges: list[CausalEdge] = []
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._error_counts: dict[str, int] = defaultdict(int)
        self._trace_counts: dict[str, int] = defaultdict(int)
        self._service_names: set[str] = set()

    # ── Data ingestion ────────────────────────────────────────────────────────

    def add_trace(self, segments: list[dict[str, Any]]) -> None:
        """Ingest X-Ray trace segments into the graph (recursive for nested subsegments)."""
        for seg in segments:
            svc_info = seg.get("service", {})
            root = svc_info.get("name", "").strip().strip('"') or None
            self._ingest_segment(seg, root_svc=root, edge_parent=root)

    def _ingest_segment(
        self,
        seg: dict[str, Any],
        root_svc: str | None,
        edge_parent: str | None,
    ) -> None:
        svc_info = seg.get("service", {})
        svc_name: str | None = svc_info.get("name", "").strip().strip('"') or None
        node_name: str | None = seg.get("name", "").strip().strip('"') or None

        # Latency + error counting:
        # - root segment (svc_name set): use svc_name
        # - named subsegment (svc_name set): use svc_name
        # - unnamed subsegment (svc_name=None, node_name set): use node_name
        #   → downstream call latency belongs to the downstream service itself
        counting_svc = svc_name if svc_name else node_name
        if counting_svc:
            self._service_names.add(counting_svc)
            lat = max((seg.get("end_time", 0) - seg.get("start_time", 0)) * 1000, 0.0)
            self._latencies[counting_svc].append(lat)
            err = svc_info.get("error", False) or seg.get("error", False) or seg.get("has_error", False)
            if err:
                self._error_counts[counting_svc] += 1
            self._trace_counts[counting_svc] += 1

        # Subsegment name → edge from edge_parent (the caller's service.name) → node_name
        if edge_parent is not None and node_name:
            lat = max((seg.get("end_time", 0) - seg.get("start_time", 0)) * 1000, 0.0)
            err = seg.get("error", False) or seg.get("has_error", False)
            self._add_edge(edge_parent, node_name, lat, error=err)

        # Recurse: edge_parent = svc_name (caller's service.name) if present;
        # else edge_parent (the caller's node name) — preserves call chain
        # across unnamed intermediate nodes (e.g. ec2-app subsegment → rds-primary).
        for sub in seg.get("subsegments", []):
            sub_name = sub.get("name", "").strip().strip('"') or None
            sub_edge_parent = svc_name if svc_name else edge_parent
            self._ingest_segment(sub, root_svc=root_svc, edge_parent=sub_edge_parent)

    def _add_edge(self, source: str, target: str, latency_ms: float, error: bool = False) -> None:
        # Merge into existing edge or append new
        for i, edge in enumerate(self.edges):
            if edge.source == source and edge.target == target:
                new_p50 = sorted([edge.latency_p50_ms, latency_ms])[len([edge.latency_p50_ms, latency_ms]) // 2]
                new_p99 = max(edge.latency_p99_ms, latency_ms)
                new_err = edge.error_rate
                new_cnt = edge.trace_count + 1
                self.edges[i] = CausalEdge(
                    source, target, new_p50, new_p99,
                    new_err + (1 if error else 0) / new_cnt,
                    new_cnt,
                )
                return
        self.edges.append(CausalEdge(
            source, target, latency_ms, latency_ms,
            1.0 if error else 0.0, 1,
        ))

    # ── Build from service graph (X-Ray get-service-graph JSON) ───────────────

    def build_from_service_graph(self, sg: dict[str, Any]) -> None:
        """Ingest X-Ray get-service-graph output to populate services + edges."""
        # Build referenceId → service name map
        ref_map: dict[int, str] = {}
        for svc in sg.get("Services", []):
            name = svc.get("Name", "unknown")
            rid = svc.get("ReferenceId", -1)
            ref_map[rid] = name
            self._service_names.add(name)

        # Ingest edges
        for edge in sg.get("Edges", []):
            from_id = edge.get("StartId", -1)
            to_id = edge.get("EndId", -1)
            if from_id not in ref_map or to_id not in ref_map:
                continue
            src = ref_map[from_id]
            tgt = ref_map[to_id]

            # Extract latency from histogram if present
            hist = edge.get("ResponseTimeHistogram", [])
            p99 = 0.0
            if hist:
                p99 = max((b.get("Value", 0) for b in hist), default=0.0) * 1000
            self.edges.append(CausalEdge(
                source=src, target=tgt,
                latency_p50_ms=0.0, latency_p99_ms=p99,
                error_rate=0.0, trace_count=0,
            ))

    # ── Latency / error helpers ───────────────────────────────────────────────

    def calculate_error_rates(self) -> dict[str, float]:
        """Return error_rate per service."""
        return {
            svc: self._error_counts[svc] / max(self._trace_counts[svc], 1)
            for svc in self._service_names
        }

    def calculate_latency_p99(self, service: str) -> float:
        lats = self._latencies.get(service, [])
        if not lats:
            return 0.0
        return float(sorted(lats)[int(len(lats) * 0.99)] if len(lats) > 1 else lats[0])

    def get_all_latencies(self, service: str) -> list[float]:
        return self._latencies.get(service, [])

    # ── Anomaly detection ────────────────────────────────────────────────────

    def detect_anomalies(
        self,
        baseline_p99: dict[str, float] | None = None,
        deviation_threshold_pct: float = 50.0,
    ) -> list[dict[str, Any]]:
        """Detect latency anomalies by comparing current p99 vs baseline."""
        anomalies = []
        baseline_p99 = baseline_p99 or {}

        for svc in sorted(self._service_names):
            current_p99 = self.calculate_latency_p99(svc)
            base = baseline_p99.get(svc, current_p99)

            if base > 0:
                deviation_pct = ((current_p99 - base) / base) * 100
            elif current_p99 > 0:
                deviation_pct = 100.0
            else:
                continue

            if deviation_pct >= deviation_threshold_pct:
                anomalies.append({
                    "service": svc,
                    "metric": "latency_p99",
                    "value_ms": round(current_p99, 2),
                    "baseline_ms": round(base, 2),
                    "deviation_pct": round(deviation_pct, 1),
                    "alert_level": "WARNING" if deviation_pct < 100 else "CRITICAL",
                })

        return sorted(anomalies, key=lambda x: x["deviation_pct"], reverse=True)

    # ── Root cause analysis ──────────────────────────────────────────────────

    def find_root_cause(
        self,
        target_service: str,
        error_rate_threshold: float = 0.05,
        latency_threshold_ms: float = 200.0,
    ) -> list[dict[str, Any]]:
        """
        BFS traversal from target_service in both directions:
        - UPSTREAM: callers[svc] → trace back to error sources
        - DOWNSTREAM: callees[svc] → include slow downstream services
        Returns suspects ranked by composite score.
        """
        # Build reverse (callers) and forward (callees) call graphs
        callers: dict[str, list[str]] = defaultdict(list)
        callees: dict[str, list[str]] = defaultdict(list)
        for edge in self.edges:
            callers[edge.target].append(edge.source)
            callees[edge.source].append(edge.target)

        error_rates = self.calculate_error_rates()
        visited: set[str] = set()
        queue: list[tuple[str, int, str]] = [(target_service, 0, "target")]  # (svc, depth, direction)
        suspects: list[dict[str, Any]] = []

        while queue:
            svc, depth, direction = queue.pop(0)
            if svc in visited:
                continue
            visited.add(svc)

            err_rate = error_rates.get(svc, 0.0)
            p99 = self.calculate_latency_p99(svc)

            # Candidate if error rate or latency exceeds threshold
            if err_rate >= error_rate_threshold or p99 >= latency_threshold_ms:
                # Confidence: weighted by error rate + latency deviation, inversely by depth
                depth_factor = max(1.0 / (depth + 1), 0.1)
                confidence = min((err_rate * 0.7) + (min(p99 / 1000.0, 1.0) * 0.3), 1.0) * depth_factor
                suspects.append({
                    "service": svc,
                    "confidence": round(confidence, 3),
                    "depth": depth,
                    "direction": direction,
                    "error_rate": round(err_rate, 4),
                    "latency_p99_ms": round(p99, 2),
                    "reason": (
                        f"error_rate={err_rate:.2%} exceeds threshold {error_rate_threshold:.2%}"
                        if err_rate >= error_rate_threshold
                        else f"latency_p99={p99:.1f}ms exceeds threshold {latency_threshold_ms}ms"
                    ),
                })

            # Traverse: upstream (callers) and downstream (callees)
            queue.extend((c, depth + 1, "upstream") for c in callers.get(svc, []))
            queue.extend((c, depth + 1, "downstream") for c in callees.get(svc, []))

        # Deduplicate by service (keep highest confidence)
        seen: dict[str, dict] = {}
        for s in suspects:
            svc = s["service"]
            if svc not in seen or s["confidence"] > seen[svc]["confidence"]:
                seen[svc] = s

        result = sorted(seen.values(), key=lambda x: x["confidence"], reverse=True)[:3]
        return result

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        error_rates = self.calculate_error_rates()
        return {
            "services": sorted(self._service_names),
            "edges": [
                {
                    "from": e.source,
                    "to": e.target,
                    "latency_p50_ms": round(e.latency_p50_ms, 2),
                    "latency_p99_ms": round(e.latency_p99_ms, 2),
                    "error_rate": round(e.error_rate, 4),
                    "trace_count": e.trace_count,
                }
                for e in self.edges
            ],
            "error_rates": {svc: round(r, 4) for svc, r in error_rates.items()},
        }


# ── CLI entry point ───────────────────────────────────────────────────────────

def build_graph_mode(args: argparse.Namespace) -> None:
    graph = CausalGraph()

    with open(args.traces, "r") as f:
        raw = json.load(f)

    # Support two input shapes:
    # 1. X-Ray service graph (dict with "Services"/"Edges")
    # 2. X-Ray trace segments (list under "Traces" key or top-level list)
    if isinstance(raw, dict):
        if "Services" in raw:
            graph.build_from_service_graph(raw)
        elif "Traces" in raw:
            graph.add_trace(raw["Traces"])
        else:
            # Try to find any list of segments
            for key in raw:
                if isinstance(raw[key], list) and len(raw[key]) > 0:
                    if isinstance(raw[key][0], dict):
                        graph.add_trace(raw[key])
                        break
    elif isinstance(raw, list):
        graph.add_trace(raw)

    output = graph.to_dict()
    output["_mode"] = "build-graph"

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[causal_inference] Graph built: {len(output['services'])} services, {len(output['edges'])} edges → {args.output}")


def find_root_cause_mode(args: argparse.Namespace) -> None:
    with open(args.graph, "r") as f:
        raw = json.load(f)

    graph = CausalGraph()
    # Replay edges from graph JSON
    for edge in raw.get("edges", []):
        graph.edges.append(CausalEdge(
            source=edge["from"],
            target=edge["to"],
            latency_p50_ms=edge.get("latency_p50_ms", 0),
            latency_p99_ms=edge.get("latency_p99_ms", 0),
            error_rate=edge.get("error_rate", 0),
            trace_count=edge.get("trace_count", 0),
        ))
    for svc in raw.get("services", []):
        graph._service_names.add(svc)

    suspects = graph.find_root_cause(
        target_service=args.target,
        error_rate_threshold=args.threshold,
        latency_threshold_ms=args.latency_threshold,
    )

    output = {"target_service": args.target, "root_cause_candidates": suspects}
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[causal_inference] find-root-cause({args.target}): {len(suspects)} candidates → {args.output}")


def detect_anomalies_mode(args: argparse.Namespace) -> None:
    with open(args.graph, "r") as f:
        raw = json.load(f)

    graph = CausalGraph()
    for edge in raw.get("edges", []):
        graph.edges.append(CausalEdge(
            source=edge["from"], target=edge["to"],
            latency_p50_ms=edge.get("latency_p50_ms", 0),
            latency_p99_ms=edge.get("latency_p99_ms", 0),
            error_rate=edge.get("error_rate", 0),
            trace_count=edge.get("trace_count", 0),
        ))
    for svc in raw.get("services", []):
        graph._service_names.add(svc)

    # Use provided baseline or empty
    baseline = {}
    if args.baseline:
        with open(args.baseline, "r") as f:
            baseline_raw = json.load(f)
            baseline = {svc: vals.get("latency_p99_ms", 0) for svc, vals in baseline_raw.items()}

    anomalies = graph.detect_anomalies(
        baseline_p99=baseline,
        deviation_threshold_pct=args.deviation_threshold,
    )

    output = {"anomalies": anomalies}
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[causal_inference] detect-anomalies: {len(anomalies)} found → {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Causal graph inference for aws-topo-discovery")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_build = sub.add_parser("build-graph", help="Build causal graph from X-Ray traces")
    p_build.add_argument("--traces", required=True, help="X-Ray traces JSON file")
    p_build.add_argument("--output", default="/tmp/causal_graph.json", help="Output path")

    p_rc = sub.add_parser("find-root-cause", help="Find root cause candidates")
    p_rc.add_argument("--graph", required=True, help="Causal graph JSON (from build-graph)")
    p_rc.add_argument("--target", required=True, help="Target service name")
    p_rc.add_argument("--threshold", type=float, default=0.05, help="Error rate threshold (default: 0.05)")
    p_rc.add_argument("--latency-threshold", type=float, default=200.0, help="Latency threshold ms (default: 200)")
    p_rc.add_argument("--output", default="/tmp/root_cause.json", help="Output path")

    p_anom = sub.add_parser("detect-anomalies", help="Detect latency anomalies")
    p_anom.add_argument("--graph", required=True, help="Causal graph JSON")
    p_anom.add_argument("--baseline", help="Baseline p99 JSON file")
    p_anom.add_argument("--deviation-threshold", type=float, default=50.0, help="Deviation %% (default: 50)")
    p_anom.add_argument("--output", default="/tmp/anomalies.json", help="Output path")

    # Backward-compat single-flag mode
    compat = argparse.ArgumentParser(add_help=False)
    compat.add_argument("--traces")
    compat.add_argument("--graph")
    compat.add_argument("--mode", choices=["build-graph", "find-root-cause", "detect-anomalies"])
    compat.add_argument("--target")
    compat.add_argument("--threshold", type=float, default=0.05)
    compat.add_argument("--latency-threshold", type=float, default=200.0)
    compat.add_argument("--baseline")
    compat.add_argument("--deviation-threshold", type=float, default=50.0)
    compat.add_argument("--output", default="/tmp/causal_output.json")

    args_extra, _ = compat.parse_known_args()
    if args_extra.mode:
        # Re-parse full compat args
        args = compat.parse_args()
        if args.mode == "build-graph":
            args.mode = "build-graph"
            args.traces = args.traces or args.graph
        # Normalize
        if args.mode == "build-graph":
            build_graph_mode(args)
        elif args.mode == "find-root-cause":
            find_root_cause_mode(args)
        elif args.mode == "detect-anomalies":
            detect_anomalies_mode(args)
        return

    args = parser.parse_args()
    if args.mode == "build-graph":
        build_graph_mode(args)
    elif args.mode == "find-root-cause":
        find_root_cause_mode(args)
    elif args.mode == "detect-anomalies":
        detect_anomalies_mode(args)


if __name__ == "__main__":
    main()
