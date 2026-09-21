---
name: speckit-implement
description: Execute approved SØNA implementation tasks with TDD, security, and verification gates.
metadata:
  origin: GitHub Spec Kit
---

# Implement

Read the active constitution, spec, plan, and tasks before changing code.

Execute tasks in dependency order. For new or broken behavior, follow the ECC TDD loop when practical: write a focused test, verify RED, implement the smallest fix, verify GREEN, then refactor while keeping tests green.

Preserve existing SØNA security boundaries. Do not expose secrets, add arbitrary tools, weaken auth, or bypass per-user storage isolation.

After implementation, run the repository's real validation commands: backend tests/compile and relevant API checks, frontend type/build/smoke checks, plus security checks for sensitive changes. Record only results that were actually executed.