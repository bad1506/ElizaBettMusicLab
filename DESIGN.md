# Eliza Bett Music Lab — Design System

## Direction
Premium professional audio workstation. Editorial, precise, dark, restrained. The visual language should feel closer to a mastering room / modern DAW than a generic SaaS dashboard.

## Dials
- Design variance: 4/10
- Motion intensity: 3/10
- Visual density: 6/10

## Anti-references
- Purple/blue gradients
- Nested cards
- Repeated three/four-card marketing grids
- Giant decorative hero artwork that competes with audio data
- Generic Inter-only SaaS appearance
- Decorative icon tiles above every heading
- Excessive glassmorphism

## Tokens
- Background: #07090a
- Surface: #0c1011
- Secondary surface: #101516
- Border: #20282a / #293234
- Primary text: #eef3f5
- Muted text: #879296
- Accent: #8ee9ff
- Positive: #8de1b0
- Warning: #e8c37d
- Negative: #ee8f8f

## Interaction principles
1. Every animation must explain state change, hierarchy or progress.
2. A/B controls must be obvious and reversible.
3. Destructive or irreversible audio operations are avoided; master processing has rollback.
4. Analytical copy must distinguish measured values from interpretation.
5. Empty, loading, success, warning and error states are explicit.


## 6.1 Signal Visualization

- Waveform is a restrained signal map, not a decorative oscilloscope.
- Peak and RMS are differentiated with line weight rather than multiple colors.
- Loudness blocks are clickable and map directly to playback position.
- A/B preview is level-matched by integrated LUFS when both measurements are available; the UI labels this as a preview aid, not a compliance measurement.
- Keep the timeline visually subordinate to the decision engine: evidence first, decoration last.

## Audio measurement reference

The engineering model follows the BS.1770 family for programme loudness and true-peak concepts. The current 6.1 segment timeline is explicitly an approximate visualization; it must not be described as a standards-compliant meter. ITU-R BS.1770-5 remains the reference for final loudness/true-peak measurement.

## 6.2 Intelligence UI
- Prefer time-local evidence over isolated headline metrics.
- Use five-second windows for visual analysis; keep final compliance meters separate.
- Findings must explain what was observed, where it occurs, why it may matter and what subsystem could respond.
- Stereo/phase warnings use restrained language: "CHECK" rather than automatic claims of damage.
- Vocal analysis is explicitly labeled as full-mix pitch estimation, not isolated-vocal transcription.
