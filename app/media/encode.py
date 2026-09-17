"""Final FFmpeg pass: multiplex the audio track and encode the deliverable video."""
import subprocess
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state


def encode(interpolated_clip: Path, output_path: Path, audio_path: Path = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(interpolated_clip)]
    if audio_path:
        cmd += ["-i", str(audio_path)]
    cmd += ["-c:v", settings.VIDEO_ENCODER, "-c:a", "aac", str(output_path)]
    subprocess.run(cmd, check=True)
    return output_path


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    interpolated = Path(job_state["artifacts"]["interpolated_clip"])
    audio = job_state["artifacts"].get("audio_track")
    output_path = settings.OUTPUT_DIR / job_id / "video.mp4"
    encode(interpolated, output_path, Path(audio) if audio else None)

    job_state["artifacts"]["rendered_video"] = str(output_path)
    job_state["current_step"] = "PLATFORM_ADAPTOR"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
