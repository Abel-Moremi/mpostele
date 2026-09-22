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
