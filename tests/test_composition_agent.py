from app.agents import composition_agent as ca
from app.config import settings

_EXAMPLE_ITEMS = [
    {"iconId": "dinosaur", "caption": "a curious dinosaur"},
    {"iconId": "knight", "caption": "a brave knight"},
    {"iconId": "astronaut", "caption": "an astronaut"},
]


def _job_state(segment_durations, topic="a bedtime story app"):
    return {
        "narration": {
            "segments": [{"text": f"Segment {i}.", "duration_seconds": d} for i, d in enumerate(segment_durations)]
        },
        "strategy_brief": {"topic": topic},
    }


def _build_scenes(job_state, title_text, outro_text, example_items=_EXAMPLE_ITEMS):
    return ca._build_scenes(job_state, title_text=title_text, outro_text=outro_text, example_items=example_items)


def test_build_scenes_frame_math_and_order():
    job_state = _job_state([2.0, 3.5])
    scenes = _build_scenes(job_state, title_text="Hook text", outro_text="CTA text")

    assert [s["component"] for s in scenes] == [
        "TitleReveal",
        "IllustratedExample",
        "CaptionOverlay",
        "CaptionOverlay",
        "AbstractTransition",
        "Outro",
    ]
    assert scenes[0]["durationInFrames"] == round(settings.TITLE_REVEAL_SECONDS * settings.REVIDEO_FPS)
    assert scenes[1]["durationInFrames"] == round(settings.ILLUSTRATED_EXAMPLE_SECONDS * settings.REVIDEO_FPS)
    assert scenes[2]["durationInFrames"] == round(2.0 * settings.REVIDEO_FPS)
    assert scenes[3]["durationInFrames"] == round(3.5 * settings.REVIDEO_FPS)
    assert scenes[4]["durationInFrames"] == round(settings.TRANSITION_BEAT_SECONDS * settings.REVIDEO_FPS)
    assert scenes[-1]["durationInFrames"] == round(settings.OUTRO_HOLD_SECONDS * settings.REVIDEO_FPS)
    assert scenes[0]["props"]["text"] == "Hook text"
    assert scenes[1]["props"]["items"] == _EXAMPLE_ITEMS
    assert scenes[-1]["props"]["text"] == "CTA text"


def test_build_scenes_single_segment():
    job_state = _job_state([4.2])
    scenes = _build_scenes(job_state, title_text="Hook", outro_text="CTA")
    assert [s["component"] for s in scenes] == [
        "TitleReveal",
        "IllustratedExample",
        "CaptionOverlay",
        "AbstractTransition",
        "Outro",
    ]


def _assert_valid_transitions(scenes):
    previous = None
    for scene in scenes[:-1]:
        transition = scene["transitionOut"]
        assert transition in ca._TRANSITIONS
        assert transition != previous
        previous = transition
    assert "transitionOut" not in scenes[-1] or scenes[-1]["transitionOut"] is None


def test_assign_transitions_uses_valid_proposal(monkeypatch):
    # 2 segments -> TitleReveal + IllustratedExample + 2xCaptionOverlay +
    # AbstractTransition + Outro = 6 scenes = 5 cuts.
    scenes = _build_scenes(_job_state([1.0, 1.0]), "hook", "cta")
    monkeypatch.setattr(
        ca, "_propose_transitions", lambda texts, n_cuts: ["slide", "matchCut", "crossfade", "slide", "matchCut"]
    )
    ca._assign_transitions(scenes, "job_abc")
    assert [s["transitionOut"] for s in scenes[:-1]] == ["slide", "matchCut", "crossfade", "slide", "matchCut"]


def test_assign_transitions_falls_back_on_empty_proposal(monkeypatch):
    scenes = _build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: [])
    ca._assign_transitions(scenes, "job_abc")
    _assert_valid_transitions(scenes)


def test_assign_transitions_falls_back_on_repeated_proposal(monkeypatch):
    scenes = _build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: ["slide"] * (len(scenes) - 1))
    ca._assign_transitions(scenes, "job_abc")
    _assert_valid_transitions(scenes)
    # The first proposed value was valid (no prior transition to repeat), so it's kept.
    assert scenes[0]["transitionOut"] == "slide"


def test_assign_transitions_falls_back_on_garbage_proposal(monkeypatch):
    scenes = _build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: ["not-a-real-transition", None, 42])
    ca._assign_transitions(scenes, "job_abc")
    _assert_valid_transitions(scenes)


def test_assign_transitions_is_deterministic_per_job_id(monkeypatch):
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: [])
    scenes_a = _build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    scenes_b = _build_scenes(_job_state([1.0, 1.0, 1.0]), "hook", "cta")
    ca._assign_transitions(scenes_a, "job_same_id")
    ca._assign_transitions(scenes_b, "job_same_id")
    assert [s.get("transitionOut") for s in scenes_a] == [s.get("transitionOut") for s in scenes_b]


def test_assign_transitions_does_not_crash_on_textless_or_items_scenes(monkeypatch):
    # AbstractTransition has no "text" prop and IllustratedExample has
    # "items" instead - _scene_summary_text must stand in for both rather
    # than KeyError-ing on scene["props"]["text"].
    scenes = _build_scenes(_job_state([1.0]), "hook", "cta")
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: [])
    ca._assign_transitions(scenes, "job_abc")
    _assert_valid_transitions(scenes)


def test_scene_summary_text_uses_items_caption_when_no_text_prop():
    scene = {"component": "IllustratedExample", "props": {"items": _EXAMPLE_ITEMS}}
    summary = ca._scene_summary_text(scene)
    for item in _EXAMPLE_ITEMS:
        assert item["caption"] in summary


def test_scene_summary_text_empty_for_textless_scene():
    scene = {"component": "AbstractTransition", "props": {}}
    assert ca._scene_summary_text(scene) == ""


def _archetypes():
    return ca._load_archetypes()


def test_choose_archetypes_uses_valid_proposal(monkeypatch):
    proposal = [
        {"iconId": "dragon", "caption": "a friendly dragon"},
        {"iconId": "robot", "caption": "a clever robot"},
        {"iconId": "mermaid", "caption": "a singing mermaid"},
    ]
    monkeypatch.setattr(ca, "_propose_archetypes", lambda topic, archetypes: proposal)
    items = ca._choose_archetypes(_job_state([1.0]), "job_abc")
    assert items == proposal


def test_choose_archetypes_falls_back_on_empty_proposal(monkeypatch):
    monkeypatch.setattr(ca, "_propose_archetypes", lambda topic, archetypes: [])
    items = ca._choose_archetypes(_job_state([1.0]), "job_abc")
    valid_ids = {a["id"] for a in _archetypes()}
    assert len(items) == ca._ARCHETYPE_COUNT
    ids = [item["iconId"] for item in items]
    assert len(set(ids)) == len(ids)  # no duplicates
    for item in items:
        assert item["iconId"] in valid_ids
        assert item["caption"]


def test_choose_archetypes_falls_back_on_unknown_icon_id(monkeypatch):
    proposal = [{"iconId": "not-a-real-archetype", "caption": "whatever"}] * 3
    monkeypatch.setattr(ca, "_propose_archetypes", lambda topic, archetypes: proposal)
    items = ca._choose_archetypes(_job_state([1.0]), "job_abc")
    valid_ids = {a["id"] for a in _archetypes()}
    for item in items:
        assert item["iconId"] in valid_ids


def test_choose_archetypes_falls_back_on_duplicate_proposal(monkeypatch):
    proposal = [{"iconId": "dragon", "caption": "a friendly dragon"}] * 3
    monkeypatch.setattr(ca, "_propose_archetypes", lambda topic, archetypes: proposal)
    items = ca._choose_archetypes(_job_state([1.0]), "job_abc")
    ids = [item["iconId"] for item in items]
    assert len(set(ids)) == len(ids)


def test_choose_archetypes_is_deterministic_per_job_id(monkeypatch):
    monkeypatch.setattr(ca, "_propose_archetypes", lambda topic, archetypes: [])
    items_a = ca._choose_archetypes(_job_state([1.0]), "job_same_id")
    items_b = ca._choose_archetypes(_job_state([1.0]), "job_same_id")
    assert items_a == items_b


def test_apply_brand_sets_abstract_transition_and_illustrated_example_colors():
    scenes = _build_scenes(_job_state([1.0]), "hook", "cta")
    spec = {"scenes": scenes}
    ca._apply_brand(spec)

    by_component = {s["component"]: s["props"] for s in spec["scenes"]}
    illustrated = by_component["IllustratedExample"]
    assert illustrated["textColor"] and illustrated["fontFamily"]

    transition = by_component["AbstractTransition"]
    assert transition["secondaryColor"] and transition["tertiaryColor"]
    assert "text" not in transition
