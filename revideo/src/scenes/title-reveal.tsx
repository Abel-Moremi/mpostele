import {Gradient, Img, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, Reference, ThreadGenerator, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

// Underline swoosh width/offset under the emphasis word - a fixed decorative
// size, not measured against the actual text width (Txt doesn't expose a
// synchronous measured width before layout runs), so emphasisText is capped
// short (composition_validator.py) precisely so this always reads as "under
// the word" rather than badly over/under-shooting it.
const EMPHASIS_UNDERLINE_WIDTH = 220;

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
	// The reference brand video's signature move: a short (1-3 word) closing
	// phrase set apart from the rest of the headline in an italic gradient
	// treatment with its own underline, reused identically by outro.tsx so
	// the video opens and closes on the same visual "rhyme". Both optional -
	// composition_agent.py supplies emphasisText only when its own prompt
	// produces one; secondaryColor only matters when it does.
	emphasisText?: string;
	secondaryColor?: string;
}

export interface TitleRevealRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	headline: Reference<Txt>;
	emphasis: Reference<Txt>;
	emphasisUnderline: Reference<Rect>;
	decoration: Reference<Img>;
}

/** Builds the node tree at rest (hidden) - no animation. Returns refs for
 * play() and for the transitions.ts orchestration in video-project.ts. */
export function mountTitleReveal(view: Layout, props: TitleRevealProps): TitleRevealRefs {
	const {text, backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', decorationSrc, emphasisText, secondaryColor} = props;
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
	const headline = createRef<Txt>();
	const emphasis = createRef<Txt>();
	const emphasisUnderline = createRef<Rect>();
	const decoration = createRef<Img>();

	// A true two-tone gradient when secondaryColor is available (brand's
	// gold, same as abstract-transition.tsx's orb), a solid accentColor
	// otherwise - either reads as "the one emphasized word", just with less
	// fidelity to the reference's peach-to-gold treatment on the fallback.
	const emphasisFill = secondaryColor
		? new Gradient({type: 'linear', fromX: -110, toX: 110, stops: [{offset: 0, color: accentColor}, {offset: 1, color: secondaryColor}]})
		: accentColor;

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
			gap={16}
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
			{emphasisText && (
				<Rect direction={'column'} alignItems={'center'} gap={6}>
					<Txt
						ref={emphasis}
						text={emphasisText}
						fontFamily={fontFamily}
						fontStyle={'italic'}
						fontWeight={700}
						fontSize={76}
						fill={emphasisFill}
						textAlign={'center'}
						opacity={0}
						scale={0}
					/>
					<Rect ref={emphasisUnderline} width={EMPHASIS_UNDERLINE_WIDTH} height={6} radius={3} fill={emphasisFill} opacity={0} />
				</Rect>
			)}
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

	return {root, anchor, headline, emphasis, emphasisUnderline, decoration};
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
	const {decorationSrc, emphasisText} = props;
	const {headline, emphasis, emphasisUnderline, decoration} = refs;

	yield* all(
		headline().opacity(1, 0.5),
		headline().scale(1, 0.6, easeOutBack),
		...(decorationSrc ? [decoration().opacity(1, 0.5)] : []),
	);

	let elapsedSeconds = 0.6;
	if (emphasisText) {
		yield* all(emphasis().opacity(1, 0.3), emphasis().scale(1, 0.4, easeOutBack));
		yield* emphasisUnderline().opacity(1, 0.25);
		elapsedSeconds += 0.4 + 0.25;
	}

	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}
}
