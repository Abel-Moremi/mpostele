from app.agents import strategy_agent
from app.config import settings


def test_load_product_brief_reads_configured_file(tmp_path, monkeypatch):
    brief_path = tmp_path / "product_brief.md"
    brief_path.write_text("# Dreamcraftr\nwarm, poetic voice", encoding="utf-8")
    monkeypatch.setattr(settings, "PRODUCT_BRIEF_PATH", str(brief_path))
    assert "warm, poetic voice" in strategy_agent._load_product_brief()


def test_load_product_brief_degrades_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PRODUCT_BRIEF_PATH", str(tmp_path / "missing.md"))
    assert strategy_agent._load_product_brief() == ""


def test_tag_mood_returns_recognized_value(monkeypatch):
    monkeypatch.setattr(strategy_agent, "call_ollama", lambda prompt, model=None: '{"mood": "calm"}')
    assert strategy_agent._tag_mood({"topic": "yoga app"}) == "calm"


def test_tag_mood_rejects_unrecognized_value(monkeypatch):
    monkeypatch.setattr(strategy_agent, "call_ollama", lambda prompt, model=None: '{"mood": "spooky"}')
    assert strategy_agent._tag_mood({"topic": "yoga app"}) is None


def test_tag_mood_handles_missing_key(monkeypatch):
    monkeypatch.setattr(strategy_agent, "call_ollama", lambda prompt, model=None: "{}")
    assert strategy_agent._tag_mood({"topic": "yoga app"}) is None


def test_tag_mood_degrades_on_call_failure(monkeypatch):
    def _raise(prompt, model=None):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(strategy_agent, "call_ollama", _raise)
    assert strategy_agent._tag_mood({"topic": "yoga app"}) is None


def test_tag_mood_degrades_on_malformed_json(monkeypatch):
    monkeypatch.setattr(strategy_agent, "call_ollama", lambda prompt, model=None: "not json at all")
    assert strategy_agent._tag_mood({"topic": "yoga app"}) is None


def test_first_alternative_splits_on_slash_with_spaces():
    # Regression: qwen2.5:1.5b handed back "Option A... / Option B..."
    # instead of picking one - only the first should survive.
    assert strategy_agent._first_alternative("Option A here / Option B here") == "Option A here"


def test_first_alternative_leaves_plain_text_untouched():
    assert strategy_agent._first_alternative("Just one hook") == "Just one hook"


def test_first_alternative_leaves_tight_slash_untouched():
    # "and/or" and "3/4" have no whitespace around the slash - not the
    # "option A / option B" shape this exists to catch.
    assert strategy_agent._first_alternative("Try it and/or share it") == "Try it and/or share it"
    assert strategy_agent._first_alternative("3/4 done") == "3/4 done"


def test_first_alternative_non_string_passthrough():
    assert strategy_agent._first_alternative(None) is None
    assert strategy_agent._first_alternative(123) == 123


def test_run_dedupes_alternatives_in_hook_and_cta(monkeypatch):
    job_state = {"input_brief": {"topic": "x"}, "media_type": "video"}
    monkeypatch.setattr(strategy_agent.state, "load", lambda job_id: job_state)
    saved = {}
    monkeypatch.setattr(
        strategy_agent.state, "update", lambda job_id, key, value, **kw: saved.setdefault(key, value)
    )
    monkeypatch.setattr(strategy_agent, "_load_product_brief", lambda: "")
    monkeypatch.setattr(strategy_agent, "_tag_mood", lambda input_brief: None)
    echoed = '{"topic": "t", "target_hook": "Hook A / Hook B", "call_to_action": "CTA A / CTA B"}'
    monkeypatch.setattr(strategy_agent, "call_ollama", lambda *a, **k: echoed)

    strategy_agent.run("job_abc")

    assert saved["strategy_brief"]["target_hook"] == "Hook A"
    assert saved["strategy_brief"]["call_to_action"] == "CTA A"
