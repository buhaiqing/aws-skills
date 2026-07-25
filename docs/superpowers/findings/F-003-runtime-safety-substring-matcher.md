---
id: F-003
severity: P0
title: runtime_safety substring matcher
status: fixed
added: 2026-07-25
closed: 2026-07-25
phase: l3-closure
---

## Root cause

`runtime_safety.py` 用 `command.find(op)` 检测 destructive-op (e.g. `terminate-instances`). 但 `aws ec2 describe-instances` 也含 `terminate-instances` substring, 被误命中 → Safety=0 → 阻断无害操作.

## Fix

改为 token-level regex `re.search(rf"\\b{re.escape(op)}\\b", command)`. 配 4 测试覆盖 describe / terminate / tag 边界.

## Lesson

任何 destructive-op 检测必须用 token boundary (regex `\b`), 不能用 substring. 同样的规则适用于所有 GCL safety checks.
