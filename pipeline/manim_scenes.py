"""Manim scene definitions for the mpostele overlay layer.

These are intentionally minimal and code-driven (no LaTeX/MathTex, which
would pull in a full TeX distribution): plain `Text` for titles and labels,
and a `Rectangle` for callout highlight boxes. Each scene is rendered as a
short, transparent-background clip by `pipeline.overlays.render_overlay`
and composited over a base motion clip with FFmpeg, keeping the rendering
stack CPU-only and modest on memory (Manim's Cairo renderer, not a GPU
video model).

Scene parameters are passed in via environment variables rather than
constructor arguments because Manim's CLI (`manim render <file> <Scene>`)
instantiates the scene class itself; this mirrors how `MPOSTELE_PASSWORD`
is already passed to the capture flow via the environment instead of a
CLI flag.
"""

from __future__ import annotations

import os

from manim import (
    Create,
    FadeIn,
    FadeOut,
    Rectangle,
    Scene,
    Text,
    UP,
    YELLOW,
)


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class TitleOverlayScene(Scene):
    """A short title card: fades in, holds, fades out."""

    def construct(self) -> None:
        text = _env_str("MPOSTELE_OVERLAY_TEXT", "Title")
        hold_seconds = _env_float("MPOSTELE_OVERLAY_HOLD", 2.0)

        title = Text(text)
        self.play(FadeIn(title, shift=UP * 0.3), run_time=0.5)
        self.wait(hold_seconds)
        self.play(FadeOut(title), run_time=0.5)


class CalloutOverlayScene(Scene):
    """A highlight box with a label, positioned over a screen region."""

    def construct(self) -> None:
        text = _env_str("MPOSTELE_OVERLAY_TEXT", "Callout")
        hold_seconds = _env_float("MPOSTELE_OVERLAY_HOLD", 2.0)
        x = _env_float("MPOSTELE_OVERLAY_X", 0.0)
        y = _env_float("MPOSTELE_OVERLAY_Y", 0.0)
        box_width = _env_float("MPOSTELE_OVERLAY_WIDTH", 3.0)
        box_height = _env_float("MPOSTELE_OVERLAY_HEIGHT", 1.0)

        box = Rectangle(width=box_width, height=box_height, color=YELLOW)
        box.move_to([x, y, 0])
        label = Text(text).next_to(box, UP)

        self.play(Create(box), FadeIn(label), run_time=0.5)
        self.wait(hold_seconds)
        self.play(FadeOut(box), FadeOut(label), run_time=0.5)
