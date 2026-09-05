# mpostele

mpostele is a lightweight, open-source pipeline for generating animated social-media product videos entirely on a local machine without relying on expensive GPU-heavy AI models.

This project is designed around a real hardware constraint: a GTX 1050 Ti with 4GB VRAM and 8GB system RAM. The goal is to stay practical, offline, and affordable by using programmatic animation and browser-based motion instead of heavy diffusion or video-generation models that require tens of GB of VRAM.

## Why this project exists

Heavy local AI video generators such as SVD or AnimateDiff often require 8GB to 12GB of VRAM or more just to render a few seconds of output. For a $0 workflow on a modest laptop, the better approach is to build motion using:

- browser automation and screenshot capture
- code-driven motion graphics
- lightweight FFmpeg filters
- local TTS and compositing

This keeps the stack within the limits of small hardware while still producing polished, animated product videos.

## Architecture overview

Animation fits directly into the media construction stage of a sequential pipeline. Instead of relying only on static screen recordings, the system transforms screenshots, UI captures, and overlays into dynamic motion before FFmpeg assembles the final output.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    SINGLE-CONTAINER WORKFLOW                            │
│                                                                         │
│  1. SCRIPT & VOICE  ──>  2. SCREENSHOT CAPTURE  ──>  3. ANIMATION ENGINE│
│   (Ollama + Kokoro)          (Playwright)             (Manim / Motion)  │
│                                                                         │
│  4. COMPOSITING & ENCODING  ──>  5. FINAL POSTING                     │
│      (FFmpeg + h264_nvenc + subtitles + voice sync)                    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Low-memory animation options

Depending on the style of motion needed, these are the best open-source options for a constrained system.

### 1. Code-driven 2D motion graphics: Manim or Motion Canvas

- How it works: programmatically creates motion graphics, text animations, UI highlights, overlays, and lower-thirds
- Why it fits: Manim and Motion Canvas typically run comfortably on CPU/GPU and use far less than 500MB of RAM in normal usage
- Best for: animated logos, text popups, feature callouts, chart motion, and simple UI emphasis

### 2. Animated web screenshots: Playwright CSS/JS animation

- How it works: injects CSS or JavaScript animations into a webpage before recording the motion
- Why it fits: uses Chromium rendering rather than heavy AI inference
- Best for: pulsing CTAs, smooth scrolling, zooming into product pages, transitions between sections, floating design motion

### 3. Image pan/zoom and Ken Burns effect: FFmpeg motion filters

- How it works: applies slow camera movement to a still image or screenshot
- Why it fits: can be hardware accelerated by the GTX 1050 Ti using NVENC and uses minimal system RAM
- Best for: transforming static screenshots into lively video backgrounds for Shorts or Reels

## Execution flow

When an animation job runs, the pipeline executes in a clear sequence:

1. Asset capture: Playwright captures high-resolution screenshots of the product UI or feature area.
2. Animation generation: Python calls Manim or another motion engine to generate an animated overlay such as a title card, arrow, badge, or lower-third.
3. Motion enhancement: FFmpeg applies a smooth zoom-and-pan or parallax effect to the screenshot when needed.
4. Voice sync and compositing: FFmpeg combines the animated UI video, overlay graphics, and Kokoro TTS voice track into a single polished output using h264_nvenc.

## Recommended directory structure

```text
ai-social-poster/
├── app/
│   ├── main.py
│   ├── agent/
│   ├── media/
│   │   ├── recorder.py      # Playwright screen recorder
│   │   ├── tts.py           # Kokoro-82M TTS
│   │   ├── animator.py      # Manim / FFmpeg motion engine
│   │   ├── composer.py      # FFmpeg final output assembly
│   │   └── assets/
│   │       ├── screenshots/
│   │       ├── overlays/
│   │       └── audio/
│   └── config/
│       └── settings.py
├── requirements.txt
├── README.md
├── LICENSE
└── docs/
```

## Why this approach works on a 1050 Ti + 8GB RAM system

By using code-driven motion graphics instead of heavy neural diffusion models, the project avoids the most common failure point: VRAM exhaustion. The stack is designed to stay lightweight, local, and fully offline while still producing modern, animated marketing content.

The result is a practical setup for generating product videos, feature showcases, and short-form social clips without needing a high-end workstation or cloud GPU rental.

## Project goals

- generate animated product videos locally
- keep the stack free and open source
- work within modest laptop hardware limits
- avoid GPU-heavy AI models where possible
- support offline content creation for marketing and product storytelling

## Future direction

The project can evolve by adding:

- a CLI for generating video jobs from a product brief
- a Playwright capture module for UI and landing page screenshots
- FFmpeg-based motion presets for different content styles
- Manim overlays for titles, highlights, and feature annotations
- automated output packaging for Shorts, Reels, and TikTok exports

## Summary

This repo is built around a realistic local-first AI video workflow: capture the product, animate it programmatically, sync voice, and composite the final output with FFmpeg. It favors efficiency, accessibility, and offline trust over heavy model inference.

That makes it a strong fit for developers and creators working with small hardware while still wanting polished, modern animated video output.

