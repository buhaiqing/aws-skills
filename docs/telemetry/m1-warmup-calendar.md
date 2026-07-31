# M1 Telemetry Warm-up Calendar

> **Purpose**: 日历卫生 — 追踪 30 天满窗，**禁止提前勾选** ADR M1 满窗 checkbox。  
> **Does not expand AUTO_HEAL**（满窗后仅解锁评审）。

## Anchors

| Field | Value |
|---|---|
| Warm-up start (UTC date of first official snapshot) | **2026-07-31** |
| Full-window target | **2026-08-30**（start + 30 days） |
| First snapshot | [`dashboard-2026-07-31.md`](dashboard-2026-07-31.md) |
| ADR gate | [`docs/adr/0001-l4-production-evidence-loop.md`](../adr/0001-l4-production-evidence-loop.md) §M1 Progress |

```bash
# 距满窗天数（本地）
python3 scripts/telemetry_warmup.py status
```

## Refresh cadence (Wave B1)

| Action | When | Command |
|---|---|---|
| Dashboard snapshot | merge to `main` high-risk CI **or** local daily | `python3 scripts/telemetry_dashboard.py dashboard --audit-dir audit-results/ --window-days 30 --out docs/telemetry/dashboard-$(date -u +%Y-%m-%d).md` |
| Alert | CI blocking | `python3 scripts/telemetry_dashboard.py alert --audit-dir audit-results/ --drop-threshold 0.05` |
| Status clock | anytime | `python3 scripts/telemetry_warmup.py status` |

## Closeout checklist（仅 ≥2026-08-30 且全部通过才勾 ADR）

- [ ] `python3 scripts/telemetry_warmup.py status` 显示 `full_window_eligible: true`
- [ ] 近 30 天内有连续/足够 snapshot（至少 start + closeout 两份，建议每周 ≥1）
- [ ] `telemetry_dashboard.py alert --drop-threshold 0.05` exit 0
- [ ] 信号源说明诚实：若 CI 仅 golden、gcl-trace 稀缺，在 ADR Progress 注明 **golden-heavy window**
- [ ] ADR §M1 满窗 checkbox → `[x]`
- [ ] **仍不**自动扩大 AUTO_HEAL（仅「可开始评审」）

## Honesty rules

1. Day &lt; 30 → `closeout-check` **必须失败**（exit 1）。
2. 不得为关单伪造 `audit-results/` 历史。
3. `audit-results/` gitignored — CI 用 artifact（retention ≥35d）保留 run 产物；跨 run 累积 gcl-trace 仍为已知缺口，满窗叙述需写明。
