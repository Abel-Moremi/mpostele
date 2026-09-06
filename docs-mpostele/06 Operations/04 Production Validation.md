# Production Validation

## Baseline narrated render

A local production-style run was completed on the target hardware class:

- CPU: Intel Core i5-7300HQ at 2.50 GHz
- RAM: 7.9 GB
- GPU: NVIDIA GTX 1050 Ti with 4 GB VRAM, plus Intel HD Graphics 630
- job: three vertical frontend scenes with two Manim overlays
- narration: three supplied local WAV files, 3.91–4.35 seconds each
- output: 1080x1920 H.264/yuv420p at nominal 30 fps
- audio: AAC, 48 kHz, stereo
- final duration: 12.4025 seconds
- render wall time: 46.518 seconds
- peak render-process-tree working set: 661.96 MiB
- export validation: passed, including fast-start layout

The memory figure is the highest aggregate working set sampled every 100 ms for the render command and its descendants. It includes Playwright, FFmpeg, and Manim children launched by the renderer. It does not include the separately started Vite development server, unrelated desktop applications, operating-system caches, or GPU VRAM. Treat it as a repeatable pipeline metric rather than total machine memory use.

This run used lightweight Windows system speech only to create temporary supplied WAV fixtures because optional Kokoro dependencies and model assets were not installed. It therefore validates supplied-audio timing and composition, not Kokoro voice quality. The generated media and benchmark report remain local under ignored `artifacts/` and `outputs/` paths.

## Result interpretation

The run demonstrates that the capture, motion, overlay, supplied-narration, normalization, concat, and validation path operates well below the 8 GB system-memory target on the reference laptop. Narration durations controlled scene lengths correctly. The MP4 reports a nominal cadence of 30 fps and an average of 29.905 fps because narration-timed scenes can end between exact frame boundaries; the validator checks nominal encoded cadence and reports both values.

Visual and narration pacing still require a human review with production voice recordings. Social-platform acceptance also remains unverified until an operator uploads the output to the intended service.

## Repeatable measurement

Start the required local page, then wrap any render command with the standard-library benchmark tool:

```powershell Terminal
python -m pipeline.benchmark --report artifacts/render-benchmark.json -- python -m pipeline.render_job jobs/vertical-local-demo.json
```

The command prints and optionally saves elapsed seconds, peak process-tree resident memory, sample count, and child-command exit code. Memory samples remain interval-based, but command completion is detected promptly rather than adding a full final sampling interval to wall time. Process-tree memory is supported on Windows and Linux. Other operating systems still receive wall-time and exit-code measurements, with memory reported as null.

## Manual upload checklist

For each target platform:

1. Upload the technically validated MP4 without recompressing it first.
2. Record whether the platform accepts the file and whether processing completes.
3. Check first frame, final frame, audio sync, overlays, text readability, and orientation.
4. Play the result on both desktop and a phone when possible.
5. Record the platform, upload date, source file checksum, and any platform warning.
6. Do not mark platform compatibility complete until the published or previewed result passes.

## Related notes

- [[06 Operations/01 Commands]]
- [[06 Operations/03 Hardware Constraints]]
- [[05 Implementation/03 Setup Checklist]]
