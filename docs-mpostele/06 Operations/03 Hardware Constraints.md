# Hardware Constraints

## Target environment

- GTX 1050 Ti with 4GB VRAM
- 8GB system RAM
- local, offline workflow

## Implications

- avoid large AI video generation models
- prefer lightweight motion systems and compositing
- keep render jobs short and modular
- rely on CPU or modest GPU acceleration for standard tasks

## Measured baseline

A narrated 1080x1920, three-scene job completed on an i5-7300HQ, 7.9 GB RAM, and GTX 1050 Ti laptop in 46.518 seconds. Peak aggregate working memory for the render process tree was 661.96 MiB at a 100 ms sampling interval. The final 12.4025-second MP4 passed codec, audio, dimensions, nominal frame-rate, duration, and fast-start checks.

This result covers CPU-side process working sets for Playwright, FFmpeg, Manim, and the Python renderer. It excludes the separate Vite server, unrelated applications, OS caches, and VRAM. See [[06 Operations/04 Production Validation]] for the procedure and limitations.

## Design principle

This project is optimized for reliability on weak hardware rather than maximum AI complexity. The measured baseline supports the current lightweight architecture while leaving substantial headroom below the 8 GB RAM target.

## Related notes

- [[01 Project Overview]]
- [[04 Research/01 Low-Memory Animation Options]]
- [[06 Operations/02 Troubleshooting]]
- [[06 Operations/04 Production Validation]]



