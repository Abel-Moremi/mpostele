"""Video rendering engine: Revideo (code-driven motion graphics, no diffusion model).

Runs as its own subprocess - reads composition_spec from state, shells out to
the Revideo render CLI in the sibling revideo/ Node project, and writes the
result back to state. Also derives and renders a cover image from the same
composition_spec (see derive_cover_props) - reused as both a standalone
output file and (in encode.py) an embedded MP4 cover stream.
"""
import json
import shutil
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.media.revideo_cli import run_revideo
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
# render.mjs's posterPropsSchema requires exactly these - composition_validator.py
# requires a TitleReveal and an Outro scene to be present, but (like every other
# gate here) still renders after MAX_QUALITY_RETRIES exhausted even if a check
# failed, so this can't be assumed - see derive_cover_props/render_cover below.
_REQUIRED_COVER_PROPS = {"headline", "ctaText", "backgroundColor", "accentColor"}


def derive_cover_props(composition_spec: dict) -> dict | None:
    """None means the spec doesn't have what a cover needs (missing
    TitleReveal/Outro, or one of them missing a required prop) - the caller
    skips the cover instead of handing render.mjs's poster schema something
    it will reject anyway."""
    scenes_by_component = {}
    for s in composition_spec.get("scenes", []):
        if isinstance(s, dict) and isinstance(s.get("props"), dict):
            scenes_by_component[s.get("component")] = s["props"]

    cover_props = {}
    for component, source_key, cover_key in _COVER_FIELD_MAP:
        props = scenes_by_component.get(component, {})
        if source_key in props:
            cover_props[cover_key] = props[source_key]

    if not _REQUIRED_COVER_PROPS <= cover_props.keys():
        return None

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
        # revideo/src/scenes/) - CaptionOverlay's progressive reveal has no
        # safe spot for a static accent. Attach to the first scene that can
        # take it, so every video gets at most one decoration, not one per
        # eligible scene.
        for scene in composition_spec["scenes"]:
            # .get() rather than scene["props"] - composition_validator.py
            # retries composition_agent up to MAX_QUALITY_RETRIES times on a
            # malformed scene (e.g. missing "props") but still renders
            # whatever's left after that, by design; this loop shouldn't be
            # the thing that turns a validator-reported problem into an
            # unhandled crash instead of a controlled Revideo-side failure.
            if scene.get("component") in ("TitleReveal", "Outro") and isinstance(scene.get("props"), dict):
                scene["props"]["decorationSrc"] = decoration_asset
                break

    output_dir.mkdir(parents=True, exist_ok=True)
    props_path = output_dir / "composition_props.json"
    props_path.write_text(json.dumps(composition_spec), encoding="utf-8")

    raw_clip = output_dir / "raw_clip.mp4"
    run_revideo("video", props_path, raw_clip)
    return raw_clip, composition_spec


def render_cover(composition_spec: dict, output_dir: Path) -> Path | None:
    cover_props = derive_cover_props(composition_spec)
    if cover_props is None:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    props_path = output_dir / "cover_props.json"
    props_path.write_text(json.dumps(cover_props), encoding="utf-8")

    cover_png = output_dir / "cover.png"
    run_revideo("poster", props_path, cover_png)
    return cover_png


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    output_dir = settings.TMP_DIR / job_id
    raw_clip, composition_spec = render(job_state, output_dir)
    raw_cover = render_cover(composition_spec, output_dir)

    final_cover = None
    if raw_cover is not None:
        final_cover = settings.OUTPUT_DIR / job_id / "cover.png"
        final_cover.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(raw_cover, final_cover)

    job_state = state.load(job_id)
    job_state["artifacts"]["raw_clip"] = str(raw_clip)
    job_state["artifacts"]["cover_image"] = str(final_cover) if final_cover else None
    job_state["current_step"] = "ENCODE"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
