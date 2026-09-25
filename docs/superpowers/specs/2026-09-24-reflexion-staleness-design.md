# Reflexion Staleness — failure-patterns growth + item-level maturity detection

> Spec. Date: 2026-09-24. Branch: `feature/reflexion-staleness`.
> Motivation: RSI audit (2026-09-24) O3: `docs/failure-patterns.jsonl` has 26 rows all `source=manual` / `last_seen=2026-08-22` (33+ days stale — reflexion auto-append not producing real data). Separately, `scan-stale-maturity` skips flagging any ⚠️ item when the *section* has any recent changelog activity, so §6.3 "M1 满窗 telemetry" stays ⚠️ without being flagged (P1-1 audit finding).

## 1. Problem (disk-verified)

**A. Reflexion data frozen**:
```
$ wc -l docs/failure-patterns.jsonl → 26
$ source counts: {'manual': 26},  last_seen range: 2026-08-22 → 2026-08-22
```
No staleness signal exists. Operator has no way to know reflexion stopped flowing.

**B. Item-level detection gap** (`self_review.py:246-247`):
```python
if recent_text.strip():   # any changelog row in section within 30d → skip ALL ⚠️
    continue
```
§6.3 was edited 2026-07-31 (M1-M4 loop) → section has recent activity → specific ⚠️ item "M1 满窗 telemetry 基线" never flagged despite 30+ days silence.

## 2. Goal / Non-goals

**Goal**
- G1: New CLI `self_review.py check-reflexion-freshness --days N` exits 1 + prints when `docs/failure-patterns.jsonl` newest `last_seen` is older than N days (or file empty/missing); exits 0 + prints fresh summary otherwise.
- G2: `scan-stale-maturity` flags a ⚠️ item when its extracted keyword does NOT appear in the recent changelog window, even if the section has other changelog activity (item-level, not section-level).
- G3: Existing behavior preserved: section with NO recent changelog still flags all ⚠️; existing 4 tests stay green.

**Non-goals**
- Not changing reflexion append logic (mechanism works; data absence is a runtime-trigger issue).
- Not auto-migrating ⚠️→❌ (still dry-run; operator decides).
- Not seeding failure-patterns.jsonl (O5's concern).

## 3. Contract

- **C1** (scope): `scripts/self_review.py` + `scripts/tests/test_maturity_stale.py` (extend) + `scripts/tests/test_reflexion.py` (extend) + `scripts/tests/test_rubric_completeness.py` (worktree-safe glob — see amendment below). No other files.
- **C2** (back-compat, **amended 2026-09-24 after GREEN round**; **corrected after Critic R1**): section with NO recent changelog still flags all ⚠️ (unchanged). **Two Fix #1 fixtures' changelog rows reworded to name their items — necessity differs (Critic R1 falsification probe verified):** **fixture 2** (`test_scan_threshold_parameterization`, `last mention` → `**21-day-old item** last mention`) — *required*: without the item name, `f30`/`f90` flag via item-level match and break the 7/30/90 threshold semantics; **fixture 1** (`test_scan_returns_empty_when_no_stale`, `referenced today` → `mentioned recently`) — *required* (corrected after Critic R2): ident falls back to the full status_part `Active item mentioned recently` (⚠️ occupies the first cell so name_part is empty), and the original changelog `active item referenced today` contains neither ident nor kw — without the reword the test would flag. Date-threshold semantics (7/30/90d) preserved exactly.
- **C3** (idempotent): `check-reflexion-freshness` is read-only; repeated runs same verdict.
- **C4** (added): only table rows (`|`-prefixed) under non-legend headings are scanned — §2 状态图例 rows and migration-rule bullets are definitions, not stale items. Finding title uses the **item identifier** (cells before ⚠️, `*`-stripped, 30 chars) instead of status text after ⚠️.
- **C5** (added): `test_rubric_completeness._rubric_files` filters `.worktrees` **relative to REPO** — the old absolute-parts filter zeroed `RUBRICS` inside any worktree (REPO lives under `.worktrees/`), crashing pytest collection via `ids=_id` receiving NotSet. Blocks full-suite gates in every worktree; fixed alongside.

## 4. Implementation

### 4.1 `check-reflexion-freshness`

New CLI subcommand:

```python
p_rf = sub.add_parser("check-reflexion-freshness",
                      help="Exit 1 if failure-patterns.jsonl newest last_seen older than --days.")
p_rf.add_argument("--patterns", default="docs/failure-patterns.jsonl")
p_rf.add_argument("--days", type=int, default=7)
p_rf.add_argument("--as-of", default=None, help="ISO date; default=today")
```

Logic: parse JSONL (per-line `json.loads`; malformed line → stderr `malformed JSONL: path:line` + exit 1, fail-closed clean — no traceback), extract max `last_seen` (ISO date), compute age; missing file / empty / no `last_seen` / malformed / age > days → stderr reason + exit 1; else exit 0 + stdout "fresh: N rows, newest <date> (<age>d)".

The subcommand declares **no `--repo`** (reads only `--patterns`); the shared `repo = Path(...)` line in `_cli` is guarded with `getattr(args, "repo", ".")` (Critic R1 MINOR: dead arg removed rather than documented).

### 4.2 `scan_stale_maturity` item-level

In the ⚠️ loop, when `recent_text.strip()` is truthy (section has activity), do NOT `continue` unconditionally. Instead check **identifier** presence:

```python
if recent_text.strip():
    hay = recent_text.replace("*", "").lower()
    if ident.lower() in hay or kw.lower() in hay:
        continue   # item addressed → fresh
    # fall through: section busy but this item untouched → flag
```

`ident` = item name (cells **before** ⚠️, `*`-stripped, ≤60 chars), falling back to full status text (icon-first legacy layout). Case-insensitive substring match — succeeds when the changelog **names the item verbatim**. **Known limitation (corrected after Critic R1)**: paraphrases without the literal name ARE flagged — the operator then either rewords the changelog row or migrates ⚠️→❌; both are valid outcomes. Fuzzy/alias matching is a follow-up if false positives grow beyond the current defensible set.

## 5. Verification

- Gate 1: `check-reflexion-freshness --days 7` on real repo (last_seen 2026-08-22, 33d stale) → exit 1 + stderr "stale".
- Gate 2: same with `--days 40` → exit 0.
- Gate 3: `scan-stale-maturity --as-of 2026-09-24` on real model → §6.3 "M1 满窗" ⚠️ now flagged (was 0 stale before).
- Gate 4: **6 new tests** (2 maturity-stale + 4 reflexion freshness) + full suite **577 passed**; ruff clean. [max 10 min]

## 6. Tests (RED first; counts corrected after Critic R1)

Extend `test_maturity_stale.py` (2 new):
1. `test_scan_flags_item_stale_when_section_active` — ⚠️ item ident absent from recent changelog → flagged, even though section has other rows.
2. `test_scan_item_fresh_when_kw_in_recent_changelog` — ident present in recent changelog → not flagged (regression guard).

Extend `test_reflexion.py` (4 new):
3. `test_check_reflexion_freshness_stale` — JSONL newest last_seen 10d old, `--days 7` → exit 1 + stderr "stale".
4. `test_check_reflexion_freshness_fresh` — newest last_seen 2d old, `--days 7` → exit 0.
5. `test_check_reflexion_freshness_missing_file` — absent file → exit 1 + stderr "missing".
6. `test_check_reflexion_freshness_malformed_jsonl` (R2) — corrupt line → exit 1 + stderr "malformed JSONL", no traceback.