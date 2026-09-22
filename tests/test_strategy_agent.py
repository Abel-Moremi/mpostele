from app.agents import strategy_agent


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
