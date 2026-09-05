# mpostele

This vault is the working knowledge base for a local-first, low-memory workflow for animated product marketing. It documents the target architecture and research direction for the project, while the repository currently also includes a front-end prototype and shared design tokens.

## Current status

The repo is in an early-to-mid stage:

- the research, constraints, and workflow notes are in place
- the project direction is clearly documented
- a Vite + Vue prototype exists for the planning UI
- the end-to-end production pipeline is still a planned implementation, not a shipped feature set

## Core idea

The project aims to create short-form product content using modest hardware such as a GTX 1050 Ti with 4GB VRAM and 8GB system RAM. The preferred approach is to avoid heavy diffusion-style video generation and instead rely on:

- Playwright for browser capture and UI automation
- lightweight animations via CSS, JS, or FFmpeg-based motion
- optional Manim overlays for titles and highlights
- local voice synthesis and final compositing in FFmpeg

## Workflow

1. [[01 Project Overview]]
2. [[02 Architecture]]
3. [[03 Workflow/01 Asset Capture]]
4. [[03 Workflow/02 Animation Engine]]
5. [[03 Workflow/03 Voice & Audio]]
6. [[03 Workflow/04 Compositing]]
7. [[03 Workflow/05 Final Export]]

## Research and decisions

- [[04 Research/01 Low-Memory Animation Options]]
- [[04 Research/02 Tool Comparison]]
- [[04 Research/03 FFmpeg Notes]]
- [[04 Research/04 Manim Notes]]
- [[04 Research/05 Playwright Notes]]

## Implementation

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/02 Milestones]]
- [[05 Implementation/03 Setup Checklist]]

## Operations

- [[06 Operations/01 Commands]]
- [[06 Operations/02 Troubleshooting]]
- [[06 Operations/03 Hardware Constraints]]

## Reference

- [[07 Reference/01 Links]]
- [[07 Reference/02 Notes Archive]]

## Repository context

This repository is best understood as a combination of design documentation and a prototype front-end, not yet as a full production pipeline. The long-term goal is still to turn these notes into a reusable, local-first generation workflow for marketing videos and short-form social content.
