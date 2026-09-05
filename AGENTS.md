# AGENTS.md

## Mission

This repository is a local-first, open-source pipeline for creating animated product videos and short-form social content using modest hardware. The core principle is to optimize for low-memory, offline execution rather than high-end GPU-heavy AI generation.

The agent working in this repo should favor practical, lightweight tooling over expensive or resource-intensive approaches.

## Project intent

- Build animated marketing videos on a GTX 1050 Ti / 4GB VRAM system
- Stay compatible with small laptops and limited RAM
- Prefer browser-based motion, code-driven animation, and FFmpeg compositing
- Avoid unnecessary cloud services, large model downloads, and GPU-heavy workflows
- Keep the workflow reproducible and understandable for a solo developer

## Non-negotiable constraints

- Offline-first by default
- No dependency on large video diffusion models when a lighter approach works
- No expensive cloud GPU assumptions for normal development
- Keep runtime and memory use modest
- Favor maintainable code and clear docs over flashy complexity

## Preferred technical direction

Use these ideas as the default solution pattern unless the task clearly requires otherwise:

1. Capture screenshots or UI states with Playwright
2. Create motion with CSS, JS, FFmpeg filters, or Manim
3. Use browser rendering for UI animation where possible
4. Composite overlays, subtitles, and voice with FFmpeg
5. Keep asset generation and export deterministic and local

## Architecture guidance

The repository is organized around a simple production flow:

- capture product UI or screens
- animate overlays and motion elements
- add timing, captions, or voice
- composite into final output
- export for Shorts, Reels, TikTok, or product showcase use

The agent should assume the project is a lightweight pipeline, not a monolithic app with large ML dependencies.

## Code and implementation preferences

- Prefer small, clear modules over broad abstractions
- Keep configuration explicit and local
- Favor deterministic workflows with visible intermediate assets
- Keep assets and generated media in structured folders
- Write code that is easy to reason about on underpowered hardware
- When adding a feature, consider whether it will still work on a modest laptop

## Project-specific guardrails

- Do not introduce heavy model inference as a default path
- Do not assume CUDA, huge VRAM, or cloud compute availability
- Do not hide complexity behind vague abstractions
- Do not add large dependencies without a clear need
- Do not optimize for fancy demos at the cost of practicality

## Recommended repo patterns

- Use documentation files under docs-mpostele for design decisions and architecture notes
- Keep root-level files focused and readable
- Treat README.md as the high-level overview for humans
- Treat docs-mpostele as the operational and design record
- When building features, preserve the low-memory narrative of the project

## When making changes

Before implementing a feature or fix, the agent should check whether it supports the repository goals:

- Is it compatible with local, offline use?
- Does it fit the modest hardware target?
- Is there a lighter alternative than a heavy model or large runtime?
- Does it keep the project easy to debug and explain?
- Does it match the motion-first, compositing-first design?

If a proposed change fails those checks, the agent should suggest a simpler or more efficient alternative.

### Mandatory documentation update rule

After every implementation, the agent must update the relevant documentation in the same change set. This includes any affected files in README.md, docs-mpostele, and any operational notes that describe architecture, workflow, setup, or usage.

The documentation update is not optional and is considered part of the implementation itself. If a change modifies behavior, configuration, assumptions, commands, or workflows, the docs must reflect that change before the work is considered complete.

## Communication style for future agents

- Be concise and practical
- Explain tradeoffs plainly
- Prefer evidence-based recommendations
- Keep implementation aligned with the repo’s purpose
- Suggest the simplest viable path first

## Suggested next directions

Good directions for this repo include:

- browser recording and screenshot capture flows
- CSS/JS animation presets for product landing pages
- FFmpeg-based pan/zoom and motion overlays
- Manim or similar lightweight motion tools for product highlights
- local voiceover and subtitle timing workflows
- CLI or script-based generation pipeline for short-form assets

Less suitable directions include:

- heavy diffusion video generation as the main path
- large cloud-based model pipelines
- GPU-heavy generative stacks that require high-end hardware
- abstractions that complicate a simple local workflow

## Final rule

This repo is best understood as a pragmatic, local-first animation pipeline for content creation under hardware limits. The agent should always choose the path that preserves that spirit: efficient, understandable, and functional on modest machines.

The agent must treat documentation as part of the implementation. No change is complete until the relevant documentation has been reviewed and updated to match the new state of the project.
