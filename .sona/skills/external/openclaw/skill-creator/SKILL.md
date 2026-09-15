---
name: skill-creator
description: "Author or review AgentSkills: create, repair, validate, or restructure SKILL.md files and bundled resources."
---

# Skill Creator

## Workflow

1. Establish the contract.
   - Read the existing skill and its resources, or collect concrete requests for a new skill.
   - Separate actual workflow branches from synonyms for the same branch.
   - **Done when:** every branch has a concrete trigger, expected outcome, and persistence target.

2. Choose invocation.
   - Model-discoverable: write a model-facing `description`; omit `disable-model-invocation`.
   - Manual-only: set `disable-model-invocation: true`; write a human-facing summary.
   - Direct tool command: set `command-dispatch: tool`, `command-tool`, and `command-arg-mode` only when the command bypasses the model.
   - **Done when:** frontmatter matches how the skill will actually be reached.

3. Structure the skill.
   - Map the shared ordered procedure to `SKILL.md`; end every step with a checkable completion criterion and finish with verification.
   - Keep routing conditions in `description`; start the body with execution.
   - Put branch-only detail in `references/`, deterministic helpers in `scripts/`, and output resources in `assets/`.
   - **Done when:** every planned resource has one purpose and a direct pointer from `SKILL.md`.

4. Draft and persist.
   - Repository-owned skill source: use the repository's normal edit and review workflow.
   - **Done when:** the source diff implements every branch and contains every required resource.

5. Validate.
   - Validate frontmatter, resource pointers and focused helper tests before enabling the skill.
   - **Done when:** all validation checks pass.

## Frontmatter

Required: `name`, `description`.

OpenClaw also supports metadata, license, allowed-tools, user-invocable, disable-model-invocation, command-dispatch, command-tool and command-arg-mode. Add optional fields only when they change runtime behavior or discovery.

## SØNA adaptation

This skill is used only to design and review SØNA skills. It never grants shell access or permission to install third-party packages by itself.
