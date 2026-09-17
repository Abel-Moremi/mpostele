# FFmpeg Notes

FFmpeg handles the last mile of the video path: taking RIFE-interpolated frames plus the audio track and producing the final deliverable, without adding any GPU inference cost of its own.

## Useful techniques

- assembling interpolated frame sequences back into a video stream
- multiplexing the narration/audio track onto the visual stream
- `h264_nvenc` for hardware-accelerated encoding where available
- trim/concat for joining sequential scenes

## Constraints

FFmpeg's own memory footprint is very low, but it runs *after* the diffusion and interpolation stages have already used and released VRAM — sequence it last in the subprocess chain so it never overlaps with a GPU-heavy stage.

## Related notes

- [[03 Workflow/03 Video Rendering Path]]
- [[03 Workflow/05 Platform Adaptation & Export]]
- [[04 Research/02 Tool Comparison]]
