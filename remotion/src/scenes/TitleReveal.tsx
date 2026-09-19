import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export const TitleReveal: React.FC<{
	text: string;
	backgroundColor: string;
	accentColor: string;
}> = ({text, backgroundColor, accentColor}) => {
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
			<div style={{width: 64, height: 8, backgroundColor: accentColor, marginBottom: 32, opacity}} />
			<div
				style={{
					fontFamily: 'sans-serif',
					fontWeight: 800,
					fontSize: 72,
					lineHeight: 1.15,
					color: '#FFFFFF',
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
