from app.agents import composition_validator as cv

_VALID_ITEMS = [
    {"iconId": "dinosaur", "caption": "a curious dinosaur"},
    {"iconId": "knight", "caption": "a brave knight"},
]


def _scene(component, duration=30, text="Real words here", **extra_props):
    props = {"text": text, "backgroundColor": "#EFE3D0"}
    if component in ("TitleReveal", "Outro"):
        props["accentColor"] = "#BE7C6C"
    if component == "CaptionOverlay":
        props["accentColor"] = "#BE7C6C"
    props.update(extra_props)
    return {"component": component, "durationInFrames": duration, "props": props}


def _illustrated_example_scene(duration=30, items=None, **extra_props):
    props = {"backgroundColor": "#EFE3D0", "accentColor": "#BE7C6C", "items": items or _VALID_ITEMS}
    props.update(extra_props)
    return {"component": "IllustratedExample", "durationInFrames": duration, "props": props}


def _abstract_transition_scene(duration=30, **extra_props):
    props = {
        "backgroundColor": "#EFE3D0",
        "accentColor": "#BE7C6C",
        "secondaryColor": "#D4A24C",
        "tertiaryColor": "#7C8B7A",
    }
    props.update(extra_props)
    return {"component": "AbstractTransition", "durationInFrames": duration, "props": props}


def _badge_checklist_scene(duration=30, items=None, **extra_props):
    props = {"backgroundColor": "#EFE3D0", "accentColor": "#BE7C6C", "items": items or _VALID_ITEMS}
    props.update(extra_props)
    return {"component": "BadgeChecklist", "durationInFrames": duration, "props": props}


def _product_mockup_scene(duration=30, items=None, **extra_props):
    props = {
        "backgroundColor": "#EFE3D0",
        "accentColor": "#BE7C6C",
        "headline": "What's your story about?",
        "typedText": "A story about a curious dinosaur and a brave knight.",
        "items": items or _VALID_ITEMS,
    }
    props.update(extra_props)
    return {"component": "ProductMockup", "durationInFrames": duration, "props": props}


def _valid_scenes():
    return [_scene("TitleReveal"), _scene("CaptionOverlay"), _scene("Outro")]


def _valid_scenes_with_new_components():
    return [
        _scene("TitleReveal"),
        _illustrated_example_scene(),
        _scene("CaptionOverlay"),
        _product_mockup_scene(),
        _badge_checklist_scene(),
        _abstract_transition_scene(),
        _scene("Outro"),
    ]


def test_valid_spec_passes():
    job_state = {"composition_spec": {"scenes": _valid_scenes()}}
    assert cv.check(job_state) == []


def test_missing_scenes_list():
    assert cv.check({"composition_spec": {}}) == ["composition_spec.scenes must be a non-empty list"]
    assert cv.check({"composition_spec": {"scenes": []}}) == ["composition_spec.scenes must be a non-empty list"]


def test_unknown_component_flagged():
    scenes = _valid_scenes()
    scenes[1]["component"] = "SomethingElse"
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("unknown component" in p for p in problems)


def test_non_positive_duration_flagged():
    scenes = _valid_scenes()
    scenes[0]["durationInFrames"] = 0
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("durationInFrames must be a positive integer" in p for p in problems)


def test_missing_required_prop_flagged():
    scenes = _valid_scenes()
    del scenes[0]["props"]["accentColor"]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("missing props" in p for p in problems)


def test_bad_hex_color_flagged():
    scenes = _valid_scenes()
    scenes[0]["props"]["accentColor"] = "not-a-color"
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("must be a 6-digit hex color" in p for p in problems)


def test_placeholder_text_flagged():
    scenes = _valid_scenes()
    scenes[1]["props"]["text"] = "..."
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("empty or placeholder-only" in p for p in problems)


def test_caption_text_too_long_flagged():
    scenes = _valid_scenes()
    scenes[1]["props"]["text"] = "x" * 1000
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("text exceeds" in p for p in problems)


def test_missing_title_reveal_or_outro_flagged():
    scenes = [_scene("CaptionOverlay")]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("missing required component" in p for p in problems)


def test_valid_spec_with_new_components_passes():
    job_state = {"composition_spec": {"scenes": _valid_scenes_with_new_components()}}
    assert cv.check(job_state) == []


def test_abstract_transition_missing_color_prop_flagged():
    scenes = _valid_scenes_with_new_components()
    abstract_transition = next(s for s in scenes if s["component"] == "AbstractTransition")
    del abstract_transition["props"]["secondaryColor"]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("missing props" in p for p in problems)


def test_abstract_transition_is_not_flagged_for_missing_text():
    # AbstractTransition has no "text" prop at all - it must not be flagged
    # as empty/placeholder text the way a real text-bearing scene would be.
    scenes = _valid_scenes_with_new_components()
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert not any("placeholder-only" in p for p in problems)


def test_illustrated_example_missing_items_flagged():
    scenes = _valid_scenes_with_new_components()
    del scenes[1]["props"]["items"]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("missing props" in p for p in problems)


def test_illustrated_example_too_many_items_flagged():
    scenes = _valid_scenes_with_new_components()
    scenes[1]["props"]["items"] = _VALID_ITEMS + [{"iconId": "dragon", "caption": "a dragon"}] * 2
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("items must be a list of 1 to" in p for p in problems)


def test_illustrated_example_empty_items_flagged():
    scenes = _valid_scenes_with_new_components()
    scenes[1]["props"]["items"] = []
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("items must be a list of 1 to" in p for p in problems)


def test_illustrated_example_unknown_icon_id_flagged():
    scenes = _valid_scenes_with_new_components()
    scenes[1]["props"]["items"] = [{"iconId": "not-a-real-archetype", "caption": "whatever"}]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("unknown iconId" in p for p in problems)


def test_illustrated_example_empty_caption_flagged():
    scenes = _valid_scenes_with_new_components()
    scenes[1]["props"]["items"] = [{"iconId": "dinosaur", "caption": "   "}]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("caption is empty" in p for p in problems)


def test_illustrated_example_caption_too_long_flagged():
    scenes = _valid_scenes_with_new_components()
    scenes[1]["props"]["items"] = [{"iconId": "dinosaur", "caption": "x" * 1000}]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("caption exceeds" in p for p in problems)


def _find(scenes, component):
    return next(s for s in scenes if s["component"] == component)


def test_badge_checklist_reuses_items_check():
    scenes = _valid_scenes_with_new_components()
    badges = _find(scenes, "BadgeChecklist")
    badges["props"]["items"] = [{"iconId": "not-a-real-archetype", "caption": "whatever"}]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("unknown iconId" in p for p in problems)


def test_product_mockup_missing_headline_flagged():
    scenes = _valid_scenes_with_new_components()
    del _find(scenes, "ProductMockup")["props"]["headline"]
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("missing props" in p for p in problems)


def test_product_mockup_placeholder_headline_flagged():
    scenes = _valid_scenes_with_new_components()
    _find(scenes, "ProductMockup")["props"]["headline"] = "..."
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("headline is empty or placeholder-only" in p for p in problems)


def test_product_mockup_placeholder_typed_text_flagged():
    scenes = _valid_scenes_with_new_components()
    _find(scenes, "ProductMockup")["props"]["typedText"] = ""
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("typedText is empty or placeholder-only" in p for p in problems)


def test_product_mockup_reuses_items_check():
    scenes = _valid_scenes_with_new_components()
    _find(scenes, "ProductMockup")["props"]["items"] = []
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("items must be a list of 1 to" in p for p in problems)


def test_emphasis_text_placeholder_flagged():
    scenes = _valid_scenes()
    scenes[0]["props"]["emphasisText"] = "..."
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("emphasisText is empty or placeholder-only" in p for p in problems)


def test_emphasis_text_too_long_flagged():
    scenes = _valid_scenes()
    scenes[0]["props"]["emphasisText"] = "x" * 1000
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("emphasisText exceeds" in p for p in problems)


def test_tagline_placeholder_flagged():
    scenes = _valid_scenes()
    scenes[-1]["props"]["tagline"] = "..."
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert any("tagline is empty or placeholder-only" in p for p in problems)


def test_valid_emphasis_and_tagline_pass():
    scenes = _valid_scenes()
    scenes[0]["props"]["emphasisText"] = "tonight?"
    scenes[-1]["props"]["tagline"] = "Let them write the rules"
    scenes[-1]["props"]["emphasisText"] = "for once."
    problems = cv.check({"composition_spec": {"scenes": scenes}})
    assert problems == []
