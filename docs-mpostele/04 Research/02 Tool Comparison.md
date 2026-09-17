# Tool Comparison

## Comparison table

| Tool | Best use | Memory profile | Fit for this project |
| --- | --- | --- | --- |
| Qwen2.5-1.5B (Ollama) | strategy/script/prompt/layout agents | low, and fully unloadable between phases | excellent |
| SD1.5 / LCM | poster background, AnimateDiff base | ~2.5GB VRAM | excellent (poster path) |
| AnimateDiff | local video fallback | high relative to card size | tight — needs validation |
| Wan2.1 (remote) | primary video path | zero local VRAM cost, network + privacy tradeoff | good, with disclosure |
| Pillow | poster text/badge compositing | negligible | excellent |
| RIFE | frame interpolation | moderate, short-lived | good |
| FFmpeg | audio mux, final encode | very low | excellent |
| SDXL | — | exceeds local VRAM budget | prohibited |

## Recommendation

Keep the LLM and poster paths fully local and transient. Treat AnimateDiff as an unvalidated fallback until measured on the actual card, and default heavier video jobs to the remote Wan2.1 path with the privacy tradeoff disclosed to the user.

## Related notes

- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/03 FFmpeg Notes]]
- [[04 Research/05 Ollama Agent Notes]]
