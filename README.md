# mpostele

mpostele is a local-first concept for creating animated product and social content on modest hardware. The repository currently contains two layers of work:

- a design and planning knowledge base under [docs-mpostele](docs-mpostele)
- a browser-based prototype UI in [frontend](frontend)

This is not yet a complete end-to-end video-generation product. The automation pipeline described in the research notes is the target architecture, but the implementation is still in progress.

## Current repo state

### What exists now

- research notes and architecture docs for a low-memory animation workflow
- a Vue + Vite frontend mockup for a content planner / campaign dashboard

### What is still planned

- Playwright-based capture workflow for product screens or landing pages
- FFmpeg motion presets and compositing pipeline
- Manim or browser-based motion overlays for callouts and titles
- local voiceover generation and export automation
- a working CLI or Python orchestration layer for end-to-end video jobs

## Design intent

The project is intentionally optimized for offline, low-memory workflows rather than heavy cloud or GPU-intensive generative stacks. The core approach remains:

- capture product UI states or screenshots
- generate motion with lightweight tools
- animate with browser, CSS, FFmpeg, or minimal overlays
- composite final output locally

## Repository structure

```text
mpostele/
├── AGENTS.md
├── README.md
├── LICENSE
├── docs-mpostele/
│   ├── 00 Home.md
│   ├── 01 Project Overview.md
│   ├── 02 Architecture.md
│   ├── 03 Workflow/
│   ├── 04 Research/
│   ├── 05 Implementation/
│   ├── 06 Operations/
│   └── 07 Reference/
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   └── README.md
└── .gitignore
```

## Frontend prototype

The frontend app is a Vite + Vue dashboard concept that demonstrates a content-planning and publishing workflow. It is useful as a design and UX reference for the broader product direction, but it is not the final automated video pipeline.

To run the frontend locally:

```bash
cd frontend
npm install
npm run dev
```

To verify the app builds cleanly:

```bash
cd frontend
npm run build
```

## Project direction

The long-term goal remains a local-first animation pipeline for product storytelling and short-form content, aiming to work on modest hardware such as a GTX 1050 Ti + 8GB RAM system without depending on heavy video diffusion models.

The current repo is the foundation for that goal: architecture notes, research, and a working prototype UI are in place and should be expanded into the actual capture, animation, and export pipeline next.

## Related docs

- [docs-mpostele/00 Home.md](docs-mpostele/00%20Home.md)
- [docs-mpostele/01 Project Overview.md](docs-mpostele/01%20Project%20Overview.md)
- [docs-mpostele/02 Architecture.md](docs-mpostele/02%20Architecture.md)
- [frontend/README.md](frontend/README.md)

