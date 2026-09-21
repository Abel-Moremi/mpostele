"""Final FFmpeg pass: multiplex the audio track, embed the cover image, encode the deliverable video.

Both branches pass -movflags +faststart - without it ffmpeg writes the moov
atom (the track/codec index a player reads before it can find the audio
track at all) after the mdat payload. Every real player can still play a
file like that by seeking, but several progressive/streaming-style players
(browsers' <video> element among them) parse front-to-back and can end up
rendering picture with no sound, or nothing at all, if they give up before
reaching a moov atom that far in. Costs a few KB of read-ahead at encode
time, nothing at playback time.
"""
import subprocess
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state


def encode(raw_clip: Path, output_path: Path, audio_path: Path = None, cover_path: Path = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(raw_clip)]

    if not cover_path:
        # raw_clip already carries its own silent placeholder audio track
        # (Revideo bakes one into every render) - without an explicit map,
        # ffmpeg's automatic stream selection can pick THAT over the real
        # mixed track from audio_path instead of just using whichever one
        # was given last (confirmed: it does, silently - the deliverable
        # plays with an apparently-valid but inaudible audio stream).
        if audio_path:
            cmd += ["-i", str(audio_path)]
        cmd += ["-map", "0:v"]
        if audio_path:
            cmd += ["-map", "1:a"]
        cmd += ["-c:v", settings.VIDEO_ENCODER, "-c:a", "aac", "-movflags", "+faststart", str(output_path)]
        subprocess.run(cmd, check=True)
        return output_path

    # A cover is a second *video-like* input, so the implicit stream mapping
    # used above (fine with at most one video + one audio input) becomes
    # ambiguous - map explicitly instead. -disposition:v:1 attached_pic is
    # what makes players/file browsers treat it as a cover image rather than
    # a second playable video track (the same mechanism MP3/M4A cover art
    # uses); -c:v:1 png keeps it a real still frame instead of re-encoding
    # it through the main video codec.
    cover_input_index = 1
    if audio_path:
        cmd += ["-i", str(audio_path)]
        cover_input_index = 2
    cmd += ["-i", str(cover_path)]

    cmd += ["-map", "0:v", "-map", f"{cover_input_index}:v"]
    if audio_path:
        cmd += ["-map", "1:a"]

    cmd += ["-c:v", settings.VIDEO_ENCODER]
    if audio_path:
        cmd += ["-c:a", "aac"]
    cmd += ["-c:v:1", "png", "-disposition:v:1", "attached_pic", "-movflags", "+faststart", str(output_path)]

    subprocess.run(cmd, check=True)
    return output_path


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    raw_clip = Path(job_state["artifacts"]["raw_clip"])
    audio = job_state["artifacts"].get("audio_track")
    cover = job_state["artifacts"].get("cover_image")
    output_path = settings.OUTPUT_DIR / job_id / "video.mp4"
    encode(raw_clip, output_path, Path(audio) if audio else None, Path(cover) if cover else None)

    job_state["artifacts"]["rendered_video"] = str(output_path)
    job_state["current_step"] = "PLATFORM_ADAPTOR"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
