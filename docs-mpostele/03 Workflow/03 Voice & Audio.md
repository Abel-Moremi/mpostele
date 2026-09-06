# Voice & Audio

This stage handles narration, pacing, and audio synchronization for the final generated video.

## Tools

- `pipeline/audio.py` for narration timing and local FFmpeg composition
- FFprobe for reading narration duration
- FFmpeg for audio cleanup and mixing
- `pipeline/tts.py` and optional Kokoro dependencies for local speech synthesis

- optional subtitle generation and timing alignment

## Goals

- generate voiceover offline
- keep output lightweight and local
- align the narration with video beats and feature highlights

## Current implementation

The audio stage accepts an existing local narration file and never requires a TTS runtime. Run:


```bash
python -m pipeline.audio --video artifacts/first_scene/motion.mp4 --audio artifacts/first_scene/voiceover.wav --output artifacts/first_scene/final.mp4
```

FFprobe determines the narration duration. FFmpeg then trims a longer visual or holds the final frame of a shorter visual, trims the audio to the same duration, applies one-pass `loudnorm`, and exports H.264 video with AAC audio. Use `--duration` to override detected duration or `--no-normalize-audio` to retain the source audio level.

This separation keeps manually recorded narration usable. When generated narration is wanted, install `requirements-tts.txt` and run `pipeline/tts.py`, or put a `script` and optional `tts` settings on a render-job scene. Kokoro is imported only during synthesis, so capture and render installations that do not use TTS remain unchanged.

Generated audio is a 24 kHz mono PCM WAV. An adjacent cache record identifies the script, voice, speed, and language; matching audio is reused on later runs. Kokoro may fetch model and voice assets the first time, so those assets must be prepared in advance for a fully offline production machine.

The frontend Audio panel exposes composition of an existing file without requiring a terminal. The Render panel additionally offers **Generate from script**, voice, speed, and language controls. Its loopback-only endpoint validates the manifest and runs the same local Python pipeline.


## Best practices

- keep voice scripts concise and structured
- generate audio first so the video can be timed around it; render jobs do this automatically for script scenes

- use clean silence and consistent pacing between sections
- normalize audio levels before final compositing

## Related notes

- [[02 Architecture]]
- [[03 Workflow/04 Compositing]]
- [[06 Operations/01 Commands]]
