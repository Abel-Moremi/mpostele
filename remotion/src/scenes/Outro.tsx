import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {getContrastColor} from '../color';

export const Outro: React.FC<{
	text: string;
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	logoSrc?: string;
	decorationSrc?: string;
}> = ({text, backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', logoSrc, decorationSrc}) => {
	const resolvedTextColor = textColor ?? getContrastColor(accentColor);
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
			{decorationSrc && (
				<Img
					src={staticFile(decorationSrc)}
					style={{position: 'absolute', bottom: 48, left: 48, width: 100, opacity}}
				/>
			)}
			{logoSrc && <Img src={staticFile(logoSrc)} style={{width: 96, marginBottom: 40, opacity}} />}
			<div
				style={{
					padding: '12px 24px',
					borderRadius: 999,
					backgroundColor: accentColor,
					color: resolvedTextColor,
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
