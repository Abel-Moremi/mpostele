"""Fixed brand identity, resolved from revideo/public/design/palette.json and
design.md's type table.

composition_agent.py and poster_layout_agent.py used to invent their own hex
colors (their prompts' own example values were an unrelated navy/blue,
"#0B1220"/"#2563EB") and never set fontFamily at all, so nothing they
produced matched Dreamcraftr's actual cream/terracotta/charcoal palette or
its Crimson Pro/Inter type system (revideo/src/fonts.ts's HEADLINE_FONT/
BODY_FONT sat unused). design.md is explicit that this is a fixed identity
for marketing content - "Warm paper, terracotta action" - not a per-job
creative choice, so it's resolved here in Python rather than left to a small
model to reinvent, the same reasoning app/agents/svg_agent.py already
applies to decoration colors.
"""
import json

from app.config import settings

_PALETTE_PATH = settings.REVIDEO_PROJECT_DIR / "public" / "design" / "palette.json"
_palette = json.loads(_PALETTE_PATH.read_text(encoding="utf-8"))

# "Cream stack - cream is the page" / "Terracotta - the only color a primary
# action is ever painted" / "Charcoal - all body text" (design.md).
BACKGROUND_COLOR = _palette["cream"]
ACCENT_COLOR = _palette["terracotta"]
TEXT_COLOR = _palette["charcoal"]

# "Button ... Primary is terracotta/white" (design.md) - ink that sits on top
# of ACCENT_COLOR (a CTA pill, an Outro accent bar), not on the page itself.
ON_ACCENT_COLOR = "#FFFFFF"

# Type table: headlines/CTAs in Crimson Pro, body copy in Inter.
HEADLINE_FONT = "Crimson Pro"
BODY_FONT = "Inter"
