# Troubleshooting

## Common issues

### `revideo_cli.run_revideo` fails with `WinError 2` on Windows

`npx`/`npm` are `.cmd` shims on Windows, not directly-executable binaries, and `subprocess.run(["npx", ...])` fails to find them — this bit the original Remotion path. `revideo/render.mjs` is invoked with plain `node` instead (a real `.exe`), so this shouldn't recur here, but if you add a new script that shells out to an `npx`/`npm`-installed binary, resolve the real path via `shutil.which()` first rather than adding `shell=True`.

### Revideo render hangs forever with no output

Revideo's default exporter (`@revideo/core/wasm`) runs an in-browser WebAssembly FFmpeg build that never completes in a headless-Chromium subprocess on this setup (no cross-origin-isolation headers for the multithreaded build) - it hangs indefinitely rather than erroring. Both `revideo/src/video-project.ts` and `poster-project.ts` force the server-side FFmpeg exporter (`@revideo/core/ffmpeg`) in their project settings; if a new project file is added without that override, it'll hit this.

### A Revideo scene's text renders blank

A `Txt` node's `text` prop bound to a reactive closure over a signal (`text={() => ...}`) silently fails on (most) captured frames server-side - `"The scene is not available in the current context"` gets logged but swallowed, the node just renders with no text, no thrown error. Drive text with imperative `tween()`/`.text(value, duration)` calls instead (see `revideo/src/scenes/caption-overlay.tsx` for the working pattern) - anything that mutates a node property from inside the running generator is fine, it's specifically a *computed/reactive* prop function that breaks.

### FFmpeg encode fails with an nvenc error

`h264_nvenc` needs a matching NVIDIA driver version (seen in practice: "Required: 13.1 Found: 13.0"). The default `VIDEO_ENCODER` is `libx264` (software, no driver dependency) precisely because of this — see `app/config/settings.py`. Set `VIDEO_ENCODER=h264_nvenc` only if your driver supports it and you want the speedup.

### Ollama model won't unload

- confirm the `keep_alive: 0` request actually reached `http://localhost:11434/api/generate` (check for network/timeout errors)
- remember `ollama serve` itself staying up is expected — only the model's residency should change

### Revideo render is slow to start or times out

- confirm `cd revideo && npm install` has actually been run — a missing `node_modules/` fails fast with a clear error, but a partial install can hang during bundling
- `REVIDEO_RENDER_TIMEOUT_SECONDS` (`app/config/settings.py`) bounds how long the orchestrator waits before raising

### Composition/poster validator keeps failing and falling through

- `composition_check`/`poster_check` in `state.json` records the actual validator problems — check those first
- the orchestrator retries the upstream agent (`composition_agent`/`poster_layout_agent`) up to `MAX_QUALITY_RETRIES` times, then renders with whatever it has rather than looping forever — if this happens often for the same kind of problem (e.g. CTA text running long), it's worth tightening the agent's prompt rather than raising the retry cap

## Related notes

- [[06 Operations/01 Commands]]
- [[06 Operations/03 Hardware Constraints]]
- [[03 Workflow/04 Memory & Process Protocol]]
