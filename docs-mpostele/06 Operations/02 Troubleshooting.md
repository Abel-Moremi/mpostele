# Troubleshooting

## Common issues

### CUDA Out Of Memory during the video path

- reduce AnimateDiff frame count and/or resolution
- confirm the previous stage's subprocess actually exited before this one started (check for a lingering process holding a CUDA context)
- fall back to the remote Wan2.1 dispatch path instead of forcing the job local

### Ollama model won't unload

- confirm the `keep_alive: 0` request actually reached `http://localhost:11434/api/generate` (check for network/timeout errors)
- remember `ollama serve` itself staying up is expected — only the model's residency should change

### Remote dispatch failures (Wan2.1 via Colab/Modal/RunPod)

- check auth/session expiry on the remote runtime
- confirm the job doesn't silently retry against a dead session — surface the failure and fall back to the local AnimateDiff path
- log whether the failure was a timeout, an auth error, or a quota limit — they need different fixes

### Audio sync problems

- verify audio duration relative to the RIFE-interpolated frame count
- double-check frame rate consistency between the raw generation FPS and the interpolation target

### Poster text overflow

- check whether a single word/token exceeds `max_width_px` — the current word-wrap implementation doesn't shrink font size or truncate, see [[04 Research/04 Pillow Compositor Notes]]

## Related notes

- [[06 Operations/01 Commands]]
- [[06 Operations/03 Hardware Constraints]]
- [[03 Workflow/04 Memory & Process Protocol]]
