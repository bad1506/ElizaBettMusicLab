---
name: music-lab-code-review
description: Review Music Lab changes for regressions, security issues, API drift and unnecessary complexity.
---

# Music Lab Code Review

Review changes in this order:
1. Correctness and regression risk.
2. API contract compatibility.
3. Security and secret handling.
4. Mobile/responsive behavior.
5. Performance and unnecessary dependencies.
6. Maintainability and tests.

Prefer targeted fixes. Flag destructive rewrites, duplicated logic, unverified production claims and changes that break existing flows.
