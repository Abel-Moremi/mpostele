"""Manim-based overlay rendering and FFmpeg compositing.

This module builds the CLI commands for rendering short, transparent-
background Manim clips (titles, callouts) and for compositing one of those
clips over a base motion video with FFmpeg. Command-building is kept as
pure functions (mirroring `pipeline.first_render.build_ffmpeg_command`) so
they can be unit tested without Manim or FFmpeg actually installed.

Manim is CPU-only (Cairo rasterization) -- no CUDA/VRAM requirement, in
keeping with the project's low-memory constraint.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Maps a public overlay type name to the Manim Scene class that implements
# it (see `pipeline/manim_scenes.py`).
OVERLAY_SCENES: dict[str, str] = {
    "title": "TitleOverlayScene",
    "callout": "CalloutOverlayScene",
}

_SCENES_FILE = Path(__file__).with_name("manim_scenes.py")


def build_manim_command(
    overlay_type: str,
    media_dir: Path | str,
    width: int = 1280,
    height: int = 720,
    frame_rate: int = 30,
    quality: str = "m",
    output_file: str = "overlay",
) -> list[str]:
    """Builds the `manim render` invocation for one overlay type.

    Renders through `python -m manim` (not a bare `manim` executable) so
    this works regardless of whether Manim's console script is on PATH,
    as long as it's installed in the active interpreter's environment.
    """
    if overlay_type not in OVERLAY_SCENES:
        raise ValueError(
            f"Unknown overlay_type {overlay_type!r}. Expected one of: "
            f"{', '.join(OVERLAY_SCENES)}"
        )

    scene_name = OVERLAY_SCENES[overlay_type]

    return [
        sys.executable,
        "-m",
        "manim",
        "render",
        str(_SCENES_FILE),
        scene_name,
        "--transparent",
        "--resolution",
        f"{width},{height}",
        "--frame_rate",
        str(frame_rate),
        f"-q{quality}",
        "--media_dir",
        str(media_dir),
        "-o",
        output_file,
    ]


def expected_overlay_output_path(
    media_dir: Path | str,
    height: int = 720,
    frame_rate: int = 30,
    output_file: str = "overlay",
) -> Path:
    """Predicts where Manim writes the rendered clip.

    Manim's community edition lays output out as
    `<media_dir>/videos/<scene_file_stem>/<height>p<frame_rate>/<output_file>.mov`
    (`.mov` because `--transparent` requires an alpha-capable container).
    This convention has held across recent Manim versions but isn't a
    stable public API, so treat it as a best-effort default -- if a Manim
    upgrade moves the output, this is the one place to fix.
    """
    resolution_folder = f"{height}p{frame_rate}"
    return (
        Path(media_dir)
        / "videos"
        / _SCENES_FILE.stem
        / resolution_folder
        / f"{output_file}.mov"
    )


def render_overlay(
    overlay_type: str,
    media_dir: Path | str,
    text: str,
    width: int = 1280,
    height: int = 720,
    frame_rate: int = 30,
    hold_seconds: float = 2.0,
    output_file: str = "overlay",
    extra_env: dict[str, str] | None = None,
) -> Path:
    """Renders one overlay clip and returns its output path."""
    target_dir = Path(media_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    command = build_manim_command(
        overlay_type,
        target_dir,
        width=width,
        height=height,
        frame_rate=frame_rate,
        output_file=output_file,
    )

    env = os.environ.copy()
    env["MPOSTELE_OVERLAY_TEXT"] = text
    env["MPOSTELE_OVERLAY_HOLD"] = str(hold_seconds)
    if extra_env:
        env.update(extra_env)

    subprocess.run(command, check=True, env=env)

    return expected_overlay_output_path(
        target_dir, height=height, frame_rate=frame_rate, output_file=output_file
    )


def build_overlay_composite_command(
    base_video: Path | str,
    overlay_video: Path | str,
    output_path: Path | str,
) -> list[str]:
    """Builds the FFmpeg command that composites a transparent overlay clip
    on top of a base motion clip.

    The overlay filter defaults to holding the overlay's last frame once it
    ends (rather than disappearing), which is fine here since each overlay
    scene already fades itself out before its clip ends -- the base video
    plays on undisturbed underneath a fully transparent frame.
    """
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(base_video),
        "-i",
        str(overlay_video),
        "-filter_complex",
        "[0:v][1:v]overlay=format=auto",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]


def composite_overlay(
    base_video: Path | str,
    overlay_video: Path | str,
    output_path: Path | str,
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    command = build_overlay_composite_command(base_video, overlay_video, target)
    subprocess.run(command, check=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a Manim title/callout overlay and composite it over a base motion clip."
    )
    parser.add_argument("--base-video", required=True, help="Path to the base motion clip (e.g. artifacts/first_scene/motion.mp4)")
    parser.add_argument("--overlay-type", choices=sorted(OVERLAY_SCENES), default="title", help="Which overlay scene to render")
    parser.add_argument("--text", required=True, help="Text shown in the overlay")
    parser.add_argument("--output", default="", help="Path for the composited output video. Defaults to <base-video>.overlay.mp4")
    parser.add_argument("--media-dir", default="artifacts/overlays", help="Directory Manim writes its intermediate render output to")
    parser.add_argument("--width", type=int, default=1280, help="Overlay/base video width in pixels")
    parser.add_argument("--height", type=int, default=720, help="Overlay/base video height in pixels")
    parser.add_argument("--hold-seconds", type=float, default=2.0, help="How long the overlay stays fully visible before fading out")
    parser.add_argument("--callout-x", type=float, default=0.0, help="Callout box x position in Manim scene units (only used for --overlay-type callout)")
    parser.add_argument("--callout-y", type=float, default=0.0, help="Callout box y position in Manim scene units (only used for --overlay-type callout)")
    args = parser.parse_args()

    base_video = Path(args.base_video)
    output_path = Path(args.output) if args.output else base_video.with_suffix(".overlay.mp4")

    extra_env = {}
    if args.overlay_type == "callout":
        extra_env["MPOSTELE_OVERLAY_X"] = str(args.callout_x)
        extra_env["MPOSTELE_OVERLAY_Y"] = str(args.callout_y)

    overlay_path = render_overlay(
        args.overlay_type,
        args.media_dir,
        text=args.text,
        width=args.width,
        height=args.height,
        hold_seconds=args.hold_seconds,
        extra_env=extra_env,
    )
    composite_overlay(base_video, overlay_path, output_path)
    print(f"Rendered '{args.overlay_type}' overlay and composited it into {output_path}.")


if __name__ == "__main__":
    main()
