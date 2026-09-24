import hashlib

from app.config import settings
from app.media.audio_engine import _pre_narration_seconds, pick_music_track


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


def _scene(component, seconds):
    return {"component": component, "durationInFrames": round(seconds * settings.REVIDEO_FPS)}


def test_pre_narration_seconds_sums_scenes_before_first_caption_overlay():
    spec = {
        "scenes": [
            _scene("TitleReveal", 2.5),
            _scene("IllustratedExample", 3.5),
            _scene("CaptionOverlay", 4.0),
            _scene("CaptionOverlay", 3.0),
        ]
    }
    assert _pre_narration_seconds(spec) == 2.5 + 3.5


def test_pre_narration_seconds_ignores_scenes_after_caption_overlay():
    # Regression guard: ProductMockup/BadgeChecklist/AbstractTransition all
    # come after CaptionOverlay in composition_agent.py's real scene order,
    # and must never be counted toward the narration's start delay.
    spec = {
        "scenes": [
            _scene("TitleReveal", 2.5),
            _scene("CaptionOverlay", 4.0),
            _scene("ProductMockup", 4.5),
            _scene("BadgeChecklist", 3.5),
            _scene("AbstractTransition", 1.2),
            _scene("Outro", 3.0),
        ]
    }
    assert _pre_narration_seconds(spec) == 2.5


def test_pre_narration_seconds_falls_back_on_malformed_spec():
    assert _pre_narration_seconds({}) == settings.TITLE_REVEAL_SECONDS
    assert _pre_narration_seconds({"scenes": "not-a-list"}) == settings.TITLE_REVEAL_SECONDS
    assert _pre_narration_seconds({"scenes": [{"component": "TitleReveal"}]}) == settings.TITLE_REVEAL_SECONDS
    assert _pre_narration_seconds({"scenes": ["not-a-dict"]}) == settings.TITLE_REVEAL_SECONDS


def test_pre_narration_seconds_falls_back_when_no_caption_overlay_present():
    spec = {"scenes": [_scene("TitleReveal", 2.5), _scene("Outro", 3.0)]}
    assert _pre_narration_seconds(spec) == settings.TITLE_REVEAL_SECONDS
