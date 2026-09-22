from app.agents import poster_validator as pv


def _valid_layout(**overrides):
    layout = {
        "headline": "Automate your stack",
        "ctaText": "Run 1-Line Install",
        "backgroundColor": "#EFE3D0",
        "accentColor": "#BE7C6C",
    }
    layout.update(overrides)
    return layout


def test_valid_layout_passes():
    assert pv.check({"poster_layout": _valid_layout()}) == []


def test_missing_required_keys_flagged():
    layout = _valid_layout()
    del layout["ctaText"]
    problems = pv.check({"poster_layout": layout})
    assert any("missing keys" in p and "ctaText" in p for p in problems)


def test_bad_hex_color_flagged():
    layout = _valid_layout(accentColor="orange")
    problems = pv.check({"poster_layout": layout})
    assert any("must be a 6-digit hex color" in p for p in problems)


def test_headline_too_long_flagged():
    layout = _valid_layout(headline="x" * 1000)
    problems = pv.check({"poster_layout": layout})
    assert any("headline exceeds" in p for p in problems)


def test_cta_too_long_flagged():
    layout = _valid_layout(ctaText="x" * (pv.MAX_CTA_CHARS + 1))
    problems = pv.check({"poster_layout": layout})
    assert any("ctaText exceeds" in p for p in problems)


def test_logo_src_is_not_required_and_does_not_break_validation():
    layout = _valid_layout(logoSrc="design/logo.png")
    assert pv.check({"poster_layout": layout}) == []
