"""SVG decoration engine: fixed, hand-written generators + the reuse library.

Runs as its own subprocess, same contract as video_engine.py/poster_engine.py.
Reads decoration_spec from state (svg_agent.py's data-only choice: which
generator, or which existing library asset to reuse) and either resolves an
existing file or writes a brand-new one - the LLM never produces markup
itself, only picks a generator name and a couple of bounded parameters
(app/agents/svg_validator.py has already checked those before this runs).

Revideo is a raster/video renderer, not an SVG exporter, so the actual .svg
files are written here in Python, then just displayed by Revideo via
<Img src={decorationSrc}>, the same way it already displays logo.png.
"""
import hashlib
import json
import math
import random
import time
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

DESIGN_DIR = settings.REVIDEO_PROJECT_DIR / "public" / "design"
GENERATED_DIR = DESIGN_DIR / "generated"
MANIFEST_PATH = GENERATED_DIR / "manifest.json"
PALETTE_PATH = DESIGN_DIR / "palette.json"


def load_palette() -> dict:
    if not PALETTE_PATH.exists():
        return {}
    return json.loads(PALETTE_PATH.read_text(encoding="utf-8"))


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"assets": []}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _with_alpha(hex_color: str, alpha: float) -> str:
    """Blends hex_color toward white by (1 - alpha) - used for the muted
    cloud tone in moon-accent so it doesn't need a second palette color."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = (round(c * alpha + 255 * (1 - alpha)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _sparkle_path(cx: float, cy: float, r_outer: float, r_inner: float) -> str:
    """A 4-point twinkle/sparkle glyph - outer points at N/E/S/W, concave
    inner points at the diagonals, like the sparkles already in logo.png."""
    points = []
    for i in range(8):
        angle = math.pi / 2 * (i // 2) + (math.pi / 4 if i % 2 else 0)
        r = r_inner if i % 2 else r_outer
        points.append((cx + r * math.sin(angle), cy - r * math.cos(angle)))
    d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in points) + " Z"
    return d


def generate_sparkle_cluster(params: dict, palette: dict, seed: int) -> str:
    color = palette.get(params.get("color"), params.get("color", "#BE7C6C"))
    size = {"small": 0.7, "medium": 1.0, "large": 1.4}.get(params.get("size", "medium"), 1.0)
    rng = random.Random(seed)
    sparkles = []
    positions = [(100, 100, 26), (60, 60, 12), (145, 55, 9), (150, 130, 15)]
    for cx, cy, r in positions:
        jitter_x, jitter_y = rng.uniform(-6, 6), rng.uniform(-6, 6)
        opacity = rng.uniform(0.75, 1.0)
        path = _sparkle_path(cx + jitter_x, cy + jitter_y, r * size, r * size * 0.22)
        sparkles.append(f'<path d="{path}" fill="{color}" opacity="{opacity:.2f}" />')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
        + "".join(sparkles)
        + "</svg>"
    )


def generate_gradient_blob(params: dict, palette: dict, seed: int) -> str:
    color_from = palette.get(params.get("colorFrom"), params.get("colorFrom", "#BE7C6C"))
    color_to = palette.get(params.get("colorTo"), params.get("colorTo", "#EFE3D0"))
    rng = random.Random(seed)

    cx, cy, base_r, points = 100, 100, 70, 10
    radii = [base_r * rng.uniform(0.75, 1.15) for _ in range(points)]
    coords = []
    for i, r in enumerate(radii):
        angle = 2 * math.pi * i / points
        coords.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    # Catmull-rom through the ring of points, converted to cubic beziers -
    # the same organic-blob technique react-svg-blob uses, reimplemented
    # here in Python so no JS dependency is needed for a static SVG file.
    d = f"M {coords[0][0]:.2f} {coords[0][1]:.2f} "
    n = len(coords)
    for i in range(n):
        p0 = coords[(i - 1) % n]
        p1 = coords[i]
        p2 = coords[(i + 1) % n]
        p3 = coords[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C {c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} {p2[0]:.2f} {p2[1]:.2f} "
    d += "Z"

    gradient_id = f"grad{abs(seed) % 10000}"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
        f'<defs><linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{color_from}" />'
        f'<stop offset="100%" stop-color="{color_to}" />'
        "</linearGradient></defs>"
        f'<path d="{d}" fill="url(#{gradient_id})" />'
        "</svg>"
    )


def generate_moon_accent(params: dict, palette: dict, seed: int) -> str:
    color = palette.get(params.get("color"), params.get("color", "#BE7C6C"))
    cloud_color = _with_alpha(color, 0.35)
    rng = random.Random(seed)
    sparkle = ""
    if rng.random() > 0.4:
        sparkle = f'<path d="{_sparkle_path(150, 40, 10, 2.5)}" fill="{color}" opacity="0.8" />'
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
        "<mask id=\"crescent\">"
        '<rect x="0" y="0" width="200" height="200" fill="white" />'
        '<circle cx="95" cy="70" r="42" fill="black" />'
        "</mask>"
        f'<circle cx="115" cy="70" r="48" fill="{color}" mask="url(#crescent)" />'
        f"{sparkle}"
        f'<circle cx="70" cy="150" r="30" fill="{cloud_color}" />'
        f'<circle cx="105" cy="160" r="36" fill="{cloud_color}" />'
        f'<circle cx="145" cy="150" r="28" fill="{cloud_color}" />'
        "</svg>"
    )


def generate_divider(params: dict, palette: dict, seed: int) -> str:
    color = palette.get(params.get("color"), params.get("color", "#BE7C6C"))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 40">'
        f'<path d="M 10 20 Q 85 0 150 20 T 290 20" fill="none" stroke="{color}" '
        'stroke-width="2.5" stroke-linecap="round" />'
        "</svg>"
    )


GENERATORS = {
    "sparkle-cluster": generate_sparkle_cluster,
    "gradient-blob": generate_gradient_blob,
    "moon-accent": generate_moon_accent,
    "divider": generate_divider,
}


def resolve(decoration_spec: dict) -> str | None:
    """Returns the decoration's path relative to revideo/public/, or None."""
    action = decoration_spec.get("action", "none")
    if action == "none":
        return None

    manifest = load_manifest()

    if action == "reuse":
        asset_id = decoration_spec["asset_id"]
        for asset in manifest["assets"]:
            if asset["id"] == asset_id:
                return asset["file"]
        return None

    generator_name = decoration_spec["generator"]
    params = decoration_spec.get("params", {})
    palette = load_palette()
    seed = int(hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest(), 16) % (2**31)

    svg_markup = GENERATORS[generator_name](params, palette, seed)

    short_hash = hashlib.sha1(f"{generator_name}{params}{seed}".encode()).hexdigest()[:8]
    param_slug = "-".join(str(v) for v in params.values()) or "default"
    asset_id = f"{generator_name}-{param_slug}-{short_hash}"
    file_name = f"{asset_id}.svg"

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_DIR / file_name).write_text(svg_markup, encoding="utf-8")

    manifest["assets"].append(
        {
            "id": asset_id,
            "generator": generator_name,
            "params": params,
            "file": f"generated/{file_name}",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    save_manifest(manifest)

    return f"generated/{file_name}"


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    decoration_spec = job_state.get("decoration_spec", {"action": "none"})
    decoration_asset = resolve(decoration_spec)

    job_state = state.load(job_id)
    job_state["decoration_asset"] = f"design/{decoration_asset}" if decoration_asset else None
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
