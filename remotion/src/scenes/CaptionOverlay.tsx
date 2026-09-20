import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {getContrastColor} from '../color';

/**
 * Word-by-word caption reveal, timed by splitting the scene's own duration
 * evenly across the word count - no Whisper/audio transcription involved,
 * since script_text is already the canonical source (see
 * app/agents/composition_agent.py), not something to re-derive from audio.
 *
 * durationInFrames is passed explicitly rather than read from
 * useVideoConfig(): inside a <Series.Sequence>, useCurrentFrame() is
 * relative to the sequence but useVideoConfig().durationInFrames is still
 * the whole composition's length, not this scene's.
 */
export const CaptionOverlay: React.FC<{
	text: string;
	backgroundColor: string;
	durationInFrames: number;
	textColor?: string;
	fontFamily?: string;
}> = ({text, backgroundColor, durationInFrames, textColor, fontFamily = 'sans-serif'}) => {
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);
	const frame = useCurrentFrame();
	const words = text.split(/\s+/).filter(Boolean);

	const framesPerWord = durationInFrames / Math.max(words.length, 1);
	const visibleWords = Math.min(words.length, Math.floor(frame / framesPerWord) + 1);

	return (
		<AbsoluteFill
			style={{
				backgroundColor,
				alignItems: 'center',
				justifyContent: 'center',
				padding: '12%',
			}}
		>
			<div
				style={{
					fontFamily,
					fontWeight: 600,
					fontSize: 56,
					lineHeight: 1.7,
					color: resolvedTextColor,
					textAlign: 'center',
				}}
			>
				{words.slice(0, visibleWords).map((word, i) => {
					const wordStartFrame = i * framesPerWord;
					const opacity = interpolate(frame, [wordStartFrame, wordStartFrame + 6], [0, 1], {
						extrapolateLeft: 'clamp',
						extrapolateRight: 'clamp',
					});
					return (
						<span key={i} style={{opacity, marginRight: 12, display: 'inline-block'}}>
							{word}
						</span>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};
