import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {getContrastColor} from '../color';

export const TitleReveal: React.FC<{
	text: string;
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	decorationSrc?: string;
}> = ({text, backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', decorationSrc}) => {
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	// Every value here is a pure function of frame index, never wall-clock
	// time - required for deterministic headless-Chromium rendering.
	const scale = spring({frame, fps, config: {damping: 12}});
	const opacity = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'});

	return (
		<AbsoluteFill
			style={{
				backgroundColor,
				alignItems: 'center',
				justifyContent: 'center',
				padding: '10%',
			}}
		>
			{decorationSrc && (
				<Img
					src={staticFile(decorationSrc)}
					style={{position: 'absolute', top: 48, right: 48, width: 120, opacity}}
				/>
			)}
			<div style={{width: 64, height: 8, backgroundColor: accentColor, marginBottom: 32, opacity}} />
			<div
				style={{
					fontFamily,
					fontWeight: 800,
					fontSize: 72,
					lineHeight: 1.15,
					letterSpacing: '-0.01em',
					color: resolvedTextColor,
					textAlign: 'center',
					opacity,
					transform: `scale(${scale})`,
				}}
			>
				{text}
			</div>
		</AbsoluteFill>
	);
};
