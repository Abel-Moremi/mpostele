import {Layout, Rect, Txt} from '@revideo/2d';
import {createRef, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

export interface CaptionOverlayProps {
	text: string;
	backgroundColor: string;
	textColor?: string;
	fontFamily?: string;
}

/**
 * Progressive caption reveal, timed across the scene's own duration - no
 * Whisper/audio transcription involved, since script_text is already the
 * canonical source (see app/agents/composition_agent.py), not something to
 * re-derive from audio.
 *
 * The Remotion version faded in individual <span> words inside a wrapping
 * flex div. Revideo's Layout engine doesn't do CSS-style paragraph reflow of
 * independently-animated inline nodes, so this uses Txt's native text
 * tweening instead (the same mechanism Revideo's own bundled examples use,
 * e.g. `txtRef().text("...", 2)`) - one real Txt node, so textWrap wrapping
 * works correctly, with a smooth progressive reveal in its place.
 */
export function* captionOverlay(
	view: Layout,
	props: CaptionOverlayProps,
	durationInFrames: number,
	fps: number,
) {
	const {text, backgroundColor, textColor, fontFamily = 'sans-serif'} = props;
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);

	const root = createRef<Rect>();
	const caption = createRef<Txt>();

	view.add(
		<Rect
			ref={root}
			size={['100%', '100%']}
			fill={backgroundColor}
			layout
			direction={'column'}
			alignItems={'center'}
			justifyContent={'center'}
			padding={230}
		>
			<Txt
				ref={caption}
				text={''}
				fontFamily={fontFamily}
				fontWeight={600}
				fontSize={56}
				lineHeight={'170%'}
				fill={resolvedTextColor}
				textAlign={'center'}
				textWrap={true}
				width={780}
			/>
		</Rect>,
	);

	const totalSeconds = durationInFrames / fps;
	const revealSeconds = Math.min(totalSeconds, Math.max(totalSeconds - 0.3, totalSeconds * 0.85));

	yield* caption().text(text, revealSeconds);
	if (totalSeconds > revealSeconds) {
		yield* waitFor(totalSeconds - revealSeconds);
	}

	root().remove();
}
