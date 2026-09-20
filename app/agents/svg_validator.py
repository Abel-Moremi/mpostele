"""SVG Validator Agent: validates the decoration choice before svg_engine acts on it.

Deterministic checks rather than another LLM call, same rationale as
quality_inspector.py/composition_validator.py/poster_validator.py. Exits
non-zero on failure so the orchestrator's subprocess check can drive the
retry loop - on final failure the orchestrator falls through to no
decoration at all (never blocks the job over a decorative accent).
"""
import json

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

DESIGN_DIR = settings.REMOTION_PROJECT_DIR / "public" / "design"
PALETTE_PATH = DESIGN_DIR / "palette.json"
MANIFEST_PATH = DESIGN_DIR / "generated" / "manifest.json"

# Keep in sync with app/media/svg_engine.py's GENERATORS and
# app/agents/svg_agent.py's PROMPT.
REQUIRED_PARAMS = {
    "sparkle-cluster": {"color"},
    "gradient-blob": {"colorFrom", "colorTo"},
    "moon-accent": {"color"},
    "divider": {"color"},
}


def check(job_state: dict) -> list:
    problems = []
    spec = job_state.get("decoration_spec", {})
    action = spec.get("action")

    if action == "none":
        return problems

    if action == "reuse":
        asset_id = spec.get("asset_id")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {"assets": []}
        if not any(a["id"] == asset_id for a in manifest["assets"]):
            problems.append(f"reuse asset_id {asset_id!r} not found in the library manifest")
        return problems

    if action == "generate":
        generator = spec.get("generator")
        if generator not in REQUIRED_PARAMS:
            problems.append(f"unknown generator {generator!r}")
            return problems

        params = spec.get("params", {})
        missing = REQUIRED_PARAMS[generator] - params.keys()
        if missing:
            problems.append(f"generator {generator!r}: missing params {sorted(missing)}")

        palette = json.loads(PALETTE_PATH.read_text(encoding="utf-8")) if PALETTE_PATH.exists() else {}
        color_keys = {"color", "colorFrom", "colorTo"} & params.keys()
        for key in color_keys:
            if params[key] not in palette:
                problems.append(f"generator {generator!r}: {key} {params[key]!r} is not a palette color")
        return problems

    return [f"unknown action {action!r}"]


def run(job_id: str) -> bool:
    job_state = state.load(job_id)
    problems = check(job_state)
    passed = not problems
    state.update(job_id, "decoration_check", {"passed": passed, "problems": problems})
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run(parse_job_arg()) else 1)
