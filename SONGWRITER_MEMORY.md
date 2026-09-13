# Songwriter Memory Architecture

The Songwriter Agent now has a local, persistent memory layer.

## 1. Memory
`songwriter_data/memory.json` stores saved drafts, modes, tags, metadata and notes.

## 2. Artist DNA
`artist_dna.json` stores a compact creative profile: themes, language tendencies, hook patterns, strengths, avoid-list and signature phrases.

## 3. Generation rule
Memory is injected into the generation context as evidence. The agent is explicitly instructed not to repeat previous lines verbatim and to use the profile as a preference layer.

## 4. Trend separation
Current music trends are not written into Artist DNA automatically. Trend research remains a separate, dated evidence layer. This prevents temporary trends from becoming permanent style rules.

## 5. Growth loop
Draft → Save → DNA rebuild → next generation → compare → refine.
