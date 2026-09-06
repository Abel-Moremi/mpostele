# Voice & Audio

This stage handles narration, pacing, and audio synchronization for the final generated video.

## Tools

- `pipeline/audio.py` for narration timing and local FFmpeg composition
- FFprobe for reading narration duration
- FFmpeg for audio cleanup and mixing
- Kokoro TTS for future local speech synthesis
- optional subtitle generation and timing alignment

## Goals

- generate voiceover offline
- keep output lightweight and local
- align the narration with video beats and feature highlights

## Current implementation

The audio stage accepts an existing local narration file rather than requiring a TTS runtime. Run:

```bash
python -m pipeline.audio --video artifacts/first_scene/motion.mp4 --audio artifacts/first_scene/voiceover.wav --output artifacts/first_scene/final.mp4
```

FFprobe determines the narration duration. FFmpeg then trims a longer visual or holds the final frame of a shorter visual, trims the audio to the same duration, applies one-pass `loudnorm`, and exports H.264 video with AAC audio. Use `--duration` to override detected duration or `--no-normalize-audio` to retain the source audio level.

This separation keeps manually recorded narration usable and allows Kokoro or another local TTS engine to be added later as an optional producer of `voiceover.wav`.

The frontend Audio panel exposes this operation without requiring a terminal. It stores only project-relative media-path preferences locally, submits them to the loopback-only `/api/run-audio` endpoint, and displays the Python/FFmpeg result. The server rejects paths outside the repository and requires both input files to exist.

## Best practices

- keep voice scripts concise and structured
- generate audio first so the video can be timed around it
- use clean silence and consistent pacing between sections
- normalize audio levels before final compositing

## Related notes

- [[02 Architecture]]
- [[03 Workflow/04 Compositing]]
- [[06 Operations/01 Commands]]
