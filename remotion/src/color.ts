/**
 * Deterministic text-contrast fallback - composition_agent/poster_layout_agent
 * invent backgroundColor/accentColor hex values with no darkness constraint,
 * and text color has always defaulted to a hardcoded white. On a light
 * background that's illegible. Rather than ask the LLM to reason about
 * contrast (the same class of thing it's unreliable at as SVG geometry or
 * exact hex picking), compute a safe default here - components still accept
 * an explicit color override (e.g. a real brand's exact charcoal) and only
 * fall back to this when one isn't given.
 */
export const getContrastColor = (backgroundColor: string): string => {
	const hex = backgroundColor.replace('#', '');
	if (hex.length !== 6) {
		return '#FFFFFF';
	}
	const r = parseInt(hex.slice(0, 2), 16);
	const g = parseInt(hex.slice(2, 4), 16);
	const b = parseInt(hex.slice(4, 6), 16);
	const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
	return luminance > 0.6 ? '#1A1A1A' : '#FFFFFF';
};
