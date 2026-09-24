import json

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


def _build_scenes(job_state, title_text, outro_text, example_items=_EXAMPLE_ITEMS, **kwargs):
    return ca._build_scenes(
        job_state, title_text=title_text, outro_text=outro_text, example_items=example_items, **kwargs
    )


def test_build_scenes_frame_math_and_order():
    job_state = _job_state([2.0, 3.5])
    scenes = _build_scenes(job_state, title_text="Hook text", outro_text="CTA text")

    assert [s["component"] for s in scenes] == [
        "TitleReveal",
        "IllustratedExample",
        "CaptionOverlay",
        "CaptionOverlay",
        "ProductMockup",
        "BadgeChecklist",
        "AbstractTransition",
        "Outro",
    ]
    assert scenes[0]["durationInFrames"] == round(settings.TITLE_REVEAL_SECONDS * settings.REVIDEO_FPS)
    assert scenes[1]["durationInFrames"] == round(settings.ILLUSTRATED_EXAMPLE_SECONDS * settings.REVIDEO_FPS)
    assert scenes[2]["durationInFrames"] == round(2.0 * settings.REVIDEO_FPS)
    assert scenes[3]["durationInFrames"] == round(3.5 * settings.REVIDEO_FPS)
    assert scenes[4]["durationInFrames"] == round(settings.PRODUCT_MOCKUP_SECONDS * settings.REVIDEO_FPS)
    assert scenes[5]["durationInFrames"] == round(settings.BADGE_CHECKLIST_SECONDS * settings.REVIDEO_FPS)
    assert scenes[6]["durationInFrames"] == round(settings.TRANSITION_BEAT_SECONDS * settings.REVIDEO_FPS)
    assert scenes[-1]["durationInFrames"] == round(settings.OUTRO_HOLD_SECONDS * settings.REVIDEO_FPS)
    assert scenes[0]["props"]["text"] == "Hook text"
    assert scenes[1]["props"]["items"] == _EXAMPLE_ITEMS
    assert scenes[4]["props"]["items"] == _EXAMPLE_ITEMS
    assert scenes[4]["props"]["headline"]
    assert scenes[4]["props"]["typedText"]
    assert scenes[5]["props"]["items"] == _EXAMPLE_ITEMS
    assert scenes[-1]["props"]["text"] == "CTA text"


def test_build_scenes_single_segment():
    job_state = _job_state([4.2])
    scenes = _build_scenes(job_state, title_text="Hook", outro_text="CTA")
    assert [s["component"] for s in scenes] == [
        "TitleReveal",
        "IllustratedExample",
        "CaptionOverlay",
        "ProductMockup",
        "BadgeChecklist",
        "AbstractTransition",
        "Outro",
    ]


def test_build_scenes_omits_emphasis_and_tagline_when_not_supplied():
    scenes = _build_scenes(_job_state([1.0]), "Hook", "CTA")
    title_props = scenes[0]["props"]
    outro_props = scenes[-1]["props"]
    assert "emphasisText" not in title_props
    assert "tagline" not in outro_props
    assert "emphasisText" not in outro_props


def test_build_scenes_includes_emphasis_and_tagline_when_supplied():
    scenes = _build_scenes(
        _job_state([1.0]),
        "Hook",
        "CTA",
        title_emphasis="tonight?",
        outro_tagline="Let them write the rules",
        outro_emphasis="for once.",
    )
    title_props = scenes[0]["props"]
    outro_props = scenes[-1]["props"]
    assert title_props["emphasisText"] == "tonight?"
    assert outro_props["tagline"] == "Let them write the rules"
    assert outro_props["emphasisText"] == "for once."


def test_build_scenes_omits_outro_emphasis_without_tagline():
    # emphasisText on Outro only makes sense nested under tagline (see
    # outro.tsx's mount function) - supplying emphasis without a tagline
    # must not produce a prop the Node component has nowhere to render.
    scenes = _build_scenes(_job_state([1.0]), "Hook", "CTA", outro_emphasis="for once.")
    assert "emphasisText" not in scenes[-1]["props"]
    assert "tagline" not in scenes[-1]["props"]


def test_build_typed_text_joins_captions_naturally():
    assert ca._build_typed_text([{"iconId": "a", "caption": "a dinosaur"}]) == "A story about a dinosaur."
    assert (
        ca._build_typed_text(
            [
                {"iconId": "a", "caption": "a dinosaur"},
                {"iconId": "b", "caption": "a knight"},
                {"iconId": "c", "caption": "an astronaut"},
            ]
        )
        == "A story about a dinosaur, a knight and an astronaut."
    )
    assert ca._build_typed_text([]) == ""


def test_clean_short_text_omits_placeholder_and_oversized_values():
    assert ca._clean_short_text("real phrase", 32) == "real phrase"
    assert ca._clean_short_text("  padded  ", 32) == "padded"
    assert ca._clean_short_text("...", 32) == ""
    assert ca._clean_short_text("", 32) == ""
    assert ca._clean_short_text(None, 32) == ""
    assert ca._clean_short_text("x" * 40, 32) == ""


def test_clean_short_text_rejects_prompt_example_placeholder():
    # Regression: qwen2.5:1.5b was observed echoing the PROMPT's own
    # example text verbatim for a real, unrelated brief.
    assert ca._clean_short_text("for once.", 32) == ""
    assert ca._clean_short_text("For Once.", 32) == ""  # case-insensitive
    assert ca._clean_short_text("  finally.  ", 32) == ""


def test_is_example_placeholder():
    assert ca._is_example_placeholder("for once.")
    assert ca._is_example_placeholder("Stop wrestling with setup scripts")
    assert not ca._is_example_placeholder("a real, unrelated phrase")
    assert not ca._is_example_placeholder(None)
    assert not ca._is_example_placeholder(123)


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
    # ProductMockup + BadgeChecklist + AbstractTransition + Outro = 8 scenes
    # = 7 cuts.
    scenes = _build_scenes(_job_state([1.0, 1.0]), "hook", "cta")
    proposal = ["slide", "matchCut", "crossfade", "slide", "matchCut", "slide", "crossfade"]
    monkeypatch.setattr(ca, "_propose_transitions", lambda texts, n_cuts: proposal)
    ca._assign_transitions(scenes, "job_abc")
    assert [s["transitionOut"] for s in scenes[:-1]] == proposal


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
    # AbstractTransition has no "text" prop, IllustratedExample/BadgeChecklist
    # have "items" instead, and ProductMockup has neither "text" nor a bare
    # "items"-only shape (it also carries headline/typedText) -
    # _scene_summary_text must stand in for all of them rather than
    # KeyError-ing on scene["props"]["text"].
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


def test_run_rejects_echoed_placeholder_title_and_outro_text(monkeypatch):
    # Regression: composition_agent.run() must not ship the PROMPT's own
    # example title_text/outro_text verbatim into a real video - it should
    # come out empty instead, so composition_validator.py's existing
    # placeholder-text check catches it like any other blank LLM response
    # and drives a normal retry.
    job_state = _job_state([1.0])
    job_state["strategy_brief"]["target_hook"] = "hook"
    job_state["strategy_brief"]["call_to_action"] = "cta"
    monkeypatch.setattr(ca.state, "load", lambda job_id: job_state)
    saved = {}
    monkeypatch.setattr(ca.state, "update", lambda job_id, key, value, **kw: saved.setdefault(key, value))
    echoed = json.dumps(
        {
            "title_text": "Stop wrestling with setup scripts",
            "title_emphasis": "finally.",
            "outro_text": "Try our CLI tool today",
            "outro_tagline": "Let the tool handle the busywork",
            "outro_emphasis": "for once.",
        }
    )
    monkeypatch.setattr(ca, "call_ollama", lambda *a, **k: echoed)

    ca.run("job_abc")

    scenes = saved["composition_spec"]["scenes"]
    title_scene = next(s for s in scenes if s["component"] == "TitleReveal")
    outro_scene = next(s for s in scenes if s["component"] == "Outro")
    assert title_scene["props"]["text"] == ""
    assert "emphasisText" not in title_scene["props"]
    assert outro_scene["props"]["text"] == ""
    assert "tagline" not in outro_scene["props"]


def test_apply_brand_sets_all_new_scene_colors():
    scenes = _build_scenes(
        _job_state([1.0]), "hook", "cta", title_emphasis="wow", outro_tagline="tagline", outro_emphasis="wow2"
    )
    spec = {"scenes": scenes}
    ca._apply_brand(spec)

    by_component = {s["component"]: s["props"] for s in spec["scenes"]}

    illustrated = by_component["IllustratedExample"]
    assert illustrated["textColor"] and illustrated["fontFamily"]

    transition = by_component["AbstractTransition"]
    assert transition["secondaryColor"] and transition["tertiaryColor"]
    assert "text" not in transition

    badges = by_component["BadgeChecklist"]
    assert badges["confirmColor"]
    assert badges["textColor"] and badges["fontFamily"]

    mockup = by_component["ProductMockup"]
    assert mockup["textColor"] and mockup["fontFamily"]

    title = by_component["TitleReveal"]
    assert title["secondaryColor"]

    outro = by_component["Outro"]
    assert outro["secondaryColor"]
