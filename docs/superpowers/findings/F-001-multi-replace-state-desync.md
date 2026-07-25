---
id: F-001
severity: P1
title: multi-replace state desync
status: accepted
added: 2026-07-25
closed: 2026-07-25
phase: l3-closure
---

## Root cause

Python 没有 partial execution. 当 `python3 << EOF` 脚本中先做 assert 检查, 再做 file replace, assert 失败时前面所有 replace 都没生效, 但 session 上下文可能仍认为它们生效了.

## Fix

无 code fix (process bug). Convention fix:
1. 每个 update 跑独立 `exec_command` session
2. 末尾 grep 反向验证 stale marker 是否清零

## Lesson

任何批量 update 必须**反向验证** (grep / read-back), 不能信 assert.
