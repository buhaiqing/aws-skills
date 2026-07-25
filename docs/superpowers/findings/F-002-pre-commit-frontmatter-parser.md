---
id: F-002
severity: P0
title: pre-commit frontmatter parser
status: fixed
added: 2026-07-25
closed: 2026-07-25
phase: l3-closure
---

## Root cause

原 `scripts/hooks/pre-commit` 用 awk 解析 markdown link `[text](path)`, 对含括号的 path 误判. SKILL.md frontmatter 含 `{{ env.X }}` 模板时被当 link 处理.

## Fix

抽 `scripts/_frontmatter.py` (109 行) 单一职责解析 frontmatter; pre-commit 调它而不是 awk. 配 8 测试.

## Lesson

凡是复杂解析 → 抽 Python helper, 不要 shell awk/sed.
