# Spec Kit integration

SØNA integrates the workflow principles of GitHub Spec Kit as repository-local Codex skills under `.agents/skills/`.

Upstream: https://github.com/github/spec-kit

## What is integrated

The workflow covers:

- `speckit` — lifecycle and project rules;
- `speckit-specify` — feature specification;
- `speckit-clarify` — high-impact ambiguity resolution;
- `speckit-plan` — codebase-grounded implementation plan;
- `speckit-checklist` — specification quality gate;
- `speckit-tasks` — dependency-ordered implementation tasks;
- `speckit-analyze` — cross-artifact consistency analysis;
- `speckit-implement` — implementation with tests and verification;
- `speckit-converge` — requirement-to-code convergence check.

The project constitution lives at `.specify/memory/constitution.md`.

## Native CLI

The official Spec Kit CLI is distributed as `specify-cli`. The maintainers document installation with `uv tool install specify-cli` or a pinned GitHub release, followed by `specify init --here --force --integration codex` for an existing project.

The repository-local skills above deliberately avoid vendoring the entire upstream CLI and template tree. This keeps SØNA's development workflow reviewable while preserving one authoritative production Agent Runtime.

## Recommended feature flow

```text
Idea
  ↓
Specify
  ↓
Clarify
  ↓
Plan
  ↓
Checklist
  ↓
Tasks
  ↓
Analyze
  ↓
Implement
  ↓
Converge
```

ECC remains the engineering verification layer: TDD RED/GREEN/refactor, security review, build/test verification, and release gates complement the Spec Kit artifact workflow.