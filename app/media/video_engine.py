"""Video rendering engine: Remotion (code-driven motion graphics, no diffusion model).

Runs as its own subprocess - reads composition_spec from state, shells out to
the Remotion CLI in the sibling remotion/ Node project, and writes the
result back to state. Also derives and renders a cover image from the same
composition_spec (see derive_cover_props) - reused as both a standalone
output file and (in encode.py) an embedded MP4 cover stream.
"""
import json
import shutil
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.media.remotion_cli import run_remotion
from app.orchestrator import state

# Poster prop -> TitleReveal/Outro scene prop it's read from. Mechanical
# reshape of data composition_validator.py has already checked - not agent
# output, so no new validator is needed.
_COVER_FIELD_MAP = [
    ("TitleReveal", "text", "headline"),
    ("TitleReveal", "backgroundColor", "backgroundColor"),
    ("TitleReveal", "accentColor", "accentColor"),
    ("TitleReveal", "textColor", "headlineColor"),
    ("TitleReveal", "fontFamily", "headlineFontFamily"),
    ("Outro", "text", "ctaText"),
    ("Outro", "textColor", "ctaTextColor"),
    ("Outro", "fontFamily", "ctaFontFamily"),
    ("Outro", "logoSrc", "logoSrc"),
]


def derive_cover_props(composition_spec: dict) -> dict:
    scenes_by_component = {s["component"]: s["props"] for s in composition_spec["scenes"]}

    cover_props = {}
    for component, source_key, cover_key in _COVER_FIELD_MAP:
        props = scenes_by_component.get(component, {})
        if source_key in props:
            cover_props[cover_key] = props[source_key]

    for component in ("TitleReveal", "Outro"):
        decoration_src = scenes_by_component.get(component, {}).get("decorationSrc")
        if decoration_src:
            cover_props["decorationSrc"] = decoration_src
            break

    return cover_props


def render(job_state: dict, output_dir: Path) -> Path:
    composition_spec = json.loads(json.dumps(job_state["composition_spec"]))  # deep copy before mutating
    decoration_asset = job_state.get("decoration_asset")
    if decoration_asset:
        # Only TitleReveal/Outro have a reserved corner slot for this (see
        # remotion/src/scenes/) - CaptionOverlay's word-by-word reveal has no
        # safe spot for a static accent. Attach to the first scene that can
        # take it, so every video gets at most one decoration, not one per
        # eligible scene.
        for scene in composition_spec["scenes"]:
            if scene["component"] in ("TitleReveal", "Outro"):
                scene["props"]["decorationSrc"] = decoration_asset
                break

    output_dir.mkdir(parents=True, exist_ok=True)
    props_path = output_dir / "composition_props.json"
    props_path.write_text(json.dumps(composition_spec), encoding="utf-8")

    raw_clip = output_dir / "raw_clip.mp4"
    run_remotion(["remotion", "render", settings.REMOTION_COMPOSITION_ID, str(raw_clip), "--props", str(props_path)])
    return raw_clip, composition_spec


def render_cover(composition_spec: dict, output_dir: Path) -> Path:
    cover_props = derive_cover_props(composition_spec)

    output_dir.mkdir(parents=True, exist_ok=True)
    props_path = output_dir / "cover_props.json"
    props_path.write_text(json.dumps(cover_props), encoding="utf-8")

    cover_png = output_dir / "cover.png"
    run_remotion(
        ["remotion", "still", settings.REMOTION_POSTER_COMPOSITION_ID, str(cover_png), "--props", str(props_path)]
    )
    return cover_png


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    output_dir = settings.TMP_DIR / job_id
    raw_clip, composition_spec = render(job_state, output_dir)
    raw_cover = render_cover(composition_spec, output_dir)

    final_cover = settings.OUTPUT_DIR / job_id / "cover.png"
    final_cover.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(raw_cover, final_cover)

    job_state = state.load(job_id)
    job_state["artifacts"]["raw_clip"] = str(raw_clip)
    job_state["artifacts"]["cover_image"] = str(final_cover)
    job_state["current_step"] = "ENCODE"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
