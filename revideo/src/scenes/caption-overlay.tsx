import {Layout, Rect, Txt} from '@revideo/2d';
import {createRef, Reference, ThreadGenerator, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

// Top-margin band every scene's anchor lives in - fixed and independent of
// each scene's own flex-centered content, so a matchCut transition always
// knows exactly where to travel to/from without waiting on a layout pass.
// Centered x here, TitleReveal/Outro offset left/right (see those files) -
// small variety in the anchor's cut-to-cut motion.
const ANCHOR_Y = -860;
const ANCHOR_X = 0;

export interface CaptionOverlayProps {
	text: string;
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
}

export interface CaptionOverlayRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	caption: Reference<Txt>;
}

/** Builds the node tree at rest (hidden) - no animation. Returns refs for
 * play() and for the transitions.ts orchestration in video-project.ts. */
export function mountCaptionOverlay(view: Layout, props: CaptionOverlayProps): CaptionOverlayRefs {
	const {backgroundColor, accentColor, textColor, fontFamily = 'sans-serif'} = props;
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
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
			opacity={0}
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

	view.add(<Rect ref={anchor} width={64} height={8} radius={4} fill={accentColor} x={ANCHOR_X} y={ANCHOR_Y} opacity={0} />);

	return {root, anchor, caption};
}

/**
 * Progressive caption reveal, timed across the scene's own duration (minus
 * any transition tail reserved at the end) - no Whisper/audio transcription
 * involved, since this segment's text is already the canonical source (see
 * app/media/narration_engine.py's per-sentence split and
 * app/agents/composition_agent.py), not something to re-derive from audio.
 *
 * root/anchor visibility is owned by transitions.ts, not here - this only
 * animates this scene's own content (the text reveal itself doubles as its
 * entrance, same as it always has).
 *
 * Uses Txt's native text tweening (`txtRef().text("...", seconds)`, the same
 * mechanism Revideo's own bundled examples use) rather than fading in
 * individually-animated <span> words the way the old Remotion version did -
 * Revideo's Layout engine doesn't reflow independently-animated inline nodes
 * the same way, so one real Txt node with a tweened value is what keeps
 * textWrap wrapping correctly.
 */
export function* playCaptionOverlay(
	refs: CaptionOverlayRefs,
	props: CaptionOverlayProps,
	durationInFrames: number,
	fps: number,
	headSeconds: number,
	tailSeconds: number,
): ThreadGenerator {
	const {text} = props;
	const {caption} = refs;

	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;
	const revealSeconds = Math.min(totalSeconds, Math.max(totalSeconds - 0.3, totalSeconds * 0.85));

	yield* caption().text(text, revealSeconds);
	if (totalSeconds > revealSeconds) {
		yield* waitFor(totalSeconds - revealSeconds);
	}
}
