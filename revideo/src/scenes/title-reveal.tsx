import {Img, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, Reference, ThreadGenerator, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

// Top-margin band every scene's anchor lives in - see caption-overlay.tsx's
// module docstring for why this is a fixed, layout-independent slot rather
// than wherever each scene's own flex content happens to place an accent.
const ANCHOR_Y = -860;
const ANCHOR_X = -160;

export interface TitleRevealProps {
	text: string;
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	decorationSrc?: string;
}

export interface TitleRevealRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	headline: Reference<Txt>;
	decoration: Reference<Img>;
}

/** Builds the node tree at rest (hidden) - no animation. Returns refs for
 * play() and for the transitions.ts orchestration in video-project.ts. */
export function mountTitleReveal(view: Layout, props: TitleRevealProps): TitleRevealRefs {
	const {text, backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', decorationSrc} = props;
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
	const headline = createRef<Txt>();
	const decoration = createRef<Img>();

	view.add(
		<Rect
			ref={root}
			size={['100%', '100%']}
			fill={backgroundColor}
			layout
			direction={'column'}
			alignItems={'center'}
			justifyContent={'center'}
			padding={108}
			opacity={0}
		>
			<Txt
				ref={headline}
				text={text}
				fontFamily={fontFamily}
				fontWeight={800}
				fontSize={72}
				lineHeight={'115%'}
				letterSpacing={-0.72}
				fill={resolvedTextColor}
				textAlign={'center'}
				textWrap={true}
				width={860}
				opacity={0}
				scale={0}
			/>
		</Rect>,
	);

	// Anchor lives outside root's flex layout, directly on view, so its
	// position/size are known exactly at mount time - see transitions.ts's
	// matchCut, which reads these before any animation runs.
	view.add(<Rect ref={anchor} width={64} height={8} radius={4} fill={accentColor} x={ANCHOR_X} y={ANCHOR_Y} opacity={0} />);

	if (decorationSrc) {
		view.add(
			<Img ref={decoration} src={decorationSrc} width={120} x={540 - 48 - 60} y={-960 + 48 + 60} opacity={0} />,
		);
	}

	return {root, anchor, headline, decoration};
}

/** Entrance animation + hold. root/anchor visibility is owned by
 * transitions.ts, not here - this only animates this scene's own content. */
export function* playTitleReveal(
	refs: TitleRevealRefs,
	props: TitleRevealProps,
	durationInFrames: number,
	fps: number,
	headSeconds: number,
	tailSeconds: number,
): ThreadGenerator {
	const {decorationSrc} = props;
	const {headline, decoration} = refs;

	yield* all(
		headline().opacity(1, 0.5),
		headline().scale(1, 0.6, easeOutBack),
		...(decorationSrc ? [decoration().opacity(1, 0.5)] : []),
	);

	const elapsedSeconds = 0.6;
	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}
}
