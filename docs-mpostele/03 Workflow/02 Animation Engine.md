# Animation Engine

This is the core motion-generation stage. It converts static assets into animated video segments without relying on heavy AI video models.

## Core strategies

### 1. FFmpeg motion filters

Use zoom, pan, and parallax effects to add motion to a still image or screenshot. `pipeline/first_render.py` implements this as a set of selectable `zoompan` motion presets (`--motion-preset`, default `zoom_in`):

- `zoom_in` / `zoom_out` -- slow push in or ease back out
- `pan_left_to_right` / `pan_right_to_left` -- fixed mild zoom, camera slides horizontally
- `pan_top_to_bottom` / `pan_bottom_to_top` -- fixed mild zoom, camera slides vertically
- `static` -- no motion, for dense/text-heavy scenes where camera movement hurts readability

### 2. Playwright animation

Inject CSS, JS, or transitions into a page to create smooth UI motion before capture.

### 3. Manim overlays

Create high-quality animated text, circles, arrows, charts, and product visual accents on transparent or solid backgrounds. Implemented in `pipeline/overlays.py` (`--overlay-type title|callout`), rendered transparent and composited over the FFmpeg motion clip with the `overlay` filter.

## Why this is important

This is the main way to stay within the hardware limits of the project while still producing modern motion graphics.

## Preferred approach

For a low-memory setup, start with:

- FFmpeg for camera movement
- Manim for overlays and callouts
- Playwright for browser-based motion effects

## Related notes

- [[03 Workflow/01 Asset Capture]]
- [[03 Workflow/04 Compositing]]
- [[04 Research/01 Low-Memory Animation Options]]
- [[04 Research/04 Manim Notes]]
- [[04 Research/05 Playwright Notes]]
