# SØNA Skill System

SØNA uses small, domain-specific skills so each AI surface has its own operating context instead of one generic prompt.

## Skills

- `assistant.md` — general SØNA conversation and routing.
- `songwriter.md` — lyrics, hooks, structure, melody direction and editing.
- `audio-analysis.md` — technical audio analysis and actionable mix feedback.
- `mastering.md` — mastering targets, loudness, dynamics and QC.
- `trends.md` — current music trends, references, audience/platform fit and idea generation.
- `projects.md` — project creation, planning, versioning and release workflow.
- `release-marketing.md` — positioning, release plans, content and promotion.
- `frontend-design.md` — SØNA interface rules inspired by current agent-skill design practice.

## Sources studied

The structure is informed by public agent-skill conventions and repositories including Anthropic's `skills`, Addy Osmani's `agent-skills`, Corey's `marketingskills`, and Phuryn's `pm-skills`. We keep SØNA's implementation original and domain-specific rather than copying source text.

## Runtime contract

Frontend sends `context.skill` when a specialized assistant is used. Backend loads the matching Markdown file and injects it into the model context. Unknown skills fall back to `assistant`.
