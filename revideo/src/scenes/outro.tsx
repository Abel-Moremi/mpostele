import {Gradient, Img, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, Reference, ThreadGenerator, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

// Same fixed decorative underline width as title-reveal.tsx's emphasis word
// - see that file's own comment for why it's fixed rather than measured.
const EMPHASIS_UNDERLINE_WIDTH = 220;

// Top-margin band every scene's anchor lives in - see caption-overlay.tsx's
// module docstring for why. Distinct from `badge` below, which stays the
// CTA's own flex-centered, self-sized container - the anchor is a separate,
// purely decorative shape dedicated to transition continuity.
const ANCHOR_Y = -860;
const ANCHOR_X = 160;

export interface OutroProps {
	text: string;
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	logoSrc?: string;
	decorationSrc?: string;
	// Closing half of title-reveal.tsx's opening/closing "rhyme" - a plain
	// line (tagline) with its emphasized closing phrase (emphasisText) set
	// apart in the same italic gradient treatment, rendered below the CTA
	// pill rather than replacing it (that pill still carries the actual call
	// to action - text above). Both optional, independent of each other.
	tagline?: string;
	emphasisText?: string;
	secondaryColor?: string;
}

export interface OutroRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	logo: Reference<Img>;
	badge: Reference<Rect>;
	tagline: Reference<Txt>;
	emphasis: Reference<Txt>;
	emphasisUnderline: Reference<Rect>;
	decoration: Reference<Img>;
}

/** Builds the node tree at rest (hidden) - no animation. Returns refs for
 * play() and for the transitions.ts orchestration in video-project.ts. */
export function mountOutro(view: Layout, props: OutroProps): OutroRefs {
	const {
		text,
		backgroundColor,
		accentColor,
		textColor,
		fontFamily = 'sans-serif',
		logoSrc,
		decorationSrc,
		tagline,
		emphasisText,
		secondaryColor,
	} = props;
	const resolvedTextColor = textColor ?? getContrastColor(accentColor);
	const bodyTextColor = getContrastColor(backgroundColor);

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
	const logo = createRef<Img>();
	const badge = createRef<Rect>();
	const label = createRef<Txt>();
	const taglineRef = createRef<Txt>();
	const emphasis = createRef<Txt>();
	const emphasisUnderline = createRef<Rect>();
	const decoration = createRef<Img>();

	// Same two-tone-gradient-or-solid-fallback logic as title-reveal.tsx.
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
			gap={40}
			opacity={0}
		>
			{logoSrc && <Img ref={logo} src={logoSrc} width={96} opacity={0} />}
			<Rect ref={badge} fill={accentColor} radius={999} padding={[12, 24]} opacity={0} scale={1}>
				<Txt
					ref={label}
					text={text}
					fontFamily={fontFamily}
					fontWeight={600}
					fontSize={40}
					fill={resolvedTextColor}
					textAlign={'center'}
				/>
			</Rect>
			{tagline && (
				<Rect direction={'column'} alignItems={'center'} gap={16}>
					<Txt
						ref={taglineRef}
						text={tagline}
						fontFamily={fontFamily}
						fontWeight={700}
						fontSize={48}
						fill={bodyTextColor}
						textAlign={'center'}
						textWrap={true}
						width={780}
						opacity={0}
					/>
					{emphasisText && (
						<Rect direction={'column'} alignItems={'center'} gap={6}>
							<Txt
								ref={emphasis}
								text={emphasisText}
								fontFamily={fontFamily}
								fontStyle={'italic'}
								fontWeight={700}
								fontSize={52}
								fill={emphasisFill}
								textAlign={'center'}
								opacity={0}
								scale={0}
							/>
							<Rect ref={emphasisUnderline} width={EMPHASIS_UNDERLINE_WIDTH} height={6} radius={3} fill={emphasisFill} opacity={0} />
						</Rect>
					)}
				</Rect>
			)}
		</Rect>,
	);

	view.add(<Rect ref={anchor} width={64} height={8} radius={4} fill={accentColor} x={ANCHOR_X} y={ANCHOR_Y} opacity={0} />);

	if (decorationSrc) {
		view.add(
			<Img ref={decoration} src={decorationSrc} width={100} x={-540 + 48 + 50} y={960 - 48 - 50} opacity={0} />,
		);
	}

	return {root, anchor, logo, badge, tagline: taglineRef, emphasis, emphasisUnderline, decoration};
}

/** Entrance animation + hold. root/anchor visibility is owned by
 * transitions.ts, not here - this only animates this scene's own content. */
export function* playOutro(
	refs: OutroRefs,
	props: OutroProps,
	durationInFrames: number,
	fps: number,
	headSeconds: number,
	tailSeconds: number,
): ThreadGenerator {
	const {logoSrc, decorationSrc, tagline: taglineText, emphasisText} = props;
	const {logo, badge, tagline, emphasis, emphasisUnderline, decoration} = refs;

	yield* all(
		badge().opacity(1, 0.5),
		...(logoSrc ? [logo().opacity(1, 0.5)] : []),
		...(decorationSrc ? [decoration().opacity(1, 0.5)] : []),
	);
	yield* badge().scale(1.06, 0.3, easeOutBack).to(1, 0.3);

	let elapsedSeconds = 1.1;
	if (taglineText) {
		yield* tagline().opacity(1, 0.3);
		elapsedSeconds += 0.3;
		if (emphasisText) {
			yield* all(emphasis().opacity(1, 0.3), emphasis().scale(1, 0.4, easeOutBack));
			yield* emphasisUnderline().opacity(1, 0.25);
			elapsedSeconds += 0.4 + 0.25;
		}
	}

	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}
}
