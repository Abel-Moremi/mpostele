"""Regenerates the placeholder background-music beds in this folder.

These are synthesized with ffmpeg (stacked sine tones shaped into a pad, no
samples or third-party audio involved) specifically so they carry no
licensing questions - stand-ins for real royalty-free tracks, swappable
later without touching audio_engine.py (which just picks a file from this
directory by name). Run directly to regenerate: `python
app/media/music/generate_placeholders.py`.
"""
import subprocess
from pathlib import Path

MUSIC_DIR = Path(__file__).resolve().parent
DURATION = 26  # seconds - longer than a single VIDEO_TARGET_DURATION_SECONDS
                # clip is ever expected to be, so audio_engine.py can usually
                # trim rather than loop this.

# Each track is a handful of sine tones (a sustained chord) shaped with
# tremolo/lowpass into something pad-like, faded in/out, loudness-normalized.
TRACKS = {
    # Slow, sparse major-7th pad.
    "calm.mp3": {
        "freqs": [130.81, 164.81, 196.00, 246.94],  # C3 E3 G3 B3
        "tremolo": "f=0.1:d=0.2",
        "lowpass": 1800,
    },
    # Slightly higher and more animated - faster tremolo reads as more
    # "energetic" without becoming rhythmic/percussive.
    "upbeat.mp3": {
        "freqs": [220.00, 277.18, 329.63, 440.00],  # A3 C#4 E4 A4
        "tremolo": "f=0.6:d=0.35",
        "lowpass": 2500,
    },
    # Plain sustained triad, minimal movement - neutral "corporate" bed.
    "corporate.mp3": {
        "freqs": [146.83, 185.00, 220.00, 293.66],  # D3 F#3 A3 D4
        "tremolo": "f=0.12:d=0.1",
        "lowpass": 2000,
    },
}


def build_track(name: str, spec: dict) -> None:
    out_path = MUSIC_DIR / name
    inputs = []
    for freq in spec["freqs"]:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={DURATION}"]

    n = len(spec["freqs"])
    mix_inputs = "".join(f"[{i}]" for i in range(n))
    filter_complex = (
        f"{mix_inputs}amix=inputs={n}:duration=longest:weights={'1 ' * n}"
        f",tremolo={spec['tremolo']}"
        f",lowpass=f={spec['lowpass']}"
        f",afade=t=in:st=0:d=3"
        f",afade=t=out:st={DURATION - 4}:d=4"
        f",loudnorm=I=-23:TP=-2:LRA=7"
    )

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-ac", "2", "-ar", "44100",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    for track_name, track_spec in TRACKS.items():
        build_track(track_name, track_spec)
