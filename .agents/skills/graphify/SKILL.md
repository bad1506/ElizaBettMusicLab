---
name: graphify
description: Use for codebase architecture, file relationships, and project-content questions. Prefer the Graphify knowledge graph when graphify-out/ exists.
---

# Graphify

Graphify turns the repository into a local, queryable knowledge graph. It uses deterministic tree-sitter AST extraction for code and can combine docs/media into the same graph. The graph is not a vector index; edges are marked as extracted or inferred.

## Installation

If the `graphify` command is unavailable, install the official PyPI package `graphifyy` with:

```bash
uv tool install --upgrade graphifyy
```

Then verify:

```bash
graphify --version
```

Do not add `graphifyy` to the application's runtime dependencies just to use the coding skill.

## Repository workflow

1. For architecture/codebase questions, check for `graphify-out/graph.json` first.
2. If it exists, query it before reading many raw files:

```bash
graphify query "<question>"
```

3. Use focused traversal when needed:

```bash
graphify explain "<concept>"
graphify path "<A>" "<B>"
```

4. Build or refresh the graph when it does not exist or is stale:

```bash
graphify .
graphify . --update
```

5. After modifying code in a session, refresh the graph:

```bash
graphify update .
```

6. Useful optional outputs:

```bash
graphify . --no-viz
graphify . --wiki
graphify . --mcp
graphify export html
```

## Safety and accuracy

- Never invent graph edges. Treat `EXTRACTED` and `INFERRED` differently.
- Use the graph for orientation, then inspect exact source lines when changing code.
- Do not expose secrets or credentials to graphify.
- Respect `.gitignore` and use `.graphifyignore` for project-specific exclusions.
- Do not enable remote Gemini/other semantic processing unless the project/user explicitly intends it.
- Do not add graphify output to the application runtime or production deployment unless explicitly required.

## SØNA / ElizaBettMusicLab integration

Graphify is a developer-analysis skill, not an SØNA production agent tool. Keep it outside `agents/tools/` and outside the runtime tool allowlists. It may be used by the coding assistant to understand the repository, while the application's custom Agent Runtime remains the production agent architecture.
