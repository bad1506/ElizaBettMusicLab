---
name: emil-design-eng
description: Design-engineering skill for Eliza Bett Music Lab based on Emil Kowalski's public design-engineering skills: UI polish, animation restraint, interaction feedback, performance, accessibility, and visual review.
---

# Emil Design Engineering

Source: https://github.com/emilkowalski/skills/tree/main/skills/emil-design-eng

Use this skill when building or reviewing the Music Lab interface. The goal is not to add decoration for its own sake. Optimize for a UI that feels intentional, fast, quiet, and physically coherent.

## Review format

When reviewing UI code, always use this table:

| Before | After | Why |
| --- | --- | --- |
| concrete current implementation | concrete replacement | short design/UX reason |

Do not give vague taste comments. Point to exact selectors/components and exact changes.

## Core rules

### Motion

- First ask whether an interaction needs animation at all.
- Keyboard-driven and very frequent actions should be instant.
- Use animation for feedback, spatial continuity, state changes, or explanation.
- Enter/exit motion should normally use ease-out; movement/morphing uses ease-in-out; continuous motion uses linear.
- Prefer strong custom curves:
  - `cubic-bezier(0.23, 1, 0.32, 1)` for responsive UI entry/feedback.
  - `cubic-bezier(0.77, 0, 0.175, 1)` for deliberate movement.
  - `cubic-bezier(0.32, 0.72, 0, 1)` for iOS-like drawers.
- Keep ordinary UI motion below 300ms. Typical ranges: 100–160ms for press feedback, 125–200ms for small popovers, 150–250ms for dropdowns, 200–500ms for drawers/modals.
- Never use `scale(0)` for an entering UI element. Start around `scale(0.95)` with opacity 0.
- Prefer CSS transitions for interruptible UI state changes; keyframes restart and are less suitable for rapidly changing UI.
- Use springs only where physical continuity or interruptibility is valuable, such as gestures and drag interactions.

### Press feedback

Every important button/control should visibly acknowledge a press:

```css
.button {
  transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.button:active {
  transform: scale(0.97);
}
```

Do not use `transition: all`. Animate only the properties that actually change.

### Hover

Hover effects must be guarded for real pointer devices:

```css
@media (hover: hover) and (pointer: fine) {
  .interactive:hover { /* hover treatment */ }
}
```

Touch devices must not receive fake hover states after tapping.

### Performance

- Prefer animating `transform` and `opacity`.
- Avoid animating layout properties such as width, height, margin, padding, and top/left when smooth interaction matters.
- Prefer CSS animation for predetermined motion because it remains smooth while JavaScript is busy.
- If using Motion for performance-sensitive movement, prefer a full `transform` value over shorthand x/y/scale props.

### Popovers and menus

Anchored popovers should originate from their trigger rather than always scaling from center. Modals are the exception and can remain centered.

### Accessibility

Respect reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  .animated { animation: fade 200ms ease; }
}
```

On reduced-motion devices, remove unnecessary movement while retaining useful opacity/color transitions.

## Music Lab visual direction

Keep the existing approved visual language:

- bright editorial minimalism;
- off-white/white surfaces;
- black typography and restrained gray borders;
- serif/italic Eliza Bett wordmark plus clean sans-serif UI;
- rounded but not excessively pill-shaped controls;
- generous whitespace;
- no human-face imagery in the product hero;
- product/audio abstractions instead of stock people;
- dense functionality should still feel calm and premium.

## Current Music Lab UI audit priorities

When reviewing the existing app, prioritize these concrete issues:

1. Replace generic `transition: .2s` / `transition: all` with property-specific transitions and the custom ease-out curve.
2. Add subtle `:active` feedback to primary buttons, navigation controls, product cards, songwriter mode buttons, saved-draft controls, and send/upload actions.
3. Gate desktop-only hover effects behind `(hover: hover) and (pointer: fine)`.
4. Make chat input/send controls feel immediate; do not animate keyboard submission.
5. Keep the Telegram Mini App layout compact on narrow iPhone screens: fixed/sticky input area, scrollable transcript, and no horizontal overflow.
6. Avoid dumping internal `AI:` / `Client:` / `[VERSE]` / `[CHORUS]` protocol text into the user-facing chat. The transcript should show natural assistant output only.
7. Keep the Songwriter Studio mode bar horizontally scrollable on mobile without shrinking controls until they become hard to tap.
8. Keep Hit Score visually secondary to the writing surface on mobile; stack it below the editor rather than competing for width.
9. Test all motion and touch behavior on a real iPhone/Telegram Mini App, not only desktop.
10. Run a reduced-motion check before release.

## Source skills worth using

The upstream project also provides specialized skills such as `review-animations`, `improve-animations`, `find-animation-opportunities`, `prototype`, `apple-design`, and `pick-ui-library`. Use those when the task specifically calls for animation review, animation planning, design exploration, Apple-style interaction, or dependency selection.
