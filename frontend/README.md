# Mpostele frontend

This folder contains the local Vite + Vue control surface for running capture, narration-compositing, and complete multi-scene render jobs.

## What this prototype includes

- a local capture command builder and runner
- a narration-compositing form for combining a generated clip with local audio
- a multi-scene editor with URL, image, and video sources; ordering; motion; overlays; narration; and export presets
- validation and status logs for capture, audio, and full render jobs
- a theme toggle and responsive dark/light design system
- password masking and non-persistence for capture credentials
- a theme-aware favicon that follows the OS color scheme by default and switches instantly when the in-app theme toggle is used

## Data persistence

Settings (theme choice, capture fields, audio/video paths, render scenes, and export choices) persist locally across reloads using [sql.js](https://github.com/sql-js/sql.js) — SQLite compiled to WebAssembly, running entirely client-side. The exported database file is stored as raw bytes in the browser's IndexedDB, so no server or cloud service is involved and the app stays fully offline.

Password fields are intentionally **never persisted**: they are excluded from stored JSON and start empty on every reload. This avoids writing plaintext credentials to disk-backed browser storage.

See [src/db/sqlite.js](src/db/sqlite.js) for the persistence module (a small `settings(key, value)` table) and the `onMounted`/`watch` wiring in [src/App.vue](src/App.vue) for how fields are loaded and saved.

## Running the capture job from the UI

The "Run capture locally" button in the Capture setup panel executes the generated `python -m pipeline.first_render` command directly on your machine — you don't have to copy/paste it into a terminal yourself. It calls a `/api/run-capture` endpoint added to the Vite dev/preview server by [server/capture-run-plugin.js](server/capture-run-plugin.js), which spawns the pipeline's Python interpreter (preferring the repo's `.venv` if present) and streams back the exit code, stdout, and stderr for display under the button.

This stays local-first and safe by design:

- **Loopback only** — the endpoint rejects any request that isn't from `127.0.0.1`/`::1`, so it's unreachable even if the dev server is started with `--host`.
- **No shell** — the interpreter is spawned with an argument array, never a shell string, so input can't break out into arbitrary shell commands.
- **Password via environment variable** — the password is passed to the child process as `MPOSTELE_PASSWORD`, never as a CLI flag, so it doesn't appear in process listings (`ps`/`tasklist`) or in the logged output. [pipeline/first_render.py](../pipeline/first_render.py) reads this env var as a fallback when `--password` isn't supplied.
- **Output directory containment** — the requested output folder is resolved and rejected if it would land outside the repository root, blocking path traversal.

This is a convenience trigger for the same command you could already run by hand — it doesn't add any new capability beyond what the pipeline script already does.

## Running narration composition from the UI

The Audio panel calls `/api/run-audio`, which runs `python -m pipeline.audio` with the selected base video, narration file, output file, and normalization setting. Paths are project-relative by default. All three paths are resolved by the server and rejected if they leave the repository; the two input files must already exist.

A typical workflow is:

1. Run Capture to create `artifacts/login_job/motion.mp4`.
2. Place a narration file at `artifacts/login_job/voiceover.wav`.
3. Open Audio and click **Create narrated video**.
4. Find the result at `artifacts/login_job/final.mp4`.

The endpoint is loopback-only, invokes Python without a shell, limits request and log sizes, and terminates jobs that exceed three minutes.

## Running a multi-scene render from the UI

The **Render** panel builds the JSON accepted by `pipeline.render_job`. Add and reorder scenes, select a URL/image/video source, configure motion and browser capture, add optional title/callout overlays and narration, then choose a vertical, landscape, or square export preset.

Selecting **Render complete video** calls the loopback-only `/api/run-render-job` endpoint from [server/render-job-run-plugin.js](server/render-job-run-plugin.js). The server validates that local media, narration, output, and work paths remain inside the repository, writes `frontend-job.json` into the selected work folder, and starts Python without a shell. A login password is sent only in `MPOSTELE_PASSWORD`, is not included in the manifest, and is not persisted by the browser. Jobs time out after 15 minutes; intermediate scene files and the generated manifest remain available for inspection.

## Why it exists

This UI provides a practical local control surface over the lightweight capture, motion, compositing, and multi-scene export pipeline without adding a cloud service or a heavy desktop runtime.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

## Verify the frontend

```bash
cd frontend
npm test
npm run build
```

The Node tests cover repository path containment and local-source validation for the render-job endpoint.

## Current status

This frontend is a working local control surface for single-clip capture, narration composition, and multi-scene assembly with platform-oriented export presets. Local TTS and real-world platform upload validation remain future work.
