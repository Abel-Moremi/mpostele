"""Validate an exported MP4 against lightweight social-video expectations.

The checks use the local FFprobe binary and a small MP4 atom scan. They do not
decode the media, keeping validation fast and suitable for modest hardware.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

PRESETS: dict[str, tuple[int, int]] = {
    "landscape_720p": (1280, 720),
    "vertical_1080p": (1080, 1920),
    "square_1080p": (1080, 1080),
}


class ExportValidationError(RuntimeError):
    """Raised when an export cannot be inspected."""


@dataclass(frozen=True)
class ExportExpectations:
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    require_audio: bool = True
    require_faststart: bool = True

    def __post_init__(self) -> None:
        if self.fps is not None and (not math.isfinite(self.fps) or self.fps <= 0):
            raise ValueError("Expected frame rate must be a finite positive number")


@dataclass(frozen=True)
class ValidationResult:
    path: str
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_probe_command(path: Path | str) -> list[str]:
    """Build the FFprobe command used for container and stream metadata."""
    return [
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(path),
    ]


def probe_export(path: Path | str) -> dict[str, Any]:
    """Read export metadata with FFprobe."""
    try:
        result = subprocess.run(
            build_probe_command(path), check=True, capture_output=True, text=True
        )
    except FileNotFoundError as exc:
        raise ExportValidationError("FFprobe was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        raise ExportValidationError(f"FFprobe could not inspect {path}: {detail}") from exc
    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExportValidationError(f"FFprobe returned invalid JSON for {path}") from exc
    if not isinstance(metadata, dict):
        raise ExportValidationError(f"FFprobe returned invalid metadata for {path}")
    return metadata


def _parse_rate(value: Any) -> float | None:
    if not isinstance(value, str) or value in {"", "0/0", "N/A"}:
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def has_faststart(path: Path | str) -> bool:
    """Return whether the top-level MP4 moov atom appears before media data."""
    media = Path(path)
    positions: dict[bytes, int] = {}
    with media.open("rb") as handle:
        file_size = media.stat().st_size
        offset = 0
        while offset + 8 <= file_size:
            handle.seek(offset)
            header = handle.read(8)
            atom_size = int.from_bytes(header[:4], "big")
            atom_type = header[4:8]
            header_size = 8
            if atom_size == 1:
                extended = handle.read(8)
                if len(extended) != 8:
                    break
                atom_size = int.from_bytes(extended, "big")
                header_size = 16
            elif atom_size == 0:
                atom_size = file_size - offset
            if atom_size < header_size or offset + atom_size > file_size:
                break
            if atom_type in {b"moov", b"mdat"} and atom_type not in positions:
                positions[atom_type] = offset
            if b"moov" in positions and b"mdat" in positions:
                break
            offset += atom_size
    return b"moov" in positions and b"mdat" in positions and positions[b"moov"] < positions[b"mdat"]


def validate_metadata(
    path: Path | str,
    metadata: dict[str, Any],
    expectations: ExportExpectations,
    *,
    faststart: bool | None,
) -> ValidationResult:
    """Validate already-probed metadata; separated for deterministic tests."""
    errors: list[str] = []
    warnings: list[str] = []
    streams = metadata.get("streams", [])
    if not isinstance(streams, list):
        streams = []
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
    video = videos[0] if videos else None
    audio = audios[0] if audios else None
    container = metadata.get("format", {}) if isinstance(metadata.get("format"), dict) else {}
    duration = _positive_float(container.get("duration"))

    if "mp4" not in str(container.get("format_name", "")).lower():
        errors.append("Container is not recognized as MP4.")
    if duration is None:
        errors.append("Container duration is missing or not positive.")
    if len(videos) != 1:
        errors.append(f"Expected exactly one video stream; found {len(videos)}.")

    nominal_fps = None
    average_fps = None
    selected_fps = None
    if video:
        if video.get("codec_name") != "h264":
            errors.append(f"Video codec must be H.264; found {video.get('codec_name', 'unknown')}.")
        if video.get("pix_fmt") != "yuv420p":
            errors.append(f"Pixel format must be yuv420p; found {video.get('pix_fmt', 'unknown')}.")
        width, height = video.get("width"), video.get("height")
        if expectations.width is not None and width != expectations.width:
            errors.append(f"Width must be {expectations.width}; found {width}.")
        if expectations.height is not None and height != expectations.height:
            errors.append(f"Height must be {expectations.height}; found {height}.")
        # Validate the encoded cadence. Average FPS can differ slightly when
        # narration-timed scenes end between exact frame boundaries.
        nominal_fps = _parse_rate(video.get("r_frame_rate"))
        average_fps = _parse_rate(video.get("avg_frame_rate"))
        selected_fps = nominal_fps or average_fps
        if expectations.fps is not None and (
            selected_fps is None or abs(selected_fps - expectations.fps) > 0.02
        ):
            errors.append(
                f"Nominal frame rate must be {expectations.fps:g} fps; "
                f"found {selected_fps or 'unknown'}."
            )

    if expectations.require_audio and len(audios) != 1:
        errors.append(f"Expected exactly one audio stream; found {len(audios)}.")
    elif not expectations.require_audio and len(audios) > 1:
        errors.append(f"Expected no more than one audio stream; found {len(audios)}.")
    if audio:
        if audio.get("codec_name") != "aac":
            errors.append(f"Audio codec must be AAC; found {audio.get('codec_name', 'unknown')}.")
        if str(audio.get("sample_rate")) != "48000":
            errors.append(f"Audio sample rate must be 48000 Hz; found {audio.get('sample_rate', 'unknown')}.")
        if audio.get("channels") != 2:
            errors.append(f"Audio must be stereo; found {audio.get('channels', 'unknown')} channels.")
    elif not expectations.require_audio:
        warnings.append("No audio stream is present.")

    if expectations.require_faststart and faststart is not True:
        errors.append("MP4 is not fast-start optimized (moov atom must precede mdat).")

    summary = {
        "duration_seconds": duration,
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
        "fps": round(selected_fps, 3) if selected_fps is not None else None,
        "average_fps": round(average_fps, 3) if average_fps is not None else None,
        "video_codec": video.get("codec_name") if video else None,
        "pixel_format": video.get("pix_fmt") if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "audio_sample_rate": int(audio["sample_rate"]) if audio and str(audio.get("sample_rate", "")).isdigit() else None,
        "audio_channels": audio.get("channels") if audio else None,
        "faststart": faststart,
    }
    return ValidationResult(str(Path(path)), not errors, tuple(errors), tuple(warnings), summary)


def validate_export(path: Path | str, expectations: ExportExpectations) -> ValidationResult:
    """Probe and validate one local MP4 export."""
    media = Path(path)
    if not media.is_file():
        raise ExportValidationError(f"Export not found: {media}")
    metadata = probe_export(media)
    faststart = has_faststart(media) if expectations.require_faststart else None
    return validate_metadata(media, metadata, expectations, faststart=faststart)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate an MP4 for the mpostele social export profile."
    )
    parser.add_argument("video", help="Path to the exported MP4")
    parser.add_argument("--preset", choices=PRESETS, help="Expected mpostele dimensions")
    parser.add_argument("--fps", type=float, default=30.0, help="Expected frame rate (default: 30)")
    parser.add_argument("--allow-no-audio", action="store_true", help="Permit a video without an audio stream")
    parser.add_argument("--skip-faststart", action="store_true", help="Do not check MP4 atom order")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Print a machine-readable report")
    args = parser.parse_args()
    if not math.isfinite(args.fps) or args.fps <= 0:
        parser.error("--fps must be a finite number greater than zero")

    dimensions = PRESETS.get(args.preset, (None, None))
    expectations = ExportExpectations(
        width=dimensions[0], height=dimensions[1], fps=args.fps,
        require_audio=not args.allow_no_audio,
        require_faststart=not args.skip_faststart,
    )
    try:
        result = validate_export(args.video, expectations)
    except ExportValidationError as exc:
        parser.error(str(exc))

    if args.json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "PASS" if result.valid else "FAIL"
        print(f"{status}: {result.path}")
        print(json.dumps(result.summary, indent=2))
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        for error in result.errors:
            print(f"ERROR: {error}")
    if not result.valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
