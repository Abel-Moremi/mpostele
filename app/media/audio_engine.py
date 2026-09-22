"""Audio engine: mixes the already-synthesized narration voiceover with a
background music bed into a single track for encode.py to mux in.

Runs after video_engine.py (needs the rendered clip's duration to probe) and
before encode.py (which already knows how to mux a single
artifacts["audio_track"] into the final render - this is the first stage
that actually produces one). The voiceover itself is synthesized earlier, by
narration_engine.py, so composition_agent.py can size scene durations against
its real length instead of guessing - this stage just probes and mixes.
Music comes from the synthesized placeholder beds in app/media/music/ - see
app/media/music/generate_placeholders.py for how those were made and how to
regenerate or replace them with licensed tracks.
"""
import hashlib
import subprocess
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.media.narration_engine import probe_duration_seconds
from app.orchestrator import state


def pick_music_track(job_id: str, mood: str = None) -> Path:
    """Prefers the track matching strategy_brief's mood tag (see
    strategy_agent.py's _tag_mood and settings.MUSIC_MOODS) when there is
    one and its file exists. Falls back to a job_id hash - deterministic per
    job_id (reproducible re-renders) but varied across jobs - for a poster
    job (no mood tagged at all), a mood tagging failure, or a mood value
    that doesn't match a real file; never worth failing a job over."""
    if mood:
        candidate = settings.MUSIC_DIR / f"{mood}.mp3"
        if candidate.exists():
            return candidate

    tracks = sorted(settings.MUSIC_DIR.glob("*.mp3"))
    if not tracks:
        raise RuntimeError(f"No placeholder tracks found in {settings.MUSIC_DIR}.")
    index = int(hashlib.sha1(job_id.encode("utf-8")).hexdigest(), 16) % len(tracks)
    return tracks[index]


def mix_audio(
    voiceover_path: Path,
    music_path: Path,
    clip_duration: float,
    out_path: Path,
    voice_delay_seconds: float = 0.0,
) -> None:
    fade = min(settings.AUDIO_FADE_SECONDS, max(clip_duration - 0.1, 0))
    fade_out_start = max(clip_duration - fade, 0)
    # Piper's raw output is dry and peaks near 0dB - this "humanizing" chain
    # takes the digital edge off before mixing: a little headroom, a warmth
    # bump around 200Hz, a cut around 4.5kHz (where neural TTS tends to
    # sound harshest/most synthetic), gentle compression for consistency, a
    # touch of short room reflection (not an audible echo - just enough to
    # not sound recorded in a dead-silent booth), and a limiter as a safety
    # net against the EQ/compression pushing it back into clipping.
    #
    # adelay shifts the voice to start when CaptionOverlay actually appears
    # on screen (voice_delay_seconds - the caller passes
    # settings.TITLE_REVEAL_SECONDS), not at t=0 - without it, narration
    # would play over the silent TitleReveal title card instead of the
    # caption text it's meant to accompany, since narration_engine.py only
    # synthesizes content.script_text (CaptionOverlay's copy).
    voice_delay_ms = round(voice_delay_seconds * 1000)
    voice_chain = (
        "aresample=44100,aformat=channel_layouts=stereo,"
        f"adelay=delays={voice_delay_ms}:all=1,"
        "volume=-3dB,"
        "highpass=f=80,"
        "equalizer=f=200:t=q:w=1:g=2,"
        "equalizer=f=4500:t=q:w=1:g=-3,"
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=60:makeup=4,"
        "aecho=0.8:0.7:35:0.18,"
        "alimiter=limit=0.97"
    )
    filter_complex = (
        f"[0:a]{voice_chain}[voice];"
        "[1:a]aresample=44100,aformat=channel_layouts=stereo,"
        f"volume={settings.MUSIC_VOLUME_DB}dB,"
        f"afade=t=in:st=0:d={fade},afade=t=out:st={fade_out_start}:d={fade}[music];"
        "[voice][music]amix=inputs=2:duration=longest:normalize=0[mixed]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voiceover_path),
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex", filter_complex,
            "-map", "[mixed]",
            "-t", str(clip_duration),
            str(out_path),
        ],
        check=True,
        timeout=settings.AUDIO_MIX_TIMEOUT_SECONDS,
    )


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    output_dir = settings.TMP_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    voiceover_path = Path(job_state["artifacts"]["voiceover"])

    raw_clip = Path(job_state["artifacts"]["raw_clip"])
    clip_duration = probe_duration_seconds(raw_clip)
    music_path = pick_music_track(job_id, job_state["strategy_brief"].get("mood"))

    audio_track_path = output_dir / "audio_track.m4a"
    mix_audio(
        voiceover_path,
        music_path,
        clip_duration,
        audio_track_path,
        voice_delay_seconds=settings.TITLE_REVEAL_SECONDS,
    )

    job_state = state.load(job_id)
    job_state["artifacts"]["audio_track"] = str(audio_track_path)
    job_state["current_step"] = "ENCODE"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
