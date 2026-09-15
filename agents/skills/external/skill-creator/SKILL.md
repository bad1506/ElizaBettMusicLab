---
name: skill-creator
description: "Author or review AgentSkills: create, repair, validate, or restructure SKILL.md files and bundled resources."
license: MIT
---

# Skill Creator

## Workflow
1. Establish the contract: triggers, expected outcome and persistence target.
2. Choose invocation: model-discoverable, manual-only, or direct tool dispatch.
3. Structure the skill: SKILL.md for workflow, references for branch-specific detail,
   scripts for deterministic helpers, assets for output resources.
4. Draft and persist through the normal repository review workflow.
5. Validate frontmatter, resource paths and focused helper tests.

## Frontmatter
Required: `name` and `description`. Add optional metadata only when it changes
runtime behavior or discovery.

## Source
Adapted from OpenClaw `skills/skill-creator/SKILL.md` at commit
`8326552c19d1eed7ac8b41471db582a1f8eb0d38`.
