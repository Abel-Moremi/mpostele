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

## First local pipeline proof

The project now includes an initial capture-and-render script in [pipeline/first_render.py](pipeline/first_render.py). It intentionally stays small and local:

- open a target page with Playwright
- capture a screenshot into an asset folder
- render a short zoom-pan clip with FFmpeg
- save output as a reproducible local asset for later compositing

The capture flow also supports a simple login-driven session for authenticated pages. The same script can accept a platform URL, credentials, and a target path:

```bash
python -m pipeline.first_render \
  --url https://example.com/login \
  --username user@example.com \
  --password secret123 \
  --target-path /dashboard \
  --base-dir artifacts/login_job
```

The frontend also includes a basic capture form in [frontend/src/App.vue](frontend/src/App.vue) that accepts the platform URL, credentials, and target route before generating the command for the local automation job.

This is the first milestone in the architecture: proving the capture -> motion -> export path works without a heavy model stack.

## Motion overlays

[pipeline/overlays.py](pipeline/overlays.py) adds a Manim-based overlay layer on top of the base motion clip:

```bash
python -m pipeline.overlays \
  --base-video artifacts/first_scene/motion.mp4 \
  --overlay-type title \
  --text "New feature"
```

`--overlay-type` is `title` (a fading title card) or `callout` (a highlight box with a label, positioned with `--callout-x`/`--callout-y`). The overlay is rendered transparent and composited over the base clip with FFmpeg. Install Manim and Playwright with `pip install -r requirements.txt` (FFmpeg itself is a separate system dependency).

## Browser-based motion sequences

By default `pipeline/first_render.py` takes a single screenshot and animates it afterwards with an FFmpeg `zoompan` preset. `--capture-mode motion` instead records a short clip of a genuine in-page CSS/JS interaction using Playwright's built-in video recorder:

```bash
python -m pipeline.first_render \
  --url http://localhost:5173 \
  --base-dir artifacts/motion_job \
  --capture-mode motion \
  --motion-trigger hover \
  --trigger-selector "button:has-text('Get started')" \
  --record-seconds 3
```

`--motion-trigger` is `hover`, `click`, `scroll`, or `none`. The recorded `.webm` is transcoded to `motion.mp4` with FFmpeg, so it works as a drop-in replacement for the screenshot-based `motion.mp4` (e.g. as input to `pipeline.overlays`).

## Related docs

- [docs-mpostele/00 Home.md](docs-mpostele/00%20Home.md)
- [docs-mpostele/01 Project Overview.md](docs-mpostele/01%20Project%20Overview.md)
- [docs-mpostele/02 Architecture.md](docs-mpostele/02%20Architecture.md)
- [frontend/README.md](frontend/README.md)

