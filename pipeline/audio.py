"""Narration timing and local FFmpeg audio compositing.

This module keeps voice synthesis separate from composition: callers can supply
any local narration file, including one generated manually or by a future TTS
adapter. FFprobe determines narration length, and FFmpeg trims or extends the
base video's final frame to match it before encoding a social-ready MP4.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


class AudioError(RuntimeError):
    """Raised when narration metadata cannot be read or is invalid."""


def build_ffprobe_command(audio_path: Path | str) -> list[str]:
    """Build the command used to read the first audio stream's duration."""
    return [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=duration:format=duration",
        "-of",
        "json",
        str(audio_path),
    ]


def probe_audio_duration(audio_path: Path | str) -> float:
    """Return narration duration in seconds using the local FFprobe binary."""
    result = subprocess.run(
        build_ffprobe_command(audio_path),
        check=True,
        capture_output=True,
        text=True,
    )

    try:
        metadata = json.loads(result.stdout)
        streams = metadata.get("streams", [])
        raw_duration = streams[0].get("duration") if streams else None
        if raw_duration in (None, "N/A"):
            raw_duration = metadata.get("format", {}).get("duration")
        duration = float(raw_duration)
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise AudioError(f"Could not determine audio duration for {audio_path}") from exc

    if duration <= 0:
        raise AudioError(f"Audio duration must be positive for {audio_path}")
    return duration


def build_audio_composite_command(
    video_path: Path | str,
    audio_path: Path | str,
    output_path: Path | str,
    duration: float,
    normalize_audio: bool = True,
) -> list[str]:
    """Build an FFmpeg command that makes the video match narration length.

    A video longer than the narration is trimmed. A shorter video holds its
    final frame. Narration is trimmed to the selected duration and optionally
    receives lightweight one-pass loudness normalization.
    """
    if duration <= 0:
        raise ValueError("duration must be greater than zero")

    duration_text = f"{float(duration):.6f}"
    video_filter = (
        f"[0:v:0]tpad=stop_mode=clone:stop_duration={duration_text},"
        f"trim=duration={duration_text},setpts=PTS-STARTPTS[v]"
    )
    audio_filters = [f"atrim=duration={duration_text}", "asetpts=PTS-STARTPTS"]
    if normalize_audio:
        audio_filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")
    filter_complex = f"{video_filter};[1:a:0]{','.join(audio_filters)}[a]"

    return [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        duration_text,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def composite_narration(
    video_path: Path | str,
    audio_path: Path | str,
    output_path: Path | str,
    duration: float | None = None,
    normalize_audio: bool = True,
) -> Path:
    """Composite narration over a clip and return the generated MP4 path."""
    video = Path(video_path)
    audio = Path(audio_path)
    if not video.is_file():
        raise FileNotFoundError(f"Base video not found: {video}")
    if not audio.is_file():
        raise FileNotFoundError(f"Narration audio not found: {audio}")

    selected_duration = duration if duration is not None else probe_audio_duration(audio)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        build_audio_composite_command(
            video,
            audio,
            target,
            selected_duration,
            normalize_audio=normalize_audio,
        ),
        check=True,
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match a base clip to local narration and export an MP4 with audio."
    )
    parser.add_argument("--video", required=True, help="Base motion or overlay video")
    parser.add_argument("--audio", required=True, help="Local narration audio file")
    parser.add_argument("--output", default="", help="Output MP4 path (default: <video>.narrated.mp4)")
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Override output duration in seconds instead of probing the narration file.",
    )
    parser.add_argument(
        "--no-normalize-audio",
        action="store_false",
        dest="normalize_audio",
        default=True,
        help="Skip FFmpeg loudness normalization.",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    output_path = Path(args.output) if args.output else video_path.with_suffix(".narrated.mp4")
    selected_duration = args.duration if args.duration is not None else probe_audio_duration(args.audio)
    composite_narration(
        video_path,
        args.audio,
        output_path,
        duration=selected_duration,
        normalize_audio=args.normalize_audio,
    )
    print(f"Composited narration into {output_path} at {selected_duration:.2f}s.")


if __name__ == "__main__":
    main()
