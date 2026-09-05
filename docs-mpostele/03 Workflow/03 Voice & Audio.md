# Voice & Audio

This stage handles narration, pacing, and audio synchronization for the final generated video.

## Tools

- Kokoro TTS for local speech synthesis
- FFmpeg for audio cleanup and mixing
- optional subtitle generation and timing alignment

## Goals

- generate voiceover offline
- keep output lightweight and local
- align the narration with video beats and feature highlights

## Best practices

- keep voice scripts concise and structured
- generate audio first so the video can be timed around it
- use clean silence and consistent pacing between sections
- normalize audio levels before final compositing

## Related notes

- [[02 Architecture]]
- [[03 Workflow/04 Compositing]]
- [[06 Operations/01 Commands]]
