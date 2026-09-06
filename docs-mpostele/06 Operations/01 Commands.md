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

## Local text to speech

Kokoro is optional and is not installed by the base requirements. Install it only on machines that need script-based voice generation:

```bash
pip install -r requirements-tts.txt
python -m pipeline.tts --text "Plan and publish from one place." --output artifacts/voiceover.wav
```

For longer text, use a UTF-8 file:

```bash
python -m pipeline.tts --text-file scripts/intro.txt --voice af_heart --speed 1.0 --lang-code a --output artifacts/intro.wav
```

The default settings are voice `af_heart`, speed `1.0`, and Kokoro language code `a` (American English). `--force` bypasses the cache. Otherwise, an existing WAV is reused when its adjacent `.tts-cache.json` key matches the text, voice, speed, and language. Kokoro may download model and voice assets on first use; prepare that cache while online before expecting fully offline synthesis.

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

      "script": "Show every campaign in one focused workspace.",
      "tts": {
        "voice": "af_heart",
        "speed": 1.0,
                "lang_code": "a"
      }
    },
    {
      "id": "demo",
      "video": "../assets/demo.mp4"
    }
  ]
}
```

Every scene must define exactly one of `url`, `image`, or `video`. URL scenes support `capture.mode` (`screenshot` or `motion`), `username`, `target_path`, `selector`, `hide_selectors`, `hide_common_overlays`, `motion_trigger`, `trigger_selector`, and timing controls. Use `MPOSTELE_PASSWORD` for authenticated scenes; passwords are rejected in manifest files to avoid storing secrets in plaintext.

A scene may define either `narration` for an existing audio file or `script` for generated speech, but not both. Script scenes accept optional `tts.voice`, `tts.speed`, and `tts.lang_code` settings. Their generated WAV and cache record remain in that scene's work folder, so an unchanged rerender skips speech inference.

Available export presets are `landscape_720p` (1280x720), `vertical_1080p` (1080x1920), and `square_1080p` (1080x1080). Explicit `export.width` and `export.height` values override the preset. All paths are relative to the manifest directory unless absolute. Scene intermediates and `concat.txt` remain in `work_dir` for inspection. Existing files are overwritten by FFmpeg.

A scene `duration` controls screenshot/image motion length and live browser recording length. It also trims a supplied video when no narration is present. If supplied or generated narration is present, its probed duration controls that scene instead.

The same workflow is available in the frontend **Render** panel. Start Vite, add or reorder scenes, choose no narration, a local audio file, or a generated script, select the remaining processing options, and choose **Render complete video**. The loopback-only `/api/run-render-job` endpoint converts project-relative paths to validated repository-contained paths, saves `frontend-job.json` in the work folder, passes any password only through `MPOSTELE_PASSWORD`, and invokes `pipeline.render_job` without a shell. The browser persists render settings locally but never stores the password.

## Notes

Add commands here as they are validated in the real workflow.

## Related notes

- [[06 Operations/02 Troubleshooting]]
- [[06 Operations/03 Hardware Constraints]]
