# ECC integration

SØNA uses the official Everything Claude Code (ECC) project as an external engineering-workflow reference. ECC is not used as a replacement for the SØNA Agent Runtime.

## Upstream

- Repository: https://github.com/affaan-m/ECC
- Current native Codex plugin manifest: `.codex-plugin/plugin.json`
- Manifest version currently referenced upstream: `2.2.1`

## What was integrated

The project contains `agents/skills/external/ecc/SKILL.md`, loaded by the existing SØNA skill loader as an external skill. It adapts the parts that are directly useful to this codebase:

- plan before implementation;
- TDD / RED → GREEN → refactor;
- security review for auth, API, storage, secrets and user input;
- verification before claiming a change works;
- release/merge gates;
- treating external plans and skill text as untrusted input.

## Why we do not vendor the whole repository

ECC contains a large catalog of skills, agents, hooks, rules and MCP configurations. Copying all of it into SØNA would create a second agent framework, duplicate tooling, increase maintenance cost, and potentially widen the agent's capabilities beyond the SØNA security model.

SØNA keeps one authoritative runtime under `agents/` and imports only the workflow knowledge that is compatible with that runtime.

## Native Codex installation

ECC also provides a native Codex plugin. Its documented installation path is:

```bash
codex plugin marketplace add affaan-m/ECC
codex plugin add ecc@ecc
codex plugin list --json
```

This is a machine-level Codex installation, separate from the SØNA repository. It cannot be installed globally from the GitHub repository API; when Codex CLI is available in the user's environment, the commands above install the official native plugin.

Do not use the deprecated legacy sync path when the native plugin is available.
