# Safety Gates (hard rules)

1. No credential prompts to user. All `{{env.*}}` from runtime; fail
   closed if missing.
2. Destructive actions require explicit human confirmation, even if
   classified `[AUTO_HEAL]`.
3. `[MANUAL]` tier actions never auto-execute.
4. Cross-account actions always `[MANUAL]`.
5. Auto-heal stops at first failure of the same action (no cascade).
6. Idempotency: every delegated write must be idempotent or guarded
   by a state check.
7. Audit trail: every action MUST write a record (CloudTrail
   naturally + an internal `aiops_actions` log entry).

See also [`execution-flow.md`](execution-flow.md) for the recover table and
human-confirmation requirements before destructive delegated calls.
