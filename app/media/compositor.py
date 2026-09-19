"""Pillow vector/text compositor for the poster path.

No GPU involved - safe to run in the same subprocess right after the SD1.5
pipeline is deleted and flushed (see app/media/poster_engine.py).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _wrap_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Wraps text against max_width using font.getbbox() for measurement.

    A single word wider than max_width is placed on its own line instead of
    overflowing silently or leaving a spurious blank line ahead of it.
    """
    words = text.split(" ")
    lines = []
    current_line = []

    for word in words:
        candidate = current_line + [word]
        bbox = font.getbbox(" ".join(candidate))
        if bbox[2] - bbox[0] <= max_width or not current_line:
            current_line = candidate
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _measure_lines(lines: list, font: ImageFont.FreeTypeFont, line_spacing: int = 10):
    """Returns (block_width, block_height, [(line, width, height), ...])."""
    measured = []
    for line in lines:
        bbox = font.getbbox(line)
        measured.append((line, bbox[2] - bbox[0], bbox[3] - bbox[1]))
    block_width = max((w for _, w, _ in measured), default=0)
    block_height = sum(h for _, _, h in measured) + line_spacing * max(len(measured) - 1, 0)
    return block_width, block_height, measured


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    start_x: int,
    start_y: int,
    fill: str,
    align: str = "center",
) -> None:
    lines = _wrap_lines(text, font, max_width)
    y_offset = start_y
    for line, line_width, line_height in _measure_lines(lines, font)[2]:
        x_pos = start_x - (line_width // 2) if align == "center" else start_x
        draw.text((x_pos, y_offset), line, font=font, fill=fill)
        y_offset += line_height + 10


def compose_poster(background_path: Path, layout: dict, output_path: Path, font_dir: Path) -> Path:
    image = Image.open(background_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    for layer in layout.get("layers", []):
        if layer["type"] == "text":
            font = ImageFont.truetype(str(font_dir / f"{layer['font']}.ttf"), layer["font_size"])
            draw_wrapped_text(
                draw,
                layer["content"],
                font,
                layer["max_width_px"],
                layer["position"]["x"],
                layer["position"]["y"],
                layer["color"],
                layer.get("align", "center"),
            )
        elif layer["type"] == "button_badge":
            font = ImageFont.truetype(str(font_dir / "Inter-Bold.ttf"), 36)
            pad_x, pad_y = 40, 20
            x, y = layer["position"]["x"], layer["position"]["y"]
            # Wrap badge text against the actual image width regardless of
            # what the layout agent asked for - a badge is meant to be a
            # short label, but nothing guarantees the model kept it short
            # (a real run used a full call-to-action sentence here and it
            # drew off both edges of the canvas before this fix).
            max_text_width = max(image.width - 2 * pad_x - 40, 40)
            lines = _wrap_lines(layer["text"], font, max_text_width)
            block_width, block_height, measured = _measure_lines(lines, font)

            draw.rounded_rectangle(
                [
                    x - block_width // 2 - pad_x,
                    y - block_height // 2 - pad_y,
                    x + block_width // 2 + pad_x,
                    y + block_height // 2 + pad_y,
                ],
                radius=16,
                fill=layer["bg_color"],
            )
            y_offset = y - block_height // 2
            for line, line_width, line_height in measured:
                draw.text((x - line_width // 2, y_offset), line, font=font, fill=layer["text_color"])
                y_offset += line_height + 10

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
