# Asset Capture

The asset capture phase collects the source visuals that become the base scenes of the generated video.

## Goal

Capture clean, high-quality product screenshots or interface frames that can later be animated, highlighted, or zoomed.

## Tools

- Playwright for browser automation
- optional screenshot utilities for local UI capture
- product landing page or app state snapshots

## Typical outputs

- full-page screenshots
- hero section captures
- feature highlight frames
- UI detail captures for close-ups

## Best practices

- prefer high-resolution screenshots
- remove noisy browser chrome if needed
- ensure consistent viewport sizes for comparison shots
- capture multiple variant frames for motion and transition effects

## Understanding the platform before recording

[pipeline/first_render.py](../../pipeline/first_render.py) inspects the page before acting on it instead of guessing blindly:

- waits for `domcontentloaded`, then best-effort `networkidle` so animations/content have settled
- detects whether a login form is actually present (a password field) before attempting to fill or click anything
- if no login form is visible on the landing page, it tries clicking a 'Log in'/'Sign in' entry point (a modal trigger, or a link to a dedicated `/login` page) and re-checks — this also polls for the URL to change or a password field to appear, since client-rendered apps (Vue/Nuxt/Next, etc.) often lazy-load the login route's JS/CSS chunk after the click, so a single fixed wait can resolve before that request even starts
- if a login is requested but still no login form is found after that, the capture fails fast with a clear `CaptureError` instead of producing a bad screenshot

## Fully completing an action (e.g. login)

A login is only considered complete once it's verified, not just clicked:

- after submitting, the flow polls for the page URL changing or the password field disappearing
- common error banners (`[role='alert']`, `.error`, text like "invalid password") are checked first and raise a `LoginVerificationError` with the detected message
- if neither success nor a clear error shows up within the timeout, the capture fails fast rather than silently screenshotting whatever state the page is in

## Deciding what to record vs. not

- `--hide-selector` (repeatable) hides extra CSS selectors before the screenshot; common cookie/consent banners are hidden by default (disable with `--no-hide-overlays`)
- `--capture-selector` scopes the screenshot to one element/region instead of the full viewport, for a feature close-up rather than the whole page

## Determining clip duration

Instead of a fixed guess, the capture step counts the words in the captured region and estimates a reading-paced duration (`--words-per-second`, clamped between `--min-duration` and `--max-duration`). Pass `--duration` explicitly to override the estimate.

## Relationship to the rest of the pipeline

Captured assets feed into the animation stage, where they can be:

- zoomed and panned
- highlighted with overlays
- transformed with Ken Burns motion
- combined with animated title cards or graphic layers

## Related notes

- [[02 Architecture]]
- [[03 Workflow/02 Animation Engine]]
- [[04 Research/05 Playwright Notes]]
