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
