# Commands

This note should hold the practical terminal commands used in the project.

## FFmpeg examples

```bash
ffmpeg -i input.mp4 -vf "zoompan" output.mp4
ffmpeg -i video.mp4 -i audio.wav -c:v h264_nvenc -c:a aac output.mp4
```

## Playwright

```bash
npx playwright install
npx playwright test
```

## Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## First render pipeline

```bash
python -m pipeline.first_render --url https://example.com --base-dir artifacts/login_job
```

Prefer the `MPOSTELE_PASSWORD` environment variable over `--password` for login flows — it keeps the credential out of shell history and process listings (`ps`/`tasklist`). The frontend's "Run capture locally" button (see [frontend/README.md](../../frontend/README.md#running-the-capture-job-from-the-ui)) already does this automatically when it triggers this command on your behalf.

Additional capture flags:

```bash
# Scope the screenshot to one element and hide an extra banner selector
python -m pipeline.first_render --url https://example.com --capture-selector "#hero" --hide-selector ".promo-banner"

# Skip the content-based duration estimate and force a fixed clip length
python -m pipeline.first_render --url https://example.com --duration 5

# Tune the reading-speed heuristic used to estimate duration
python -m pipeline.first_render --url https://example.com --words-per-second 2.5 --min-duration 3 --max-duration 8
```

If `--username`/`--password` are supplied but no password field is found on the page, or a login is submitted but cannot be verified (URL unchanged, password field still visible, or an error message detected), the command fails fast with a clear error instead of producing a bad screenshot.

## Narration composition

FFmpeg and FFprobe must be available on `PATH`. Supply a local narration file and a base motion or overlay clip:

```bash
python -m pipeline.audio --video artifacts/first_scene/motion.mp4 --audio artifacts/first_scene/voiceover.wav --output artifacts/first_scene/final.mp4
```

The output duration defaults to the narration duration. A short visual holds its final frame; a long visual is trimmed. Use `--duration 5` to override the detected duration or `--no-normalize-audio` to skip the default one-pass loudness normalization.

To run this from the frontend, start Vite, open the **Audio** panel, enter repository-contained paths for the base video, narration, and output, then select **Create narrated video**. The local `/api/run-audio` endpoint rejects paths outside the project and reports FFmpeg output in the panel.

## Multi-scene render job

Create a JSON manifest and run it through the orchestrator:

```bash
python -m pipeline.render_job jobs/product-short.json
```

Example manifest:

```json
{
  "output": "../outputs/product-short.mp4",
  "work_dir": "../artifacts/product-short",
  "export": { "preset": "vertical_1080p", "fps": 30 },
  "scenes": [
    {
      "id": "intro",
      "url": "http://localhost:5173",
      "duration": 4,
      "motion_preset": "zoom_in",
      "capture": {
        "selector": "#app",
        "hide_selectors": [".debug-toolbar"]
      },
      "overlay": {
        "type": "title",
        "text": "Plan content locally",
        "hold_seconds": 2
      }
    },
    {
      "id": "feature",
      "image": "../assets/feature.png",
      "duration": 5,
      "motion_preset": "pan_left_to_right",
      "narration": "../assets/feature.wav"
    },
    {
      "id": "demo",
      "video": "../assets/demo.mp4"
    }
  ]
}
```

Every scene must define exactly one of `url`, `image`, or `video`. URL scenes support `capture.mode` (`screenshot` or `motion`), `username`, `target_path`, `selector`, `hide_selectors`, `hide_common_overlays`, `motion_trigger`, `trigger_selector`, and timing controls. Use `MPOSTELE_PASSWORD` for authenticated scenes; passwords are rejected in manifest files to avoid storing secrets in plaintext.

Available export presets are `landscape_720p` (1280x720), `vertical_1080p` (1080x1920), and `square_1080p` (1080x1080). Explicit `export.width` and `export.height` values override the preset. All paths are relative to the manifest directory unless absolute. Scene intermediates and `concat.txt` remain in `work_dir` for inspection. Existing files are overwritten by FFmpeg.

A scene `duration` controls screenshot/image motion length and live browser recording length. It also trims a supplied video when no narration is present. If narration is supplied, its probed duration controls that scene instead.

The same workflow is available in the frontend **Render** panel. Start Vite, add or reorder scenes, select source and processing options, and choose **Render complete video**. The loopback-only `/api/run-render-job` endpoint converts project-relative paths to validated repository-contained paths, saves `frontend-job.json` in the work folder, passes any password only through `MPOSTELE_PASSWORD`, and invokes `pipeline.render_job` without a shell. The browser persists render settings locally but never stores the password.

## Notes

Add commands here as they are validated in the real workflow.

## Related notes

- [[06 Operations/02 Troubleshooting]]
- [[06 Operations/03 Hardware Constraints]]
