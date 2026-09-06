"""Optional, local Kokoro text-to-speech adapter.

Kokoro is imported lazily so capture, motion, and composition continue to work
without TTS dependencies. Generated WAV files are accompanied by a small cache
record and are reused when the script and voice settings have not changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_VOICE = "af_heart"
DEFAULT_LANG_CODE = "a"
DEFAULT_SPEED = 1.0


class TTSError(RuntimeError):
    """Raised when local speech synthesis is unavailable or produces no audio."""


def synthesis_key(
    text: str,
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    lang_code: str = DEFAULT_LANG_CODE,
) -> str:
    """Return a stable key for a script and its audible synthesis settings."""
    payload = json.dumps(
        {
            "backend": "kokoro",
            "lang_code": lang_code,
            "speed": float(speed),
            "text": text,
            "voice": voice,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_path(output_path: Path) -> Path:
    return output_path.with_suffix(output_path.suffix + ".tts-cache.json")


def _read_cache_key(output_path: Path) -> str | None:
    try:
        data = json.loads(_cache_path(output_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return data.get("key") if isinstance(data, dict) else None


def synthesize_speech(
    text: str,
    output_path: Path | str,
    *,
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    lang_code: str = DEFAULT_LANG_CODE,
    force: bool = False,
    pipeline: Any | None = None,
) -> Path:
    """Generate a mono WAV with Kokoro, reusing an identical cached result."""
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("TTS text must not be empty")
    if not isinstance(voice, str) or not voice.strip():
        raise ValueError("TTS voice must not be empty")
    if not isinstance(lang_code, str) or not lang_code.strip():
        raise ValueError("TTS language code must not be empty")
    if speed <= 0:
        raise ValueError("TTS speed must be greater than zero")

    target = Path(output_path)
    key = synthesis_key(clean_text, voice.strip(), speed, lang_code.strip())
    if not force and target.is_file() and _read_cache_key(target) == key:
        return target

    try:
        import numpy as np
        import soundfile as sf
        if pipeline is None:
            from kokoro import KPipeline
            pipeline = KPipeline(lang_code=lang_code.strip())
    except ImportError as exc:
        raise TTSError(
            "Local TTS dependencies are not installed. "
            "Run: pip install -r requirements-tts.txt"
        ) from exc

    chunks = [
        np.asarray(audio, dtype=np.float32)
        for _graphemes, _phonemes, audio in pipeline(
            clean_text,
            voice=voice.strip(),
            speed=float(speed),
            split_pattern=r"\n+",
        )
        if len(audio)
    ]
    if not chunks:
        raise TTSError("Kokoro did not produce any audio for the supplied script")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        sf.write(temporary, np.concatenate(chunks), 24000, format="WAV", subtype="PCM_16")
        temporary.replace(target)
        _cache_path(target).write_text(
            json.dumps({"key": key, "backend": "kokoro"}, indent=2),
            encoding="utf-8",
        )
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local narration WAV with optional Kokoro TTS.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Narration text")
    source.add_argument("--text-file", help="UTF-8 file containing narration text")
    parser.add_argument("--output", required=True, help="Output WAV path")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Kokoro voice (default: {DEFAULT_VOICE})")
    parser.add_argument("--lang-code", default=DEFAULT_LANG_CODE, help=f"Kokoro language code (default: {DEFAULT_LANG_CODE})")
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED, help="Speech speed multiplier")
    parser.add_argument("--force", action="store_true", help="Regenerate even when the cached settings match")
    args = parser.parse_args()

    try:
        text = args.text if args.text is not None else Path(args.text_file).read_text(encoding="utf-8-sig")
        output = synthesize_speech(
            text,
            args.output,
            voice=args.voice,
            speed=args.speed,
            lang_code=args.lang_code,
            force=args.force,
        )
    except (OSError, TTSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Generated local narration at {output}.")


if __name__ == "__main__":
    main()
