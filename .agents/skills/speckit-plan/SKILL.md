---
name: speckit-plan
description: Turn a reviewed SØNA specification into a minimal implementation plan grounded in the existing codebase.
metadata:
  origin: GitHub Spec Kit
---

# Plan

Read the active spec, constitution, and repository architecture before planning.

Produce `plan.md` beside the active `spec.md` with:
- affected components/files and existing contracts;
- technical approach and interfaces;
- data/storage/auth implications;
- dependencies only where justified;
- test and verification strategy;
- deployment/configuration impact;
- rollback or compatibility considerations.

Prefer extending existing SØNA architecture over introducing parallel runtimes or unnecessary services. Keep the plan implementable in small reviewable steps.