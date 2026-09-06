# Inference Latency SLA — Design Spec

> Backfilled 2026-09-06: commit `d10ebda` referenced this file but it was
> never written, leaving the implementation untraceable. Content is derived
> from the shipped code, not the reverse.

## Problem Statement

`aws-aiops-cruise` collects X-Ray service-graph data but discards its
`ResponseTimeHistogram`, so ML inference endpoints (SageMaker / Bedrock /
custom model servers) are invisible in patrol output. Latency regressions on
those endpoints surface only as user complaints — there is no percentile,
no SLA threshold, no rule ID, and the capacity plan has no latency-decay
view. A latent bug compounded this: `audit_xray_service_graph()` never
populated `signals["XRay"]`, so any X-Ray consumer was dead code.

## Solution

Add a percentile layer over X-Ray histograms: compute P50/P95/P99 per node,
filter to inference endpoints, emit rule `INFER-LAT-P95-01` against a
configurable SLA, render a Markdown SLA table, and expose week-over-week P95
drift to capacity planning.

## User Stories

1. As an ops engineer, I see inference endpoint P50/P95/P99 in the patrol
   report so I can judge tail latency without opening X-Ray.
2. As an ops engineer, I get an `INFER-LAT-P95-01` incident when an endpoint
   exceeds the P95 SLA, with level escalated at 1.5× SLA.
3. As an ops engineer, I can override the SLA per environment via
   `INFER_P95_SLA_MS` without editing code.
4. As a capacity planner, I see which inference endpoints' P95 drifted
   >30% week-over-week so latency growth enters the capacity forecast.
5. As a maintainer, X-Ray signals flow into `signals["XRay"]` so downstream
   rules can consume them (bug fix).

## Implementation Decisions

| § | Decision | Location |
|---|----------|----------|
| S1 | `percentile_from_buckets(buckets, p)` — linear interpolation inside the bucket holding the percentile rank; returns `None` for empty input / zero count / p outside (0,1]. Bucket keys are seconds (X-Ray), output converted to **ms**. | `_shared.py:600` |
| S1 | `extract_xray_latency_signals(response)` → `{node: {p50,p95,p99,n,fault_rate}}`, ms. | `_inference.py` |
| S1 | `audit_xray_service_graph()` returns `(incidents, signals)` tuple — fixes always-empty `signals["XRay"]`. | `collectors/compute.py:144` |
| S1 | `patrol_region()` returns `signals` as 6th element; `daily-health-check.py` merges per-layer into `combined_signals`. | `daily-health-check.py:76,134` |
| S2 | `infer_latency_p95_rule()` emits `INFER-LAT-P95-01`. SLA default **1500 ms**, env `INFER_P95_SLA_MS`; `critical = 1.5 × SLA`; skips nodes with `n < 10` samples (low-confidence guard). Level: WARNING if `p95 < critical`, CRITICAL otherwise. | `_inference.py` |
| S2 | Endpoint detection: `_is_inference_endpoint(name)` name-hint heuristic — fallback used because older X-Ray service maps omit `node_type`. | `_inference.py` |
| S3 | `build_inference_latency_table(signals, sla_ms)` renders `## Inference Latency SLA` Markdown table (Endpoint/P50/P95/P99/Samples/SLA/Status); `_report.render_markdown_report()` emits it when `signals["XRay"]` is non-empty. | `_inference.py`, `_report.py:110` |
| S4 | `infer_p95_wow_change(region, wow_threshold_pct=30)` calls X-Ray twice (now, 7d ago), returns endpoints whose P95 moved >30%. | `_inference.py` |
| S4 | `capacity-planning.py` adds `inference_p95_wow` to its report; **best-effort** — X-Ray failure logs `WARN` and yields `[]`, never fails the run. | `capacity-planning.py` |

## Testing Decisions

21 unit tests in `aws-aiops-cruise/tests/test_inference.py`, mapped 1:1 to
spec sections:

| Group | Class | Covers |
|---|---|---|
| V1 | `TestPercentileFromBuckets` | §S1 interpolation, empty/zero-count/`p` bounds, seconds→ms |
| V2 | `TestExtractXrayLatencySignals` | §S1 graph→signals conversion |
| V3 | `TestInferLatencyP95Rule` | §S2 threshold, WARNING/CRITICAL split, `n<10` skip, env override |
| V4 | `TestBuildInferenceLatencyTable` | §S3 rendering, status column, no-endpoint case |

Verification: `pytest aws-aiops-cruise/tests/ -q` (126 passed) ·
`pytest scripts/tests/ -q` (426 passed) · `ruff check` clean.

## Out of Scope

- Real-time alerting / CloudWatch alarm creation from percentiles.
- P99 as a rule trigger (reported only; P95 drives alerting).
- SageMaker `ModelLatency` vs `OverheadLatency` split (recommendation text
  only — requires per-model CloudWatch metrics).
- Historical trend storage; §S4 recomputes from X-Ray on each run.

## Further Notes

- `n < 10` sample floor is a confidence guard, not a tuning knob — a node
  with 9 samples at P95 5 s produces no incident. Raise only with evidence
  that X-Ray sampling under-reports in a given account.
- Auto-scaling detectors (`detect_app_autoscaling_sagemaker` etc.) already
  existed; this spec does not change them.
