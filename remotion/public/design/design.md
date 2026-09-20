# Designing with Dreamcraftr

Practical rules for building new surfaces. `README.md` explains *why* the brand
looks this way; this file is *how* to apply it. When the two disagree, the
production codebase (`dreamcraftr/dreamcraftr`) wins.

Load `colors_and_type.css` first. It carries every token, both font stacks,
and base element styles.

---

## The one-paragraph brief

Warm paper, terracotta action, serif voice. Nothing is pure white, nothing is
pure black, nothing snaps. Every surface should feel like it was printed on
good stock and left on a table near a window. If a screen feels like a SaaS
dashboard, you have gone wrong — add whitespace, soften the shadow, switch
a heading to Crimson Pro.

---

## Type decisions

| Situation | Face | Weight | Notes |
| --- | --- | --- | --- |
| Page headline, section title | Crimson Pro | 700–800 | `letter-spacing: -0.01em` |
| Card / panel title | Crimson Pro | 700 | 24–30px |
| Body, labels, nav, buttons | Inter | 400–600 | 14–16px, `line-height: 1.7` |
| Stat numerals, badges, splash | Outfit | 600–800 | accent only, never body |
| Book page body | Lora | 400 | 20px / 1.8, justified, drop cap |
| Drop cap | Playfair Display | 500 | `4.8em`, floated left |
| Eyebrow / micro-label | Inter | 500 | 12px, `letter-spacing: 0.35em`, uppercase |

Three rules that matter more than the table:

1. **Never set body copy in Crimson Pro.** It is a display face here.
2. **Never set a headline in Inter.** Inter is chrome; Crimson Pro is voice.
3. **Outfit is seasoning.** One or two elements per screen — a big number, a
   badge. A whole page in Outfit reads like a different product.

---

## Color decisions

- **Terracotta** — the only color a primary action is ever painted. One
  primary CTA per view.
- **Sage** — confirmations, checkmarks, "step 2" energy. Never a CTA.
- **Gold** — celebration and highlight: the featured pricing tier, a rating
  star, a success shimmer. Use it once per screen or it stops meaning anything.
- **Cream stack** — `cream` is the page, `cream-dark` is a sunk section,
  `cream-darker` is a hairline. White is only for cards, inputs, and the
  glass navbar.
- **Charcoal** — all body text. **Muted** — supporting copy and placeholders.
- **Red** — errors only. It is not in the palette for any other purpose.

Contrast floor: 4.5:1 for text. Terracotta on cream passes; terracotta on
gold does not — put white ink on terracotta instead.

---

## Component recipes

**Button** — always a full pill. `padding: 12px 24px` (md), Inter 600, hover
lifts `translateY(-2px)` and promotes the shadow one step. Primary is
terracotta/white; secondary is white/charcoal; outline is a 2px terracotta
ring. Disabled drops to `opacity: 0.6` and loses the lift.

**Card** — `border-radius: 32px`, `padding: 32px`, `--shadow-soft`, no border.
On hover, lift 8px and jump to `--shadow-large`. Never add a stroke to get
definition; raise the elevation instead.

**Input** — white, `border-radius: 12px`, floating label that shrinks to 12px
terracotta on focus. Focus ring is `0 0 0 2px var(--color-terracotta)`, never
a browser outline. Search fields are pills with a 18px stroke icon inset 18px
from the left.

**Badge / pill** — `border-radius: 9999px`. Soft variant is
`rgba(193,119,103,.1)` on terracotta text; solid variant is gold on charcoal.
Uppercase micro-badges get `letter-spacing: 0.08em` at 10–11px.

**Step pip** — 48px circle, one of the three `--gradient-badge-0*` values,
Crimson Pro 700 numeral in white.

**Image placeholder** — when real art is unavailable, use a 135° gradient
between two palette colors plus one or two `…` glyphs at 35–50% white. Do not
draw illustrations in SVG; they read as clip art against real storybook art.

---

## Layout

- Marketing content: `max-width: 1200px`, sections at `96px` vertical padding,
  alternating `cream` → `cream-dark` → `white`.
- Dashboard: 240px left rail, `32px 40px` content padding, 4-column masonry
  feed with `16px` gaps.
- Book viewer: 900×560 frame on a `#1a1612` ground, centred, nav arrows at the
  viewport edges.
- Lay out sibling groups with flex/grid + `gap`. Never space with margins on
  each child.

---

## Motion

Defaults that cover most cases:

```css
transition: transform .3s var(--ease-out), box-shadow .3s var(--ease-out);
```

- Entrances: 0.6–1s, `power3.out`, 0.15s stagger, come up 20–50px.
- Hover: 250–300ms, lift only, no color flashes.
- Page flip: 800ms, `var(--ease-page)` — the signature motion, don't retime it.
- Ambient float/pulse: 4–8s, infinite, subtle enough to be missed.

Anything faster than 180ms or bouncier than `back.out(1.7)` is off-brand.

---

## Writing

Second person, warm, a little poetic. Title Case headings, sentence case
helper copy, verb-phrase CTAs. Headlines run 3–5 words. Say *dream, craft,
unfold, journey, spark*; never say *generate, AI, prompt, output, render* —
the machinery stays offstage. No emoji, ever; the single ★ on the hero
rating stat is the only decorative glyph in the product.

---

## Checklist before shipping a screen

- [ ] One primary terracotta action, and only one
- [ ] Headings in Crimson Pro, body in Inter
- [ ] No pure white page background, no pure black text
- [ ] Every elevated surface uses a shadow, not a border
- [ ] Buttons are pills, cards are 32px radius
- [ ] Icons are stroke-only Heroicons Outline at 1.5–2px
- [ ] Gold appears at most once
- [ ] Copy uses the story vocabulary, not the machine vocabulary
- [ ] Hover states lift; nothing snaps
