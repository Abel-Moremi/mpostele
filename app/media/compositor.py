"""Pillow vector/text compositor for the poster path.

No GPU involved - safe to run in the same subprocess right after the SD1.5
pipeline is deleted and flushed (see app/media/poster_engine.py).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


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

    y_offset = start_y
    for line in lines:
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
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
            bbox = font.getbbox(layer["text"])
            pad_x, pad_y = 40, 20
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x, y = layer["position"]["x"], layer["position"]["y"]
            draw.rounded_rectangle(
                [x - w // 2 - pad_x, y - h // 2 - pad_y, x + w // 2 + pad_x, y + h // 2 + pad_y],
                radius=16,
                fill=layer["bg_color"],
            )
            draw.text((x - w // 2, y - h // 2), layer["text"], font=font, fill=layer["text_color"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
