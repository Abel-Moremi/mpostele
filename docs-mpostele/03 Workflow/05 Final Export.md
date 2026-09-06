# Final Export

The final export stage packages the completed video for social distribution and review.

## Output goals

- stable final render
- correct aspect ratio for platform requirements
- consistent quality and audio levels
- suitable duration for short-form video traffic

## Platforms

This project targets export styles suitable for:

- YouTube Shorts
- Instagram Reels
- TikTok
- LinkedIn style product clips

## Implemented export flow

`pipeline/render_job.py` normalizes every scene before concatenation so the final stream-copy pass receives matching H.264 video and AAC stereo audio. Scenes without audio receive a silent 48 kHz track. This avoids expensive final re-encoding while keeping scene boundaries compatible.

Available presets are:

- `landscape_720p`: 1280x720
- `vertical_1080p`: 1080x1920
- `square_1080p`: 1080x1080

Custom manifest width and height values may override a preset. Inputs preserve their aspect ratio and receive black padding where their shape differs from the export canvas. Intermediate normalized scenes remain in the job work directory.

## Export considerations

- use the vertical preset for Shorts, Reels, and TikTok, or square/landscape where appropriate
- keep file sizes manageable for local storage
- test playback and upload compatibility on target platforms before publishing
- consider a future hardware-encoder option only after the CPU path is verified and remains the portable default

## Related notes

- [[03 Workflow/04 Compositing]]
- [[06 Operations/02 Troubleshooting]]
