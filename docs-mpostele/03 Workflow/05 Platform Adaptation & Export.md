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

Intermediate frame sequences, raw diffusion dumps, and temp audio clips are purged at this point — only the final output artifacts remain in the destination directory.

## Related notes

- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[06 Operations/02 Troubleshooting]]
