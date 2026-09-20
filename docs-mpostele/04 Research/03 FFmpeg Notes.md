# FFmpeg Notes

FFmpeg handles the last mile of the video path: taking Remotion's rendered clip plus the audio track and producing the final deliverable. There's no interpolation step feeding it any more (RIFE was removed along with the diffusion paths it served) — it encodes straight from `artifacts.raw_clip`.

## Useful techniques

- multiplexing the narration/audio track onto the Remotion-rendered visual stream
- trim/concat for joining sequential scenes

## Encoder choice

Default is `libx264` (software) — see `app/config/settings.py`'s `VIDEO_ENCODER`. `h264_nvenc` (hardware-accelerated) is available via the same setting, but **failed on the actual dev machine's driver** (nvenc API 13.1 required, 13.0 found) — real measured failure, not a guess. Software encoding has no driver dependency and is the safer out-of-the-box default now that there's no VRAM budget forcing the hardware-encode choice.

## Related notes

- [[03 Workflow/03 Video Rendering Path]]
- [[03 Workflow/05 Platform Adaptation & Export]]
- [[04 Research/02 Tool Comparison]]
