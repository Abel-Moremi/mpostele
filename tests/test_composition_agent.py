from app.agents import composition_agent as ca
from app.config import settings


def _job_state(segment_durations):
    return {
        "narration": {
            "segments": [{"text": f"Segment {i}.", "duration_seconds": d} for i, d in enumerate(segment_durations)]
        }
    }


def test_build_scenes_frame_math_and_order():
    job_state = _job_state([2.0, 3.5])
    scenes = ca._build_scenes(job_state, title_text="Hook text", outro_text="CTA text")

    assert [s["component"] for s in scenes] == ["TitleReveal", "CaptionOverlay", "CaptionOverlay", "Outro"]
    assert scenes[0]["durationInFrames"] == round(settings.TITLE_REVEAL_SECONDS * settings.REVIDEO_FPS)
    assert scenes[1]["durationInFrames"] == round(2.0 * settings.REVIDEO_FPS)
    assert scenes[2]["durationInFrames"] == round(3.5 * settings.REVIDEO_FPS)
    assert scenes[-1]["durationInFrames"] == round(settings.OUTRO_HOLD_SECONDS * settings.REVIDEO_FPS)
    assert scenes[0]["props"]["text"] == "Hook text"
    assert scenes[-1]["props"]["text"] == "CTA text"


def test_build_scenes_single_segment():
    job_state = _job_state([4.2])
    scenes = ca._build_scenes(job_state, title_text="Hook", outro_text="CTA")
    assert [s["component"] for s in scenes] == ["TitleReveal", "CaptionOverlay", "Outro"]


def _assert_valid_transitions(scenes):
    previous = None
    for scene in scenes[:-1]:
        transition = scene["transitionOut"]
        assert transition in ca._TRANSITIONS
        assert transition != previous
        previous = transition
    assert "transitionOut" not in scenes[-1] or scenes[-1]["transitionOut"] is None


def test_assign_transitions_uses_valid_proposal(monkeypatch):
    # 2 segments -> TitleReveal + 2xCaptionOverlay + Outro = 4 scenes = 3 cuts.
    scenes = ca._build_scenes(_job_state([1.0, 1.0]), "hook", "cta")
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: ["slide", "matchCut", "crossfade"])
    ca._assign_transitions(scenes, "job_abc")
    assert [s["transitionOut"] for s in scenes[:-1]] == ["slide", "matchCut", "crossfade"]


def test_assign_transitions_falls_back_on_empty_proposal(monkeypatch):
    scenes = ca._build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: [])
    ca._assign_transitions(scenes, "job_abc")
    _assert_valid_transitions(scenes)


def test_assign_transitions_falls_back_on_repeated_proposal(monkeypatch):
    scenes = ca._build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: ["slide", "slide", "slide"])
    ca._assign_transitions(scenes, "job_abc")
    _assert_valid_transitions(scenes)
    # The first proposed value was valid (no prior transition to repeat), so it's kept.
    assert scenes[0]["transitionOut"] == "slide"


def test_assign_transitions_falls_back_on_garbage_proposal(monkeypatch):
    scenes = ca._build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: ["not-a-real-transition", None, 42])
    ca._assign_transitions(scenes, "job_abc")
    _assert_valid_transitions(scenes)


def test_assign_transitions_is_deterministic_per_job_id(monkeypatch):
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: [])
    scenes_a = ca._build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    scenes_b = ca._build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    ca._assign_transitions(scenes_a, "job_same_id")
    ca._assign_transitions(scenes_b, "job_same_id")
    assert [s.get("transitionOut") for s in scenes_a] == [s.get("transitionOut") for s in scenes_b]
