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
