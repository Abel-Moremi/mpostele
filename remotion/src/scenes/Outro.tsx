import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export const Outro: React.FC<{
	text: string;
	backgroundColor: string;
	accentColor: string;
	fontFamily?: string;
	logoSrc?: string;
}> = ({text, backgroundColor, accentColor, fontFamily = 'sans-serif', logoSrc}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	const opacity = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'});
	const pulse = spring({frame, fps, config: {damping: 10}, durationInFrames: 20});
	const badgeScale = 1 + pulse * 0.06;

	return (
		<AbsoluteFill
			style={{
				backgroundColor,
				alignItems: 'center',
				justifyContent: 'center',
				padding: '10%',
			}}
		>
			{logoSrc && <Img src={staticFile(logoSrc)} style={{width: 96, marginBottom: 40, opacity}} />}
			<div
				style={{
					padding: '12px 24px',
					borderRadius: 999,
					backgroundColor: accentColor,
					color: '#FFFFFF',
					fontFamily,
					fontWeight: 600,
					fontSize: 40,
					textAlign: 'center',
					opacity,
					transform: `scale(${badgeScale})`,
				}}
			>
				{text}
			</div>
		</AbsoluteFill>
	);
};
