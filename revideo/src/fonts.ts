/**
 * Brand fonts per public/design/design.md's type table - Crimson Pro for
 * headlines, Inter for body/labels/buttons. Self-hosted via @fontsource
 * (see global.css) rather than a Google Fonts CDN fetch at render time.
 * Scene components take an optional fontFamily prop (falling back to a
 * generic sans-serif) so a future, differently-branded job isn't forced
 * into these - only pass these exports when rendering for this brand.
 */
export const HEADLINE_FONT = 'Crimson Pro';
export const BODY_FONT = 'Inter';
