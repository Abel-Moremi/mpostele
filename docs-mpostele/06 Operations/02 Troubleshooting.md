# Troubleshooting

## Common issues

### Audio sync problems

- verify audio duration relative to video timeline
- trim voiceover to match the final sequence length
- double-check frame rate consistency

### Video quality issues

- ensure output resolution matches intended export dimensions
- test NVENC acceleration support before relying on it
- simplify animations if the system is under load

### Resource limits

- reduce animation complexity
- generate shorter scenes
- prefer FFmpeg or pre-rendered overlays over heavy live generation

## Related notes

- [[06 Operations/01 Commands]]
- [[06 Operations/03 Hardware Constraints]]
