from app.agents import creative_critic


def _job_state():
    return {
        "strategy_brief": {"target_hook": "Stop wrestling with setup scripts", "call_to_action": "Try it today"},
        "content": {"script_text": "Our CLI automates the whole thing for you."},
    }


def test_passed_response_returns_no_problems(monkeypatch):
    monkeypatch.setattr(
        creative_critic, "call_ollama", lambda prompt, model=None: '{"passed": true, "problems": []}'
    )
    assert creative_critic.check(_job_state()) == []


def test_failed_response_returns_problems(monkeypatch):
    monkeypatch.setattr(
        creative_critic,
        "call_ollama",
        lambda prompt, model=None: '{"passed": false, "problems": ["the CTA does not relate to the hook"]}',
    )
    problems = creative_critic.check(_job_state())
    assert problems == ["the CTA does not relate to the hook"]


def test_failed_response_without_reasons_gets_a_default_message(monkeypatch):
    monkeypatch.setattr(creative_critic, "call_ollama", lambda prompt, model=None: '{"passed": false}')
    problems = creative_critic.check(_job_state())
    assert len(problems) == 1


def test_call_failure_degrades_to_pass(monkeypatch):
    def _raise(prompt, model=None):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(creative_critic, "call_ollama", _raise)
    assert creative_critic.check(_job_state()) == []


def test_malformed_json_degrades_to_pass(monkeypatch):
    monkeypatch.setattr(creative_critic, "call_ollama", lambda prompt, model=None: "not json")
    assert creative_critic.check(_job_state()) == []
