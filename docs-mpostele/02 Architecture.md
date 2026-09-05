# Architecture

## High-level pipeline

```text
Script & Voice
    ↓
Screenshot Capture
    ↓
Animation Engine
    ↓
Compositing & Encoding
    ↓
Final Posting / Export
```

## Components

### 1. Script and narrative generation

This stage defines the story, tone, and pacing. It may use a local model or a structured prompt pipeline to generate the talking points and scene plan.

### 2. Screenshot capture

Playwright can record product screens, landing pages, or feature interactions. These frames become the base visual elements for the final video.

### 3. Animation engine

This is where motion is created using low-memory tools:

- static screenshots with FFmpeg pan/zoom
- CSS or JS animation in a browser
- Manim overlays for text and feature highlights

### 4. Voice & audio

A local TTS model such as Kokoro can produce narration that matches the script and clip timing.

### 5. Compositing and encoding

FFmpeg merges the generated visuals, voiceover, and overlays into a final video using a practical encoder profile such as `h264_nvenc` when available.

## Practical fit

This architecture matches the hardware constraints because it avoids heavy neural video generation models and relies on efficient rendering, compositing, and browser-driven motion.

## Related notes

- [[03 Workflow/01 Asset Capture]]
- [[03 Workflow/02 Animation Engine]]
- [[03 Workflow/03 Voice & Audio]]
- [[03 Workflow/04 Compositing]]
- [[03 Workflow/05 Final Export]]
