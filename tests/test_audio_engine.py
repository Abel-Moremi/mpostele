import hashlib

from app.config import settings
from app.media.audio_engine import pick_music_track


def test_mood_match_is_preferred():
    for mood in settings.MUSIC_MOODS:
        track = pick_music_track("any_job_id", mood)
        assert track == settings.MUSIC_DIR / f"{mood}.mp3"
        assert track.exists()


def test_unrecognized_mood_falls_back_to_hash():
    job_id = "job_test_fallback"
    tracks = sorted(settings.MUSIC_DIR.glob("*.mp3"))
    index = int(hashlib.sha1(job_id.encode("utf-8")).hexdigest(), 16) % len(tracks)
    assert pick_music_track(job_id, "not-a-real-mood") == tracks[index]


def test_missing_mood_falls_back_to_hash():
    job_id = "job_test_fallback_2"
    tracks = sorted(settings.MUSIC_DIR.glob("*.mp3"))
    index = int(hashlib.sha1(job_id.encode("utf-8")).hexdigest(), 16) % len(tracks)
    assert pick_music_track(job_id, None) == tracks[index]


def test_fallback_pick_is_deterministic_per_job_id():
    assert pick_music_track("same_job", None) == pick_music_track("same_job", None)
