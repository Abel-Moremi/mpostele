import pytest

from app.config import settings
from app.media import publish_engine
from app.orchestrator import state


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise publish_engine.requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json


@pytest.fixture
def job(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JOBS_DIR", tmp_path)
    job_id = "job_publish_test"
    job_state = state.create(job_id, "video", "9:16", {"topic": "t"})
    media_path = tmp_path / "video.mp4"
    media_path.write_bytes(b"fake")
    job_state["artifacts"]["rendered_video"] = str(media_path)
    job_state["platform_copy"] = {"tiktok": "Hook 1", "x": "Hook 2"}
    state.save(job_state)
    return job_id


def _fake_post(upload_response, capture=None):
    def fake_post(url, **kwargs):
        if url.endswith("/upload"):
            return _FakeResponse(upload_response)
        if capture is not None:
            capture["body"] = kwargs["json"]
        return _FakeResponse({"ok": True})

    return fake_post


def test_skips_when_no_api_key(job, monkeypatch):
    monkeypatch.setattr(settings, "POSTIZ_API_KEY", None)
    publish_engine.run(job)
    assert state.load(job)["publish_status"] == {
        "status": "skipped",
        "detail": "POSTIZ_API_KEY not configured",
    }


def test_skips_when_no_rendered_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(settings, "POSTIZ_API_KEY", "key")
    job_id = "job_no_artifact"
    state.create(job_id, "video", "9:16", {"topic": "t"})
    publish_engine.run(job_id)
    assert state.load(job_id)["publish_status"]["status"] == "skipped"


def test_skips_when_no_platform_has_configured_integration(job, monkeypatch):
    monkeypatch.setattr(settings, "POSTIZ_API_KEY", "key")
    monkeypatch.setattr(settings, "POSTIZ_INTEGRATION_IDS", {"tiktok": None, "x": None})
    monkeypatch.setattr(publish_engine.requests, "post", _fake_post({"id": "img1"}))
    publish_engine.run(job)
    status = state.load(job)["publish_status"]
    assert status["status"] == "skipped"
    assert "integration" in status["detail"]


def test_partial_integration_config_only_posts_configured_platforms(job, monkeypatch):
    monkeypatch.setattr(settings, "POSTIZ_API_KEY", "key")
    monkeypatch.setattr(settings, "POSTIZ_INTEGRATION_IDS", {"tiktok": "abc", "x": None})
    captured = {}
    monkeypatch.setattr(publish_engine.requests, "post", _fake_post({"id": "img1"}, captured))
    publish_engine.run(job)
    assert len(captured["body"]["posts"]) == 1
    assert captured["body"]["posts"][0]["settings"]["__type"] == "tiktok"


def test_defaults_to_draft_not_immediate(job, monkeypatch):
    monkeypatch.setattr(settings, "POSTIZ_API_KEY", "key")
    monkeypatch.setattr(settings, "POSTIZ_INTEGRATION_IDS", {"tiktok": "abc", "x": "def"})
    captured = {}
    monkeypatch.setattr(publish_engine.requests, "post", _fake_post({"id": "img1"}, captured))
    publish_engine.run(job)
    assert captured["body"]["type"] == "draft"
    assert len(captured["body"]["posts"]) == 2
    assert state.load(job)["publish_status"]["status"] == "drafted"


def test_publish_now_flag_posts_immediately(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(settings, "POSTIZ_API_KEY", "key")
    monkeypatch.setattr(settings, "POSTIZ_INTEGRATION_IDS", {"tiktok": "abc"})
    job_id = "job_now"
    job_state = state.create(job_id, "poster", "1:1", {"topic": "t"}, publish_now=True)
    media_path = tmp_path / "poster.png"
    media_path.write_bytes(b"fake")
    job_state["artifacts"]["final_poster"] = str(media_path)
    job_state["platform_copy"] = {"tiktok": "Hook"}
    state.save(job_state)

    captured = {}
    monkeypatch.setattr(publish_engine.requests, "post", _fake_post({"id": "img1"}, captured))
    publish_engine.run(job_id)

    assert captured["body"]["type"] == "now"
    assert state.load(job_id)["publish_status"]["status"] == "published"


def test_degrades_on_request_failure(job, monkeypatch):
    monkeypatch.setattr(settings, "POSTIZ_API_KEY", "key")
    monkeypatch.setattr(settings, "POSTIZ_INTEGRATION_IDS", {"tiktok": "abc", "x": "def"})

    def raise_error(*args, **kwargs):
        raise publish_engine.requests.ConnectionError("no route to host")

    monkeypatch.setattr(publish_engine.requests, "post", raise_error)
    publish_engine.run(job)
    status = state.load(job)["publish_status"]
    assert status["status"] == "failed"
    assert "no route to host" in status["detail"]
