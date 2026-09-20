import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';

/**
 * Static - rendered via `remotion still` (a single frame capture), so no
 * useCurrentFrame/interpolate/spring here, unlike the video scenes. Reuses
 * TitleReveal/Outro's visual language (accent bar + headline, CTA badge)
 * combined into one frame instead of sequenced. Headline/CTA follow
 * remotion/public/design/design.md's type table: Crimson Pro for the
 * headline, Inter 600 for the CTA button text - pass headlineFontFamily/
 * ctaFontFamily explicitly per brand; a future, differently-branded job can
 * leave them at the generic sans-serif default.
 */
export const Poster: React.FC<{
	headline: string;
	ctaText: string;
	backgroundColor: string;
	accentColor: string;
	headlineColor?: string;
	headlineFontFamily?: string;
	ctaFontFamily?: string;
	logoSrc?: string;
}> = ({
	headline,
	ctaText,
	backgroundColor,
	accentColor,
	headlineColor = '#FFFFFF',
	headlineFontFamily = 'sans-serif',
	ctaFontFamily = 'sans-serif',
	logoSrc,
}) => {
	return (
		<AbsoluteFill
			style={{
				backgroundColor,
				alignItems: 'center',
				justifyContent: 'center',
				padding: '10%',
			}}
		>
			{logoSrc && <Img src={staticFile(logoSrc)} style={{width: 140, marginBottom: 48}} />}
			<div style={{width: 96, height: 10, backgroundColor: accentColor, marginBottom: 40}} />
			<div
				style={{
					fontFamily: headlineFontFamily,
					fontWeight: 800,
					fontSize: 84,
					lineHeight: 1.15,
					letterSpacing: '-0.01em',
					color: headlineColor,
					textAlign: 'center',
					marginBottom: 80,
				}}
			>
				{headline}
			</div>
			<div
				style={{
					padding: '12px 24px',
					borderRadius: 999,
					backgroundColor: accentColor,
					color: '#FFFFFF',
					fontFamily: ctaFontFamily,
					fontWeight: 600,
					fontSize: 44,
					textAlign: 'center',
				}}
			>
				{ctaText}
			</div>
		</AbsoluteFill>
	);
};
