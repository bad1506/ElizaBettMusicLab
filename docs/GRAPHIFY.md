# Graphify

ElizaBettMusicLab uses Graphify as a developer-side codebase analysis skill.

Upstream: https://github.com/Graphify-Labs/graphify
Package: `graphifyy`

## Purpose

Graphify creates a local knowledge graph from source code and project documentation. It is used to orient coding work, trace relationships, and answer architecture questions before broad raw-file exploration.

## Install locally

```bash
uv tool install --upgrade graphifyy
graphify --version
graphify .
```

## Query

```bash
graphify query "how does authentication flow through the backend?"
graphify explain "Agent Runtime"
graphify path "auth" "agent router"
```

The graph is developer tooling only. It is not part of the SØNA production Agent Runtime and must not receive arbitrary production credentials or become an application tool without an explicit security review.
