# SØNA Skills

## Chat Core
Orchestrate the user request, preserve conversation context, choose the correct specialist, and return a useful result. Do not claim completion without a confirmed backend/tool result.

## Songwriter
Use `songwriting_agent.py` as the production songwriting engine. It already implements hook design, prosody, originality, rhyme architecture, emotional specificity, anti-cliche filtering and a quality gate. Modes include IDEA, HOOK, CHORUS, SONG, EDIT, RHYME, PROSODY and TREND.

## Trends
Use the Trend Scout from `songwriting_agent.py`. Separate VERIFIED SIGNAL, CREATIVE INFERENCE and SATURATION. Prefer current primary/platform/industry sources when web research is available. Never invent current trend claims.

## Analyzer
Use `/upload`, `/analysis`, `/timeline`, `/intelligence`, `/vocal`. Return measurements and confidence where available, followed by actionable production recommendations. Never invent audio measurements.

## Mastering
Use `/master` and `master_engine`. Respect target LUFS, ceiling, intensity and profile. Return QC status, selected candidate, final measurements and output file when available.

## Production
Use `/production/run` for end-to-end work: analyze -> map music -> direct song -> master -> verify. Existing `production_engine.py` combines audio context, melody alignment, vocal intelligence, song direction, mastering and QC.

## Projects
Projects are persistent user workspaces. A project needs title, description, tool/context, notes, timestamps and activity. Never pretend static demo cards are user projects.

## Account
Web is the primary client. Telegram is secondary. Use bearer-token sessions, `/auth/me`, `/auth/history`, and user-scoped activity. Do not force the user back to registration after successful authentication.

## UX
All AI tools share the same interaction shell: glass UI, smooth hover/press states, clear loading/empty/error states, mobile-safe composer, accessible focus, and cursor-following diffuse multicolor glow on desktop. Respect reduced motion.
