# Pillow Compositor Notes

> **Superseded.** The Pillow-based poster compositor was removed in favor of a Remotion `still` render (`remotion/src/scenes/Poster.tsx`) — see [[03 Workflow/02 Poster Rendering Path]]. Kept as the design record for the real edge cases found while it was in use.

Pillow was the vector/text compositor for the poster path — it never touched the GPU, so it could run right after the SD1.5 background subprocess exited with no VRAM concerns.

## Word-wrap implementation

```python
from PIL import ImageDraw, ImageFont

def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                      max_width: int, start_x: int, start_y: int, fill: str, align: str = "center"):
    """Wraps text using font.getbbox() to stay within max_width."""
    words = text.split(" ")
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = font.getbbox(test_line)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    lines.append(" ".join(current_line))

    y_offset = start_y
    for line in lines:
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]

        x_pos = start_x
        if align == "center":
            x_pos = start_x - (line_width // 2)

        draw.text((x_pos, y_offset), line, font=font, fill=fill)
        y_offset += line_height + 10
```

## Known edge cases (not yet handled)

- if the **first** word alone is wider than `max_width`, `current_line` is empty when the `else` branch fires, so an empty string gets appended as a spurious first line
- a single token wider than `max_width` (long URL, hashtag, unbroken word) is drawn at full width with no font-size shrink or truncation fallback — wrapping alone cannot guarantee it stays inside the box
- line height is recomputed per line from that line's own bbox, so spacing can vary slightly line to line depending on ascenders/descenders

## Use cases

- poster headline and body text, wrapped against `poster_layout.layers[].max_width_px`
- badges (`button_badge` layer type) and logo placement
- any other vector shape needed on top of the SD1.5 background

## Related notes

- [[03 Workflow/02 Poster Rendering Path]]
- [[04 Research/02 Tool Comparison]]
