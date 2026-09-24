from app.agents import quality_inspector as qi


def test_within_limits_passes():
    job_state = {"content": {"overlay_text": "Short", "script_text": "Also short."}}
    assert qi.check(job_state) == []


def test_overlay_too_long_flagged():
    job_state = {"content": {"overlay_text": "x" * (qi.MAX_OVERLAY_CHARS + 1), "script_text": "fine"}}
    problems = qi.check(job_state)
    assert any("overlay_text exceeds" in p for p in problems)


def test_script_too_long_flagged():
    job_state = {"content": {"overlay_text": "fine", "script_text": "x" * (qi.MAX_SCRIPT_CHARS + 1)}}
    problems = qi.check(job_state)
    assert any("script_text exceeds" in p for p in problems)


def test_missing_content_treated_as_empty():
    assert qi.check({}) == []


def test_script_with_slash_separated_alternatives_flagged():
    job_state = {
        "content": {
            "overlay_text": "fine",
            "script_text": "Try it today - link in bio! / Or discover the joy of storytelling.",
        }
    }
    problems = qi.check(job_state)
    assert any("two alternative options" in p for p in problems)


def test_overlay_with_slash_separated_alternatives_flagged():
    job_state = {"content": {"overlay_text": "Warm Whimsy / Cozy Nights", "script_text": "fine"}}
    problems = qi.check(job_state)
    assert any("two alternative options" in p for p in problems)


def test_slash_without_surrounding_spaces_not_flagged():
    # "and/or", "3/4" etc. have no whitespace around the slash - only the
    # "option A / option B" shape (spaces on both sides) should trip this.
    job_state = {"content": {"overlay_text": "3/4 done", "script_text": "Try it and/or share it today."}}
    assert qi.check(job_state) == []
