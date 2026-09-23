"""Publish engine: sends the finished artifact to social platforms via a
self-hosted or hosted Postiz instance (docs.postiz.com/public-api).

Runs last, after platform_adaptor.py, and only when a job opts in
(app.main's --publish/--publish-now flags -> job_state["publish_now"], set
at job creation - see orchestrator.py). Best-effort, same degradation shape
as strategy_agent.py's mood tagging: a Postiz outage, a missing API key, or
a platform with no connected integration ID should never undo an
already-rendered video/poster, so every failure here degrades to a recorded
publish_status rather than raising.

Default (--publish) creates a real Postiz draft ("type": "draft") rather
than an immediate or scheduled post - confirmed directly against the
v2.11.3 source (posts.service.ts) that a draft's publish job is never
enqueued, so it only goes out once a human promotes it from the Postiz UI.
--publish-now ("type": "now") skips that review step entirely.
"""
from datetime import datetime, timezone
from pathlib import Path

import requests

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state


def _upload_media(media_path: Path) -> dict:
    with open(media_path, "rb") as f:
        response = requests.post(
            f"{settings.POSTIZ_API_URL}/upload",
            headers={"Authorization": settings.POSTIZ_API_KEY},
            files={"file": (media_path.name, f)},
            timeout=settings.POSTIZ_REQUEST_TIMEOUT_SECONDS,
        )
    response.raise_for_status()
    return response.json()


def _configured_platforms(platform_copy: dict) -> dict:
    """Captions for platforms that also have a Postiz integration ID
    configured - a platform missing either is skipped, not fatal, since
    OAuth-connecting an account is a manual step in Postiz's own dashboard
    this pipeline can't perform for you."""
    configured = {}
    for platform, caption in platform_copy.items():
        if settings.POSTIZ_INTEGRATION_IDS.get(platform):
            configured[platform] = caption
        else:
            print(f"Warning: no Postiz integration configured for '{platform}', skipping.")
    return configured


def _build_posts(configured: dict, media: dict) -> list:
    return [
        {
            "integration": {"id": settings.POSTIZ_INTEGRATION_IDS[platform]},
            "value": [{"content": caption, "image": [media]}],
            "settings": {"__type": platform},
        }
        for platform, caption in configured.items()
    ]


def run(job_id: str) -> None:
    job_state = state.load(job_id)

    if not settings.POSTIZ_API_KEY:
        _finish(job_id, "skipped", "POSTIZ_API_KEY not configured")
        return

    media_path_str = job_state["artifacts"].get("rendered_video") or job_state["artifacts"].get(
        "final_poster"
    )
    if not media_path_str:
        _finish(job_id, "skipped", "no rendered artifact to publish")
        return

    configured = _configured_platforms(job_state.get("platform_copy") or {})
    if not configured:
        _finish(job_id, "skipped", "no platforms with a configured integration ID")
        return

    try:
        media = _upload_media(Path(media_path_str))
        posts = _build_posts(configured, media)

        publish_now = job_state.get("publish_now", False)
        # "date" is required by Postiz's DTO regardless of type, but a
        # draft's date is purely informational (createPost only reads it
        # for "now"/"schedule" - see posts.service.ts) - "now" is a fine
        # placeholder either way.
        response = requests.post(
            f"{settings.POSTIZ_API_URL}/posts",
            headers={
                "Authorization": settings.POSTIZ_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "type": "now" if publish_now else "draft",
                "date": datetime.now(timezone.utc).isoformat(),
                "shortLink": False,
                "tags": [],
                "posts": posts,
            },
            timeout=settings.POSTIZ_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        _finish(
            job_id,
            "published" if publish_now else "drafted",
            f"{len(posts)} platform(s)",
        )
    except (requests.RequestException, OSError) as exc:
        print(f"Warning: publish to Postiz failed, continuing without it: {exc}")
        _finish(job_id, "failed", str(exc))


def _finish(job_id: str, status: str, detail: str) -> None:
    state.update(job_id, "publish_status", {"status": status, "detail": detail})


if __name__ == "__main__":
    run(parse_job_arg())
