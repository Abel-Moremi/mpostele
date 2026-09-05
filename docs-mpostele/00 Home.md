# mpostele

This vault is the knowledge base for a local-first, low-memory workflow for generating animated product videos without expensive cloud GPU services.

## Core idea

The project focuses on automated video generation for short-form product marketing using only modest hardware such as a GTX 1050 Ti with 4GB VRAM and 8GB system RAM.

Instead of relying on heavy diffusion or AI video models, the system uses:

- Playwright for screenshot capture
- lightweight animation tooling such as Manim or FFmpeg motion filters
- local voice synthesis with Kokoro
- FFmpeg for compositing and final delivery

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

## Why this project exists

The main design constraint is to avoid memory-heavy AI tooling that cannot run comfortably on older laptop hardware. The goal is to produce polished automated product content using accessible, open-source tools that work on local machines.
