# Compositing

This stage combines all generated media into a unified final video.

## Responsibilities

- combine animation layers and screenshot motion
- add lower-thirds, overlays, and title cards
- sync voiceover with visual events
- encode the final media for output

## Tools

- FFmpeg for merging clips and audio
- `h264_nvenc` where GPU acceleration is available
- optional alpha-channel overlay support for transparent motion graphics

## Typical outputs

- final short video
- vertical export for social platforms
- preview renders for testing

## Related notes

- [[03 Workflow/02 Animation Engine]]
- [[03 Workflow/05 Final Export]]
- [[04 Research/03 FFmpeg Notes]]
