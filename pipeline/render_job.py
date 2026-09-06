"""Manifest-driven multi-scene rendering for the local mpostele pipeline.

The orchestrator reuses the existing capture, overlay, and audio modules, then
normalizes and concatenates scenes with FFmpeg. Intermediate files are retained
for reproducibility and low-cost debugging.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline.audio import composite_narration
from pipeline.first_render import (
    MOTION_PRESETS,
    MOTION_TRIGGERS,
    capture_motion_sequence,
    capture_page,
    render_motion_video,
    transcode_to_mp4,
)
from pipeline.overlays import OVERLAY_SCENES, composite_overlay, render_overlay

EXPORT_PRESETS: dict[str, tuple[int, int]] = {
    "landscape_720p": (1280, 720),
    "vertical_1080p": (1080, 1920),
    "square_1080p": (1080, 1080),
}
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class RenderJobError(ValueError):
    """Raised when a render manifest is invalid."""


@dataclass(frozen=True)
class ExportSettings:
    width: int
    height: int
    fps: int
    output: Path


@dataclass(frozen=True)
class Scene:
    scene_id: str
    source_type: str
    source: str | Path
    duration: float | None
    motion_preset: str
    capture: dict[str, Any]
    overlay: dict[str, Any] | None
    narration: Path | None
    normalize_audio: bool


@dataclass(frozen=True)
class RenderJob:
    manifest_path: Path
    work_dir: Path
    export: ExportSettings
    scenes: tuple[Scene, ...]


def _positive(value: Any, label: str, *, integer: bool = False) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise RenderJobError(f"{label} must be a positive number")
    if integer and not float(value).is_integer():
        raise RenderJobError(f"{label} must be a whole number")
    return int(value) if integer else float(value)


def _path(base: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RenderJobError(f"{label} must be a non-empty path string")
    result = Path(value).expanduser()
    return result.resolve() if result.is_absolute() else (base / result).resolve()


def load_render_job(manifest_path: Path | str) -> RenderJob:
    """Read and validate a JSON job; relative paths use its directory."""
    manifest = Path(manifest_path).resolve()
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise RenderJobError(f"Manifest not found: {manifest}") from exc
    except json.JSONDecodeError as exc:
        raise RenderJobError(f"Invalid JSON in {manifest}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RenderJobError("Manifest root must be a JSON object")

    base = manifest.parent
    export_raw = raw.get("export", {})
    if not isinstance(export_raw, dict):
        raise RenderJobError("export must be an object")
    preset = export_raw.get("preset", "landscape_720p")
    if preset not in EXPORT_PRESETS:
        raise RenderJobError(
            f"Unknown export preset {preset!r}; expected one of: {', '.join(EXPORT_PRESETS)}"
        )
    default_width, default_height = EXPORT_PRESETS[preset]
    export = ExportSettings(
        width=_positive(export_raw.get("width", default_width), "export.width", integer=True),
        height=_positive(export_raw.get("height", default_height), "export.height", integer=True),
        fps=_positive(export_raw.get("fps", 30), "export.fps", integer=True),
        output=_path(base, raw.get("output", "outputs/final.mp4"), "output"),
    )
    work_dir = _path(base, raw.get("work_dir", "artifacts/render_job"), "work_dir")

    scene_items = raw.get("scenes")
    if not isinstance(scene_items, list) or not scene_items:
        raise RenderJobError("scenes must be a non-empty array")

    scenes: list[Scene] = []
    ids: set[str] = set()
    for index, item in enumerate(scene_items, start=1):
        label = f"scenes[{index - 1}]"
        if not isinstance(item, dict):
            raise RenderJobError(f"{label} must be an object")
        scene_id = item.get("id", f"scene-{index:02d}")
        if not isinstance(scene_id, str) or not _ID_PATTERN.fullmatch(scene_id):
            raise RenderJobError(f"{label}.id may contain only letters, numbers, '_' and '-'")
        if scene_id in ids:
            raise RenderJobError(f"Duplicate scene id: {scene_id}")
        ids.add(scene_id)

        source_fields = [key for key in ("url", "image", "video") if item.get(key)]
        if len(source_fields) != 1:
            raise RenderJobError(f"{label} must define exactly one of url, image, or video")
        source_type = source_fields[0]
        source_value = item[source_type]
        if not isinstance(source_value, str) or not source_value.strip():
            raise RenderJobError(f"{label}.{source_type} must be a non-empty string")
        source: str | Path = source_value if source_type == "url" else _path(base, source_value, f"{label}.{source_type}")

        duration_value = item.get("duration")
        duration = None if duration_value is None else _positive(duration_value, f"{label}.duration")
        motion_preset = item.get("motion_preset", "zoom_in")
        if motion_preset not in MOTION_PRESETS:
            raise RenderJobError(f"Unknown motion preset {motion_preset!r} in {label}")

        capture = item.get("capture", {})
        if not isinstance(capture, dict):
            raise RenderJobError(f"{label}.capture must be an object")
        if "password" in capture:
            raise RenderJobError(
                f"{label}.capture.password is not allowed; use the MPOSTELE_PASSWORD environment variable"
            )
        if capture.get("mode", "screenshot") not in ("screenshot", "motion"):
            raise RenderJobError(f"{label}.capture.mode must be 'screenshot' or 'motion'")
        if capture.get("motion_trigger", "hover") not in MOTION_TRIGGERS:
            raise RenderJobError(f"Unknown motion trigger in {label}")
        hidden = capture.get("hide_selectors", [])
        if not isinstance(hidden, list) or not all(isinstance(value, str) for value in hidden):
            raise RenderJobError(f"{label}.capture.hide_selectors must be an array of strings")

        overlay = item.get("overlay")
        if overlay is not None:
            if not isinstance(overlay, dict):
                raise RenderJobError(f"{label}.overlay must be an object")
            if overlay.get("type", "title") not in OVERLAY_SCENES:
                raise RenderJobError(f"Unknown overlay type in {label}")
            if not isinstance(overlay.get("text"), str) or not overlay["text"].strip():
                raise RenderJobError(f"{label}.overlay.text must be a non-empty string")

        narration_value = item.get("narration")
        narration = None if narration_value is None else _path(base, narration_value, f"{label}.narration")
        normalize_audio = item.get("normalize_audio", True)
        if not isinstance(normalize_audio, bool):
            raise RenderJobError(f"{label}.normalize_audio must be true or false")

        scenes.append(Scene(scene_id, source_type, source, duration, motion_preset, dict(capture), dict(overlay) if overlay else None, narration, normalize_audio))

    return RenderJob(manifest, work_dir, export, tuple(scenes))


def build_scene_normalize_command(
    input_path: Path | str,
    output_path: Path | str,
    width: int,
    height: int,
    fps: int,
    has_audio: bool,
    duration: float | None = None,
) -> list[str]:
    """Build a consistent H.264/AAC scene, adding silence when necessary."""
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps}"
    )
    command = ["ffmpeg", "-y", "-i", str(input_path)]
    if not has_audio:
        command.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])
    command.extend(["-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0", "-vf", video_filter])
    if has_audio:
        command.extend(["-af", "aresample=48000"])
    command.extend([
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-ac", "2", "-shortest",
    ])
    if duration is not None:
        command.extend(["-t", f"{duration:.6f}"])
    command.append(str(output_path))
    return command


def build_concat_command(list_path: Path | str, output_path: Path | str) -> list[str]:
    """Build the final stream-copy concat command for normalized scenes."""
    return [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c", "copy", "-movflags", "+faststart", str(output_path),
    ]


def build_duration_probe_command(path: Path | str) -> list[str]:
    """Build an FFprobe command for a media container's duration."""
    return [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]


def _probe_duration(path: Path | str) -> float:
    result = subprocess.run(
        build_duration_probe_command(path), check=True, capture_output=True, text=True
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RenderJobError(f"Could not determine media duration for {path}") from exc
    if duration <= 0:
        raise RenderJobError(f"Media duration must be positive for {path}")
    return duration


def _has_audio(path: Path | str) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _render_base(scene: Scene, scene_dir: Path, export: ExportSettings, password: str) -> Path:
    motion_path = scene_dir / "motion.mp4"
    if scene.source_type == "video":
        source = Path(scene.source)
        if not source.is_file():
            raise FileNotFoundError(f"Scene video not found: {source}")
        return source
    if scene.source_type == "image":
        source = Path(scene.source)
        if not source.is_file():
            raise FileNotFoundError(f"Scene image not found: {source}")
        render_motion_video(source, motion_path, scene.duration or 4.0, export.width, export.height, scene.motion_preset)
        return motion_path

    capture = scene.capture
    if capture.get("mode", "screenshot") == "motion":
        seconds = scene.duration or float(capture.get("record_seconds", 4.0))
        result = capture_motion_sequence(
            str(scene.source), scene_dir, export.width, export.height,
            username=str(capture.get("username", "")),
            password=password,
            target_path=str(capture.get("target_path", "")),
            extra_hide_selectors=capture.get("hide_selectors", []),
            hide_common_overlays=capture.get("hide_common_overlays", True),
            motion_trigger=capture.get("motion_trigger", "hover"),
            trigger_selector=str(capture.get("trigger_selector", "")),
            record_seconds=seconds,
        )
        transcode_to_mp4(result.video_path, motion_path)
        return motion_path

    capture_path = scene_dir / "capture.png"
    result = capture_page(
        str(scene.source), capture_path, export.width, export.height,
        username=str(capture.get("username", "")),
        password=password,
        target_path=str(capture.get("target_path", "")),
        capture_selector=str(capture.get("selector", "")),
        extra_hide_selectors=capture.get("hide_selectors", []),
        hide_common_overlays=capture.get("hide_common_overlays", True),
        words_per_second=float(capture.get("words_per_second", 3.0)),
        min_duration=float(capture.get("min_duration", 3.0)),
        max_duration=float(capture.get("max_duration", 10.0)),
    )
    render_motion_video(result.screenshot_path, motion_path, scene.duration or result.duration, export.width, export.height, scene.motion_preset)
    return motion_path


def render_job(job: RenderJob) -> Path:
    """Render all scenes and return the final MP4 path."""
    job.work_dir.mkdir(parents=True, exist_ok=True)
    job.export.output.parent.mkdir(parents=True, exist_ok=True)
    password = os.environ.get("MPOSTELE_PASSWORD", "")
    normalized: list[Path] = []

    for index, scene in enumerate(job.scenes, start=1):
        scene_dir = job.work_dir / f"{index:02d}-{scene.scene_id}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        current = _render_base(scene, scene_dir, job.export, password)

        if scene.overlay:
            overlay = scene.overlay
            extra_env: dict[str, str] = {}
            if overlay.get("type", "title") == "callout":
                extra_env = {"MPOSTELE_OVERLAY_X": str(overlay.get("x", 0)), "MPOSTELE_OVERLAY_Y": str(overlay.get("y", 0))}
            layer = render_overlay(
                overlay.get("type", "title"), scene_dir / "overlay-media", overlay["text"],
                job.export.width, job.export.height, job.export.fps,
                float(overlay.get("hold_seconds", 2.0)), "overlay", extra_env,
            )
            current = composite_overlay(current, layer, scene_dir / "with-overlay.mp4")

        if scene.narration:
            current = composite_narration(current, scene.narration, scene_dir / "with-narration.mp4", normalize_audio=scene.normalize_audio)

        output = scene_dir / "normalized.mp4"
        # A generated lavfi silence source is infinite. Always cap unnarrated
        # scenes to the requested or probed visual duration so -shortest does
        # not gain encoder-buffer padding at scene boundaries.
        normalize_duration = None
        if scene.narration is None:
            normalize_duration = scene.duration or _probe_duration(current)
        subprocess.run(
            build_scene_normalize_command(
                current, output, job.export.width, job.export.height,
                job.export.fps, _has_audio(current), normalize_duration,
            ),
            check=True,
        )
        normalized.append(output)

    concat_file = job.work_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{path.as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for path in normalized), encoding="utf-8")
    subprocess.run(build_concat_command(concat_file, job.export.output), check=True)
    return job.export.output


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a multi-scene video from a local JSON manifest.")
    parser.add_argument("manifest", help="Path to the render job JSON file")
    args = parser.parse_args()
    try:
        job = load_render_job(args.manifest)
        output = render_job(job)
    except (RenderJobError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(f"Rendered {len(job.scenes)} scenes to {output}.")


if __name__ == "__main__":
    main()
