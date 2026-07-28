# P0 Trust Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development`.

**Goal:** Make GCL and Runtime Safety enforce their documented trust boundaries at runtime.

**Architecture:** Keep GCL orchestration in `scripts/gcl_runner.py`, with a
small set of internal helpers for redaction, process execution, and contract
validation. Centralize destructive detection and confirmation-token derivation
in `scripts/runtime_safety.py`; add `scripts/safe_tool_proxy.py` as the only
execution wrapper for structured tool calls.

**Tech Stack:** Python 3.12 standard library, pytest, ruff, JSON stdin/stdout.

---

### Task 1: GCL trust-boundary regression tests

**Files:**
- Create: `scripts/tests/test_gcl_runner.py`
- Modify: none

- [x] Test Critic subprocess input omits raw request and `user` namespace.
- [x] Test prior Critic suggestions appear in the next Generator input.
- [x] Test malformed Generator/Critic JSON is rejected.
- [x] Test subprocess timeout returns deterministic failure and cleans up.
- [x] Test trace redaction removes secret keys and credential-like values.
- [x] Run `python3 -m pytest -p no:rerunfailures scripts/tests/test_gcl_runner.py -q` RED then GREEN.

### Task 2: Runtime Safety trust-boundary tests

**Files:**
- Modify: `scripts/tests/test_runtime_safety.py`
- Create: `scripts/tests/test_safe_tool_proxy.py`

- [x] Test destructive risk is detected when caller flag is false or absent.
- [x] Test arbitrary non-empty confirmation is rejected.
- [x] Test exact plan-bound confirmation is accepted without matching pattern.
- [x] Test plan changes invalidate the previous confirmation.
- [x] Test proxy blocks WARN/BLOCK and executes only ALLOW.
- [x] Run focused tests and observe RED then GREEN before implementation.

### Task 3: Implement GCL boundary

**Files:**
- Modify: `scripts/gcl_runner.py`

- [x] Add recursive redaction and sanitized request/trace serialization.
- [x] Split Generator and Critic contexts so Critic receives no raw request.
- [x] Add `critic_feedback` to the next Generator iteration.
- [x] Add bounded process-group execution and strict JSON validation.
- [x] Make malformed/timeout paths terminate as `SAFETY_FAIL`.
- [x] Run `python3 -m pytest -p no:rerunfailures scripts/tests/test_gcl_runner.py -q`.

### Task 4: Implement Runtime Safety and proxy

**Files:**
- Modify: `scripts/runtime_safety.py`
- Create: `scripts/safe_tool_proxy.py`

- [x] Add operation-level destructive detection for AWS CLI and boto3 names.
- [x] Add canonical normalized-plan confirmation token helper.
- [x] Make missing or invalid confirmation a BLOCK for destructive calls.
- [x] Preserve failure-pattern BLOCK behavior.
- [x] Implement proxy JSON input, safety check, command execution, and output schema.
- [x] Run focused Runtime Safety and proxy tests.

### Task 5: Update contracts and integration guidance

**Files:**
- Modify: `aws-skill-generator/references/gcl-spec.md`
- Modify: `AGENTS.md`

- [x] Document the separated Critic context and feedback contract.
- [x] Document timeout, schema, redaction, and safe proxy requirements.
- [x] Update Runtime Safety decision table to reflect autonomous detection and BLOCK-on-invalid-confirmation.
- [x] Keep examples aligned with the implemented token format.

### Task 6: Verification and review

- [x] Run focused RED/GREEN tests and record output.
- [x] Run `python3 -m pytest -p no:rerunfailures scripts/tests/ -q` — 142 passed.
- [x] Run `ruff check .` — clean.
- [x] Run `python3 scripts/gcl_runner.py --skill aws-s3-ops --self-test --no-prune` — destructive SAFETY_FAIL and read-only PASS.
- [x] Run proxy read-only and destructive dry-run checks.
- [x] Run full structural/content/cross-cutting review and inspect `git diff --stat`.

## Verification note

`python3 scripts/te_gate.py --all --strict` remains red on the pre-existing
37-Skill TE baseline (line-count/Common JSON Paths violations); this P0 change
does not modify any operational Skill and introduces no new TE target.
