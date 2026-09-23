# Platform Adaptation & Export

The final stage before artifacts are flushed to disk.

## Platform Adaptor Agent

Reformats the raw script and captions into platform-native copy for TikTok, Instagram, X, and LinkedIn, using the already-generated `content` and `strategy_brief` blocks from `state.json`.

## Output goals

- correct aspect ratio for the target platform (`9:16`, `1:1`, etc., as set by `aspect_ratio` in `state.json`)
- consistent quality and audio levels for video output
- captions matched to each platform's tone and length conventions

## Final artifacts

- `artifacts.final_poster` or `artifacts.rendered_video`, depending on `media_type`
- job status flipped to a terminal state once artifacts are confirmed written

## Cleanup

Intermediate render props and temp files are purged at this point — only the final output artifacts remain in the destination directory.

## Publish engine (opt-in)

`app/media/publish_engine.py` runs last, after platform adaptation, only when a job is started with `--publish` or `--publish-now`. It schedules the finished artifact to social platforms through a self-hosted or hosted [Postiz](https://docs.postiz.com/public-api) instance, one post per platform that has both a caption in `platform_copy` and a connected Postiz integration ID (`POSTIZ_INTEGRATION_*` env vars in `app/config/settings.py`).

- **Postiz over Mixpost:** Postiz's free/self-hosted tier covers all four platforms `platform_adaptor.py` already writes copy for; Mixpost's open-core edition gates broader platform support behind its paid tier.
- **A real draft by default, not immediate:** the default (`--publish`) sends `"type": "draft"`, confirmed against the pinned v2.11.3 source (`posts.service.ts`) to never enqueue a publish job — it only goes out once a human promotes it from the Postiz UI. `--publish-now` sends `"type": "now"` and skips that review step entirely.
- **Account connection is manual:** Postiz's OAuth flow for connecting a social account happens once, in its own dashboard — this pipeline only submits/schedules to already-connected integration IDs, it doesn't do account onboarding.
- **Never blocks a render:** a missing API key, an unconfigured platform, or a Postiz outage all degrade to a recorded `job_state["publish_status"]`, the same proportionate-degradation shape as `strategy_agent.py`'s mood tagging — a publish failure never undoes an already-rendered video/poster.

## Related notes

- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[06 Operations/02 Troubleshooting]]
