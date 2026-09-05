# Low-Memory Animation Options

This note captures the practical choices for making motion graphics without exhausting the laptop's VRAM or RAM budget.

## Recommended options

### 1. Manim

- good for scripted motion graphics
- lightweight compared with heavy AI video generation
- useful for lower-thirds, annotations, overlays, diagrams, and emphasis

### 2. Motion Canvas

- browser-focused animation workflow
- useful for web-based motion and product UI emphasis
- less resource heavy than GPU-driven diffusion pipelines

### 3. Playwright CSS/JS animation

- ideal for animating webpage elements before capture
- does not require expensive video models
- excellent for smooth product highlights and transitions

### 4. FFmpeg Ken Burns effect

- fastest way to add motion to still screenshots
- ideal for simple zoom and pan motion
- works well with NVENC acceleration

## Why these are preferred

They keep the system practical for a laptop with a GTX 1050 Ti and limited memory, while still producing polished content.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/02 Animation Engine]]
- [[04 Research/02 Tool Comparison]]
