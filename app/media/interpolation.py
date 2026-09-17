"""RIFE frame interpolation: raises the native generation FPS to the export target."""
import subprocess
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state


def interpolate(raw_clip: Path, output_dir: Path) -> Path:
    if not settings.RIFE_BINARY:
        raise RuntimeError(
            "RIFE_BINARY is not configured (app/config/settings.py) - "
            "install RIFE and point RIFE_BINARY at its executable."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    interpolated = output_dir / "interpolated.mp4"
    subprocess.run(
        [
            settings.RIFE_BINARY,
            "--input", str(raw_clip),
            "--output", str(interpolated),
            "--target-fps", str(settings.INTERPOLATION_TARGET_FPS),
        ],
        check=True,
    )
    return interpolated


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    raw_clip = Path(job_state["artifacts"]["raw_clip"])
    interpolated = interpolate(raw_clip, settings.TMP_DIR / job_id)

    job_state["artifacts"]["interpolated_clip"] = str(interpolated)
    job_state["current_step"] = "ENCODE"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
