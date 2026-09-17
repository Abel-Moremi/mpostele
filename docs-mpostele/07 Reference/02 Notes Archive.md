# Notes Archive

This is the archive for lower-priority or exploratory notes that are not yet part of the active workflow.

Use it for:

- experiments
- prototype ideas
- iterative notes that may later become formal decisions
- old ideas retained for future reference

## Superseded architecture (retired)

The project's original design used Playwright screenshot capture, Manim overlays, and FFmpeg Ken Burns motion instead of diffusion models, on the reasoning that AnimateDiff/SVD-class models needed too much VRAM for this hardware. That design was retired in favor of the current Sequential Execution Contract architecture (LLM agent swarm + SD1.5 poster/video generation + remote Wan2.1 dispatch), which keeps diffusion models in scope by making every stage transient and explicitly memory-unloaded rather than excluding them outright. Full detail on the prior approach is preserved in git history rather than duplicated here.

## Related notes

- [[07 Reference/01 Links]]
