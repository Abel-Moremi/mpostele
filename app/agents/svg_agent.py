"""SVG Decoration Agent: chooses a decorative accent, or none - never draws it.

Shared across both media types, same role quality_inspector.py plays - runs
once per job, independent of composition_agent/poster_layout_agent (no
coordination needed: every scene centers its text with generous padding, and
the decoration always renders in a fixed corner slot per component, so it
can't collide with the main content by construction).

Produces a choice from a fixed generator set (never raw SVG/JSX - see
app/media/svg_engine.py for why) plus bounded, named-palette parameters, or a
choice to reuse an asset already in the library, or no decoration at all.
"""
import json

from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

DESIGN_DIR = settings.REVIDEO_PROJECT_DIR / "public" / "design"
PALETTE_PATH = DESIGN_DIR / "palette.json"
MANIFEST_PATH = DESIGN_DIR / "generated" / "manifest.json"

# Keep in sync with app/media/svg_engine.py's GENERATORS and
# app/agents/svg_validator.py's ALLOWED_GENERATORS/REQUIRED_PARAMS.
PROMPT = """You are a decoration director choosing at most one small decorative accent for a
piece of marketing content. Respond with ONLY a JSON object matching one of these three shapes -
no prose, no markdown fences.

If no accent suits this content, or the scene is already visually busy enough:
{{"action": "none"}}

If an existing library asset (listed below) already fits:
{{"action": "reuse", "asset_id": "<id from the library>"}}

If a new one should be made, using ONLY one of these generators and ONLY these color names:
- "sparkle-cluster": params {{"color": "<palette color name>", "size": "small"|"medium"|"large"}}
- "gradient-blob": params {{"colorFrom": "<palette color name>", "colorTo": "<palette color name>"}}
- "moon-accent": params {{"color": "<palette color name>"}}
- "divider": params {{"color": "<palette color name>"}}
{{"action": "generate", "generator": "<one of the four above>", "params": {{...}}}}

Available palette colors: {palette_names}
Existing library assets: {library_assets}

Content topic: {topic}
Tone: {tone}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)

    palette = json.loads(PALETTE_PATH.read_text(encoding="utf-8")) if PALETTE_PATH.exists() else {}
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {"assets": []}
    library_summary = [{"id": a["id"], "generator": a["generator"]} for a in manifest["assets"]] or "none yet"

    response = call_ollama(
        PROMPT.format(
            palette_names=list(palette.keys()) or "none configured",
            library_assets=json.dumps(library_summary),
            topic=job_state["strategy_brief"]["topic"],
            tone=job_state["input_brief"].get("tone", ""),
        )
    )
    decoration_spec = extract_json(response)
    state.update(job_id, "decoration_spec", decoration_spec, current_step="SVG_VALIDATOR")


if __name__ == "__main__":
    run(parse_job_arg())
