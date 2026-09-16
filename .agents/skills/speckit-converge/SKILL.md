---
name: speckit-converge
description: Verify that implemented SØNA code satisfies the active specification and close remaining gaps with concrete follow-up tasks.
metadata:
  origin: GitHub Spec Kit
---

# Converge

Read the active constitution, specification, plan, and tasks, then inspect the resulting code and validation evidence.

For every functional requirement, identify the implementation and verification evidence. Check acceptance scenarios, edge cases, security constraints, API contracts, and deployment configuration.

If a requirement is incomplete, append a concrete task to `tasks.md` rather than declaring success. Re-run the relevant validation after closing gaps. Finish only when there are no known artifact-to-code gaps or clearly documented follow-ups.