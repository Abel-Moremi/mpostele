# FFmpeg Notes

FFmpeg is one of the most important tools in the workflow because it allows motion, composition, exporting, and encoding without heavy GPU inference.

## Useful techniques

- zoompan filter for Ken Burns effect -- implemented as the `MOTION_PRESETS` in `pipeline/first_render.py` (`zoom_in`, `zoom_out`, `pan_left_to_right`, `pan_right_to_left`, `pan_top_to_bottom`, `pan_bottom_to_top`, `static`), selectable via `--motion-preset`
- overlay composition for animated text and graphics
- trim and concat for sequential scenes
- `h264_nvenc` for hardware acceleration where available

## Example ideas

- create a slow push-in motion for product screenshots
- combine a title card and voiceover audio
- fade between scenes and transitions

## Constraints

On low memory hardware, prefer simple filters and avoid heavy multi-stream effects unless necessary.

## Related notes

- [[03 Workflow/04 Compositing]]
- [[03 Workflow/05 Final Export]]
- [[04 Research/02 Tool Comparison]]
