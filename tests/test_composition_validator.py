from app.agents import composition_validator as cv


def _scene(component, duration=30, text="Real words here", **extra_props):
    props = {"text": text, "backgroundColor": "#EFE3D0"}
    if component in ("TitleReveal", "Outro"):
        props["accentColor"] = "#BE7C6C"
    if component == "CaptionOverlay":
        props["accentColor"] = "#BE7C6C"
    props.update(extra_props)
    return {"component": component, "durationInFrames": duration, "props": props}


def _valid_scenes():
    return [_scene("TitleReveal"), _scene("CaptionOverlay"), _scene("Outro")]


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
