---
name: speckit-specify
description: Create a bounded, testable feature specification before implementation.
metadata:
  origin: GitHub Spec Kit
---

# Specify

Read `.agents/skills/speckit/SKILL.md` first.

Create or update one feature specification under `specs/<NNN-feature>/spec.md`.

Focus on **what** the user needs and **why**, not implementation details. Capture:
- problem and user value;
- actors and user scenarios;
- functional requirements that can be tested;
- edge cases and failure behavior;
- assumptions and explicit scope boundaries;
- measurable, technology-agnostic success criteria.

Limit `[NEEDS CLARIFICATION]` items to decisions that materially affect scope, security/privacy, or UX. Prefer documented reasonable defaults for everything else.

Do not write production code in this phase. Finish with a specification-quality review and a checklist path.