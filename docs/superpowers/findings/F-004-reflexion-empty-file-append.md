---
id: F-004
severity: P2
title: reflexion empty-file append
status: open
added: 2026-07-25
closed: 
phase: l4-closure
---

## Root cause

`_reflexion.append_or_increment` 当目标文件存在但为空 (0-byte) 时静默数据丢失 — 直接 write 不带 header.

## Fix

抽 `_FRESH_HEADER` 常量 + `_needs_fresh_init(path)` helper, 0-byte 时按 fresh init 路径处理. 配 9 测试.

## Lesson

任何 append-or-update helper 必须先 check 目标文件 size, 不要假设 existing content 有 schema.
