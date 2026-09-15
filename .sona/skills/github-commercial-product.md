---
name: github-commercial-product
description: Commercial product, growth, UX and delivery skill synthesized from selected public GitHub AgentSkills sources for SØNA.
version: 1.0.0
license: MIT
metadata:
  sources:
    - coreyhaines31/marketingskills
    - phuryn/pm-skills
---

# SØNA Commercial Product Skill

Use this skill when the task concerns the SØNA website as a commercial product: onboarding, account flow, conversion, pricing, product positioning, feature discovery, launch, analytics, project delivery or UX quality.

## Product-first workflow
1. Identify the user, job-to-be-done, desired outcome and current friction.
2. Preserve the SØNA product context: music creation, analysis, improvement and release in one workspace.
3. Prefer a complete working flow over a decorative mockup.
4. For every new interaction define: loading state, success state, empty state, error state and retry path.
5. Keep account, project, activity and assistant context persistent across reloads when the user is authenticated.
6. Never claim a live integration works until the real endpoint has returned usable data.

## Growth and conversion
Apply the relevant marketing frameworks from the selected public sources without copying their text:
- product marketing: audience, positioning, value proposition and proof;
- copywriting: clear benefit-led headings, specific outcomes and concise CTAs;
- CRO: reduce friction, expose the next useful action and make errors recoverable;
- onboarding: shortest path from account creation to first meaningful result;
- pricing: distinguish Free / Pro / Studio by real capabilities and value;
- launch: connect creation, release planning and promotion into one workflow;
- analytics: measure activation, tool usage, project creation, successful AI runs and return usage.

## Product management
Use the relevant PM patterns represented in phuryn/pm-skills:
- discovery before building large features;
- assumptions and risks before implementation;
- outcome-focused prioritization;
- PRD-like acceptance criteria for important flows;
- test happy paths, edge cases and failures;
- define metrics and a concrete next experiment.

## SØNA tool routing
Each AI tool has its own context and skill. Never send all tools through an undifferentiated generic prompt.
- Songwriter → songwriter / songwriting-and-ai-music
- Audio Analyzer → audio-analysis
- AI Mastering → mastering
- Trends → trends / trend-jacking
- Statistics → analytics / social-analytics
- Finances → finance
- Projects → projects / product-management context
- Release and SMM → release-marketing plus relevant marketing skill

The main assistant may coordinate results, but each tool owns its specialized task and output format.

## UX standard
The interface should feel like a premium SFEROOM-style AI workspace: translucent dark assistant panel, soft borders, animated depth, rounded controls, horizontal quick actions, smooth press states and a subtle multi-color light following the pointer on capable devices.

## Reliability standard
A button is not finished when it looks clickable. It is finished only when its complete path works in production: request → backend → result → persistence → visible success/error state.

## Source policy
This file is an SØNA adaptation based on publicly documented concepts from the following repositories. It is not a verbatim copy of their skill files.
- https://github.com/coreyhaines31/marketingskills
- https://github.com/phuryn/pm-skills
