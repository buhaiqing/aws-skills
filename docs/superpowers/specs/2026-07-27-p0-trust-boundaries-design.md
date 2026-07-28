# P0 Trust Boundaries Design

- **Date**: 2026-07-27
- **Status**: Approved for implementation from the P0 objective
- **Scope**: GCL orchestration and Runtime Safety execution boundary

## Problem

The repository has strong safety policies, but two runtime boundaries are
weaker than their contracts. The GCL Critic receives a context that still
contains the original user request, retries do not pass Critic feedback back to
the Generator, external subprocesses have no bounded execution contract, and
trace output is not consistently redacted. Runtime Safety trusts the caller's
destructive-operation flag and accepts arbitrary non-empty confirmation text.

## Goals

1. Keep the Critic context independent from the raw user request.
2. Feed validated Critic suggestions into the next Generator iteration.
3. Bound Generator/Critic subprocesses and validate their JSON contracts.
4. Redact secrets before trace persistence and Critic delivery.
5. Detect destructive operations inside the safety boundary, not only in the caller.
6. Require an exact confirmation token bound to the operation plan.
7. Provide a single safe tool-proxy entry point for executable tool calls.

## Non-goals

- Rewriting every AWS skill or AWS operation implementation.
- Adding live AWS calls to the test suite.
- Cryptographic human identity verification; the token binds the displayed plan,
  not the identity of the approving person.
- Replacing existing failure-pattern storage.

## Design

### GCL context boundary

`GeneratorContext` may contain the raw request. `CriticContext` must contain
only `iter`, sanitized generator output/trace, rubric, derived output fields,
and previous decision evidence. It must not contain `user`, `request`, or raw
user-originated prompt fields. The runner derives risk and confirmation data
from the Generator result before constructing CriticContext.

The runner stores a sanitized request representation and sanitized Generator
output in the trace. Secret-like keys and values are redacted recursively.

### GCL retry and process contract

The runner carries the prior Critic suggestions as `output.critic_feedback` in
the next Generator context. External Generator and Critic commands run with a
bounded timeout, process-group cleanup on timeout, and strict JSON object
validation. Invalid output is a safety failure, never a best-effort pass.

### Runtime Safety boundary

`runtime_safety.py` derives destructive risk from AWS CLI service/operation
tokens and boto3/custom operation names. The caller-provided legacy flag is
ignored for the decision. A destructive call without the exact plan-bound
confirmation token is blocked.

The canonical token is derived from normalized tool name, normalized args,
region, account, and an optional expiry. The token format is stable and
human-readable: `CONFIRM <operation> <plan-sha256-prefix>`. The same helper is
used by the CLI and proxy, preventing duplicated token logic.

`safe_tool_proxy.py` accepts a structured JSON tool call, invokes
`runtime_safety.check_tool_call`, and executes the command only after ALLOW.
It never executes on WARN or BLOCK and emits a structured decision record.

## Acceptance criteria

- Critic subprocess input contains no `user` key or raw request.
- A failed first iteration with Critic feedback changes the second Generator input.
- Generator/Critic timeout and malformed JSON produce deterministic safety failure.
- Known secret keys and common credential patterns are absent from persisted trace.
- Destructive risk is detected even when the caller marks it false or omits the flag.
- A random non-empty confirmation is blocked.
- The exact token generated for the same normalized plan allows the call when no
  high-frequency failure pattern matches.
- Safe proxy executes read-only commands, and refuses destructive commands unless
  Runtime Safety returns ALLOW.
- Existing tests remain green; new tests prove each acceptance criterion.

