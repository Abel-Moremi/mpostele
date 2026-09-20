# Troubleshooting

## Common issues

### `npx remotion render`/`still` fails with `WinError 2` on Windows

`npx`/`npm` are `.cmd` shims on Windows, not directly-executable binaries — `subprocess.run(["npx", ...])` fails to find them. `app/media/video_engine.py`/`poster_engine.py` resolve the real path via `shutil.which(settings.NODE_BINARY)` before invoking it; if you hit this outside those modules (e.g. a new script), apply the same fix rather than adding `shell=True`.

### FFmpeg encode fails with an nvenc error

`h264_nvenc` needs a matching NVIDIA driver version (seen in practice: "Required: 13.1 Found: 13.0"). The default `VIDEO_ENCODER` is `libx264` (software, no driver dependency) precisely because of this — see `app/config/settings.py`. Set `VIDEO_ENCODER=h264_nvenc` only if your driver supports it and you want the speedup.

### Ollama model won't unload

- confirm the `keep_alive: 0` request actually reached `http://localhost:11434/api/generate` (check for network/timeout errors)
- remember `ollama serve` itself staying up is expected — only the model's residency should change

### Remotion render hangs or times out

- confirm `cd remotion && npm install` has actually been run — a missing `node_modules/` fails fast with a clear error, but a partial install can hang during bundling
- `REMOTION_RENDER_TIMEOUT_SECONDS` (`app/config/settings.py`) bounds how long the orchestrator waits before raising

### Composition/poster validator keeps failing and falling through

- `composition_check`/`poster_check` in `state.json` records the actual validator problems — check those first
- the orchestrator retries the upstream agent (`composition_agent`/`poster_layout_agent`) up to `MAX_QUALITY_RETRIES` times, then renders with whatever it has rather than looping forever — if this happens often for the same kind of problem (e.g. CTA text running long), it's worth tightening the agent's prompt rather than raising the retry cap

## Related notes

- [[06 Operations/01 Commands]]
- [[06 Operations/03 Hardware Constraints]]
- [[03 Workflow/04 Memory & Process Protocol]]
