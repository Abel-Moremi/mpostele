# mpostele

mpostele is a local-first toolkit for creating animated product and social content on modest hardware. The repository contains:

- a design and planning knowledge base under [docs-mpostele](docs-mpostele)
- a browser-based prototype UI in [frontend](frontend)
- a Python media pipeline under [pipeline](pipeline)

The pipeline and frontend can produce multi-scene videos with supplied or locally generated narration; real-platform export validation is still in progress.


## Current repo state

### What exists now

- research notes and architecture docs for a low-memory animation workflow
- a Vue + Vite frontend mockup for a content planner / campaign dashboard
- local Playwright capture, FFmpeg motion, Manim overlays, narration compositing, and optional Kokoro TTS modules
- a JSON-driven multi-scene renderer with landscape, vertical, and square export presets


### What is still planned

- voice-pacing validation with representative scripts
- end-to-end testing against representative social-platform uploads

- additional production presets and reusable render-job templates

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

The frontend app is a Vite + Vue local control surface for capture, narration-compositing, and multi-scene render jobs. Its loopback-only endpoints run the Python pipeline locally and display process logs without introducing a cloud service.

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

The current repository provides that foundation plus a working capture, animation, optional local narration generation, narration-compositing, and multi-scene export pipeline. The next work is production and platform validation.


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
  --target-path /dashboard \
  --base-dir artifacts/login_job
```

Set `MPOSTELE_PASSWORD` in the environment before authenticated command-line captures so the password is not written into shell history. The frontend also includes a basic capture form in [frontend/src/App.vue](frontend/src/App.vue) that accepts the platform URL, credentials, and target route before generating the command for the local automation job.

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

## Narration compositing

[pipeline/audio.py](pipeline/audio.py) accepts any local narration file, detects its duration with FFprobe, and creates a narrated MP4 with FFmpeg:

```bash
python -m pipeline.audio \
  --video artifacts/first_scene/motion.mp4 \
  --audio artifacts/first_scene/voiceover.wav \
  --output artifacts/first_scene/final.mp4
```

The visual is trimmed or its final frame is held to match the narration. Audio receives lightweight one-pass loudness normalization by default; pass `--no-normalize-audio` to preserve the source level. This stage continues to accept existing recordings, so TTS never becomes mandatory.


The same operation is available in the frontend's **Audio** panel. Its local `/api/run-audio` endpoint validates that all media paths stay inside the repository before invoking the Python module without a shell.

## Optional local text to speech

[pipeline/tts.py](pipeline/tts.py) generates narration WAV files with Kokoro. Its dependencies stay separate so the normal capture/render installation remains lightweight:

```bash
pip install -r requirements-tts.txt
python -m pipeline.tts --text "Plan and publish from one place." --output artifacts/voiceover.wav
```

The first Kokoro use may need network access to populate its local model/voice cache; synthesis is local after those assets are cached. Generated scene narration is keyed by script, voice, speed, and language settings and reused on unchanged rerenders.

## Multi-scene render jobs


[pipeline/render_job.py](pipeline/render_job.py) turns the individual stages into one manifest-driven workflow. Each scene uses exactly one source: a URL, an image, or a video. It can then add an optional title/callout and either a local narration file or a TTS `script` before all scenes are normalized and concatenated.


Run a job with:

```bash
python -m pipeline.render_job path/to/job.json
```

The manifest supports `landscape_720p`, `vertical_1080p`, and `square_1080p` export presets. Paths are resolved relative to the manifest file. Intermediate captures and encoded scenes stay in `work_dir` so a failed render can be inspected without opaque cache state. Login passwords are deliberately excluded from manifests; set `MPOSTELE_PASSWORD` in the environment when an authenticated URL scene needs one. The frontend **Render** panel can create and execute the same job visually.

See [the commands note](docs-mpostele/06%20Operations/01%20Commands.md#multi-scene-render-job) for a complete manifest example.

## Related docs

- [docs-mpostele/00 Home.md](docs-mpostele/00%20Home.md)
- [docs-mpostele/01 Project Overview.md](docs-mpostele/01%20Project%20Overview.md)
- [docs-mpostele/02 Architecture.md](docs-mpostele/02%20Architecture.md)
- [frontend/README.md](frontend/README.md)

