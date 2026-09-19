import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export const Outro: React.FC<{
	text: string;
	backgroundColor: string;
	accentColor: string;
}> = ({text, backgroundColor, accentColor}) => {
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
			<div
				style={{
					padding: '20px 40px',
					borderRadius: 999,
					backgroundColor: accentColor,
					color: '#FFFFFF',
					fontFamily: 'sans-serif',
					fontWeight: 700,
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
