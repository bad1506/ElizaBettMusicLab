---
name: speckit-analyze
description: Cross-check SØNA specification, plan, tasks, constitution, and codebase for contradictions or missing coverage.
metadata:
  origin: GitHub Spec Kit
---

# Analyze

Read the active constitution, `spec.md`, `plan.md`, and `tasks.md`.

Check for:
- requirements with no implementation or test task;
- tasks with no supporting requirement;
- security or authorization gaps;
- incompatible contracts or duplicated architecture;
- unnecessary scope or dependencies;
- missing deployment/configuration implications.

Report concrete findings and update the plan/tasks only when the correction is within the approved scope. Do not silently invent new product requirements.